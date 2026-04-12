from fastapi import APIRouter
from pydantic import BaseModel
from core.config import load_config, save_config
from services.vision import processor

router = APIRouter(prefix="/api/config", tags=["Configuration"])

class PlateRequest(BaseModel):
    plate: str

@router.get("")
def get_config_endpoint():
    return load_config()

@router.post("/plates")
def add_plate(data: PlateRequest):
    cfg = load_config()
    plates = cfg.get("authorized_plates", [])
    plate = data.plate.upper().strip()
    
    if plate and plate not in plates:
        plates.append(plate)
        cfg["authorized_plates"] = plates
        save_config(cfg)
        processor.update_config()
        
    return {"status": "success", "plates": plates}

@router.delete("/plates/{plate}")
def delete_plate(plate: str):
    cfg = load_config()
    plates = cfg.get("authorized_plates", [])
    plate = plate.upper().strip()
    
    if plate in plates:
        plates.remove(plate)
        cfg["authorized_plates"] = plates
        save_config(cfg)
        processor.update_config()
        
    return {"status": "success", "plates": plates}
