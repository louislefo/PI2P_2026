import os
import json
from datetime import datetime
import sqlite3

def _resolve_path(env_var, docker_path, local_path):
    """Résout le chemin : variable d'env > chemin Docker > chemin dev local."""
    env_val = os.environ.get(env_var)
    if env_val:
        return env_val
    if os.path.exists(docker_path) or os.path.exists(os.path.dirname(docker_path)):
        return docker_path
    return local_path

CONFIG_PATH = _resolve_path("CONFIG_PATH", "config/settings.json", "../config/settings.json")
DB_PATH = _resolve_path("DB_PATH", "data/pi2p.db", "data/pi2p.db")

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Historique
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT,
            time TEXT,
            status TEXT,
            image_filename TEXT
        )
    ''')
    
    # Plaques Autorisées
    c.execute('''
        CREATE TABLE IF NOT EXISTS authorized_plates (
            plate TEXT PRIMARY KEY,
            owner_name TEXT,
            email TEXT,
            created_at TEXT,
            valid_until TEXT
        )
    ''')
    conn.commit()
    
    # Migration des plaques depuis le JSON s'il y en a et que la table est vide
    c.execute('SELECT COUNT(*) FROM authorized_plates')
    if c.fetchone()[0] == 0:
        cfg = load_config()
        old_plates = cfg.get("authorized_plates", [])
        for p in old_plates:
            c.execute('INSERT OR IGNORE INTO authorized_plates (plate, created_at) VALUES (?, ?)', (p, datetime.now().isoformat()))
        conn.commit()
        
    conn.close()

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
            # Ajout des valeurs par défaut si elles sont manquantes dans le JSON
            if "entry_code" not in cfg: cfg["entry_code"] = "0000#"
            if "gate_mode" not in cfg: cfg["gate_mode"] = "auto"
            if "detection_objects" not in cfg: cfg["detection_objects"] = ["car"]
            return cfg
    except Exception as e:
        print("Erreur de config:", e)
        return {
            "camera_source": 0,
            "door_relay_pin": 17,
            "door_sensor_pin": 27,
            "yolo_model_path": "yolov8n.pt",
            "confidence_threshold": 0.5,
            "entry_code": "0000#",
            "gate_mode": "auto",
            "detection_objects": ["car"]
        }

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=4)
        return True
    except Exception as e:
        print("Erreur sauvegarde config:", e)
        return False

def load_history(limit=50):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT id, plate, time, status, image_filename FROM history ORDER BY time DESC LIMIT ?', (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print("Erreur chargement SQLite:", e)
        return []

def add_history(plate, status="Autorisé", image_filename=None):
    time_str = datetime.now().isoformat()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO history (plate, time, status, image_filename)
            VALUES (?, ?, ?, ?)
        ''', (plate, time_str, status, image_filename))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Erreur sauvegarde SQLite:", e)
        
    return {"plate": plate, "time": time_str, "status": status, "image_filename": image_filename}

def delete_history(log_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 1. Récupérer le nom de l'image avant de supprimer le record
        c.execute('SELECT image_filename FROM history WHERE id = ?', (log_id,))
        row = c.fetchone()
        
        if row and row[0]:
            img_path = os.path.join("data/historique_voiture_entree", row[0])
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                    print(f"🗑️ [FILE] Image supprimée : {row[0]}")
                except Exception as fe:
                    print(f"⚠️ [FILE] Impossible de supprimer {row[0]}: {fe}")

        # 2. Supprimer de la DB
        c.execute('DELETE FROM history WHERE id = ?', (log_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Erreur delete_history SQLite:", e)
        return False

# ----- Gestion des Plaques en Base de Données -----

def get_authorized_plates():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT plate, owner_name, email, created_at, valid_until FROM authorized_plates')
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print("Erreur get_authorized_plates SQLite:", e)
        return []

def add_plate_to_db(plate, owner_name=None, email=None, valid_until=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        created_at = datetime.now().isoformat()
        c.execute('''
            INSERT OR REPLACE INTO authorized_plates (plate, owner_name, email, created_at, valid_until)
            VALUES (?, ?, ?, ?, ?)
        ''', (plate.upper().strip(), owner_name, email, created_at, valid_until))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Erreur add_plate_to_db SQLite:", e)
        return False

def delete_plate_from_db(plate):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM authorized_plates WHERE plate = ?', (plate.upper().strip(),))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Erreur delete_plate_from_db SQLite:", e)
        return False

# Initialiser la DB au premier chargement global (après les définitions)
init_db()
