from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from core.config import load_config, save_config, get_authorized_plates, add_plate_to_db, delete_plate_from_db
from services.vision import processor

router = APIRouter(prefix="/api/config", tags=["Configuration"])

class PlateRequest(BaseModel):
    plate: str
    owner_name: Optional[str] = None
    email: Optional[str] = None
    valid_until: Optional[str] = None

class SettingsRequest(BaseModel):
    entry_code: Optional[str] = None
    gate_mode: Optional[str] = None
    detection_objects: Optional[list[str]] = None

@router.get("")
def get_config_endpoint():
    cfg = load_config()
    cfg["authorized_plates"] = get_authorized_plates()
    return cfg

@router.post("/settings")
def update_settings(data: SettingsRequest):
    cfg = load_config()
    
    # Gestion du changement de mode de barrière
    if data.gate_mode and data.gate_mode in ["auto", "always_open", "always_closed"]:
        old_mode = cfg.get("gate_mode", "auto")
        new_mode = data.gate_mode
        cfg["gate_mode"] = new_mode
        
        # Trigger matériel si on change le mode
        if new_mode != old_mode:
            from core.hardware import relay
            if new_mode == "always_open":
                relay.on()
            else:
                relay.off()
    
    # Changement du code d'entrée
    if data.entry_code is not None:
        cfg["entry_code"] = data.entry_code
        
    # Mise à jour des objets à détecter
    if data.detection_objects is not None:
        cfg["detection_objects"] = data.detection_objects
        from services.vision import processor
        processor.update_config()
        
    save_config(cfg)
    return {"status": "success", "settings": cfg}

@router.post("/plates")
def add_plate(data: PlateRequest):
    plate = data.plate.upper().strip()
    
    if plate:
        add_plate_to_db(plate, data.owner_name, data.email, data.valid_until)
        processor.update_config()
        
    return {"status": "success", "plates": get_authorized_plates()}

@router.delete("/plates/{plate}")
def delete_plate(plate: str):
    plate = plate.upper().strip()
    
    if plate:
        delete_plate_from_db(plate)
        processor.update_config()
        
    return {"status": "success", "plates": get_authorized_plates()}
