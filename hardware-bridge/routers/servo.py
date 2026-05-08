from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.hardware import move_servo, get_leds, is_gpio_available, get_servo_angle, set_leds_state, _angle_to_servo_value, toggle_emergency_stop, get_emergency_stop
from core.audio import play_pattern

router = APIRouter(tags=["Hardware"])

@router.get("/status")
def get_status():
    leds = get_leds()
    def led_state(led): return bool(led.is_active) if hasattr(led, "is_active") else False
    angle = get_servo_angle()
    return {
        "gpio_available": is_gpio_available(),
        "leds": {
            "green":  led_state(leds["green"]),
            "orange": led_state(leds["orange"]),
            "red":    led_state(leds["red"]),
        },
        "servo": {
            "angle":     angle,
            "is_open":   angle >= 45,
            "is_closed": angle < 45,
        },
        "emergency_stop": get_emergency_stop()
    }

@router.post("/led/{color}/{state}")
def control_led(color: str, state: str):
    leds = get_leds()
    if color not in leds:
        raise HTTPException(400, f"Couleur inconnue: '{color}'")
        
    # Si on contrôle manuellement une LED, on désactive la gestion mutuellement exclusive pour cette action, 
    # ou on utilise set_leds_state si on veut forcer l'exclusivité. 
    # Pour garder la flexibilité, on contrôle juste l'objet gpiozero.
    led = leds[color]
    if state == "on":       led.on()
    elif state == "off":    led.off()
    elif state == "toggle":
        (led.off if (hasattr(led, "is_active") and led.is_active) else led.on)()
    else:
        raise HTTPException(400, f"État inconnu: '{state}'")
        
    is_on = bool(led.is_active) if hasattr(led, "is_active") else False
    print(f"💡 [LED] {color.upper()} → {'ON  ✅' if is_on else 'OFF ⚫'}")
    return {"led": color, "state": "on" if is_on else "off"}

@router.post("/servo/{angle}")
def control_servo(angle: int, auto_close: bool = False, delay: int = 5):
    if get_emergency_stop():
        raise HTTPException(status_code=403, detail="Arrêt d'urgence activé, mouvement bloqué.")
    move_servo(angle, auto_close, delay)
    return {
        "angle": angle,
        "raw_value": round(_angle_to_servo_value(angle), 3),
        "is_open": angle >= 45,
        "auto_close": auto_close,
        "delay": delay
    }

@router.post("/servo/emergency/toggle")
def toggle_emergency():
    state = toggle_emergency_stop()
    return {"status": "success", "emergency_stop": state}

class AudioRequest(BaseModel):
    freq: int = 880
    duration: float = 0.5
    pattern: str = "single"

@router.post("/audio/test")
def play_audio_endpoint(req: AudioRequest):
    play_pattern(req.pattern, req.freq)
    return {"status": "playing", "pattern": req.pattern}

@router.get("/health")
def health():
    return {"status": "OK", "gpio": is_gpio_available(), "servo_angle": get_servo_angle()}
