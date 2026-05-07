from fastapi import APIRouter, WebSocket
import asyncio
from pydantic import BaseModel
from typing import Optional
from core.hardware import relay, door_sensor
from core.config import load_history, add_history, delete_history, load_config

router = APIRouter(tags=["System"])

clients = []

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
            # Récupérer l'état réel depuis le Raspberry Pi
            import requests
            try:
                # Requête asynchrone / courte pour ne pas bloquer trop longtemps
                resp = await asyncio.to_thread(requests.get, "http://192.168.137.94:8083/status", timeout=0.5)
                hw_state = resp.json()
                door_open = hw_state.get("servo", {}).get("is_open", False)
            except Exception:
                door_open = False
                
            from services.vision import processor
            state = {
                "door_open": door_open,
                "car_present": False,
                "tested_cars": processor.tested_cars_count
            }
            await websocket.send_json({"type": "status", "data": state})
    except Exception:
        if websocket in clients:
            clients.remove(websocket)

async def broadcast_history():
    hist = load_history()
    for ws in clients:
        try:
            await ws.send_json({"type": "history", "data": hist})
        except Exception:
            pass

@router.get("/api/history")
def get_history_endpoint():
    return load_history()

class AccessRequest(BaseModel):
    plate: str
    image_filename: Optional[str] = None

@router.post("/api/system/access")
async def trigger_access(req: AccessRequest):
    # L'IA a détecté une plaque autorisée
    add_history(req.plate, "Autorisé (IA)", req.image_filename)
    await broadcast_history()
    
    cfg = load_config()
    if cfg.get("gate_mode", "auto") == "auto":
        import requests
        try:
            delay = cfg.get("gate_open_time", 5)
            requests.post(f"http://192.168.137.94:8083/servo/90?auto_close=true&delay={delay}", timeout=2)
            print(f"✅ [SYSTEM] Barrière ouverte via Hardware Bridge (IA) - {delay}s")
        except Exception as e:
            print(f"❌ [SYSTEM] Erreur ouverture barrière: {e}")
    return {"status": "success"}

@router.post("/door/open")
async def open_door():
    cfg = load_config()
    if cfg.get("gate_mode", "auto") == "always_closed":
        # Bloquage forcé, on ignore l'ordre d'ouverture
        add_history("MANUEL", "Refusé (Bloqué)")
        await broadcast_history()
        return {"status": "error", "message": "Gate is permanently closed"}

    add_history("MANUEL", "Autorisé (Bouton)")
    await broadcast_history()
    
    if cfg.get("gate_mode", "auto") == "auto":
        import requests
        try:
            delay = cfg.get("gate_open_time", 5)
            requests.post(f"http://192.168.137.94:8083/servo/90?auto_close=true&delay={delay}", timeout=2)
            print(f"✅ [SYSTEM] Barrière ouverte via Hardware Bridge (Manuel) - {delay}s")
        except Exception as e:
            print(f"❌ [SYSTEM] Erreur ouverture barrière: {e}")
    return {"status": "success", "message": "Door opened manually"}

@router.delete("/api/history/{log_id}")
async def delete_history_endpoint(log_id: int):
    if delete_history(log_id):
        await broadcast_history()
        return {"status": "success", "message": "Log deleted"}
    return {"status": "error", "message": "Failed to delete log"}
