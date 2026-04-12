# 🅿️ PI2P 2026 - Central Command Center (Groupe 3309)

[![Groupe](https://img.shields.io/badge/Groupe-3309-blue.svg)](#)
[![Stack](https://img.shields.io/badge/Stack-YOLOv8--EasyOCR--FastAPI--React-success)](#)
[![Database](https://img.shields.io/badge/Database-SQLite-orange)](#)
[![Device](https://img.shields.io/badge/Device-Raspberry%20Pi%204-red)](#)

Système de gestion de parking intelligent de nouvelle génération. Alie la puissance de la vision par ordinateur (YOLOv8) à une interface de commandement industrielle pour une gestion fluide des accès ESILV.

## 🌟 Nouvelles Fonctionnalités (v2.0)

- **Command Center Unifié :** Interface full-screen avec flux vidéo 30 FPS et annotations IA en temps réel.
- **Base de Données Centralisée (SQLite) :** Migration des fichiers JSON vers une base `pi2p.db` robuste gérant les plaques, les noms, les emails et les dates de validité.
- **Gestion Expirelle :** Autorisations temporaires avec suppression automatique ou blocage à expiration.
- **Système de Surcharge Hardware (Override) :** 
    - `Auto` : IA pilotée par plaques.
    - `Always Open` : Forçage physique du relai (Pin 17) ouvert.
    - `Always Closed` : Blocage de sécurité de toute intrusion.
- **Code d'Entrée Physique :** Digicode numérique configurable depuis le dashboard.
- **IA Modulaire :** Choisissez en temps réel ce que l'IA doit surveiller (Voitures, Motos, Personnes, Animaux).

## 🗂️ Architecture du Projet

```text
├── backend/
│   ├── Data/
│   │   └── pi2p.db           # Base SQLite unique (Historique + Plaques)
│   ├── core/                 # Hardware (GPIO) et Config
│   ├── services/             # VisionProcessor (YOLO + OCR dynamique)
│   └── routers/              # API Rest et WebSockets pour le live
├── config/
│   └── settings.json         # Paramètres matériels et système (Mode, Code)
└── frontend/
    ├── src/
    │   ├── routes/           # Nouveau système de routage modulaire
    │   ├── components/views/ # Les 4 modules (Dashboard, DB, Logs, Settings)
    │   └── App.jsx           # Etat central et gestion WebSocket
```

## 🚀 Installation Express

### 1. Backend (Python 3.11+)
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### 2. Frontend (Node.js)
```bash
cd frontend
npm install
npm run dev
```

## 🛠️ Utilisation du Command Center

1. **Dashboard** : Surveillez le flux vidéo. Le bouton "Ouvrir" force l'ouverture logicielle pour 5 secondes.
2. **Base de Données** : Enregistrez les véhicules autorisés avec leurs coordonnées.
3. **Paramètres** : 
    - Changez le **Gate Mode** pour forcer le portail ouvert lors d'un événement.
    - Configurez les objets à détecter (ex: activer la détection "Personne" pour la sécurité nocturne).
    - Modifiez le code PIN du digicode.

## 🐳 Docker
Le projet est prêt pour le déploiement industriel via Docker Compose sur Raspberry Pi 4.
```bash
docker-compose up --build -d
```

---
*Projet réalisé dans le cadre de l'A3 PI2P à l'ESILV par le Groupe 3309.*