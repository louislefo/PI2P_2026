import sys
from core.config import load_config

# Import sécurisé pour contrer le bug Windows (BadPinFactory)
try:
    if sys.platform == "win32":
        raise ImportError("Environnement Windows détecté: Forcer le Mock GPIO.")
        
    from gpiozero import OutputDevice, Button
    GPIO_AVAILABLE = True
    print("✅ [HARDWARE] GPIO Natif Initialisé.")
except (ImportError, Exception) as e:
    print(f"⚠️ [HARDWARE] {e}")
    print("⚠️ [HARDWARE] Activation du MOCK GPIO de développement.")
    GPIO_AVAILABLE = False
    
    class OutputDevice:
        def __init__(self, pin):
            self.pin = pin
            self.value = 0
            print(f"   ⚙️ [MOCK] OutputDevice configuré -> Pin {pin}")
        def on(self): 
            self.value = 1
            print(f"   🔋 [MOCK] Pin {self.pin} -> ALLUMÉ")
        def off(self): 
            self.value = 0
            print(f"   🪫 [MOCK] Pin {self.pin} -> ÉTEINT")

    class Button:
        def __init__(self, pin):
            self.pin = pin
            self.is_pressed = False
            print(f"   ⚙️ [MOCK] Button configuré -> Pin {pin}")

config = load_config()

# Instanciation Globale
relay = OutputDevice(config.get("door_relay_pin", 17))
door_sensor = Button(config.get("door_sensor_pin", 27))
