from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import time
import threading
import requests as _requests
from services.vision import processor

router = APIRouter(tags=["Video"])

# ──── Cache pour le flux brut USB (port 8082 sur le Pi) ────
_raw_lock = threading.Lock()
_raw_frame: bytes | None = None
_raw_running = False

def _run_raw_cam():
    """Thread dédié : tire les images JPEG du bridge USB (Pi:8082) à ~30 FPS."""
    global _raw_frame, _raw_running
    url = "http://192.168.137.94:8082/latest.jpg"
    while _raw_running:
        try:
            r = _requests.get(url, timeout=1.0)
            if r.status_code == 200 and r.content:
                with _raw_lock:
                    _raw_frame = r.content
        except Exception:
            pass
        time.sleep(1 / 30.0)

def _ensure_raw_started():
    global _raw_running
    if not _raw_running:
        _raw_running = True
        t = threading.Thread(target=_run_raw_cam, daemon=True)
        t.start()

# ──── Générateurs MJPEG ────

def gen_frames_primary():
    """Flux CSI avec annotations YOLO/OCR du backend."""
    last_frame = None
    while True:
        frame = processor.get_frame()
        if frame is not None and frame != last_frame:
            last_frame = frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(1 / 30.0)

def gen_frames_raw():
    """Flux USB brut proxifié depuis la Pi."""
    _ensure_raw_started()
    last_frame = None
    while True:
        with _raw_lock:
            frame = _raw_frame
        if frame is not None and frame != last_frame:
            last_frame = frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(1 / 30.0)

# ──── Endpoints ────

@router.get("/video_feed")
def video_feed():
    """Flux principal : caméra CSI (Nappe) avec IA YOLO."""
    return StreamingResponse(gen_frames_primary(), media_type="multipart/x-mixed-replace; boundary=frame")

@router.get("/video_feed_raw")
def video_feed_raw():
    """Flux secondaire : caméra USB brut, sans IA."""
    return StreamingResponse(gen_frames_raw(), media_type="multipart/x-mixed-replace; boundary=frame")
