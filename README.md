# Projet VISIO · GreenBin / WDP SaaS

Version corrigée pour Nicolas.

## Changements principaux

- Lancement Flask stabilisé : création automatique de `data/db` et `data/uploads`.
- Upload image sécurisé : extensions autorisées, nom de fichier sécurisé, limite de taille.
- Base SQLite avec SQLAlchemy.
- Extraction de caractéristiques image avec Pillow/OpenCV.
- Classification par règles.
- Scoring de risque.
- Interface WDP SaaS restaurée : Signalement, Modération, Dashboard.
- Suppression de la page About.
- Dashboard restauré dans l'esprit de la maquette d'origine : cartes KPI, courbe d'évolution, zone chaude mockup, tableau des derniers signalements.

## Installation Windows

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Pages disponibles

- `http://127.0.0.1:5000/citoyen` : envoyer un signalement.
- `http://127.0.0.1:5000/agent` : modérer les images.
- `http://127.0.0.1:5000/dashboard` : visualiser les statistiques.

## Parcours de test

1. Ouvrir `/citoyen`.
2. Envoyer une image.
3. Ouvrir `/agent` pour valider l'image.
4. Ouvrir `/dashboard` pour voir les statistiques mises à jour.


## Mise à jour carte moderne

Les cartes `/citoyen` et `/dashboard` utilisent maintenant un style plus moderne : fond sombre par défaut, bascule sombre/clair, marqueur citoyen personnalisé, marqueurs de risque avec couleurs et effet de pulsation pour les zones à risque élevé.

Une connexion Internet est nécessaire pour charger les tuiles de carte.
