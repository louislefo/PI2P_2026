from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import time
from services.vision import processor

router = APIRouter(tags=["Video"])

def gen_frames():
    while True:
        frame = processor.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(0.1)

@router.get("/video_feed")
def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")
