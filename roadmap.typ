#set document(title: "ezShell - Feuille de Route & Plan de Travail", author: "Équipe ezShell")
#set page(
  paper: "a4",
  margin: (x: 2cm, top: 2.2cm, bottom: 2.2cm),
  header: align(right)[
    #text(size: 8.5pt, fill: luma(110))[*ezShell* — Roadmap & Passation Technique]
  ]
)

#set text(
  font: ("Inter", "Liberation Sans"),
  size: 10.5pt,
  fill: black,
  lang: "fr"
)

#set par(justify: true, leading: 0.72em)
#set heading(numbering: "1.1")

// --- Style des titres en noir & blanc ---
#show heading: it => [
  #v(10pt)
  #text(fill: black, weight: "bold")[#it]
  #v(4pt)
]

// --- Header Principal (Noir & Blanc) ---
#block(
  fill: white,
  stroke: 1.5pt + black,
  inset: 16pt,
  radius: 4pt,
  width: 100%,
  [
    #grid(
      columns: (1fr, auto),
      align: (left + horizon, right + horizon),
      [
        #text(size: 22pt, weight: "bold")[ezShell] \
        #v(2pt)
        #text(size: 13pt, weight: "bold")[Feuille de Route & Plan de Développement (2 Jours)] \
        #text(fill: luma(90), size: 9.5pt)[Assistant Terminal & Bureau Intelligent propulsé par Groq LLM]
      ],
      [
        #box(
          stroke: 1pt + black,
          radius: 3pt,
          inset: (x: 10pt, y: 6pt),
          [#text(size: 8.5pt, weight: "bold")[VERSION 0.1.0 • MVP]]
        )
      ]
    )
  ]
)

#v(10pt)

// --- Métadonnées ---
#grid(
  columns: (1fr, 1fr),
  gutter: 12pt,
  [
    #block(fill: luma(250), stroke: 1pt + luma(180), inset: 9pt, radius: 4pt)[
      #text(size: 8pt, fill: luma(90), weight: "bold")[PÉRIODE] \
      #text(weight: "medium")[16 - 17 Octobre 2026]
    ]
  ],
  [
    #block(fill: luma(250), stroke: 1pt + luma(180), inset: 9pt, radius: 4pt)[
      #text(size: 8pt, fill: luma(90), weight: "bold")[PROJET & DÉPÔT] \
      #text(weight: "medium")[Waddle-io / ezShell]
    ]
  ]
)

#v(8pt)

== Synthèse des Travaux Réalisés

Toutes les fondations critiques du système ont été finalisées et déployées sur la branche principale (`main`) :

#block(
  fill: luma(252),
  stroke: 1pt + luma(180),
  inset: 12pt,
  radius: 4pt,
  [
    - *Suppression du texte statique bidon* : Remplacement par un vrai *Launcher dynamique*.
    - *Historique Shell Réel* : Détection automatique de la dernière commande exécutée (`.bash_history`, `.zsh_history`, `$HISTFILE` et `.last_command`).
    - *Hooks Shell & Raccourci Global* : Intégration transparente pour Zsh et Bash avec injection de la combinaison *`Alt+E`*.
    - *Sécurité & Masquage des Secrets* : Implémentation de `src/core/redact.py` pour caviarder les clés API (`gsk_`, `sk-`), tokens et mots de passe.
    - *Internationalisation Bilingue* : Système `src/i18n.py` complet (Français / Anglais) avec auto-détection de locale.
    - *Refonte de l'Affichage* : Formatage épuré des réponses de l'IA (puces nettoyées, commande prioritaire tout en haut, pas de parasites markdown).
  ]
)

#v(8pt)

== Ce Que Je Fais Aujourd'hui (Jour 1 — Finalisation Développeur)

Objectif du jour : consolider l'expérience locale, valider les flux en conditions réelles et préparer une passation sans accroc pour mon collègue.

=== 1. Validation & Prise en Main en Conditions Réelles
- [ ] *Activer le hook shell en local* :
  Exécuter `ezsh init --install` puis recharger la configuration avec `source ~/.bashrc` (ou `~/.zshrc`).
- [ ] *Tester la détection des pannes* :
  Lancer intentionnellement une fausse commande (ex: `git pushh`), puis appuyer sur *`Alt+E`*.
- [ ] *Vérifier l'ouverture du popup* :
  S'assurer que la commande échouée apparaît immédiatement dans l'encart avec le bouton *« Diagnostiquer cette erreur »*.

=== 2. Nettoyage de l'Environnement & Sécurité
- [ ] S'assurer que le fichier `.env.local` contenant la clé Groq personnelle n'est *jamais* commité (`.gitignore` vérifié).
- [ ] Confirmer que `.env.example` contient bien toutes les variables nécessaires (`GROQ_API_KEY`, `EZSHELL_MODEL`, `EZSHELL_LANG`).

=== 3. Préparation de la Passation
- [ ] Vérifier que le `README.md` est clair et permet un onboarding immédiat en moins de 2 minutes.
- [ ] Laisser des notes précises sur les modules clés (`src/core/shell_hook.py`, `src/ui/gui_window.py`).

#v(8pt)

== Ce Que Mon Collègue Fait Demain (Jour 2 — Déploiement & Packaging)

Objectif du jour 2 : automatiser la distribution, faciliter l'installation pour tout nouvel utilisateur et préparer la release publique.

=== 1. Script d'Installation Universel (`install.sh`)
- [ ] Rédiger un script autonome `install.sh` installable en une ligne via curl :
  ```bash
  curl -fsSL https://raw.githubusercontent.com/Waddle-io/ezShell/main/install.sh | bash
  ```
- [ ] Le script doit :
  + Créer l'environnement virtuel dans `~/.local/share/ezshell/venv`.
  + Installer le package et les dépendances Python.
  + Créer un lien symbolique dans `~/.local/bin/ezsh` (ou `/usr/local/bin`).
  + Proposer l'ajout automatique de `eval "$(ezsh init <shell>)"` dans le `.rc`.

=== 2. Packaging PyPI (`pyproject.toml`)
- [ ] Moderniser le packaging de `setup.py` vers un `pyproject.toml` conforme PEP 621.
- [ ] Tester le build de distribution : `python -m build`.
- [ ] Préparer la publication test sur TestPyPI puis PyPI (`pip install ezshell-ai`).

=== 3. Améliorations Optionnelles (Nice-to-Have)
- [ ] *Support Fish Shell* : Valider les hooks Fish dans des environnements réels.
- [ ] *Mode Notification Système* : Proposer une bulle de notification bureau lorsqu'une commande longue en arrière-plan se termine avec une erreur.

#v(10pt)

== Résumé des Commandes Indispensables

#table(
  columns: (auto, 1fr),
  fill: (col, row) => if row == 0 { black } else if calc.even(row) { luma(248) } else { white },
  stroke: 0.5pt + luma(180),
  inset: 7pt,
  [#text(fill: white, weight: "bold")[Commande]], [#text(fill: white, weight: "bold")[Description]],
  [`ezsh`], [Ouvre la fenêtre d'assistance en mode Launcher dynamique],
  [`ezsh init --install`], [Injecte automatiquement le hook dans le shell actif (~/.zshrc ou ~/.bashrc)],
  [`Alt + E`], [Raccourci clavier universel pour appeler ezShell depuis le terminal],
  [`ezsh --check-key`], [Vérifie la validité et la connectivité de la clé API Groq],
  [`ezsh --tui`], [Mode terminal pur (Textual) pour les sessions distantes ou SSH],
)
