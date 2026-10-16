#set document(title: "Roadmap", author: "Emmanuel Bayaro")
#set page(
  paper: "a4",
  margin: (x: 2cm, top: 2.2cm, bottom: 2.2cm),
  footer: context {
    let page_number = counter(page).get().first()
    let total_pages = counter(page).final().first()
    align(center)[
      #text(size: 8.5pt, fill: rgb("#94a3b8"))[Page #page_number sur #total_pages]
    ]
  }
)

#set text(
  font: ("Geist", "Inter", "Liberation Sans"),
  size: 10.5pt,
  fill: rgb("#1e293b"),
  lang: "fr"
)

#set par(justify: true, leading: 0.72em)
#set heading(numbering: "1.1")

// --- Couleurs thématiques ezShell ---
#let brand-dark = rgb("#0b121b")
#let brand-blue = rgb("#2563eb")
#let surface-card = rgb("#f8fafc")
#let border-card = rgb("#e2e8f0")

// --- Header Principal ---
#block(
  
  inset: 18pt,
  radius: 4pt,
  width: 100%,
  stroke: 1pt + rgb("#1e293b"),
  [
    #align(center)[
      #text(size: 22pt, weight: "bold")[ezShell Roadmap]
    ]
  ]
)

#v(10pt)

#v(12pt)

== Synthèse des Travaux Réalisés

Toutes les fondations critiques du système ont été finalisées, testées et déployées sur la branche principale (`main`) :

#block(
  fill: surface-card,
  inset: 12pt,
  radius: 6pt,
  stroke: 1pt + border-card,
  [
    - *Suppression du texte statique bidon* : Le faux exemple `git pull --rebase` a été éliminé au profit d'un vrai *Launcher dynamique*.
    - *Historique Shell Réel* : Détection automatique de la dernière commande exécutée (`.bash_history`, `.zsh_history`, `$HISTFILE` et `.last_command`).
    - *Hooks Shell & Raccourci Global* : Intégration transparente pour Zsh et Bash avec injection de la combinaison *`Alt+E`*.
    - *Sécurité & Masquage des Secrets* : Implémentation de `src/core/redact.py` pour caviarder les clés API (`gsk_`, `sk-`), tokens et mots de passe.
    - *Internationalisation Bilingue* : Système `src/i18n.py` complet (Français / Anglais) avec auto-détection de locale.
    - *Design & Typographie* : Éléments typographiques agrandis (titres 20px, code 15px) avec polices _Inter Display_ et _JetBrains Mono_.
  ]
)

#v(12pt)

== Ce Que Je Fais Aujourd'hui (Jour 1 — Finalisation Développeur)

Objectif du jour : consolider l'expérience locale, valider les flux en conditions réelles et préparer une passation sans accroc pour mon collègue.

=== 1. Validation & Test en Conditions Réelles
- [ ] *Activer le hook shell en local* :
  Exécuter `ezsh init --install` puis recharger la configuration avec `source ~/.bashrc` (ou `~/.zshrc`).
- [ ] *Tester la détection des pannes* :
  Lancer intentionnellement une fausse commande (ex: `pytest inexistant/` ou `git pushh`), puis appuyer sur *`Alt+E`*.
- [ ] *Vérifier l'ouverture du popup* :
  S'assurer que la commande échouée apparaît immédiatement dans l'encart avec le bouton *« Diagnostiquer cette erreur »*.

=== 2. Nettoyage de l'Environnement & Sécurité
- [ ] S'assurer que le fichier `.env.local` contenant la clé Groq personnelle n'est *jamais* commité (`.gitignore` vérifié).
- [ ] Confirmer que `.env.example` contient bien toutes les variables nécessaires (`GROQ_API_KEY`, `EZSHELL_MODEL`, `EZSHELL_LANG`).

=== 3. Préparation de la Passation
- [ ] Vérifier que le `README.md` est clair et permet un onboarding immédiat en moins de 2 minutes.
- [ ] Laisser des notes précises sur les modules clés (`src/core/shell_hook.py`, `src/ui/gui_window.py`).

#v(12pt)

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

#v(14pt)

== Résumé des Commandes Indispensables

#table(
  columns: (auto, 1fr),
  fill: (col, row) => if row == 0 { rgb("#1e293b") } else if calc.even(row) { rgb("#f8fafc") } else { rgb("#ffffff") },
  stroke: 0.5pt + rgb("#cbd5e1"),
  inset: 7pt,
  [*Commande*], [*Description*],
  [#text(fill: brand-blue, font: "JetBrains Mono")[ezsh]], [Ouvre la fenêtre d'assistance en mode Launcher dynamique],
  [#text(fill: brand-blue, font: "JetBrains Mono")[ezsh init --install]], [Injecte automatiquement le hook dans le shell actif (~/.zshrc ou ~/.bashrc)],
  [#text(fill: brand-blue, font: "JetBrains Mono")[Alt + E]], [Raccourci clavier universel pour appeler ezShell depuis le terminal],
  [#text(fill: brand-blue, font: "JetBrains Mono")[ezsh --check-key]], [Vérifie la validité et la connectivité de la clé API Groq],
  [#text(fill: brand-blue, font: "JetBrains Mono")[ezsh --tui]], [Mode terminal pur (Textual) pour les sessions distantes ou SSH],
  [#text(fill: brand-blue, font: "JetBrains Mono")[pytest tests/ -v]], [Lance les 30 tests unitaires du projet],
)


