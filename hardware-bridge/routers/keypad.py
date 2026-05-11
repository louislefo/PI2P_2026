import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
from core.hardware import scan_keypad, move_servo
from core.audio import play_pattern

router = APIRouter(tags=["Keypad"])

class KeypadManager:
    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self.entry_code = "0000#"
        self.current_buffer = ""
        self._last_key = None
        self._running = False

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        print(f"📡 [KEYPAD-WS] Client connecté — total: {len(self._clients)}")

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._clients.discard(ws)
        print(f"📴 [KEYPAD-WS] Client déconnecté — total: {len(self._clients)}")

    async def broadcast(self, payload: dict):
        dead = set()
        async with self._lock:
            clients = set(self._clients)
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        if dead:
            async with self._lock:
                self._clients -= dead

    def set_code(self, code: str):
        self.entry_code = code
        print(f"🔐 [KEYPAD] Code d'entrée mis à jour : {code}")

    async def run_scanner(self):
        self._running = True
        print("⌨️ [KEYPAD] Démarrage du scanner...")
        while self._running:
            key = scan_keypad()
            
            if key and key != self._last_key:
                # Nouvelle touche pressée
                print(f"⌨️ [KEYPAD] Touche détectée : {key}")
                self.current_buffer += key
                
                # Broadcast pour le mode Test
                await self.broadcast({"event": "key_press", "key": key, "buffer": self.current_buffer})
                
                # Validation du code
                if self.current_buffer.endswith(self.entry_code):
                    print("🔓 [KEYPAD] Code CORRECT !")
                    play_pattern("success")
                    move_servo(90, auto_close=True, delay=5)
                    self.current_buffer = ""
                elif len(self.current_buffer) > 20: # Sécurité pour ne pas saturer le buffer
                    self.current_buffer = ""
                elif key == "#": # Reset buffer sur # si le code ne match pas
                    # On garde le # dans le buffer pour le test au dessus, 
                    # mais si on arrive ici c'est que ça n'a pas matché
                    self.current_buffer = ""
                    play_pattern("error")
                
                self._last_key = key
            elif not key:
                self._last_key = None
                
            await asyncio.sleep(0.1)

keypad_manager = KeypadManager()

@router.websocket("/ws/keypad")
async def ws_keypad(ws: WebSocket):
    await keypad_manager.connect(ws)
    try:
        while True:
            await ws.receive_text() # Garde la connexion ouverte
    except WebSocketDisconnect:
        pass
    finally:
        await keypad_manager.disconnect(ws)

@router.post("/config/code")
async def update_keypad_code(data: dict):
    code = data.get("code")
    if code:
        keypad_manager.set_code(code)
        return {"status": "success", "code": code}
    return {"status": "error", "message": "Code manquant"}

@router.post("/test/press/{key}")
async def test_key_press(key: str):
    """Simule une pression de touche pour le mode Mock"""
    await keypad_manager.broadcast({"event": "key_press", "key": key, "buffer": "MOCK"})
    return {"status": "success", "key": key}
