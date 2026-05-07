FROM python:3.11-slim

# Dépendances système :
#   build-essential → gcc requis pour compiler les extensions Python (lgpio, etc.)
#   alsa-utils      → aplay pour la sortie audio jack 3.5mm
#   lgpio           → librairie GPIO moderne (remplace RPi.GPIO, préféré par gpiozero 2.x)
RUN apt-get update && apt-get install -y \
    build-essential \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances Python
#   lgpio     → pin factory moderne pour gpiozero sur Pi 4
#   gpiozero  → abstraction haut niveau LEDs, Servo, etc.
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    gpiozero \
    lgpio \
    pydantic


COPY . .

EXPOSE 8083

CMD ["python", "-u", "main.py"]
