from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import cv2
import time
import threading
from services.vision import processor
from core.config import load_config

router = APIRouter(tags=["Video"])

def gen_frames_primary():
    """Flux avec IA/YOLO/OCR."""
    last_frame = None
    while True:
        frame = processor.get_frame()
        if frame is not None and frame != last_frame:
            last_frame = frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(1/30.0)

@router.get("/video_feed")
def video_feed():
    """
    Flux vidéo IA principal.
    Le flux brut de l'autre caméra est lu directement depuis la Pi par le frontend.
    """
    return StreamingResponse(gen_frames_primary(), media_type="multipart/x-mixed-replace; boundary=frame")
