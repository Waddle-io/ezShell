#set document(title: "Roadmap ezShell", author: "Emmanuel Bayaro")
#set page(
  paper: "a4",
  margin: (x: 2.5cm, y: 2.5cm)
)

#set text(
  font: ("Space Grotesk", "JetBrains Mono NL"),
  size: 10pt,
  fill: black,
  lang: "fr"
)

#set par(justify: true, leading: 0.65em)
#set heading(numbering: "1.")

// --- Titre Simple ---
#align(center)[
  #text(size: 20pt, weight: "regular", font: "Space Grotesk")[#text(weight: "bold")[ezShell]Roadmap]]

#v(8pt)
#line(length: 100%, stroke: 0.5pt + black)
#v(8pt)

= Partie I : Ce qui est fait

- *Launcher dynamique* : Recherche immédiate, suppression des textes statiques git.
- *Historique shell* : Lecture automatique de la dernière commande (.bash_history, .zsh_history).
- *Hooks shell* : Intégration automatique (`ezsh init --install`) et raccourci global `Alt+E`.
- *Sécurité* : Masquage automatique des clés d'API et tokens (`redact.py`).
- *Internationalisation* : Interface bilingue Français / Anglais (`i18n.py`).
- *Affichage* : Commande en haut et nettoyage du formatage de l'IA.
- *Script d'installation* : `install.sh` exécutable via curl en une ligne.
- *Packaging PEP 621* : `pyproject.toml` avec 3 points d'entrée (`ezsh`, `ezshell`, `eszh`), `setup.py` supprimé.
- *Tests* : Suite complète (30/30), hooks, redact, context, safety.
- *Documentation* : `CONTRIBUTING.md` pour la prise en main par un nouveau développeur.

= Partie II : Distribution (à faire)

== pipx / pip (priorité 1)

La méthode la plus directe. Une fois le paquet publié sur PyPI :

#block(
  fill: luma(245),
  inset: 8pt,
  radius: 3pt,
)[
  ```
  pipx install ezshell        # recommandé (environnement isolé)
  pip install ezshell         # alternative
  ```
]

- [ ] Créer un compte PyPI et générer un token d'API.
- [ ] Configurer `~/.pypirc` ou le secret GitHub `PYPI_TOKEN`.
- [ ] Tester `python -m build` puis `twine upload dist/*`.
- [ ] Publier une version `0.1.0` sur PyPI.
- [ ] Vérifier l'installation depuis zéro avec `pipx install ezshell`.

== GitHub Releases + install.sh (priorité 1, déjà en place)

#block(
  fill: luma(245),
  inset: 8pt,
  radius: 3pt,
)[
  ```
  curl -fsSL https://raw.githubusercontent.com/Waddle-io/ezShell/main/install.sh | bash
  ```
]

- *Script* : `install.sh` fonctionnel (clone le repo, crée le venv, symlinks).
- [ ] Associer chaque release GitHub à un tag `vX.Y.Z` avec l'`install.sh` en pièce jointe.
- [ ] Tester le script sur Ubuntu 22.04, Fedora 40, Arch, macOS 14.

== Homebrew : macOS / Linux (priorité 2)

- [ ] Créer un tap personnel : `github.com/Waddle-io/homebrew-ezshell`.
- [ ] Rédiger la `Formula/ezshell.rb` (source PyPI ou archive GitHub).
- [ ] Tester `brew install Waddle-io/ezshell/ezshell`.
- [ ] (Optionnel) Soumettre à `homebrew-core` une fois la v1.0 stable.

== APT : Debian / Ubuntu (priorité 3)

- [ ] Générer un paquet `.deb` avec `fpm` ou `stdeb`.
- [ ] Héberger un dépôt APT via GitHub Pages (ou Cloudflare R2).
- [ ] Permettre : `sudo apt install ezshell` après ajout du dépôt.

== DNF / RPM : Fedora / RHEL (priorité 3)

- [ ] Générer un paquet `.rpm` avec `fpm`.
- [ ] Héberger un dépôt RPM (Copr ou auto-hébergé).
- [ ] Permettre : `sudo dnf install ezshell` après ajout du dépôt.

== AUR : Arch Linux (priorité 3)

- [ ] Créer un `PKGBUILD` pointant vers PyPI.
- [ ] Publier sur AUR (`aur.archlinux.org`) : `yay -S ezshell`.

= Partie III : Automatisation CI/CD

- [ ] Workflow GitHub Actions `release.yml` : build + `twine upload` sur `git tag v*`.
- [ ] Workflow `test.yml` : `pytest` sur push et pull request (Ubuntu + macOS).
- [ ] Badge de statut des tests dans le `README.md`.

= Commandes principales

#table(
  columns: (auto, 1fr),
  stroke: 0.5pt + black,
  inset: 6pt,
  [*Commande*], [*Action*],
  [`ezsh`], [Ouvre l'assistant en mode popup],
  [`ezsh init --install`], [Installe le hook dans le shell actif],
  [`Alt + E`], [Raccourci pour ouvrir ezShell dans le terminal],
  [`ezsh --check-key`], [Vérifie la connexion à l'API Groq],
  [`ezsh --tui`], [Mode terminal sans interface graphique (SSH)],
  [`pipx install ezshell`], [Installation via PyPI (utilisateurs finaux)],
)
