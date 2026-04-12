Architecture Portail Automatique (Docker + React + FastAPI)Cette version utilise une séparation stricte entre le traitement d'image, le contrôle matériel et l'interface utilisateur.  
1. Stack TechniqueIA : 
   - YOLOv8 Nano (exporté en format ONNX pour le Pi 4).
   - Backend : FastAPI (Asynchrone, idéal pour le streaming vidéo).
   - Frontend : React + Tailwind CSS + Lucide Icons (Interface moderne).
   - Conteneurisation : Docker + Docker Compose.
   - Communication : WebSockets pour les alertes de plaques en temps réel.2. Structure du Projet/portail-project  

```
├── docker-compose.yml
├── config/
│   └── settings.json        # Pins GPIO et plaques autorisées
├── backend/
│   ├── Dockerfile
│   ├── main.py              # API et Logique
│   ├── processor.py         # Thread IA
│   └── requirements.txt
└── frontend/
    ├── Dockerfile
    └── App.jsx              # Application React (Dashboard)
```

1. Déploiement Docker Composeversion: '3.8'
```docker-compose
services:
  api:
    build: ./backend
    privileged: true
    volumes:
      - ./config:/app/config
      - /dev:/dev
    ports:
      - "8000:8000"
    restart: always

  dashboard:
    build: ./frontend
    ports:
      - "80:80"
    environment:
      - VITE_API_URL=http://[IP_DU_PI]:8000
    restart: always
```

1. Optimisation Pi 4
   - Mémoire : On utilise zram sur le Pi pour augmenter virtuellement la RAM.
   - CPU : L'inférence IA est limitée à 2-3 FPS pour la détection de plaques, ce qui suffit largement pour un portail et évite la surchauffe.
   - GPU : Utilisation de v4l2 pour l'accès direct à la caméra.


### Backend : FastAPI + YOLOv8 Nano + ONNX + WebSockets   
exemple :

```python
import cv2
import json
import asyncio
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
from gpiozero import OutputDevice
import threading
import time

app = FastAPI()

# 1. Chargement de la Configuration Dynamique
try:
    with open('/app/config/settings.json', 'r') as f:
        config = json.load(f)
except Exception:
    config = {
        "pins": {"motor_open": 17, "motor_close": 27},
        "authorized_plates": ["AA-123-BB"]
    }

# 2. Initialisation GPIO
# Note: Sur PC, gpiozero peut utiliser un mock si les pins ne sont pas trouvées
motor_open = OutputDevice(config['pins']['motor_open'])
motor_close = OutputDevice(config['pins']['motor_close'])

# 3. Initialisation IA (YOLOv8)
# Utiliser .onnx pour de meilleures performances sur Pi 4
model = YOLO('yolov8n.pt') 

# 4. Global State
camera = cv2.VideoCapture(0)
last_detected_plate = None

def alpr_worker():
    """ Thread séparé pour ne pas bloquer le flux vidéo principal """
    global last_detected_plate
    while True:
        success, frame = camera.read()
        if not success:
            time.sleep(1)
            continue
        
        # Inférence légère (on resize l'image pour aller plus vite)
        # On ne traite qu'une frame sur 10 pour économiser le CPU
        results = model(frame, imgsz=320, conf=0.6, verbose=False)
        
        for r in results:
            # Ici on filtre les classes (la classe 'license plate' dépend de ton modèle)
            # Si détection, on déclenche l'ouverture
            pass
        
        time.sleep(0.1)

# Lancement du worker IA
threading.Thread(target=alpr_worker, daemon=True).start()

# 5. Endpoints API
@app.get("/video_feed")
async def video_feed():
    def gen_frames():
        while True:
            success, frame = camera.read()
            if not success:
                break
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.post("/gate/{action}")
async def control_gate(action: str):
    if action == "open":
        motor_close.off()
        motor_open.on()
        return {"status": "opening"}
    elif action == "close":
        motor_open.off()
        motor_close.on()
        return {"status": "closing"}
    elif action == "stop":
        motor_open.off()
        motor_close.off()
        return {"status": "stopped"}
    else:
        raise HTTPException(status_code=400, detail="Action invalide")

@app.get("/status")
async def get_status():
    return {
        "motor_open": motor_open.value,
        "motor_close": motor_close.value,
        "config": config
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```