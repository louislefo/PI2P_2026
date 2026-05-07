FROM python:3.11-slim

# Dépendances système : ALSA (aplay pour le jack audio) + RPi.GPIO
RUN apt-get update && apt-get install -y \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances Python
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    gpiozero \
    RPi.GPIO \
    pydantic

COPY app.py .

EXPOSE 8083

CMD ["python", "-u", "app.py"]
