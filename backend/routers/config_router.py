from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import csv
import io
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

@router.post("/plates/import-csv")
async def import_plates_csv(file: UploadFile = File(...)):
    """Import plates from a CSV file. Expected columns: plate, owner_name, email, valid_until"""
    content = await file.read()
    text = content.decode("utf-8-sig")  # utf-8-sig handles BOM from Excel
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    
    imported = 0
    errors = []
    
    for i, row in enumerate(reader, start=2):
        plate = row.get("plate", "").strip().upper()
        if not plate:
            errors.append(f"Ligne {i}: plaque vide, ignorée")
            continue
        
        owner_name = row.get("owner_name", "").strip() or None
        email = row.get("email", "").strip() or None
        valid_until = row.get("valid_until", "").strip() or None
        
        add_plate_to_db(plate, owner_name, email, valid_until)
        imported += 1
    
    processor.update_config()
    return {
        "status": "success",
        "imported": imported,
        "errors": errors,
        "plates": get_authorized_plates()
    }

@router.get("/plates/template-csv")
def download_template_csv():
    """Download a CSV template for bulk plate import"""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["plate", "owner_name", "email", "valid_until"])
    writer.writerow(["AA-123-BB", "Jean Dupont", "jean@exemple.fr", "2026-12-31"])
    writer.writerow(["CC-456-DD", "Marie Martin", "marie@exemple.fr", ""])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=modele_plaques.csv"}
    )
