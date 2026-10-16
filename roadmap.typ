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
  #text(size: 20pt, weight: "regular", font: "Space Grotesk")[#text(weight: "bold")[ezShell] Roadmap] ]

#v(8pt)
#line(length: 100%, stroke: 0.5pt + black)
#v(8pt)

= Partie I 

- *Launcher dynamique* : Recherche immédiate, suppression des textes statiques git.
- *Historique shell* : Lecture automatique de la dernière commande (.bash_history, .zsh_history).
- *Hooks shell* : Intégration automatique (`ezsh init --install`) et raccourci global `Alt+E`.
- *Sécurité* : Masquage automatique des clés d'API et tokens (`redact.py`).
- *Internationalisation* : Interface bilingue Français / Anglais (`i18n.py`).
- *Affichage* : Commande en haut et nettoyage du formatage de l'IA.


- [] * Test 1* : Tester le hook en local (`ezsh init --install` puis `source ~/.bashrc` ou `~/.zshrc`).
- [] *Test 2* : Tester le raccourci `Alt+E` après une commande en erreur (ex: `git pushh`).
- [] *Vérification* : Vérifier que le fichier `.env.local` est bien ignoré par git.
- [] *Mise à jour* : Mettre à jour les instructions de démarrage dans le README.
- [] *Script d'installation* : Créer `install.sh` exécutable via curl en une ligne.

= Partie II (Distribution)
- *Packaging PyPI* : Configurer la publication pip (`pyproject.toml`).
- *Multi-plateformes* : Vérifier le comportement sur d'autres distributions Linux et macOS.

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
)
