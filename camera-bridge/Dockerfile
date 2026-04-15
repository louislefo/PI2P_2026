FROM debian:bookworm-slim

# Outils de base + Python (pour le serveur MJPEG)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg curl ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*

# Ajout du dépôt officiel Raspberry Pi
RUN curl -fsSL https://archive.raspberrypi.com/debian/raspberrypi.gpg.key \
    | gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] https://archive.raspberrypi.com/debian/ bookworm main" \
    > /etc/apt/sources.list.d/raspberrypi.list

# ─── APT Pinning ────────────────────────────────────────────────────────────
# Debian Bookworm ship libcamera0.5 + libcamera-ipa qui CASSENT libcamera0 du Pi.
# On force le dépôt Pi (priorité 1001 > 500) pour tous les paquets libcamera*/rpicam*
# → apt choisira les versions Pi compatibles entre elles.
RUN printf '\
Package: libcamera*\n\
Pin: origin "archive.raspberrypi.com"\n\
Pin-Priority: 1001\n\
\n\
Package: rpicam*\n\
Pin: origin "archive.raspberrypi.com"\n\
Pin-Priority: 1001\n\
' > /etc/apt/preferences.d/99-raspberrypi-camera

# Installation — libcamera0 sera tiré automatiquement comme dépendance de rpicam-apps-lite
RUN apt-get update && apt-get install -y --no-install-recommends \
    rpicam-apps-lite \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY bridge.py .

EXPOSE 8081

CMD ["python3", "-u", "bridge.py"]
