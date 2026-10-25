# Changelog

Notes de version en langage utilisateur. `ezsh --update` les affiche avant la mise à jour ;
elles alimentent aussi la release GitHub. `web/data/releases.json` en est la copie lisible par le
serveur (un test vérifie que les deux restent identiques).

Comment publier : mettre à jour `src/__init__.py` et ce fichier, passer la version à
`"status": "released"` dans `web/data/releases.json`, pousser le tag `vX.Y.Z`
(la CI publie sur PyPI), puis déployer le site.

## 0.2.0

### Nouveautés

- Nouvelle commande `ezsh --update` : affiche les nouveautés puis demande confirmation avant de mettre à jour.
- Rappel discret (une fois par jour) quand une nouvelle version est disponible.
- Installation depuis PyPI : `pipx install ezshell`.

## 0.1.0

### Nouveautés

- Première version : Alt+E, panneau inline, TUI, fenêtre de bureau, détection de risque.
