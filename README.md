# 🅿️ PI2P 2026 - Central Command Center

<div align="center">
  <br />
  <p align="center">
    <b>Système de gestion de parking intelligent de nouvelle génération.</b>
    <br />
    Allie la puissance de la vision par ordinateur (YOLOv8) à une interface de commandement industrielle pour une gestion fluide des accès.
  </p>

  [![Groupe](https://img.shields.io/badge/Groupe-3309-blue.svg)](#)
  [![Stack](https://img.shields.io/badge/Stack-YOLOv8--EasyOCR--FastAPI--React-success)](#)
  [![Database](https://img.shields.io/badge/Database-SQLite-orange)](#)
  [![Device](https://img.shields.io/badge/Device-Raspberry%20Pi%204-red)](#)
</div>

---

## 🚀 Vue d'Ensemble

Le projet **PI2P 2026** est une solution complète de contrôle d'accès automatisé. Grâce à l'IA, le système identifie les véhicules, lit leurs plaques d'immatriculation et pilote une barrière physique en fonction des autorisations stockées en base de données.

### 🌟 Fonctionnalités Clés

- ** Vision IA de Pointe** : Détection temps réel (YOLOv8) et reconnaissance de plaques (EasyOCR).
- ** Command Center Industriel** : Dashboard React ultra-réactif avec flux vidéo et overlays IA.
- ** Intercom & Hardware** : Système audio bidirectionnel, digicode physique et gestion de servo-moteur.
- ** Gestion de Base de Données** : Administration complète des plaques autorisées avec dates de validité.
- ** Architecture Distribuée** : Ponts dédiés pour la caméra et le hardware afin de maximiser les performances.

---

## 🛠️ Tech Stack

| Module | Technologies |
| :--- | :--- |
| **IA & Vision** | YOLOv8, EasyOCR, OpenCV |
| **Backend** | FastAPI (Python 3.11), SQLite |
| **Frontend** | React 19, Vite, Tailwind CSS 4, Lucide Icons |
| **Hardware** | Raspberry Pi 4, GPIOZero, Servo, LEDs, Digicode |
| **Déploiement** | Docker, Docker Compose |

---

## 🏗️ Architecture du Projet

Le projet est découpé en services modulaires pour une robustesse maximale :

- `backend/` : Le cerveau. Gère l'IA, l'API centrale et la base de données.
- `frontend/` : L'interface. Dashboard de contrôle et monitoring.
- `camera-bridge/` : Le flux. Capture et diffuse les images de la caméra (CSI ou USB).
- `hardware-bridge/` : Les membres. Contrôle direct des composants physiques (Servo, LEDs, Audio).

> [!IMPORTANT]
> Pour un schéma détaillé des communications entre ces composants, consultez le [**Dossier Technique (.documents/Tech.md)**](./.documents/Tech.md).

---

## 📸 Captures d'Écran

### 📟 Tableau de Bord (Live View)
Interface principale permettant de surveiller le flux vidéo avec les annotations de l'IA en temps réel.
![Tableau de bord](.documents/image_readme/TDB.png)

### 📂 Gestion des Accès
Interface d'administration pour ajouter, modifier ou supprimer des plaques autorisées.
![base de données](.documents/image_readme/basededonnées.png)

### 📜 Journal d'Activité
Historique complet des passages avec horodatage et captures d'écran des plaques détectées.
![Journal d'activité](.documents/image_readme/Historique.png)

---

## ⚡ Installation Rapide

### Avec Docker (Recommandé)
```bash
docker-compose up --build -d
```

### Installation Manuelle

1. **Backend** :
   ```bash
   cd backend && pip install -r requirements.txt
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Frontend** :
   ```bash
   cd frontend && npm install && npm run dev
   ```

3. **Bridges** (Sur Raspberry Pi) :
   Consultez les fichiers `Dockerfile` respectifs pour les instructions spécifiques.

---

<div align="center">
  <p><i>Projet réalisé dans le cadre de l'A3 PI2P à l'ESILV par le Groupe 3309.</i></p>
</div>
