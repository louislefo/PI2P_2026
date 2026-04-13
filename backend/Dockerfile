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

# ──── INSTALLATION PYTHON EN UNE SEULE COUCHE (optimise l'espace disque) ────
# 1. PyTorch CPU-only depuis le repo officiel CPU (pas de CUDA = ~200Mo au lieu de 1.5Go)
# 2. requirements.txt (torch déjà satisfait, pip ne re-télécharge pas)
# 3. lgpio pour GPIO natif du Pi
# 4. Nettoyage : supprime opencv-python (non-headless dupliqué par ultralytics)
COPY requirements.txt .
RUN pip install --no-cache-dir \
        torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir lgpio 2>/dev/null || true && \
    pip uninstall -y opencv-python 2>/dev/null || true && \
    find /usr/local/lib/python3.11 -name '*.pyc' -delete && \
    find /usr/local/lib/python3.11 -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

COPY . .

# Créer les dossiers de données
RUN mkdir -p data/historique_voiture_entree data/debug_ocr

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
