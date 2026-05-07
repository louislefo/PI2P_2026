"""
hardware-bridge/app.py
----------------------
Micro-service FastAPI qui tourne sur la Raspberry Pi dans Docker.
Expose une API REST pour contrôler :
  - LEDs (verte BCM27, orange BCM17, rouge BCM22)
  - Servomoteur (BCM12 / PWM0)
  - Audio jack (aplay)

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
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="PI2P Hardware Bridge", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── GPIO Setup ───────────────────────────────────────────────────────────────

# Pins BCM
PIN_LED_GREEN  = int(os.environ.get("PIN_LED_GREEN",  "27"))  # Board 13
PIN_LED_ORANGE = int(os.environ.get("PIN_LED_ORANGE", "17"))  # Board 11
PIN_LED_RED    = int(os.environ.get("PIN_LED_RED",    "22"))  # Board 15
PIN_SERVO      = int(os.environ.get("PIN_SERVO",      "12"))  # Board 32 / PWM0

try:
    if sys.platform == "win32":
        raise ImportError("Windows détecté → Mock GPIO")
    from gpiozero import LED, Servo
    from gpiozero.pins.lgpio import LGPIOFactory
    factory = LGPIOFactory()
    
    led_green  = LED(PIN_LED_GREEN,  pin_factory=factory)
    led_orange = LED(PIN_LED_ORANGE, pin_factory=factory)
    led_red    = LED(PIN_LED_RED,    pin_factory=factory)
    # Servo gpiozero : value -1 (0°) à +1 (180°), 0 = 90°
    servo = Servo(PIN_SERVO, pin_factory=factory, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)
    GPIO_AVAILABLE = True
    print(f"✅ [HW-BRIDGE] GPIO initialisé (lgpio) — LEDs: {PIN_LED_GREEN}/{PIN_LED_ORANGE}/{PIN_LED_RED}, Servo: {PIN_SERVO}")

except Exception as e:
    print(f"⚠️ [HW-BRIDGE] {e} → Mock GPIO activé")
    GPIO_AVAILABLE = False

    class MockLED:
        def __init__(self, pin): 
            self.pin = pin
            self.is_active = False
        def on(self):  
            self.is_active = True
            print(f"   🟢 [MOCK] LED pin {self.pin} → ON")
        def off(self): 
            self.is_active = False
            print(f"   ⚫ [MOCK] LED pin {self.pin} → OFF")

    class MockServo:
        def __init__(self, pin): 
            self.pin = pin
            self.value = 0.0  # -1 à +1
        def __setattr__(self, name, val):
            object.__setattr__(self, name, val)
            if name == "value" and hasattr(self, "pin"):
                print(f"   🔧 [MOCK] Servo pin {self.pin} → value={val:.2f}")

    led_green  = MockLED(PIN_LED_GREEN)
    led_orange = MockLED(PIN_LED_ORANGE)
    led_red    = MockLED(PIN_LED_RED)
    servo      = MockServo(PIN_SERVO)

_leds = {
    "green":  led_green,
    "orange": led_orange,
    "red":    led_red,
}

# ── État interne ─────────────────────────────────────────────────────────────

_servo_angle = 0  # 0-180
_auto_close_timer = None

# ── Audio ────────────────────────────────────────────────────────────────────

def _generate_beep_wav(freq: int = 880, duration: float = 0.5, volume: float = 0.7) -> str:
    """Génère un fichier WAV temporaire avec un bip pur."""
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
    """Joue un bip via aplay (ALSA — jack Pi)."""
    wav_path = None
    try:
        wav_path = _generate_beep_wav(freq, duration)
        # Force la sortie sur le jack 3.5mm (card 0, device 0)
        result = subprocess.run(
            ["aplay", "-D", "plughw:0,0", wav_path],
            timeout=duration + 2,
            capture_output=True
        )
        if result.returncode != 0:
            # Fallback sans spécifier le device
            subprocess.run(["aplay", wav_path], timeout=duration + 2, capture_output=True)
        print(f"🔊 [HW-BRIDGE] Bip joué ({freq}Hz, {duration}s)")
    except FileNotFoundError:
        print("⚠️ [HW-BRIDGE] aplay introuvable (ALSA non disponible)")
    except Exception as e:
        print(f"⚠️ [HW-BRIDGE] Erreur audio: {e}")
    finally:
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/status")
def get_status():
    """Retourne l'état de tous les composants hardware."""
    def led_state(led):
        return led.is_active if hasattr(led, "is_active") else False
    
    return {
        "gpio_available": GPIO_AVAILABLE,
        "leds": {
            "green":  led_state(led_green),
            "orange": led_state(led_orange),
            "red":    led_state(led_red),
        },
        "servo": {
            "angle": _servo_angle,
            "value": getattr(servo, "value", 0),
        }
    }

