trouver le pi :
arp -a
ssh admin@ip # 192.168.137.250


voir les cam :
v4l2-ctl --list-devices
rpicam-still --list-cameras

Sur le Raspberry Pi, lancer docker compose build → doit compiler sans erreur.
docker compose up -d → les deux services (api + dashboard) doivent être healthy.
Accéder au dashboard via http://<IP_PI>:80 → page chargée.
Le flux vidéo http://<IP_PI>:8000/video_feed → doit streamer.
Vérifier que la base SQLite persiste après docker compose down && docker compose up -d.

