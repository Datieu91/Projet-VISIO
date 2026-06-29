# Version propre prête à push

## Commandes recommandées

```bash
git checkout -b fix/clean-citizen-interface
git add .
git commit -m "fix: clean citizen interface and prepare operational GreenBin app"
git push origin fix/clean-citizen-interface
```

Puis créer une Pull Request vers `main`.

## Installation locale

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scripts\reset_database.py
python app.py
```

Ouvrir ensuite :

```text
http://127.0.0.1:5000/citoyen
```

## Comptes de test

```text
agent / agent123
admin / admin123
```

## Routes principales à vérifier

- `/citoyen`
- `/login`
- `/agent`
- `/dashboard`
- `/route-planning`
- `/bin-locations`
- `/dataset`
- `/evaluation`
- `/conformity`
- `/admin/settings`

## Nettoyage effectué

- Suppression de la base SQLite locale `data/db/*.db`.
- Conservation des fichiers `.gitkeep` dans `data/db` et `data/uploads`.
- Suppression des dossiers de maquettes statiques obsolètes.
- Suppression des caches Python.
- Conservation du dataset d'exemple dans `data/raw`, `data/processed` et des CSV d'annotations.
