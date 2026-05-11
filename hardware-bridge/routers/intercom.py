import asyncio
import subprocess
import re
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
from core.audio import play_wav_loop, stop_wav_loop, play_pattern

router = APIRouter(tags=["Intercom"])

def find_mic_device() -> str:
    """Recherche le périphérique d'enregistrement USB (ou autre) via arecord -l"""
    try:
        res = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
        # Cherche une ligne du genre "card 1: ... device 0: ..."
        # On essaie de privilégier un périphérique USB
        matches = re.findall(r"card (\d+):.*?device (\d+):", res.stdout)
        if matches:
            # S'il y a plusieurs cartes, on prend la dernière en espérant que ce soit l'USB
            # (la carte 0 est souvent la sortie jack/HDMI interne, bien qu'elle n'ait pas de micro)
            card, device = matches[-1]
            dev_name = f"plughw:{card},{device}"
            print(f"🎤 [MIC-WS] Microphone auto-détecté : {dev_name}")
            return dev_name
    except Exception as e:
        print(f"⚠️ [MIC-WS] Erreur détection micro : {e}")
    
    print("⚠️ [MIC-WS] Aucun micro détecté dynamiquement, essai de 'default'")
    return "default"

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
        play_wav_loop("data/attente.wav")
        asyncio.run_coroutine_threadsafe(
            self.broadcast({"event": "incoming_call", "call_active": True}),
            loop,
        )

    def end_call(self, loop):
        self.call_active = False
        stop_wav_loop()
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
    
    # L'appel a été décroché (le frontend se connecte à l'audio)
    stop_wav_loop()
    play_pattern("success")

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
        # Auto-détection du périphérique (ex: plughw:1,0)
        device = find_mic_device()
        
        proc = await asyncio.create_subprocess_exec(
            "arecord", "-D", device, "-f", "S16_LE", "-r", "16000", "-c", "1", "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE  # On capte stderr pour voir les erreurs ALSA
        )
        
        while True:
            data = await proc.stdout.read(4096)
            if not data:
                stderr_output = await proc.stderr.read()
                print(f"❌ [MIC-WS] arecord a terminé prématurément. stderr: {stderr_output.decode(errors='ignore')}")
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
