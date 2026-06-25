# GreenBin / VISIO — version stable

Cette version corrige les bugs de navigation, sépare les interfaces par rôle, utilise une base propre et optimise les cartes sans les masquer.

## Pages

- `/citoyen` : signalement public avec upload + carte toujours affichée
- `/login` : connexion agent/admin
- `/agent` : modération protégée agent/admin
- `/dashboard` : statistiques protégées admin
- `/logout` : déconnexion

## Comptes de test

- Agent : `agent / agent123`
- Admin : `admin / admin123`

## Lancer le projet

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Puis ouvrir :

```text
http://127.0.0.1:5000/citoyen
```

## Mode développeur

Pour ne pas être ralenti par la connexion pendant le développement :

```powershell
$env:GREENBIN_DEV_BYPASS="1"
python app.py
```

## Base de données propre

Cette version utilise une nouvelle base :

```text
data/db/greenbin_live.db
```

Elle est vide au démarrage. Les anciennes images déjà présentes venaient généralement de l'ancien fichier `data/db/wdp.db` ou d'une base locale déjà seedée.

Pour réinitialiser complètement :

```powershell
python scripts\reset_database.py
```

Pour vérifier le contenu de la base :

```powershell
python scripts\check_database.py
```

## Cartes optimisées

Les cartes restent affichées en permanence sur :

- `/citoyen` : carte centrée sur l'utilisateur, point bleu = position réelle, marqueur vert = position du signalement.
- `/dashboard` : carte des zones avec marqueurs légers.

Optimisations appliquées :

- Leaflet chargé seulement sur les pages qui ont une carte.
- Fond de carte CARTO sombre plus moderne.
- `preferCanvas` sur la carte dashboard.
- Marqueurs légers côté dashboard.
- Limite de points dans `/api/map-reports`.
- Désactivation du zoom molette par défaut pour limiter les chargements involontaires.

## Parcours de test

1. Aller sur `/citoyen`.
2. Uploader une image et vérifier la position sur la carte.
3. Envoyer le signalement.
4. Se connecter avec `agent / agent123`.
5. Aller sur `/agent` et modérer l'image.
6. Se connecter avec `admin / admin123`.
7. Aller sur `/dashboard` et vérifier les KPI + carte.

## Mise à jour UI moderne

Cette version améliore uniquement l’ergonomie et la lisibilité de l’interface :

- nouvelle sidebar plus claire avec accès par rôle ;
- interface citoyen réorganisée en parcours Photo → Position → Envoi ;
- carte citoyen toujours visible, plus lisible, avec point utilisateur et marqueur de signalement ;
- modération agent plus lisible avec grande zone image, actions visibles et panneau technique à droite ;
- dashboard modernisé avec KPI, courbe, carte des zones à risque et tableau des derniers signalements ;
- CSS nettoyé pour éviter les styles en doublon et améliorer la cohérence visuelle ;
- conservation des routes et des identifiants HTML utilisés par le JavaScript existant.

Les accès restent inchangés :

- citoyen : `/citoyen`, accès public ;
- agent : `/agent`, compte `agent / agent123` ;
- admin : `/dashboard`, compte `admin / admin123`.


## Dernières fonctionnalités ajoutées

- Correction / annulation des annotations agent depuis l’espace de modération.
- Contrôle qualité image avant envoi côté citoyen : poids, dimensions, luminosité et flou approximatif.
- Blocage serveur des images trop petites ou de qualité trop faible.
- Filtres dashboard : statut, état vide/pleine, niveau de risque, période et zone/tag.
- Les KPI, le tableau et la carte du dashboard se mettent à jour selon les filtres appliqués.

## Fonctionnalités ajoutées : export, dataset et évaluation

Cette version ajoute trois éléments importants pour rendre le projet plus exploitable par une collectivité et plus aligné avec les attendus d’évaluation.

### Export CSV des signalements

Dans le dashboard admin, le bouton **Exporter CSV** permet de télécharger les signalements visibles avec les filtres actifs.

Route :

```text
/exports/reports.csv
```

Le fichier exporté contient notamment : ID, date, statut, annotation agent, prédiction automatique, confiance, score de risque, localisation, tags, image, dimensions, luminosité, contraste et qualité image.

### Page Dataset

Une nouvelle page admin est disponible :

```text
/dataset
```

Elle affiche :

- le nombre d’images dans `data/annotations.csv` ;
- la répartition des labels `vide` / `pleine` ;
- le split `train` / `test` ;
- le nombre de signalements importés en base ;
- les commandes utiles pour préparer et importer le jeu de données.

Scripts utiles :

```powershell
python scripts\prepare_dataset.py
python scripts\dataset_summary.py
python scripts\enrich_and_seed_dataset.py --seed-db --reset
```

Pour importer quelques images en attente afin de tester la modération :

```powershell
python scripts\enrich_and_seed_dataset.py --seed-db --reset --pending-count 6
```

### Évaluation des règles

Une nouvelle page admin est disponible :

```text
/evaluation
```

Elle calcule les métriques entre l’annotation humaine et la prédiction automatique :

- accuracy ;
- precision ;
- recall ;
- matrice de confusion.

Script équivalent en terminal :

```powershell
python scripts\evaluate_rules.py
```

Ces métriques sont à utiliser dans le rapport pour justifier la partie “résultats de classification”.
