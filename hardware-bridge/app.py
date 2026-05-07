"""
hardware-bridge/app.py
----------------------
Micro-service FastAPI qui tourne sur la Raspberry Pi dans Docker.
Expose une API REST + WebSocket pour contrôler :
  - LEDs (verte BCM27, orange BCM17, rouge BCM22)
  - Servomoteur (BCM12 / PWM0) — ferme=0°, ouvre=90°
  - Audio jack (aplay) — bips de test
  - Bouton d'appel (BCM26) — interphone
  - WebSocket /ws/call  → événements d'appel en temps réel
  - WebSocket /ws/audio → flux audio PCM du PC vers le jack Pi

Port : 8083
"""

import os
import sys
import math
import struct
import wave
import tempfile
import subprocess
import threading
import asyncio
import time
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Set

app = FastAPI(title="PI2P Hardware Bridge", version="1.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pins ──────────────────────────────────────────────────────────────────────

PIN_LED_GREEN  = int(os.environ.get("PIN_LED_GREEN",  "27"))  # Board 13
PIN_LED_ORANGE = int(os.environ.get("PIN_LED_ORANGE", "17"))  # Board 11
PIN_LED_RED    = int(os.environ.get("PIN_LED_RED",    "22"))  # Board 15
PIN_SERVO      = int(os.environ.get("PIN_SERVO",      "12"))  # Board 32 / PWM0
PIN_BUTTON     = int(os.environ.get("PIN_BUTTON",     "26"))  # Board 37

SERVO_DETACH_DELAY = float(os.environ.get("SERVO_DETACH_DELAY_S", "0.6"))

print("=" * 60)
print("🚀 [HW-BRIDGE] Démarrage Hardware Bridge v1.2")
print(f"   LED Verte  → BCM{PIN_LED_GREEN}  (Board 13)")
print(f"   LED Orange → BCM{PIN_LED_ORANGE}  (Board 11)")
print(f"   LED Rouge  → BCM{PIN_LED_RED}  (Board 15)")
print(f"   Servo      → BCM{PIN_SERVO}  (Board 32 / PWM0)")
print(f"   Bouton     → BCM{PIN_BUTTON}  (Board 37)")
print("=" * 60)

# ── GPIO Setup ────────────────────────────────────────────────────────────────

# Référence à la boucle asyncio principale (définie au startup)
_main_loop: asyncio.AbstractEventLoop | None = None

try:
    if sys.platform == "win32":
        raise ImportError("Windows détecté → Mock GPIO activé")
    from gpiozero import LED, Servo, Button
    from gpiozero.pins.lgpio import LGPIOFactory
    factory = LGPIOFactory()

    led_green  = LED(PIN_LED_GREEN,  pin_factory=factory)
    led_orange = LED(PIN_LED_ORANGE, pin_factory=factory)
    led_red    = LED(PIN_LED_RED,    pin_factory=factory)
    servo = Servo(
        PIN_SERVO,
        pin_factory=factory,
        min_pulse_width=0.5 / 1000,
        max_pulse_width=2.5 / 1000,
    )
    call_button = Button(PIN_BUTTON, pull_up=True, bounce_time=0.05, pin_factory=factory)
    GPIO_AVAILABLE = True
    print(f"✅ [HW-BRIDGE] GPIO lgpio initialisé avec succès")

except Exception as e:
    print(f"⚠️ [HW-BRIDGE] GPIO indisponible : {e}")
    print("⚠️ [HW-BRIDGE] Mode MOCK activé")
    GPIO_AVAILABLE = False

    class MockLED:
        def __init__(self, pin):
            self.pin = pin
            self.is_active = False
        def on(self):
            self.is_active = True
            print(f"   🟢 [MOCK] LED BCM{self.pin} → ON")
        def off(self):
            self.is_active = False
            print(f"   ⚫ [MOCK] LED BCM{self.pin} → OFF")

    class MockServo:
        def __init__(self, pin):
            self.pin = pin
            self._value = None
        @property
        def value(self): return self._value
        @value.setter
        def value(self, val):
            self._value = val
            label = "DÉTACHÉ" if val is None else f"value={val:+.3f}"
            print(f"   🔧 [MOCK] Servo BCM{self.pin} → {label}")

    class MockButton:
        def __init__(self, pin, **kwargs):
            self.pin = pin
            self.when_pressed = None
            print(f"   🔘 [MOCK] Bouton BCM{self.pin} configuré")

    led_green  = MockLED(PIN_LED_GREEN)
    led_orange = MockLED(PIN_LED_ORANGE)
    led_red    = MockLED(PIN_LED_RED)
    servo      = MockServo(PIN_SERVO)
    call_button = MockButton(PIN_BUTTON)

_leds = {"green": led_green, "orange": led_orange, "red": led_red}

# ── État interne ──────────────────────────────────────────────────────────────

_servo_angle    = 0
_servo_lock     = threading.Lock()
_auto_close_timer = None

# ── WebSocket Call Manager ────────────────────────────────────────────────────

class CallManager:
    """Gère les connexions WebSocket pour les événements d'appel."""

    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self.call_active = False

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        print(f"📡 [CALL-WS] Client connecté — total: {len(self._clients)}")
        # Envoyer l'état actuel immédiatement
        await ws.send_json({"event": "status", "call_active": self.call_active})

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._clients.discard(ws)
        print(f"📴 [CALL-WS] Client déconnecté — total: {len(self._clients)}")

    async def broadcast(self, payload: dict):
        dead = set()
        async with self._lock:
            clients = set(self._clients)
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        if dead:
            async with self._lock:
                self._clients -= dead

    def trigger_call(self):
        """Appelé depuis le thread gpiozero (non-async) quand le bouton est pressé."""
        if _main_loop is None:
            print("⚠️ [CALL] Boucle asyncio non prête, événement ignoré")
            return
        self.call_active = True
        print("🔔 [CALL] Bouton pressé → Appel entrant !")
        asyncio.run_coroutine_threadsafe(
            self.broadcast({"event": "incoming_call", "call_active": True}),
            _main_loop,
        )

    def end_call(self):
        self.call_active = False
        if _main_loop:
            asyncio.run_coroutine_threadsafe(
                self.broadcast({"event": "call_ended", "call_active": False}),
                _main_loop,
            )

call_manager = CallManager()

# Branchement du bouton
call_button.when_pressed = call_manager.trigger_call

# ── Helpers servo ─────────────────────────────────────────────────────────────

def _angle_to_servo_value(angle: int) -> float:
    """
    Convertit angle (0-180°) en valeur gpiozero (-1.0 à +1.0).

    Comportement PHYSIQUE observé sur ce montage :
      value =  0.0 → impulsion 1.5ms → bras BAS   = FERMÉ
      value = -1.0 → impulsion 0.5ms → bras HAUT  = OUVERT
      value = +1.0 → impulsion 2.5ms → bras bas++ (dépasse le fermé)

    Donc :
      angle=  0 → value =  0.0 → FERMÉ  (bras bas)
      angle= 90 → value = -1.0 → OUVERT (bras levé)
      angle=180 → value = -1.0 → (clamped, même que 90° = ouvert max)
    """
    raw = -(angle / 90.0)
    return max(-1.0, min(1.0, raw))

def _move_servo(angle: int):
    global _servo_angle
    angle = max(0, min(180, angle))
    value = _angle_to_servo_value(angle)
    label = "FERMÉ" if angle < 45 else "OUVERT"
    print(f"🔧 [SERVO] Déplacement → {angle}° [{label}] (raw={value:+.3f})")
    with _servo_lock:
        try:
            servo.value = value
        except Exception as e:
            print(f"❌ [SERVO] Erreur : {e}")
            return
    _servo_angle = angle

    def _detach():
        time.sleep(SERVO_DETACH_DELAY)
        with _servo_lock:
            try:
                servo.value = None
                print(f"🔇 [SERVO] PWM détaché — position maintenue à {angle}°")
            except Exception: pass

    threading.Thread(target=_detach, daemon=True).start()

# ── Audio ─────────────────────────────────────────────────────────────────────

def _generate_beep_wav(freq: int = 880, duration: float = 0.5, volume: float = 0.7) -> str:
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = b""
        for i in range(n_samples):
            sample = int(volume * 32767 * math.sin(2 * math.pi * freq * i / sample_rate))
            data += struct.pack("<h", sample)
        wf.writeframes(data)
    return tmp.name

def _play_audio(freq: int = 880, duration: float = 0.5):
    wav_path = None
    try:
        wav_path = _generate_beep_wav(freq, duration)
        print(f"🔊 [AUDIO] Bip {freq}Hz × {duration}s...")
        result = subprocess.run(
            ["aplay", "-D", "plughw:0,0", wav_path],
            timeout=duration + 2, capture_output=True
        )
        if result.returncode != 0:
            subprocess.run(["aplay", wav_path], timeout=duration + 2, capture_output=True)
        print(f"✅ [AUDIO] Bip terminé")
    except FileNotFoundError:
        print("❌ [AUDIO] aplay introuvable")
    except Exception as e:
        print(f"❌ [AUDIO] Erreur : {e}")
    finally:
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global _main_loop
    _main_loop = asyncio.get_event_loop()
    print("✅ [HW-BRIDGE] Boucle asyncio capturée")
    print("🔧 [SERVO] Initialisation → position FERMÉE (0°)")
    _move_servo(0)

# ── WebSocket : Événements d'appel ────────────────────────────────────────────

@app.websocket("/ws/call")
async def ws_call(ws: WebSocket):
    """
    WebSocket pour les événements d'appel temps-réel.
    Messages reçus :
      {"action": "hangup"}  → fin d'appel
      {"action": "test"}    → simule un appel (pour test)
    Messages envoyés :
      {"event": "incoming_call", "call_active": true}
      {"event": "call_ended",    "call_active": false}
      {"event": "status",        "call_active": bool}
    """
    await call_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")
            if action == "hangup":
                print("📴 [CALL] Raccrochage depuis le frontend")
                call_manager.end_call()
            elif action == "test":
                print("🧪 [CALL] Simulation d'appel (test frontend)")
                call_manager.trigger_call()
    except WebSocketDisconnect:
        pass
    finally:
        await call_manager.disconnect(ws)

# ── WebSocket : Flux audio PC → Jack Pi ──────────────────────────────────────

@app.websocket("/ws/audio")
async def ws_audio(ws: WebSocket):
    """
    Reçoit des chunks audio PCM bruts (Int16, mono, 16000Hz) depuis le
    navigateur PC et les joue en temps réel sur le jack 3.5mm du Pi via aplay.

    Format attendu : Int16 Little-Endian, 1 canal, 16000 Hz
    """
    await ws.accept()
    print("🎙️ [AUDIO-WS] Connexion audio reçue — démarrage aplay stdin...")

    proc = None
    try:
        proc = subprocess.Popen(
            ["aplay", "-f", "S16_LE", "-r", "16000", "-c", "1", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("✅ [AUDIO-WS] aplay démarré — audio en cours...")

        while True:
            # Recevoir les données binaires PCM du navigateur
            data = await ws.receive_bytes()
            if proc.poll() is not None:
                print("⚠️ [AUDIO-WS] aplay s'est arrêté, relancement...")
                proc = subprocess.Popen(
                    ["aplay", "-f", "S16_LE", "-r", "16000", "-c", "1", "-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            try:
                proc.stdin.write(data)
                proc.stdin.flush()
            except BrokenPipeError:
                print("⚠️ [AUDIO-WS] Pipe cassé")
                break

    except WebSocketDisconnect:
        print("📴 [AUDIO-WS] Client déconnecté")
    except FileNotFoundError:
        print("❌ [AUDIO-WS] aplay introuvable dans le conteneur")
        await ws.send_text("ERROR: aplay not found")
    except Exception as e:
        print(f"❌ [AUDIO-WS] Erreur : {e}")
    finally:
        if proc and proc.poll() is None:
            proc.stdin.close()
            proc.terminate()
            print("🛑 [AUDIO-WS] aplay arrêté proprement")

# ── Endpoints REST ────────────────────────────────────────────────────────────

@app.get("/status")
def get_status():
    def led_state(led): return bool(led.is_active) if hasattr(led, "is_active") else False
    return {
        "gpio_available": GPIO_AVAILABLE,
        "leds": {
            "green":  led_state(led_green),
            "orange": led_state(led_orange),
            "red":    led_state(led_red),
        },
        "servo": {
            "angle":     _servo_angle,
            "is_open":   _servo_angle >= 45,
            "is_closed": _servo_angle < 45,
        },
        "call": {
            "active":          call_manager.call_active,
            "connected_clients": 0,  # Pas accessible depuis sync
        },
    }

@app.post("/led/{color}/{state}")
def control_led(color: str, state: str):
    if color not in _leds:
        raise HTTPException(400, f"Couleur inconnue: '{color}'")
    led = _leds[color]
    if state == "on":       led.on()
    elif state == "off":    led.off()
    elif state == "toggle":
        (led.off if (hasattr(led, "is_active") and led.is_active) else led.on)()
    else:
        raise HTTPException(400, f"État inconnu: '{state}'")
    is_on = bool(led.is_active) if hasattr(led, "is_active") else False
    print(f"💡 [LED] {color.upper()} → {'ON  ✅' if is_on else 'OFF ⚫'}")
    return {"led": color, "state": "on" if is_on else "off"}

@app.post("/servo/{angle}")
def control_servo(angle: int, auto_close: bool = False, delay: int = 5):
    global _auto_close_timer
    _move_servo(angle)
    if auto_close and angle >= 45:
        if _auto_close_timer:
            _auto_close_timer.cancel()
        def _ac():
            print(f"⏰ [SERVO] Auto-fermeture après {delay}s")
            _move_servo(0)
        _auto_close_timer = threading.Timer(delay, _ac)
        _auto_close_timer.start()
        print(f"⏰ [SERVO] Auto-fermeture dans {delay}s")
    return {
        "angle": angle,
        "raw_value": round(_angle_to_servo_value(angle), 3),
        "is_open": angle >= 45,
        "auto_close": auto_close,
    }
class AudioRequest(BaseModel):
    freq: int = 880
    duration: float = 0.5
    pattern: str = "single"

@app.post("/audio/test")
def play_audio(req: AudioRequest):
    patterns = {
        "single":  [(req.freq, 0.4)],
        "double":  [(req.freq, 0.2), (req.freq, 0.2)],
        "triple":  [(req.freq, 0.15), (req.freq, 0.15), (req.freq, 0.15)],
        "success": [(523, 0.15), (659, 0.15), (784, 0.3)],
        "error":   [(300, 0.3), (200, 0.4)],
    }
    sequence = patterns.get(req.pattern, patterns["single"])
    print(f"🔊 [AUDIO] Pattern '{req.pattern}' → {len(sequence)} bip(s)")
    def _play():
        for i, (f, d) in enumerate(sequence):
            _play_audio(f, d)
            if i < len(sequence) - 1: time.sleep(0.08)
    threading.Thread(target=_play, daemon=True).start()
    return {"status": "playing", "pattern": req.pattern}

@app.get("/health")
def health():
    return {"status": "OK", "gpio": GPIO_AVAILABLE, "servo_angle": _servo_angle}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
