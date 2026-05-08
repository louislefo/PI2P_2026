import cv2
import threading
import time
import requests
import re
import numpy as np
import os
from ultralytics import YOLO
from core.config import load_config, get_authorized_plates
import logging
from datetime import datetime

# On coupe les logs inutiles d'easyocr
logging.getLogger("easyocr").setLevel(logging.ERROR)

# ── Sémaphore global : 1 seul OCR actif à la fois pour ne pas saturer ──────
_ocr_semaphore = threading.Semaphore(1)


class VisionProcessor:
    def __init__(self):
        self.config = load_config()
        self.running = False
        self.thread = None
        self.latest_frame = None
        self.lock = threading.Lock()
        self.tested_cars_count = 0

        # Cache config pour éviter les lectures disque à chaque frame
        self._config_cache = self.config.copy()
        self._config_cache_time = 0
        self._config_cache_ttl = 5.0  # Rafraîchir la config toutes les 5s max

        print("🤖 [VISION] Chargement du Modèle YOLO pour Détection Véhicules...")
        try:
            model_path = self.config.get("yolo_model_path", "yolov8n.pt")
            self.model = YOLO(model_path)
            print(f"✅ [VISION] YOLO prêt ({model_path}).")
        except Exception as e:
            print("❌ [VISION] Erreur YOLO:", e)
            self.model = None

        print("🔤 [VISION] Chargement de EasyOCR pour Lecture de texte...")
        try:
            import easyocr
            self.reader = easyocr.Reader(['en', 'fr'], gpu=True)
            print("✅ [VISION] EasyOCR prêt (Mode GPU).")
        except Exception as e:
            print("❌ [VISION] Erreur EasyOCR:", e)
            self.reader = None

        self.last_ocr_time = 0
        self.last_plate_match_time = 0  # Anti-spam après un accès autorisé

        self.coco_vehicle_ids = [2, 3, 5, 7]  # car, motorcycle, bus, truck
        self.coco_all_ids = [0, 1, 2, 3, 5, 7]  # + person, bicycle

    def _get_config(self):
        """Retourne la config en cache (rafraîchie au max toutes les 5s)."""
        now = time.time()
        if now - self._config_cache_time > self._config_cache_ttl:
            self._config_cache = load_config()
            self._config_cache_time = now
        return self._config_cache

    def update_config(self):
        self._config_cache = load_config()
        self._config_cache_time = time.time()
        print("⚙️ [VISION] Configuration rafraîchie.")

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _trigger_access(self, plate, image_filename=None):
        try:
            requests.post(
                "http://127.0.0.1:8000/api/system/access",
                json={"plate": plate, "image_filename": image_filename},
                timeout=3,
            )
        except Exception as e:
            print(f"⚠️ Erreur déclenchement trigger: {e}")

    def _preprocess_plate_roi(self, roi_bgr):
        """
        Prépare l'image ROI pour la meilleure lecture OCR possible.
        Stratégie multi-passe : retourne l'image qui a le plus de chance de fonctionner.
        """
        h, w = roi_bgr.shape[:2]

        # Agrandir si trop petit (minimum 200x60 pour une plaque)
        scale = max(1, 300 // max(w, 1), 100 // max(h, 1))
        if scale > 1:
            roi_bgr = cv2.resize(roi_bgr, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

        # Conversion gris + amélioration contraste (CLAHE)
        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
        gray = clahe.apply(gray)

        # Agrandissement x2 pour l'OCR
        enlarged = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Légère netteté
        kernel_sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened = cv2.filter2D(enlarged, -1, kernel_sharpen)

        return sharpened

    def _extract_plate_zone(self, frame, x1, y1, x2, y2):
        """
        Extrait la moitié inférieure du bounding box du véhicule (pleine largeur).
        Coupe horizontalement en deux et garde uniquement la partie basse.
        """
        h = y2 - y1
        mid_y = y1 + h // 2  # Milieu vertical exact

        # Sécurité : bornes dans l'image
        fh, fw = frame.shape[:2]
        crop_y1 = max(0, mid_y)
        crop_y2 = min(fh, y2)
        crop_x1 = max(0, x1)
        crop_x2 = min(fw, x2)

        return frame[crop_y1:crop_y2, crop_x1:crop_x2]

    def _run(self):
        csi_base = os.environ.get("CSI_BRIDGE_URL", "http://192.168.137.94:8081")
        latest_url = csi_base.rstrip("/") + "/latest.jpg"
        health_url = csi_base.rstrip("/") + "/health"

        print(f"🎥 [VISION] Mode réseau PULL HTTP CSI : {latest_url}")

        # Attente que le bridge Pi soit prêt
        for attempt in range(15):
            try:
                r = requests.get(health_url, timeout=2)
                if r.status_code == 200 and b"OK" in r.content:
                    print("✅ [VISION] Bridge CSI Pi prêt.")
                    break
            except Exception:
                pass
            print(f"⏳ [VISION] En attente du Pi (CSI) (tentative {attempt+1}/15)...")
            time.sleep(2)

        session = requests.Session()  # Réutilise la connexion HTTP

        def get_frame():
            try:
                r = session.get(latest_url, timeout=2.0)
                if r.status_code == 200 and r.content:
                    arr = np.frombuffer(r.content, dtype=np.uint8)
                    return cv2.imdecode(arr, cv2.IMREAD_COLOR)
            except Exception:
                pass
            return None

        last_yolo_time = 0
        last_boxes = []

        while self.running:
            cfg = self._get_config()
            ai_fps = cfg.get("ai_fps", 4)
            yolo_interval = 1.0 / max(1, ai_fps)  # ex: 4fps → 0.25s

            frame = get_frame()
            if frame is None:
                time.sleep(0.2)
                continue

            annotated_frame = frame.copy()
            current_time = time.time()

            if self.model and (current_time - last_yolo_time > yolo_interval):
                # YOLO : détection sur frame complète
                results = self.model(
                    frame,
                    classes=self.coco_all_ids,
                    verbose=False,
                    conf=cfg.get("confidence_threshold", 0.45),
                    imgsz=640,  # Taille d'inférence (640 = bon compromis vitesse/précision)
                )
                last_boxes = results[0].boxes
                last_yolo_time = current_time

                # ── OCR séquentiel ── : déclenche 1 seul OCR à la fois
                ocr_cooldown = 3.0  # secondes entre deux OCR sur le même véhicule
                after_match_cooldown = 12.0  # pause longue après un accès autorisé

                ocr_ready = (
                    self.reader is not None
                    and cfg.get("gate_mode", "auto") == "auto"
                    and current_time - self.last_ocr_time > ocr_cooldown
                    and current_time - self.last_plate_match_time > after_match_cooldown
                    and _ocr_semaphore._value > 0  # Pas d'OCR en cours
                )

                if ocr_ready:
                    for box in last_boxes:
                        cls_id = int(box.cls[0])
                        if cls_id not in self.coco_vehicle_ids:
                            continue
                        conf = float(box.conf[0])
                        if conf < 0.50:  # Ignorer les détections incertaines
                            continue

                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        box_w, box_h = x2 - x1, y2 - y1

                        # Ignorer les véhicules trop petits (trop loin = plaque illisible)
                        if box_w < 80 or box_h < 60:
                            continue

                        # Extraire uniquement la zone de la plaque (bas du véhicule)
                        plate_zone = self._extract_plate_zone(frame, x1, y1, x2, y2)
                        if plate_zone.size == 0 or plate_zone.shape[0] < 15 or plate_zone.shape[1] < 30:
                            continue

                        obj_name = {2: "Voiture", 3: "Moto", 5: "Bus", 7: "Camion"}.get(cls_id, "Véhicule")
                        self.tested_cars_count += 1
                        self.last_ocr_time = current_time
                        print(f"🚙 [OCR] {obj_name} ({conf:.0%}) détectée — Analyse #{self.tested_cars_count}")

                        # Sauvegarde debug
                        os.makedirs("data/debug_ocr", exist_ok=True)
                        preprocessed = self._preprocess_plate_roi(plate_zone)
                        cv2.imwrite(f"data/debug_ocr/roi_{int(current_time)}.jpg", preprocessed)

                        # Lancement OCR dans thread séparé (non-bloquant, limité par sémaphore)
                        threading.Thread(
                            target=self._run_ocr_thread,
                            args=(preprocessed, plate_zone.copy(), current_time),
                            daemon=True,
                        ).start()
                        break  # Une seule détection par cycle YOLO

            # ── Annotation vidéo ────────────────────────────────────────────
            name_map = {0: "Humain", 1: "Velo", 2: "Voiture", 3: "Moto", 5: "Bus", 7: "Camion"}
            for box in last_boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label = f"{name_map.get(cls_id, 'Objet')} {int(conf*100)}%"
                color = (0, 220, 80) if cls_id in self.coco_vehicle_ids else (0, 165, 255)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(annotated_frame, label, (x1, max(15, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

                # Visualiser la zone plaque ciblée : moitié basse (pleine largeur)
                if cls_id in self.coco_vehicle_ids:
                    mid_y = y1 + (y2 - y1) // 2
                    cv2.rectangle(annotated_frame, (x1, mid_y), (x2, y2), (255, 100, 0), 1)

            ret, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
            if ret:
                with self.lock:
                    self.latest_frame = buffer.tobytes()

            # Throttle : on attend le prochain cycle YOLO plutôt que de loop en permanence
            elapsed = time.time() - current_time
            sleep_time = max(0.05, yolo_interval - elapsed)
            time.sleep(sleep_time)

    def _run_ocr_thread(self, preprocessed_img, color_roi, current_time):
        """Thread OCR sérialisé par sémaphore (1 seul à la fois)."""
        import difflib

        if not _ocr_semaphore.acquire(blocking=False):
            print("⏳ [OCR] OCR déjà en cours, analyse ignorée.")
            return

        try:
            allowed_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            ocr_results = self.reader.readtext(
                preprocessed_img,
                allowlist=allowed_chars,
                batch_size=1,
                detail=1,
                paragraph=False,
                width_ths=0.7,
            )

            if not ocr_results:
                print("   → [OCR] Aucun texte détecté sur la zone plaque.")
                return

            plates = get_authorized_plates()
            now = datetime.now().isoformat()
            valid_plates = []
            for p in plates:
                if p.get('valid_until') and p['valid_until'] < now:
                    continue
                cleaned = re.sub(r'[^A-Z0-9]', '', p['plate'].upper())
                if cleaned:
                    valid_plates.append(cleaned)

            if not valid_plates:
                print("   → [OCR] Aucune plaque autorisée dans la BDD.")
                return

            best_global_match = None
            best_global_ratio = 0.0
            best_global_text = ""

            for (bbox, raw_text, prob) in ocr_results:
                if prob < 0.2:  # Ignorer les lectures très incertaines
                    continue
                text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
                if len(text) < 4:
                    continue

                print(f"   → [OCR] Lu: '{text}' (confiance: {prob:.0%})")

                for auth_plate in valid_plates:
                    ratio = difflib.SequenceMatcher(None, text, auth_plate).ratio()
                    if ratio > best_global_ratio:
                        best_global_ratio = ratio
                        best_global_match = auth_plate
                        best_global_text = text

            if best_global_match is None:
                print("   → [OCR] Aucune correspondance valide.")
                return

            print(f"🔍 [OCR] Lu: '{best_global_text}' | Meilleure: '{best_global_match}' ({int(best_global_ratio*100)}%)")

            # Seuil : 55% (permet GV179DS → GV17DS mais rejette les faux positifs)
            MATCH_THRESHOLD = 0.55

            if best_global_ratio >= MATCH_THRESHOLD:
                print(f"✅ [ACCÈS AUTORISÉ] '{best_global_match}' validé ! Ouverture...")
                self.last_plate_match_time = time.time()

                history_dir = "data/historique_voiture_entree"
                os.makedirs(history_dir, exist_ok=True)
                image_filename = f"{int(current_time)}_{best_global_match}.jpg"
                cv2.imwrite(os.path.join(history_dir, image_filename), color_roi)

                threading.Thread(
                    target=self._trigger_access,
                    args=(best_global_match, image_filename),
                    daemon=True,
                ).start()
            else:
                print(f"❌ [ACCÈS REFUSÉ] Score trop faible ({int(best_global_ratio*100)}% < {int(MATCH_THRESHOLD*100)}%).")

        except Exception as e:
            print(f"❌ [OCR] Erreur inattendue: {e}")
        finally:
            _ocr_semaphore.release()

    def get_frame(self):
        with self.lock:
            return self.latest_frame


processor = VisionProcessor()
