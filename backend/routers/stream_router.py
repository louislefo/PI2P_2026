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
    """Thread dédié pour capturer la caméra secondaire (USB)."""
    global _secondary_frame, _secondary_running
    import platform
    is_windows = platform.system() == "Windows"
    
    if is_windows:
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    else:
        print("🎥 [STREAM] Lancement capture USB secondaire via V4L2 natif (index 1)")
        cap = cv2.VideoCapture(1, cv2.CAP_V4L2)
        
    if cap.isOpened():
        print("✅ [STREAM] Caméra USB trouvée à l'index 1.")
    else:
        print("⚠️ [STREAM] Caméra USB introuvable à l'index 1.")
        _secondary_running = False
        return
    
    # --- OPTIMISATION: Limiter résolution, buffer et forcer YUYV ---
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print("✅ [STREAM] Caméra secondaire prête.")
    while _secondary_running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            with _secondary_cam_lock:
                _secondary_frame = buffer.tobytes()
        time.sleep(1/15)  # 15 FPS pour la caméra secondaire (moins gourmand)
    
    cap.release()

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
