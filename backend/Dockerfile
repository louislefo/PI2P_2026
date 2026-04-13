FROM python:3.11-slim-bookworm

WORKDIR /app

# Dépendances système pour OpenCV headless, EasyOCR sur ARM64
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Variables d'environnement
ENV CONFIG_PATH=config/settings.json
ENV DB_PATH=data/pi2p.db

# Étape 1 : Installer PyTorch CPU-ONLY (pas de CUDA, économise +1.5 Go)
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# Étape 2 : Installer le reste des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Créer les dossiers de données au build
RUN mkdir -p data/historique_voiture_entree data/debug_ocr

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
