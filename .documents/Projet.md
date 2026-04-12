# 📑 Dossier Technique - IA Parking Command Center

Ce document détaille l'architecture logicielle et matérielle du système de gestion de parking intelligent du Groupe 3309 (ESILV 2026).

## 1. Stack Technologique (v2.0)

- **Vision** : YOLOv8 Nano ( ultralytics ) + EasyOCR.
- **Backend** : FastAPI (Python 3.11).
- **Frontend** : React.js + Vite + Tailwind CSS + Lucide Icons.
- **Stockage** : SQLite 3 (Centralisé dans `backend/Data/pi2p.db`).
- **Hardware** : GPIOZero (Controlleur Relai + Bouton).

## 2. Architecture de la Base de Données

Le système est passé d'un stockage JSON vers un schéma SQL unifié pour garantir l'intégrité des données et permettre des requêtes complexes :

- **Table `authorized_plates`** : 
    - `plate` (PK) : La plaque normalisée.
    - `owner_name` : Nom du titulaire.
    - `email` : Contact pour notifications.
    - `created_at` / `valid_until` : Gestion de la temporalité des accès.
- **Table `history`** : 
    - Journal complet des passages (Horodatage, Plaque, Statut d'accessibilité, Référence image).

## 3. Logique de Vision & OCR

Le `VisionProcessor` tourne en tâche de fond (`threading.Thread`) pour ne pas ralentir l'API.

### Pipeline de détection :
1. **YOLO Inférence** : On filtre sur les IDs configurés (Car=2, Person=0, etc.).
2. **Filtrage Intelligent** : L'IA dessine les cadres de tous les objets, mais déclenche l'OCR uniquement sur les véhicules (`[2, 3, 5, 7]`).
3. **Optimisation OCR** :
    - Découpe de la zone du véhicule.
    - Passage en noir et blanc (Grayscale) + Seuil adaptatif.
    - Export debug dans `backend/data/debug_ocr`.
4. **Fuzzy Matching** : Comparaison entre le texte lu et la DB via `difflib.get_close_matches` avec un seuil de 0.6.

## 4. Système de Surcharge Hardware (Override)

Une innovation majeure de cette version est la gestion des modes de barrière via `settings.json` :

| Mode | État Relai | Logique IA | Sécurité |
| :--- | :--- | :--- | :--- |
| **Auto** | Impulsionnel | Active | Standard |
| **Always Open** | BLOQUÉ ON | Désactivée | Événementiel |
| **Always Closed** | BLOQUÉ OFF | Désactivée | Sécurité Maximale |

> [!TIP]
> Lorsque le mode est forcé (`Open`/`Lock`), le `VisionProcessor` court-circuite l'OCR pour économiser 80% des ressources CPU du Raspberry Pi.

## 5. Interface de Commande (Frontend)

L'UI a été architecturé pour ressembler à un poste de sécurité industriel :
- **Sidebar Réductible** : Optimisation de l'espace de surveillance.
- **AppRouter** : Séparation stricte de la logique de routage pour une maintenance facilitée.
- **Feedback Temps Réel** : WebSockets pour recevoir l'état du capteur magnétique (porte) et les nouvelles entrées sans recharger la page.

## 6. Déploiement & Sécurité

### Dockerization :
Le projet utilise Docker Compose pour isoler les services. Le volume `/config` permet de persister les réglages et la base de données SQLite en dehors des conteneurs éphémères.

### Hardware : 
Le système détecte l'OS hôte. Sur Windows, un `MockDevice` est utilisé pour simuler le comportement des pins GPIO, permettant le développement sans matériel.