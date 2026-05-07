"""
hardware-bridge/app.py
----------------------
Micro-service FastAPI qui tourne sur la Raspberry Pi dans Docker.
Expose une API REST pour contrôler :
  - LEDs (verte BCM27, orange BCM17, rouge BCM22)
  - Servomoteur (BCM12 / PWM0)
  - Audio jack (aplay)

Port : 8083

Logique servo :
  - angle 0   = FERMÉ (barrière en bas)
  - angle 90  = OUVERT (barrière levée)
  - Après positionnement → détachement du signal PWM (servo.value = None)
    pour éviter le jitter (tremblement) en position maintenue.
"""

import os
import sys
import math
import struct
import wave
import tempfile
import subprocess
import threading
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="PI2P Hardware Bridge", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── GPIO Setup ────────────────────────────────────────────────────────────────

PIN_LED_GREEN  = int(os.environ.get("PIN_LED_GREEN",  "27"))  # Board 13
PIN_LED_ORANGE = int(os.environ.get("PIN_LED_ORANGE", "17"))  # Board 11
PIN_LED_RED    = int(os.environ.get("PIN_LED_RED",    "22"))  # Board 15
PIN_SERVO      = int(os.environ.get("PIN_SERVO",      "12"))  # Board 32 / PWM0

# Délai avant détachement du servo (ms) → stoppe le jitter
SERVO_DETACH_DELAY = float(os.environ.get("SERVO_DETACH_DELAY_S", "0.6"))

print("=" * 55)
print("🚀 [HW-BRIDGE] Démarrage Hardware Bridge v1.1")
print(f"   LED Verte  → BCM{PIN_LED_GREEN}  (Board 13)")
print(f"   LED Orange → BCM{PIN_LED_ORANGE}  (Board 11)")
print(f"   LED Rouge  → BCM{PIN_LED_RED}  (Board 15)")
print(f"   Servo      → BCM{PIN_SERVO}  (Board 32 / PWM0)")
print(f"   Détachement servo après {SERVO_DETACH_DELAY}s")
print("=" * 55)

try:
    if sys.platform == "win32":
        raise ImportError("Windows détecté → Mock GPIO activé")
    from gpiozero import LED, Servo
    from gpiozero.pins.lgpio import LGPIOFactory
    factory = LGPIOFactory()

    led_green  = LED(PIN_LED_GREEN,  pin_factory=factory)
    led_orange = LED(PIN_LED_ORANGE, pin_factory=factory)
    led_red    = LED(PIN_LED_RED,    pin_factory=factory)

    # min_pulse_width=0.5ms, max_pulse_width=2.5ms → plage classique SG90
    servo = Servo(
        PIN_SERVO,
        pin_factory=factory,
        min_pulse_width=0.5 / 1000,
        max_pulse_width=2.5 / 1000,
    )
    GPIO_AVAILABLE = True
    print(f"✅ [HW-BRIDGE] GPIO lgpio initialisé avec succès")

except Exception as e:
    print(f"⚠️ [HW-BRIDGE] GPIO indisponible : {e}")
    print("⚠️ [HW-BRIDGE] Mode MOCK activé — les commandes seront simulées")
    GPIO_AVAILABLE = False

    class MockLED:
        def __init__(self, pin):
            self.pin = pin
            self.is_active = False
        def on(self):
            self.is_active = True
            print(f"   🟢 [MOCK] LED pin BCM{self.pin} → ON")
        def off(self):
            self.is_active = False
            print(f"   ⚫ [MOCK] LED pin BCM{self.pin} → OFF")

    class MockServo:
        def __init__(self, pin):
            self.pin = pin
            self._value = None
        @property
        def value(self):
            return self._value
        @value.setter
        def value(self, val):
            self._value = val
            if val is None:
                print(f"   🔧 [MOCK] Servo BCM{self.pin} → DÉTACHÉ (anti-jitter)")
            else:
                print(f"   🔧 [MOCK] Servo BCM{self.pin} → value={val:.3f}")

    led_green  = MockLED(PIN_LED_GREEN)
    led_orange = MockLED(PIN_LED_ORANGE)
    led_red    = MockLED(PIN_LED_RED)
    servo      = MockServo(PIN_SERVO)

