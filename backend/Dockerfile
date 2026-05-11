FROM python:3.11-slim-bookworm

WORKDIR /app

# 1. Dépendances système (ne change presque jamais)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -f render && usermod -aG video,render root

# 2. INSTALLATION DE PYTORCH SEULE (La couche la plus lourde)
# On le fait AVANT de copier le requirements.txt
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# ──── INSTALLATION OPTIMISÉE POUR PI (CPU-ONLY) ────
# 1. PyTorch CPU-only (~200Mo au lieu de 1.5Go CUDA)
# 2. opencv-python-headless AVANT les deps (pour que ultralytics ne tire pas la version lourde)
# 3. requirements.txt (torch + opencv déjà satisfaits = pas re-téléchargés)
# 4. lgpio pour GPIO natif Pi (Linux-only, fallback si échec)
# 5. Force-reinstall opencv-python-headless pour écraser toute version non-headless
#    installée par ultralytics/easyocr (les deux partagent le même dossier cv2/)
# 3. Maintenant on copie le requirements.txt
COPY requirements.txt .

# 4. Installation des autres dépendances
# Si tu modifies ton requirements.txt, Docker repartira d'ici, sans toucher à Torch
RUN pip install --no-cache-dir opencv-python-headless && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir lgpio 2>/dev/null || true && \
    pip install --force-reinstall --no-cache-dir opencv-python-headless && \
    find /usr/local/lib/python3.11 -name '*.pyc' -delete

COPY . .

# Créer les dossiers de données et modèles
RUN mkdir -p data/historique_voiture_entree data/debug_ocr data/models

# Variables d'environnement
ENV CONFIG_PATH=config/settings.json
ENV DB_PATH=data/pi2p.db
ENV YOLO_CONFIG_DIR=/app/data/models
ENV EASYOCR_MODULE_PATH=/app/data/models

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
