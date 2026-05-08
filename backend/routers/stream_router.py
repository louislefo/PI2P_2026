from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import cv2
import time
import threading
from services.vision import processor

router = APIRouter(tags=["Video"])

# ──── Cache pour la caméra secondaire (pas d'IA dessus) ────
_secondary_cam_lock = threading.Lock()
_secondary_frame = None
_secondary_thread = None
_secondary_running = False

def _run_secondary_cam():
    """Thread dédié pour capturer la caméra secondaire depuis le réseau (Pi)."""
    global _secondary_frame, _secondary_running
    import requests

    usb_url = "http://192.168.137.94:8082/latest.jpg"
    print(f"🎥 [STREAM] Lancement lecture réseau Caméra USB ({usb_url})")
    
    while _secondary_running:
        try:
            r = requests.get(usb_url, timeout=1.5)
            if r.status_code == 200 and r.content:
                # Transmet directement le Buffer Jpeg encodé depuis le serveur !
                with _secondary_cam_lock:
                    _secondary_frame = r.content
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(1/15.0)  # On limite à 15 FPS pour ne pas étouffer le Pi

def _ensure_secondary_started():
    """Démarre le thread de la caméra secondaire si pas déjà actif."""
    global _secondary_thread, _secondary_running
    if not _secondary_running:
        _secondary_running = True
        _secondary_thread = threading.Thread(target=_run_secondary_cam, daemon=True)
        _secondary_thread.start()

def gen_frames_primary():
    """Flux de la caméra principale (avec IA/YOLO/OCR)."""
    while True:
        frame = processor.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(0.1)

def gen_frames_secondary():
    """Flux de la caméra secondaire (brut, sans IA)."""
    _ensure_secondary_started()
    while True:
        with _secondary_cam_lock:
            frame = _secondary_frame
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(0.1)

@router.get("/video_feed")
def video_feed(cam: str = Query(default="CAM_01_IN")):
    """
    Flux vidéo MJPEG.
    - cam=CAM_01_IN  → Caméra principale (CSI/Nappe) avec overlay IA
    - cam=CAM_02_OUT → Caméra secondaire (USB) flux brut
    """
    if cam == "CAM_02_OUT":
        return StreamingResponse(gen_frames_secondary(), media_type="multipart/x-mixed-replace; boundary=frame")
    return StreamingResponse(gen_frames_primary(), media_type="multipart/x-mixed-replace; boundary=frame")