@app.post("/led/{color}/{state}")
def control_led(color: str, state: str):
    """
    Allume ou éteint une LED.
    color: green | orange | red
    state: on | off | toggle
    """
    if color not in _leds:
        raise HTTPException(status_code=400, detail=f"Couleur inconnue: {color}. Valeurs: green, orange, red")
    
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
        raise HTTPException(status_code=400, detail=f"État inconnu: {state}. Valeurs: on, off, toggle")
    
    is_on = led.is_active if hasattr(led, "is_active") else False
    print(f"💡 [HW-BRIDGE] LED {color} → {'ON' if is_on else 'OFF'}")
    return {"led": color, "state": "on" if is_on else "off"}

@app.post("/servo/{angle}")
def control_servo(angle: int, auto_close: bool = False, delay: int = 3):
    """
    Positionne le servo à l'angle donné (0-180 degrés).
    Si auto_close=true, ferme après `delay` secondes.
    """
    global _servo_angle, _auto_close_timer
    
    angle = max(0, min(180, angle))
    # gpiozero Servo : -1 = min (0°), 0 = milieu (90°), +1 = max (180°)
    servo_value = (angle / 90.0) - 1.0
    
    try:
        servo.value = servo_value
    except Exception as e:
        print(f"⚠️ [HW-BRIDGE] Erreur servo: {e}")
    
    _servo_angle = angle
    print(f"🔧 [HW-BRIDGE] Servo → {angle}° (value={servo_value:.2f})")
    
    # Auto-fermeture
    if auto_close and angle > 0:
        if _auto_close_timer:
            _auto_close_timer.cancel()
        def close():
            global _servo_angle
            try:
                servo.value = -1.0
                _servo_angle = 0
                print("🔧 [HW-BRIDGE] Servo → Fermeture automatique")
            except Exception: pass
        _auto_close_timer = threading.Timer(delay, close)
        _auto_close_timer.start()
    
    return {"angle": angle, "value": round(servo_value, 3), "auto_close": auto_close}

class AudioRequest(BaseModel):
    freq: int = 880
    duration: float = 0.5
    pattern: str = "single"  # single | double | triple | success | error

@app.post("/audio/test")
def play_audio(req: AudioRequest):
    """Joue un son de test sur le jack 3.5mm du Pi."""
    patterns = {
        "single":  [(req.freq, 0.4)],
        "double":  [(req.freq, 0.2), (req.freq, 0.2)],
        "triple":  [(req.freq, 0.15), (req.freq, 0.15), (req.freq, 0.15)],
        "success": [(523, 0.15), (659, 0.15), (784, 0.3)],
        "error":   [(300, 0.3), (200, 0.4)],
    }
    
    sequence = patterns.get(req.pattern, patterns["single"])
    
    def play_sequence():
        for freq, dur in sequence:
            _play_audio(freq, dur)
            time.sleep(0.05)  # Petit gap entre les bips
    
    threading.Thread(target=play_sequence, daemon=True).start()
    return {"status": "playing", "pattern": req.pattern, "sequence_length": len(sequence)}

@app.get("/health")
def health():
    return {"status": "OK", "gpio": GPIO_AVAILABLE}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
