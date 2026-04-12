from ultralytics import YOLO
import cv2

print("Chargement du modèle YOLO...")
# YOLO va télécharger automatiquement "yolov8n.pt" (le modèle très léger et rapide) la première fois
model = YOLO("yolov8n.pt")  

print("Ouverture de la webcam...")
# Le port "0" est généralement la webcam principale sur un PC Windows
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Erreur: Impossible d'accéder à la webcam.")
    exit()

print("Appuyez sur la touche 'q' sur la fenêtre vidéo pour quitter le test.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Erreur de flux vidéo")
        break
        
    # Faire la détection (stream=True améliore les performances vidéo)
    results = model(frame, verbose=False)
    
    # Annoter l'image (dessine les boites de détection, ex: "car", "person")
    annotated_frame = results[0].plot()
    
    # Afficher le résultat dans une vraie fenêtre Windows
    cv2.imshow("PI2P - Test Webcam IA", annotated_frame)
    
    # Attendre la touche 'q' pour quitter
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