_leds = {
    "green":  led_green,
    "orange": led_orange,
    "red":    led_red,
}

# ── État interne ──────────────────────────────────────────────────────────────

_servo_angle   = 0       # 0 = fermé, 90 = ouvert, etc.
_servo_lock    = threading.Lock()
_auto_close_timer = None

# ── Helpers servo ─────────────────────────────────────────────────────────────

def _angle_to_servo_value(angle: int) -> float:
    """
    Convertit un angle (0-180°) en valeur gpiozero (-1.0 à +1.0).

    Convention physique de la barrière :
      angle 0   → servo.value = +1.0  → position FERMÉE
      angle 90  → servo.value =  0.0  → position OUVERTE (90°)
      angle 180 → servo.value = -1.0  → position extrême inverse

    La direction est INVERSÉE par rapport à la formule naïve car
    le servo est monté de façon à ce que +1 corresponde à "barrière fermée".
    """
    # Formule inversée : 0° → +1.0, 180° → -1.0
    return 1.0 - (angle / 90.0)

def _move_servo(angle: int):
    """
    Envoie la commande au servo puis détache le signal après SERVO_DETACH_DELAY
    pour éliminer le jitter (tremblement en position maintenue).
    """
    global _servo_angle
    angle = max(0, min(180, angle))
    value = _angle_to_servo_value(angle)

    print(f"🔧 [SERVO] Déplacement → {angle}° (raw_value={value:+.3f})")

    with _servo_lock:
        try:
            servo.value = value
        except Exception as e:
            print(f"❌ [SERVO] Erreur lors du déplacement : {e}")
            return

    _servo_angle = angle

    # Détachement différé pour stopper le jitter
    def _detach():
        time.sleep(SERVO_DETACH_DELAY)
        with _servo_lock:
            try:
                servo.value = None
                print(f"🔇 [SERVO] Signal PWM détaché (anti-jitter) — position maintenue à {angle}°")
            except Exception as e:
                print(f"⚠️ [SERVO] Erreur détachement : {e}")

    threading.Thread(target=_detach, daemon=True).start()

# ── Initialisation : servo en position FERMÉE au démarrage ───────────────────

print("🔧 [SERVO] Initialisation → position FERMÉE (0°)")
_move_servo(0)

# ── Audio ─────────────────────────────────────────────────────────────────────

def _generate_beep_wav(freq: int = 880, duration: float = 0.5, volume: float = 0.7) -> str:
    """Génère un fichier WAV temporaire avec un bip sinusoïdal pur."""
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
    """Joue un bip via aplay (ALSA — sortie jack 3.5mm)."""
    wav_path = None
    try:
        wav_path = _generate_beep_wav(freq, duration)
        print(f"🔊 [AUDIO] Lecture bip {freq}Hz pendant {duration}s via aplay...")
        result = subprocess.run(
            ["aplay", "-D", "plughw:0,0", wav_path],
            timeout=duration + 2,
            capture_output=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="ignore")
            print(f"⚠️ [AUDIO] plughw:0,0 échoué ({stderr.strip()}) → fallback aplay par défaut")
            subprocess.run(["aplay", wav_path], timeout=duration + 2, capture_output=True)
        else:
            print(f"✅ [AUDIO] Bip {freq}Hz joué avec succès")
    except FileNotFoundError:
        print("❌ [AUDIO] aplay introuvable — ALSA non installé ou non accessible dans le conteneur")
    except subprocess.TimeoutExpired:
        print(f"⚠️ [AUDIO] Timeout lors de la lecture ({freq}Hz)")
    except Exception as e:
        print(f"❌ [AUDIO] Erreur inattendue : {e}")
    finally:
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)

# ── Endpoints API ─────────────────────────────────────────────────────────────

