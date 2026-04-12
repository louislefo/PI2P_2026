import cv2
import threading
import time
import requests
import re
from ultralytics import YOLO
from core.config import load_config
import logging

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

    def _trigger_access(self, plate):
        try:
            # On demande au router d'ouvrir la porte et de faire l'historique
            requests.post("http://127.0.0.1:8000/api/system/access", json={"plate": plate})
        except Exception as e:
            print(f"⚠️ Erreur déclenchement trigger: {e}")

    def _process_plate(self, raw_text):
        # Nettoyage : Retire les espaces et autres caractères louches
        text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
        if len(text) < 4: return False
        
        print(f"\n🔍 [OCR] Texte brut lu sur la plaque : '{raw_text}' -> Formaté : '{text}'")
        
        plates = self.config.get("authorized_plates", [])
        normalized_plates = [re.sub(r'[^A-Z0-9]', '', p.upper()) for p in plates]
        
        if text in normalized_plates:
            print(f"✅ [ACCÈS AUTORISÉ] La plaque '{text}' est enregistrée ! Ouverture du Portail...")
            threading.Thread(target=self._trigger_access, args=(text,), daemon=True).start()
            return True
        else:
            print(f"❌ [ACCÈS REFUSÉ] La plaque '{text}' n'est pas connue du système.")
            
        return False

    def _run(self):
        source = self.config.get("camera_source", 0)
        cap = cv2.VideoCapture(source)
        
        if not cap.isOpened() and source != 0:
            cap = cv2.VideoCapture(0)
            
        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            annotated_frame = frame.copy()
            if self.model:
                # 0 = humain, 1 = velo, 2 = voiture
                results = self.model(frame, classes=[0, 1, 2], verbose=False) 
                annotated_frame = results[0].plot()
                
                # --- LANCEMENT OCR INTELLIGENT ---
                current_time = time.time()
                # On limite l'OCR à 1 fois toutes les 2 secondes pour éviter le lag video
                if self.reader and (current_time - self.last_ocr_time > 2.0):
                    boxes = results[0].boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        if cls_id == 2:  # Filtre OCR : On ne scanne la plaque QUE sur les voitures (2)
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            
                            # On passe la voiture ENTIÈRE à l'OCR pour ne pas risquer de couper la plaque au montage
                            roi_y1 = y1
                            car_roi = frame[y1:y2, x1:x2]
                            
                            if car_roi.shape[0] > 10 and car_roi.shape[1] > 10: 
                                print("🚗 [INFO] Voiture détectée ! Tentative de lecture de plaque...")
                                
                                # -- LIGNE DE DEBUG : Sauvegarder l'historique brut --
                                import os
                                os.makedirs("debug_ocr", exist_ok=True)
                                
                                # AMÉLIORATION OCR : Traitement d'image pour aider EasyOCR
                                # 1. Passage en niveaux de gris
                                gray = cv2.cvtColor(car_roi, cv2.COLOR_BGR2GRAY)
                                
                                # 2. Agrandissement de l'image (X2) pour mieux voir les pixels
                                enlarged = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                                
                                # 3. Filtre de contraste (Optionnel, on essaye d'abord juste le zoom+gris)
                                cv2.imwrite(f"debug_ocr/roi_{int(current_time)}.jpg", enlarged)
                                
                                # 4. OCR DANS UN THREAD (Pour ne jamais bloquer la vidéo)
                                self.last_ocr_time = current_time # Verrouillage immédiat pour ne pas lancer 100 threads
                                threading.Thread(target=self._run_ocr_thread, args=(enlarged, x1, roi_y1, annotated_frame.copy()), daemon=True).start()
                                break
                    self.last_ocr_time = max(self.last_ocr_time, current_time)

            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            if ret:
                with self.lock:
                    self.latest_frame = buffer.tobytes()
            
            time.sleep(1/30) # Vitesse 30 FPS pour un stream plus fluide
            
        if cap:
            cap.release()
            
    def _run_ocr_thread(self, image, x, y, debug_frame):
        import difflib
        
        allowed_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
        ocr_results = self.reader.readtext(image, allowlist=allowed_chars)
        plate_found = False
        
        if len(ocr_results) == 0:
            print("   -> [OCR] Aucun texte détecté sur l'image coupée.")
        else:
            for (bbox, raw_text, prob) in ocr_results:
                print(f"   -> [OCR DIAGNOSTIC] '{raw_text}' (Probabilité: {prob:.2f})")
                
                # Nettoyage
                text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
                if len(text) < 4: continue
                
                plates = self.config.get("authorized_plates", [])
                normalized_plates = [re.sub(r'[^A-Z0-9]', '', p.upper()) for p in plates]
                
                # FUZZY MATCHING : Accepte les fautes de frappe de l'OCR !
                best_match = None
                best_ratio = 0
                for auth_plate in normalized_plates:
                    ratio = difflib.SequenceMatcher(None, text, auth_plate).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = auth_plate
                
                print(f"\n🔍 [OCR] Lu: '{text}' | Meilleure correspondance: '{best_match}' (Score: {int(best_ratio*100)}%)")
                
                # Tolérance de 50% de similarité (parfait pour GV179DS -> 1790S)
                score_minimum = 0.50
                
                if best_ratio >= score_minimum:
                    print(f"✅ [ACCÈS AUTORISÉ] La reconnaissance floue valide '{best_match}' ! Ouverture du Portail...")
                    # Update OCR delay because it's a match
                    self.last_ocr_time = time.time() + 10.0
                    threading.Thread(target=self._trigger_access, args=(best_match,), daemon=True).start()
                    plate_found = True
                    break
                else:
                    print(f"❌ [ACCÈS REFUSÉ] Trop éloigné d'une plaque connue.")
        
    def get_frame(self):
        with self.lock:
            return self.latest_frame

processor = VisionProcessor()
