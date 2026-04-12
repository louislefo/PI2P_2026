from fastapi import APIRouter, WebSocket
import asyncio
from pydantic import BaseModel
from core.hardware import relay, door_sensor
from core.config import load_history, add_history

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

@router.post("/api/system/access")
async def trigger_access(req: AccessRequest):
    # L'IA a détecté une plaque autorisée
    add_history(req.plate, "Autorisé (IA)")
    await broadcast_history()
    
    relay.on()
    await asyncio.sleep(5)
    relay.off()
    return {"status": "success"}

@router.post("/door/open")
async def open_door():
    add_history("MANUEL", "Autorisé (Bouton)")
    await broadcast_history()
    
    relay.on()
    await asyncio.sleep(5)
    relay.off()
    return {"status": "success", "message": "Door opened manually"}
