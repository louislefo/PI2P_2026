"""
camera-bridge/bridge.py
-----------------------
Capture la caméra CSI (nappe OV5647) via rpicam-vid et expose
un flux MJPEG HTTP sur http://0.0.0.0:8081/stream

- Consommé par le conteneur `api` via OpenCV : cv2.VideoCapture(url)
- Reconnexion automatique si rpicam-vid plante
- Supporte plusieurs clients simultanés (lecture du dernier frame)
"""

import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler


# ─── Frame partagé entre le thread de capture et les clients HTTP ───
latest_frame: bytes | None = None
frame_lock = threading.Lock()
frame_event = threading.Event()  # Signal : un nouveau frame est dispo


# ──────────────────────────────────────────────────────────────────────
# Thread de capture rpicam-vid → parser MJPEG → latest_frame
# ──────────────────────────────────────────────────────────────────────
def capture_loop():
    global latest_frame

    # Paramètres caméra CSI (3 fps = assez pour YOLO + lecture plaque)
    CMD = [
        "rpicam-vid",
        "-t", "0",               # Durée infinie
        "--width", "640",
        "--height", "480",
        "--framerate", "5",
        "--codec", "mjpeg",
        "--nopreview",
        "-o", "-",               # Sortie sur stdout
    ]

    while True:
        print("🎥 [BRIDGE] Lancement rpicam-vid ...", flush=True)
        try:
            proc = subprocess.Popen(
                CMD,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            buf = b""
            while True:
                chunk = proc.stdout.read(8192)
                if not chunk:
                    # rpicam-vid s'est arrêté
                    break
                buf += chunk

                # Parsing MJPEG : SOI = FF D8, EOI = FF D9
                while True:
                    start = buf.find(b"\xff\xd8")
                    if start == -1:
                        buf = b""
                        break
                    end = buf.find(b"\xff\xd9", start + 2)
                    if end == -1:
                        buf = buf[start:]   # On garde depuis le début du frame
                        break
                    frame_data = buf[start : end + 2]
                    buf = buf[end + 2:]
                    with frame_lock:
                        latest_frame = frame_data
                    frame_event.set()
                    frame_event.clear()

            proc.wait()
            print("⚠️ [BRIDGE] rpicam-vid terminé, reconnexion dans 2s ...", flush=True)

        except Exception as e:
            print(f"❌ [BRIDGE] Erreur capture: {e}", flush=True)

        time.sleep(2)   # Pause avant de retenter


# ──────────────────────────────────────────────────────────────────────
# Serveur HTTP MJPEG
# ──────────────────────────────────────────────────────────────────────
class StreamHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/stream":
            self._serve_stream()
        elif self.path == "/latest.jpg":
            self._serve_latest()
        elif self.path == "/health":
            self._serve_health()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        print(f"📡 [BRIDGE] Client connecté : {self.client_address}", flush=True)
        try:
            while True:
                # Attendre un frame dispo (timeout 5s pour ne pas bloquer éternellement)
                frame_event.wait(timeout=5.0)
                with frame_lock:
                    frame = latest_frame
                if frame is None:
                    continue
                self.wfile.write(
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            print(f"📴 [BRIDGE] Client déconnecté : {self.client_address}", flush=True)
        except Exception as e:
            print(f"⚠️ [BRIDGE] Erreur stream: {e}", flush=True)

    def _serve_latest(self):
        """Retourne le dernier JPEG capturé — mode pull, zéro buffer."""
        with frame_lock:
            frame = latest_frame
        if frame is None:
            self.send_response(503)  # Pas encore de frame dispo
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(frame)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(frame)

    def _serve_health(self):
        self.send_response(200)
        self.end_headers()
        status = b"OK" if latest_frame is not None else b"NO_FRAME"
        self.wfile.write(status)

    def log_message(self, format, *args):
        # Silencieux pour éviter du bruit dans les logs Docker
        pass


# ──────────────────────────────────────────────────────────────────────
# Point d'entrée
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    t = threading.Thread(target=capture_loop, daemon=True)
    t.start()

    print("🚀 [BRIDGE] Serveur MJPEG démarré sur http://0.0.0.0:8081", flush=True)
    print("   → Flux CSI : http://0.0.0.0:8081/stream", flush=True)
    print("   → Santé    : http://0.0.0.0:8081/health", flush=True)

    server = HTTPServer(("0.0.0.0", 8081), StreamHandler)
    server.serve_forever()
