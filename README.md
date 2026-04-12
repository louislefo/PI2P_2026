#  PI2P 2026 - Parking Automatisé (Groupe 3309)

[![Groupe](https://img.shields.io/badge/Groupe-3309-blue.svg)](#)
[![Stack](https://img.shields.io/badge/Stack-YOLOv8%20%7C%20FastAPI%20%7C%20React-success)](#)
[![Device](https://img.shields.io/badge/Device-Raspberry%20Pi%204-red)](#)

Bienvenue dans le dépôt du projet de parking automatisé pour l'ESILV.
Ce projet fournit une solution clé en main utilisant la vision par ordinateur pour détecter les plaques d'immatriculation et autoriser l'accès via le port GPIO du Raspberry Pi.

## 🌟 Fonctionnalités

- **IA Haute Performance :** Utilise YOLOv8 Nano pour détecter les voitures, les humains et les vélos en temps réel.
- **LPR (License Plate Recognition) :** Lecture de plaques via EasyOCR avec traitement d'image dynamique (Noire/Blanc + Zoom 2X).
- **Fuzzy Matching :** Algorithme de correction d'erreurs d'IA (difflib) permettant d'ouvrir le portail même si l'OCR fait une faute de lecture (ex: `1790S` au lieu de `GV179DS`).
- **Contrôle Hardware & Simulation (Windows) :** Gestion réelle sur Raspberry Pi (GPIO) ou Simulation automatique sur Windows (Mock GPIO).
- **Dashboard Moderne :** Interface React ultra-fluide (30 FPS) avec historique de passage et gestion des plaques en direct.

## 🗂️ Architecture

```text
├── config/
│   ├── settings.json       # Configuration des plaques et des pins
│   └── history.json        # Historique automatique des accès
├── backend/
│   ├── main.py             # Point d'entrée FastAPI
│   ├── core/               # Configuration et Simulation Hardware
│   ├── services/           # Logique Vision (YOLO + OCR + Fuzzy)
│   ├── routers/            # Endpoints API (Status, Caméra, Config)
│   └── debug_ocr/          # Dossier généré pour le debug visuel de l'IA
└── frontend/
    ├── src/                # UI React + Tailwind v4
    └── vite.config.js
```

## 🚀 Démarrage Rapide (Windows)

### 1. Prérequis
- **Python 3.11+** installé.
- **Node.js** installé.
- Une **Webcam** branchée.

### 2. Configuration du Backend
```bash
# Ouvrir un terminal dans le dossier /backend
python -m venv .venv
.\.venv\Scripts\activate

# Installation des dépendances (YOLO, EasyOCR, FastAPI)
pip install -r requirements.txt

# Lancement du serveur
uvicorn main:app --reload
```
> [!TIP]
> Sur Windows, le terminal affichera `⚠️ Activation du MOCK GPIO`. C'est normal, cela permet de tester le logiciel sans Raspberry Pi.

### 3. Configuration du Frontend
```bash
# Ouvrir un second terminal dans le dossier /frontend
npm install
npm run dev
```

### 4. Utilisation
1. Ouvrez votre navigateur sur `http://localhost:5173`.
2. Allez dans le panneau **"Plaques Autorisées"** et ajoutez votre plaque (ex: `GV-179-DS`).
3. Placez-vous ou une photo de voiture devant la webcam.
4. L'IA détectera la voiture, tentera une lecture OCR, et ouvrira le portail si le score de ressemblance est > 50%.

## 🛠️ Débogage de l'IA (Vision)
Si l'IA ne lit pas bien votre plaque, consultez le dossier `backend/debug_ocr/`. 
Le système y enregistre automatiquement l'image agrandie et nettoyée qu'il a tenté de lire. Cela vous permet de voir si l'image est trop floue ou mal cadrée.

---
## 🐳 Déploiement Docker (Raspberry Pi)
Pour une installation de production sur Raspberry Pi 4 :
```bash
docker-compose up --build -d
```
L'application sera alors accessible sur le port 80 de l'IP du Pi.