# Plan d'implémentation : Refonte "SaaS Moderne" de l'Agent

Suite à votre demande, nous allons transformer l'interface Agent (actuellement très minimaliste et centrée sur l'image) en une véritable plateforme SaaS professionnelle.

## Objectifs de la refonte
1.  **Architecture SaaS :** Introduction d'un menu latéral (Sidebar) pour naviguer entre les différents espaces (Modération, Dashboard).
2.  **Affichage permanent des métadonnées :** Suppression de la touche `Shift`. Les informations techniques seront toujours visibles dans un panneau latéral dédié pour accélérer la prise de décision.
3.  **Espaces clairement définis :** Utilisation de "Cards" (cartes avec bordures subtiles et ombres) pour séparer l'image, les contrôles, et les données.
4.  **Intégration du Dashboard :** Création d'une nouvelle vue contenant de faux graphiques (Chart.js) et une maquette de carte pour prévisualiser la vue "Décideur".

## Proposed Changes

### [MODIFY] templates/agent.html
Le layout global va drastiquement changer. Nous passerons d'un écran 100% image à une disposition en grille (Grid/Flexbox) :
- **Sidebar (Gauche) :** Menu de navigation ("Modération", "Dashboard").
- **Header (Haut) :** Barre de recherche, Profil, et KPIs globaux.
- **Espace "Modération" (Grille centrale) :**
  - **Zone 1 (Large) :** L'image à modérer avec les boutons d'action en dessous.
  - **Zone 2 (Étroite, à droite) :** Panneau permanent affichant toutes les métadonnées (ID, GPS, Poids, Couleur, Prédiction IA).
- **Espace "Dashboard" (Caché par défaut) :**
  - Grille de widgets (KPIs, Graphique d'évolution simulé, Carte des points chauds).

### [MODIFY] static/css/agent.css
- Abandon du design "brutaliste/terminal" pur pour un design SaaS "Premium" (Bordures très fines, ombres douces `box-shadow`, coins légèrement arrondis `border-radius: 12px` - à moins que vous ne souhaitiez conserver les angles 100% droits ?).
- Mise en place des layouts CSS Grid pour la séparation claire des espaces.

### [MODIFY] static/js/agent.js
- Ajout de la logique de navigation (pour passer de la vue Modération à la vue Dashboard sans recharger la page).
- Ajout de la librairie **Chart.js** via CDN pour injecter les exemples de graphiques dans la vue Dashboard.
- Adaptation du script pour remplir les métadonnées dans le nouveau panneau fixe au lieu de l'overlay conditionnel.

---

## User Review Required

> [!IMPORTANT]
> Avant de commencer à coder cette refonte massive :
> 1. **Esthétique globale :** Pour un look "SaaS Moderne", la norme est d'utiliser des coins légèrement arrondis et des ombres douces. Êtes-vous d'accord pour que j'abandonne le style "Brutaliste sans aucune courbe" que nous avions mis en place précédemment, ou souhaitez-vous garder les angles stricts à 90° dans ce nouveau layout ?
> 2. Le plan vous convient-il globalement pour lancer l'implémentation ?
