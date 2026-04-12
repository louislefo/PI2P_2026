import os
import json
from datetime import datetime

CONFIG_PATH = os.environ.get("CONFIG_PATH", "../config/settings.json")
HISTORY_PATH = os.environ.get("HISTORY_PATH", "../config/history.json")

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print("Erreur de config:", e)
        return {
            "camera_source": 0,
            "door_relay_pin": 17,
            "door_sensor_pin": 27,
            "authorized_plates": [],
            "yolo_model_path": "yolov8n.pt"
        }

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=4)
        return True
    except Exception as e:
        print("Erreur sauvegarde config:", e)
        return False

def load_history():
    try:
        with open(HISTORY_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []

def add_history(plate, status="Autorisé"):
    hist = load_history()
    entry = {"plate": plate, "time": datetime.now().isoformat(), "status": status}
    hist.insert(0, entry)
    
    # Garder seulement les 50 derniers passages pour éviter un fichier trop gros
    if len(hist) > 50:
        hist = hist[:50]
        
    try:
        with open(HISTORY_PATH, "w") as f:
            json.dump(hist, f, indent=4)
    except Exception as e:
        print("Erreur sauvegarde historique:", e)
        
    return entry