@app.get("/status")
def get_status():
    """Retourne l'état actuel de tous les composants hardware."""
    def led_state(led):
        return bool(led.is_active) if hasattr(led, "is_active") else False

    status = {
        "gpio_available": GPIO_AVAILABLE,
        "leds": {
            "green":  led_state(led_green),
            "orange": led_state(led_orange),
            "red":    led_state(led_red),
        },
        "servo": {
            "angle":       _servo_angle,
            "is_open":     _servo_angle >= 45,
            "is_closed":   _servo_angle < 45,
            "pwm_attached": getattr(servo, "value", None) is not None,
        },
    }
    return status

@app.post("/led/{color}/{state}")
def control_led(color: str, state: str):
    """
    Contrôle une LED.
      color : green | orange | red
      state : on | off | toggle
    """
    if color not in _leds:
        raise HTTPException(400, f"Couleur inconnue: '{color}'. Valeurs acceptées: green, orange, red")

    led = _leds[color]

    if state == "on":
        led.on()
    elif state == "off":
        led.off()
    elif state == "toggle":
        if hasattr(led, "is_active") and led.is_active:
            led.off()
        else:
            led.on()
    else:
        raise HTTPException(400, f"État inconnu: '{state}'. Valeurs acceptées: on, off, toggle")

    is_on = bool(led.is_active) if hasattr(led, "is_active") else False
    print(f"💡 [LED] {color.upper()} → {'ON  ✅' if is_on else 'OFF ⚫'}")
    return {"led": color, "state": "on" if is_on else "off"}

@app.post("/servo/{angle}")
def control_servo(angle: int, auto_close: bool = False, delay: int = 5):
    """
    Positionne le servo.
      angle     : 0 (FERMÉ) à 180°
      auto_close: si True, referme automatiquement après `delay` secondes
    """
    global _auto_close_timer

    _move_servo(angle)
    label = "FERMÉ" if angle < 45 else "OUVERT" if angle >= 45 else f"{angle}°"
    print(f"🚧 [SERVO] Position → {angle}° [{label}]")

    if auto_close and angle >= 45:
        if _auto_close_timer:
            _auto_close_timer.cancel()
            print(f"⏰ [SERVO] Ancien timer d'auto-fermeture annulé")

        def _auto_close_fn():
            print(f"⏰ [SERVO] Auto-fermeture déclenchée après {delay}s")
            _move_servo(0)

        _auto_close_timer = threading.Timer(delay, _auto_close_fn)
        _auto_close_timer.start()
        print(f"⏰ [SERVO] Auto-fermeture programmée dans {delay}s")

    return {
        "angle": angle,
        "raw_value": round(_angle_to_servo_value(angle), 3),
        "is_open": angle >= 45,
        "auto_close": auto_close,
        "auto_close_delay": delay if auto_close else None,
    }

class AudioRequest(BaseModel):
    freq: int = 880
    duration: float = 0.5
    pattern: str = "single"  # single | double | triple | success | error

@app.post("/audio/test")
def play_audio(req: AudioRequest):
    """Joue un son de test via le jack 3.5mm du Pi."""
    patterns = {
        "single":  [(req.freq, 0.4)],
        "double":  [(req.freq, 0.2), (req.freq, 0.2)],
        "triple":  [(req.freq, 0.15), (req.freq, 0.15), (req.freq, 0.15)],
        "success": [(523, 0.15), (659, 0.15), (784, 0.3)],
        "error":   [(300, 0.3), (200, 0.4)],
    }

    sequence = patterns.get(req.pattern, patterns["single"])
    print(f"🔊 [AUDIO] Pattern '{req.pattern}' → {len(sequence)} bip(s)")

    def _play_seq():
        for i, (freq, dur) in enumerate(sequence):
            print(f"   🎵 [AUDIO] Bip {i+1}/{len(sequence)} : {freq}Hz × {dur}s")
            _play_audio(freq, dur)
            if i < len(sequence) - 1:
                time.sleep(0.08)

    threading.Thread(target=_play_seq, daemon=True).start()
    return {"status": "playing", "pattern": req.pattern, "sequence": sequence}

@app.get("/health")
def health():
    return {"status": "OK", "gpio": GPIO_AVAILABLE, "servo_angle": _servo_angle}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
