from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import cv2
import time
import threading
from services.vision import processor
from core.config import load_config

router = APIRouter(tags=["Video"])

# ──── Cache pour la caméra brute (pas d'IA dessus) ────
_raw_cam_lock = threading.Lock()
_raw_frame = None
_raw_running = False
_raw_thread = None

def _run_raw_cam():
    """Thread dédié pour capturer la caméra non analysée depuis le Pi."""
    global _raw_frame, _raw_running
    import requests
    
    while _raw_running:
        cfg = load_config()
        ai_cam = cfg.get("vision_camera", "CSI")
        # Si l'IA est sur CSI (8081), on veut lire USB (8082) en brut, et inversement
        raw_port = "8082" if ai_cam == "CSI" else "8081"
        url = f"http://192.168.137.94:{raw_port}/latest.jpg"
        
        try:
            r = requests.get(url, timeout=1.0)
            if r.status_code == 200 and r.content:
                with _raw_cam_lock:
                    _raw_frame = r.content
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(1/15.0)

def _ensure_raw_started():
    global _raw_thread, _raw_running
    if not _raw_running:
        _raw_running = True
        _raw_thread = threading.Thread(target=_run_raw_cam, daemon=True)
        _raw_thread.start()

def gen_frames_primary():
    """Flux avec IA/YOLO/OCR."""
    while True:
        frame = processor.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(0.1)

def gen_frames_raw():
    """Flux brut, sans IA."""
    _ensure_raw_started()
    while True:
        with _raw_cam_lock:
            frame = _raw_frame
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(0.1)

@router.get("/video_feed")
def video_feed(cam: str = Query(default="CSI")):
    """
    cam peut être "CSI" ou "USB".
    Si cam == vision_camera (config), on renvoie gen_frames_primary (avec IA).
    Sinon on renvoie gen_frames_raw (sans IA).
    """
    cfg = load_config()
    ai_cam = cfg.get("vision_camera", "CSI")
    
    if cam == ai_cam:
        return StreamingResponse(gen_frames_primary(), media_type="multipart/x-mixed-replace; boundary=frame")
    else:
        return StreamingResponse(gen_frames_raw(), media_type="multipart/x-mixed-replace; boundary=frame")
