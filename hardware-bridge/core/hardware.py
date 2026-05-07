import os
import sys
import threading
import time

PIN_LED_GREEN  = int(os.environ.get("PIN_LED_GREEN",  "27"))  # Board 13
PIN_LED_ORANGE = int(os.environ.get("PIN_LED_ORANGE", "17"))  # Board 11
PIN_LED_RED    = int(os.environ.get("PIN_LED_RED",    "22"))  # Board 15
PIN_SERVO      = int(os.environ.get("PIN_SERVO",      "12"))  # Board 32 / PWM0
PIN_BUTTON     = int(os.environ.get("PIN_BUTTON",     "26"))  # Board 37

SERVO_DETACH_DELAY = float(os.environ.get("SERVO_DETACH_DELAY_S", "0.6"))

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
    print(f"✅ [HW-CORE] GPIO lgpio initialisé avec succès")

except Exception as e:
    print(f"⚠️ [HW-CORE] GPIO indisponible : {e}")
    print("⚠️ [HW-CORE] Mode MOCK activé")
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

leds = {"green": led_green, "orange": led_orange, "red": led_red}

_servo_angle = 0
_servo_lock = threading.Lock()
_auto_close_timer = None
_orange_led_timer = None

def _angle_to_servo_value(angle: int) -> float:
    raw = -(angle / 90.0)
    return max(-1.0, min(1.0, raw))

def get_servo_angle():
    return _servo_angle

def is_gpio_available():
    return GPIO_AVAILABLE

def get_leds():
    return leds

def set_leds_state(green=False, orange=False, red=False):
    """Gère l'état mutuellement exclusif ou non des LEDs."""
    if green: led_green.on()
    else: led_green.off()
        
    if orange: led_orange.on()
    else: led_orange.off()
        
    if red: led_red.on()
    else: led_red.off()

def move_servo(angle: int, auto_close: bool = False, delay: int = 5):
    global _servo_angle, _auto_close_timer, _orange_led_timer
    
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
    
    # Logique des LEDs
    if angle >= 45:
        # Barrière ouverte -> LED Verte
        set_leds_state(green=True)
    else:
        # Barrière fermée -> LED Rouge
        set_leds_state(red=True)

    def _detach():
        time.sleep(SERVO_DETACH_DELAY)
        with _servo_lock:
            try:
                servo.value = None
            except Exception: pass

    threading.Thread(target=_detach, daemon=True).start()

    # Logique d'auto-fermeture
    if _auto_close_timer:
        _auto_close_timer.cancel()
    if _orange_led_timer:
        _orange_led_timer.cancel()

    if auto_close and angle >= 45:
        # Programmation de la LED Orange 1 seconde avant la fermeture
        orange_delay = max(0.1, delay - 1.0)
        
        def _set_orange():
            print("⏰ [SERVO] Pré-fermeture (LED Orange)")
            set_leds_state(orange=True)
            
        def _ac():
            print(f"⏰ [SERVO] Auto-fermeture après {delay}s")
            move_servo(0)
            
        _orange_led_timer = threading.Timer(orange_delay, _set_orange)
        _auto_close_timer = threading.Timer(delay, _ac)
        
        _orange_led_timer.start()
        _auto_close_timer.start()
        print(f"⏰ [SERVO] Auto-fermeture dans {delay}s (Orange dans {orange_delay}s)")

# Initialisation au démarrage
set_leds_state(red=True)
