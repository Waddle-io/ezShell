#set document(title: "Roadmap ezShell", author: "Emmanuel Bayaro")
#set page(
  paper: "a4",
  margin: (x: 2.5cm, y: 2.5cm)
)

#set text(
  font: ("Inter", "Liberation Sans"),
  size: 10pt,
  fill: black,
  lang: "fr"
)

#set par(justify: true, leading: 0.65em)
#set heading(numbering: "1.")

// --- Titre Simple ---
#align(center)[
  #text(size: 20pt, weight: "bold")[ezShell — Roadmap] \
  #v(4pt)
  #text(size: 10pt)[Emmanuel Bayaro • 16 - 17 Octobre 2026]
]

#v(8pt)
#line(length: 100%, stroke: 0.5pt + black)
#v(8pt)

= Ce qui est fait (Aujourd'hui)

- *Launcher dynamique* : Recherche immédiate, suppression des textes statiques git.
- *Historique shell* : Lecture automatique de la dernière commande (.bash_history, .zsh_history).
- *Hooks shell* : Intégration automatique (`ezsh init --install`) et raccourci global `Alt+E`.
- *Sécurité* : Masquage automatique des clés d'API et tokens (`redact.py`).
- *Internationalisation* : Interface bilingue Français / Anglais (`i18n.py`).
- *Affichage* : Commande en haut et nettoyage du formatage de l'IA.

= Ce que je fais aujourd'hui (Validation)

- [ ] Tester le hook en local (`ezsh init --install` puis `source ~/.bashrc` ou `~/.zshrc`).
- [ ] Tester le raccourci `Alt+E` après une commande en erreur (ex: `git pushh`).
- [ ] Vérifier que le fichier `.env.local` est bien ignoré par git.
- [ ] Mettre à jour les instructions de démarrage dans le README.

= Ce que le collègue fait demain (Distribution)

- [ ] *Script d'installation* : Créer `install.sh` exécutable via curl en une ligne.
- [ ] *Packaging PyPI* : Configurer la publication pip (`pyproject.toml`).
- [ ] *Multi-plateformes* : Vérifier le comportement sur d'autres distributions Linux et macOS.

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
