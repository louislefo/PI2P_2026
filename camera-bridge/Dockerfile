FROM debian:bookworm-slim

# Outils de base + Python (pour le serveur MJPEG)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg curl ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*

# Ajout du dépôt officiel Raspberry Pi (nécessaire pour rpicam-apps)
RUN curl -fsSL https://archive.raspberrypi.com/debian/raspberrypi.gpg.key \
    | gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] https://archive.raspberrypi.com/debian/ bookworm main" \
    > /etc/apt/sources.list.d/raspberrypi.list

# Installation de rpicam-apps-lite (sans preview GUI) + libcamera
RUN apt-get update && apt-get install -y --no-install-recommends \
    rpicam-apps-lite \
    libcamera0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY bridge.py .

EXPOSE 8081

CMD ["python3", "-u", "bridge.py"]
