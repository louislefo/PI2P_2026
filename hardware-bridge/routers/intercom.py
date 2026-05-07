import asyncio
import subprocess
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set

router = APIRouter(tags=["Intercom"])

class CallManager:
    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self.call_active = False

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        print(f"📡 [CALL-WS] Client connecté — total: {len(self._clients)}")
        await ws.send_json({"event": "status", "call_active": self.call_active})

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._clients.discard(ws)
        print(f"📴 [CALL-WS] Client déconnecté — total: {len(self._clients)}")

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

    def trigger_call(self, loop):
        if loop is None:
            return
        self.call_active = True
        print("🔔 [CALL] Bouton pressé → Appel entrant !")
        asyncio.run_coroutine_threadsafe(
            self.broadcast({"event": "incoming_call", "call_active": True}),
            loop,
        )

    def end_call(self, loop):
        self.call_active = False
        if loop:
            asyncio.run_coroutine_threadsafe(
                self.broadcast({"event": "call_ended", "call_active": False}),
                loop,
            )

call_manager = CallManager()

@router.websocket("/ws/call")
async def ws_call(ws: WebSocket):
    await call_manager.connect(ws)
    loop = asyncio.get_running_loop()
    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")
            if action == "hangup":
                print("📴 [CALL] Raccrochage depuis le frontend")
                call_manager.end_call(loop)
            elif action == "test":
                print("🧪 [CALL] Simulation d'appel (test frontend)")
                call_manager.trigger_call(loop)
    except WebSocketDisconnect:
        pass
    finally:
        await call_manager.disconnect(ws)

@router.websocket("/ws/audio")
async def ws_audio(ws: WebSocket):
    await ws.accept()
    print("🎙️ [AUDIO-WS] Connexion audio reçue — démarrage aplay stdin...")

    proc = None
    try:
        proc = subprocess.Popen(
            ["aplay", "-f", "S16_LE", "-r", "16000", "-c", "1", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("✅ [AUDIO-WS] aplay démarré — audio en cours...")

        while True:
            data = await ws.receive_bytes()
            if proc.poll() is not None:
                proc = subprocess.Popen(
                    ["aplay", "-f", "S16_LE", "-r", "16000", "-c", "1", "-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            try:
                proc.stdin.write(data)
                proc.stdin.flush()
            except BrokenPipeError:
                break

    except WebSocketDisconnect:
        print("📴 [AUDIO-WS] Client déconnecté")
    except Exception as e:
        print(f"❌ [AUDIO-WS] Erreur : {e}")
    finally:
        if proc and proc.poll() is None:
            proc.stdin.close()
            proc.terminate()

@router.websocket("/ws/mic")
async def ws_mic(ws: WebSocket):
    await ws.accept()
    print("🎙️ [MIC-WS] Connexion reçue — démarrage arecord (Pi → PC)...")
    
    proc = None
    try:
        # Essai avec plughw:1,0 (webcam USB typique sur Pi)
        # S'il n'y a pas de son, on pourrait implémenter un fallback dynamique avec "arecord -l"
        proc = await asyncio.create_subprocess_exec(
            "arecord", "-D", "plughw:1,0", "-f", "S16_LE", "-r", "16000", "-c", "1", "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        
        while True:
            data = await proc.stdout.read(4096)
            if not data:
                break
            await ws.send_bytes(data)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"❌ [MIC-WS] Erreur : {e}")
    finally:
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
