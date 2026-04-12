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
            state = {
                "door_open": bool(relay.value),
                "car_present": bool(door_sensor.is_pressed)
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
        relay.on()
        await asyncio.sleep(5)
        relay.off()
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
        relay.on()
        await asyncio.sleep(5)
        relay.off()
    return {"status": "success", "message": "Door opened manually"}

@router.delete("/api/history/{log_id}")
async def delete_history_endpoint(log_id: int):
    if delete_history(log_id):
        await broadcast_history()
        return {"status": "success", "message": "Log deleted"}
    return {"status": "error", "message": "Failed to delete log"}
