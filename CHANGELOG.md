# Changelog

Notes de version en langage utilisateur. `ezsh --update` les affiche avant la mise à jour ;
elles alimentent aussi la release GitHub. `web/data/releases.json` en est la copie lisible par le
serveur (un test vérifie que les deux restent identiques).

Comment publier : mettre à jour `src/__init__.py` et ce fichier, passer la version à
`"status": "released"` dans `web/data/releases.json`, pousser le tag `vX.Y.Z`
(la CI publie sur PyPI), puis déployer le site.

## 0.3.3

### À noter en premier

- La connexion au site change : vous serez déconnecté une seule fois et devrez vous reconnecter. Vos terminaux déjà connectés avec `ezsh login` continuent de fonctionner, sans rien refaire.

### Nouveautés

- Nouveau système de connexion web (lien magique par e-mail ou GitHub), plus sûr et plus fiable.
- Connexion d'un terminal : après vous être connecté sur la page d'activation, vous approuvez explicitement le code affiché, ce qui évite qu'un lien piégé connecte l'appareil d'un tiers.

### Corrections

- Les liens de connexion envoyés par e-mail pointent toujours vers l'adresse officielle du site.

## 0.3.2

### À noter en premier

- La connexion au site change : vous serez déconnecté une seule fois et devrez vous reconnecter. Vos terminaux déjà connectés avec `ezsh login` continuent de fonctionner, sans rien refaire.

### Nouveautés

- Nouveau système de connexion web (lien magique par e-mail ou GitHub), plus sûr et plus fiable.
- Connexion d'un terminal : après vous être connecté sur la page d'activation, vous approuvez explicitement le code affiché, ce qui évite qu'un lien piégé connecte l'appareil d'un tiers.

### Corrections

- Les liens de connexion envoyés par e-mail pointent toujours vers l'adresse officielle du site.

## 0.3.1

### Corrections

- Correction du flux de connexion CLI et des liens d'activation qui pouvaient pointer vers `localhost`.
- Correction de l'affichage des pages `/login` et `/activate`.
- Renforcement de la validation des connexions GitHub et des liens magiques.

## 0.3.0

### Nouveautés

- Authentification CLI et web avec activation sécurisée des appareils.
- Comptes utilisateurs, tableau de bord, quotas et console d'administration.
- Raccourcis clavier personnalisables avec détection des conflits.

### Corrections

- Compatibilité améliorée du shell hook avec Bash, PowerShell et Windows.
- Build de production web compatible avec le prerendering Next.js.

## 0.2.0

### Nouveautés

- Nouvelle commande `ezsh --update` : affiche les nouveautés puis demande confirmation avant de mettre à jour.
- Rappel discret (une fois par jour) quand une nouvelle version est disponible.
- Installation depuis PyPI : `pipx install ezshell`.

## 0.1.0

### Nouveautés

- Première version : Alt+E, panneau inline, TUI, fenêtre de bureau, détection de risque.
