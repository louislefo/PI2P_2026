FROM python:3.11-slim-bookworm

WORKDIR /app

# Dépendances système pour OpenCV headless, EasyOCR et PyTorch sur ARM64
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Variables d'environnement pour les chemins (overridables via docker-compose)
ENV CONFIG_PATH=config/settings.json
ENV DB_PATH=data/pi2p.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Créer les dossiers de données au build
RUN mkdir -p data/historique_voiture_entree data/debug_ocr

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
