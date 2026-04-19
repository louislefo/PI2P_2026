"""
camera-bridge/bridge_usb.py
-----------------------
Capture la caméra USB via OpenCV et expose
un flux MJPEG HTTP sur http://0.0.0.0:8082/stream
"""

import cv2
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

latest_frame: bytes | None = None
frame_lock = threading.Lock()
frame_event = threading.Event()

def capture_loop():
    global latest_frame
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    # Optimisation pour webcam standard
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    while True:
        if not cap.isOpened():
            print("🎥 [BRIDGE-USB] Lancement OpenCV capture USB...", flush=True)
            cap.open(0, cv2.CAP_V4L2)
            time.sleep(2)
            continue
            
        ret, frame = cap.read()
        if not ret:
            print("⚠️ [BRIDGE-USB] Perte de frame, reconnexion...", flush=True)
            cap.release()
            time.sleep(2)
            continue
            
        ret2, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret2:
            frame_data = buffer.tobytes()
            with frame_lock:
                latest_frame = frame_data
            frame_event.set()
            frame_event.clear()
            
        # Limite à 15 FPS pour économiser le CPU du Pi
        time.sleep(1/15.0)

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

        print(f"📡 [BRIDGE-USB] Client connecté : {self.client_address}", flush=True)
        try:
            while True:
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
            print(f"📴 [BRIDGE-USB] Client déconnecté : {self.client_address}", flush=True)
        except Exception as e:
            print(f"⚠️ [BRIDGE-USB] Erreur stream: {e}", flush=True)

    def _serve_latest(self):
        with frame_lock:
            frame = latest_frame
        if frame is None:
            self.send_response(503)
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
        pass

if __name__ == "__main__":
    t = threading.Thread(target=capture_loop, daemon=True)
    t.start()

    port = 8082
    print(f"🚀 [BRIDGE-USB] Serveur MJPEG démarré sur http://0.0.0.0:{port}", flush=True)
    server = HTTPServer(("0.0.0.0", port), StreamHandler)
    server.serve_forever()
