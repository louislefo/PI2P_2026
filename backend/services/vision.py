import cv2
import threading
import time
import requests
import re
from ultralytics import YOLO
from core.config import load_config, get_authorized_plates
import logging
from datetime import datetime



# On coupe les logs inutiles d'easyocr
logging.getLogger("easyocr").setLevel(logging.ERROR)

class VisionProcessor:
    def __init__(self):
        self.config = load_config()
        self.running = False
        self.thread = None
        self.latest_frame = None
        self.lock = threading.Lock()
        self.tested_cars_count = 0
        
        print("🤖 [VISION] Chargement du Modèle YOLO pour Détection Véhicules...")
        try:
            self.model = YOLO(self.config.get("yolo_model_path", "yolov8n.pt"))
            print("✅ [VISION] YOLO prêt.")
        except Exception as e:
            print("❌ [VISION] Erreur YOLO:", e)
            self.model = None

        print("🔤 [VISION] Chargement de EasyOCR pour Lecture de texte...")
        try:
            import easyocr
            # Exploitation du GPU (CUDA/DirectML) pour le traitement rapide
            self.reader = easyocr.Reader(['en', 'fr'], gpu=True) 
            print("✅ [VISION] EasyOCR prêt (Mode GPU).")
        except Exception as e:
            print("❌ [VISION] Erreur EasyOCR:", e)
            self.reader = None
            
        self.last_ocr_time = 0
        self.ocr_active = False
        
        # Mappage des IDs COCO pour les objets funs
        self.coco_mapping = {
            "person": 0, "bicycle": 1, "car": 2, "motorcycle": 3, 
            "bus": 5, "truck": 7, "dog": 16, "cat": 15
        }

    def update_config(self):
        self.config = load_config()
        print("⚙️ [VISION] Configuration rafraîchie.")

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            
    def update_config(self):
        self.config = load_config()

    def _trigger_access(self, plate, image_filename=None):
        try:
            # On demande au router d'ouvrir la porte et de faire l'historique
            requests.post("http://127.0.0.1:8000/api/system/access", json={"plate": plate, "image_filename": image_filename})
        except Exception as e:
            print(f"⚠️ Erreur déclenchement trigger: {e}")

    def _process_plate(self, raw_text):
        cfg = load_config()
        if cfg.get("gate_mode", "auto") != "auto":
            print("⏳ [VISION] OCR ignoré : Le portail est en sur-régime (Ouvert/Bloqué)")
            return False
            
        # Nettoyage : Retire les espaces et autres caractères louches
        text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
        if len(text) < 4: return False
        
        print(f"\n🔍 [OCR] Texte brut lu sur la plaque : '{raw_text}' -> Formaté : '{text}'")
        
        plates = get_authorized_plates()
        now = datetime.now().isoformat()
        
        # Filtre les plaques expirées
        valid_plates = []
        for p in plates:
            if p['valid_until'] and p['valid_until'] < now:
                continue
            valid_plates.append(re.sub(r'[^A-Z0-9]', '', p['plate'].upper()))
            
        if text in valid_plates:
            print(f"✅ [ACCÈS AUTORISÉ] La plaque '{text}' est enregistrée ! Ouverture du Portail...")
            threading.Thread(target=self._trigger_access, args=(text,), daemon=True).start()
            return True
        else:
            print(f"❌ [ACCÈS REFUSÉ] La plaque '{text}' n'est pas connue du système ou est expirée.")
            
        return False

    def _run(self):
        # ── Abstraction d'acquisition de frame ──────────────────────────────────
        # Mode RÉSEAU PULL HTTP (depuis le Pi)
        import requests
        import numpy as np
        import os

        print(f"🎥 [VISION] Mode réseau PULL HTTP activé")

        for attempt in range(5):
            try:
                # Juste un check rapide
                r = requests.get("http://192.168.137.94:8081/health", timeout=2)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)

        def get_frame():
            """Récupère le dernier frame disponible sur le Pi."""
            cam_setting = self.config.get("vision_camera", "CSI")
            cam_port = "8082" if cam_setting == "USB" else "8081"
            latest_url = f"http://192.168.137.94:{cam_port}/latest.jpg"
            try:
                r = requests.get(latest_url, timeout=1.5)
                if r.status_code == 200 and r.content:
                    arr = np.frombuffer(r.content, dtype=np.uint8)
                    return cv2.imdecode(arr, cv2.IMREAD_COLOR)
            except Exception:
                pass
            return None

        # ── Boucle principale ───────────────────────────────────────────────────
        while self.running:
            # Limitation du FPS de l'IA (et du flux vidéo associé)
            ai_fps = self.config.get("ai_fps", 3)
            try: ai_fps = int(ai_fps)
            except: ai_fps = 3
            if ai_fps < 1: ai_fps = 1
            if ai_fps > 30: ai_fps = 30
            frame_interval = 1.0 / ai_fps

            frame = get_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            annotated_frame = frame.copy()
            if self.model:
                current_time = time.time()

                # --- Détection Multiple (Véhicules, Humains, Animaux, Vélos) ---
                # YOLO détecte TOUT en une seule passe (c'est très rapide), imgsz=640 limite la charge CPU
                target_ids = [0, 1, 2, 3, 5, 7, 15, 16] 
                results = self.model(frame, imgsz=640, classes=target_ids, verbose=False)

                # On garde les boxes pour dessiner
                last_boxes = results[0].boxes

                # --- LANCEMENT OCR INTELLIGENT ---
                cfg = load_config()
                if self.reader and not self.ocr_active and (current_time - self.last_ocr_time > 2.0) and cfg.get("gate_mode", "auto") == "auto":
                    for box in last_boxes:
                        cls_id = int(box.cls[0])
                        if cls_id in [2, 3, 5, 7]:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            car_roi = frame[y1:y2, x1:x2]

                            if car_roi.shape[0] > 10 and car_roi.shape[1] > 10:
                                self.ocr_active = True
                                self.tested_cars_count += 1
                                obj_name = "Voiture" if cls_id == 2 else "Moto/Camion"
                                print(f"🚙 [INFO] {obj_name} détectée ! Tentative de lecture de plaque (Analyse #{self.tested_cars_count})...")
                                import os
                                os.makedirs("data/debug_ocr", exist_ok=True)
                                gray = cv2.cvtColor(car_roi, cv2.COLOR_BGR2GRAY)
                                enlarged = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                                cv2.imwrite(f"data/debug_ocr/roi_{int(current_time)}.jpg", enlarged)
                                self.last_ocr_time = current_time
                                threading.Thread(target=self._run_ocr_thread, args=(enlarged, car_roi.copy(), current_time), daemon=True).start()
                                break

                # Dessiner les dernières box connues et leurs labels pour un rendu vidéo ultra qualitatif
                for box in last_boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    # On devine le nom, fallback sur "Objet"
                    name_map = {0: "Humain", 1: "Velo", 2:"Voiture", 3:"Moto", 5:"Bus", 7:"Camion", 15:"Chat", 16:"Chien"}
                    label_text = f"{name_map.get(cls_id, 'Objet')} {int(conf*100)}%"
                    
                    # Dessin du rectangle avec couleur dynamique par ID
                    color = (0, 255, 0) if cls_id in [2,3,5,7] else (0, 165, 255) # Vert = Véhicules, Orange = Humains/Animaux
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated_frame, label_text, (x1, max(15, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            ret, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                with self.lock:
                    self.latest_frame = buffer.tobytes()

            if frame_interval > 0:
                time.sleep(frame_interval)
            
    def _run_ocr_thread(self, enlarged_img, color_roi, current_time):
        import difflib
        
        allowed_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
        ocr_results = self.reader.readtext(enlarged_img, allowlist=allowed_chars)
        plate_found = False
        
        if len(ocr_results) == 0:
            print("   -> [OCR] Aucun texte détecté sur l'image coupée.")
        else:
            for (bbox, raw_text, prob) in ocr_results:
                print(f"   -> [OCR DIAGNOSTIC] '{raw_text}' (Probabilité: {prob:.2f})")
                
                # Nettoyage
                text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
                if len(text) < 4: continue
                
                plates = get_authorized_plates()
                now = datetime.now().isoformat()
                
                # Filtre les plaques expirées
                valid_plates = []
                for p in plates:
                    if p['valid_until'] and p['valid_until'] < now:
                        continue
                    valid_plates.append(re.sub(r'[^A-Z0-9]', '', p['plate'].upper()))
                
                # FUZZY MATCHING : Accepte les fautes de frappe de l'OCR !
                best_match = None
                best_ratio = 0
                for auth_plate in valid_plates:
                    ratio = difflib.SequenceMatcher(None, text, auth_plate).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = auth_plate
                
                print(f"\n🔍 [OCR] Lu: '{text}' | Meilleure correspondance: '{best_match}' (Score: {int(best_ratio*100)}%)")
                
                # Tolérance de 50% de similarité (parfait pour GV179DS -> 1790S)
                score_minimum = 0.50
                
                if best_ratio >= score_minimum:
                    print(f"✅ [ACCÈS AUTORISÉ] La reconnaissance floue valide '{best_match}' ! Ouverture du Portail...")
                    
                    # Sauvegarde de l'image de l'historique
                    import os
                    history_dir = "data/historique_voiture_entree"
                    os.makedirs(history_dir, exist_ok=True)
                    image_filename = f"{int(current_time)}_{best_match}.jpg"
                    image_path = os.path.join(history_dir, image_filename)
                    cv2.imwrite(image_path, color_roi)
                    
                    # Update OCR delay because it's a match
                    self.last_ocr_time = time.time() + 10.0
                    threading.Thread(target=self._trigger_access, args=(best_match, image_filename), daemon=True).start()
                    plate_found = True
                    break
                else:
                    print(f"❌ [ACCÈS REFUSÉ] Trop éloigné d'une plaque connue.")
        
        self.ocr_active = False

    def get_frame(self):
        with self.lock:
            return self.latest_frame

processor = VisionProcessor()
