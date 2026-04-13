FROM python:3.11-slim-bookworm

WORKDIR /app

# Dépendances système pour OpenCV headless + EasyOCR sur ARM64
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Variables d'environnement
ENV CONFIG_PATH=config/settings.json
ENV DB_PATH=data/pi2p.db

# ──── ÉTAPE 1 : PyTorch CPU-ONLY ────
# Sur le Pi il n'y a pas de GPU NVIDIA, donc on installe la version CPU
# qui fait ~200 Mo au lieu de +1.5 Go (CUDA inutile)
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# ──── ÉTAPE 2 : Dépendances Python ────
# torch est déjà installé, pip skip la dépendance CUDA de ultralytics/easyocr
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ──── ÉTAPE 3 : Lib GPIO spécifique au Pi (Linux-only) ────
RUN pip install --no-cache-dir lgpio || echo "lgpio non disponible, fallback mock GPIO"

COPY . .

# Créer les dossiers de données
RUN mkdir -p data/historique_voiture_entree data/debug_ocr

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
