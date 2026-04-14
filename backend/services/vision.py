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
            self.reader = easyocr.Reader(['en', 'fr'], gpu=False) # gpu=False plus stable sur Windows/Pi sans CUDA
            print("✅ [VISION] EasyOCR prêt.")
        except Exception as e:
            print("❌ [VISION] Erreur EasyOCR:", e)
            self.reader = None
            
        self.last_ocr_time = 0
        
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
        import platform
        is_windows = platform.system() == "Windows"
        
        if is_windows:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        else:
            print("🎥 [VISION] Connexion au flux Nappe CSI via V4L2 natif (index 0)")
            cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
            
        # --- OPTIMISATION VIDEO ---
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        last_yolo_time = 0
        last_boxes = []

        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            annotated_frame = frame.copy()
            if self.model:
                current_time = time.time()
                
                # YOLO Throttle: Exécution 2 fois par sec max (0.5s)
                if current_time - last_yolo_time > 0.5:
                    # --- Filtrage Véhicules Uniquement ---
                    target_ids = [2, 3, 5, 7] # 2=car, 3=motorcycle, 5=bus, 7=truck
                    results = self.model(frame, classes=target_ids, verbose=False) 
                    
                    # On garde les boxes pour dessiner fluidement sur les frames sans YOLO intermédiaires
                    last_boxes = results[0].boxes
                    last_yolo_time = current_time
                    
                    # --- LANCEMENT OCR INTELLIGENT ---
                    cfg = load_config()
                    if self.reader and (current_time - self.last_ocr_time > 2.0) and cfg.get("gate_mode", "auto") == "auto":
                        for box in last_boxes:
                            cls_id = int(box.cls[0])
                            if cls_id in [2, 3, 5, 7]:
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                car_roi = frame[y1:y2, x1:x2]
                                
                                if car_roi.shape[0] > 10 and car_roi.shape[1] > 10: 
                                    obj_name = "Voiture" if cls_id == 2 else "Moto/Camion"
                                    print(f"🚙 [INFO] {obj_name} détectée ! Tentative de lecture de plaque...")
                                    import os
                                    os.makedirs("data/debug_ocr", exist_ok=True)
                                    gray = cv2.cvtColor(car_roi, cv2.COLOR_BGR2GRAY)
                                    enlarged = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                                    cv2.imwrite(f"data/debug_ocr/roi_{int(current_time)}.jpg", enlarged)
                                    self.last_ocr_time = current_time
                                    threading.Thread(target=self._run_ocr_thread, args=(enlarged, car_roi.copy(), current_time), daemon=True).start()
                                    break
                        self.last_ocr_time = max(self.last_ocr_time, current_time)

                # Dessiner les dernières box connues pour un rendu vidéo fluide
                for box in last_boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            if ret:
                with self.lock:
                    self.latest_frame = buffer.tobytes()
            
            time.sleep(1/30) # Vitesse 30 FPS pour un stream plus fluide
            
        if cap:
            cap.release()
            
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
        
    def get_frame(self):
        with self.lock:
            return self.latest_frame

processor = VisionProcessor()
