<div align="center">

<img src="assets/logos/ezshell-horizontal-transparent.png" alt="ezShell" width="335">

**Un assistant de terminal propulsé par Groq (`openai/gpt-oss-120b` par défaut).**
*Il repère la commande qui vient d'échouer, explique la cause et place une correction dans votre prompt, sans jamais l'exécuter à votre place.*

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Licence](https://img.shields.io/badge/licence-MIT-green)
![Version](https://img.shields.io/badge/version-0.1.0-orange)
![Statut](https://img.shields.io/badge/statut-MVP-yellow)

[Fonctionnalités](#fonctionnalités) · [Installation](#installation) · [Configuration](#configuration) · [Utilisation](#utilisation) · [Développement](#développement)

</div>

---

## Présentation

ezShell s'intègre à votre shell habituel (Zsh, Bash ou Fish). Des hooks légers notent chaque commande et son code de sortie. Quand quelque chose échoue, `Alt+E` ouvre un panneau directement dans le terminal : diagnostic, commande corrigée, niveau de risque. La commande choisie est **insérée dans votre ligne de saisie** ; c'est vous qui appuyez sur Entrée.

Une fenêtre de bureau (CustomTkinter) et une interface plein terminal (Textual) sont aussi disponibles.

### Fonctionnalités

- **Diagnostic de la dernière erreur** : cause probable, en français ou en anglais selon votre locale.
- **Correction prête à l'emploi** : la commande proposée arrive dans le prompt, jamais exécutée silencieusement.
- **Langage naturel** : tapez votre besoin dans la ligne de saisie puis `Alt+E` (« lister les ports ouverts »), ou `/` dans le panneau.
- **Évaluation du risque** : chaque suggestion est classée (faible / moyen / élevé) ; les commandes à risque élevé ou sur plusieurs lignes demandent une confirmation explicite (`y`).
- **Masquage des secrets** : mots de passe, clés API (`gsk_…`, `sk-…`, `ghp_…`), jetons et clés privées sont masqués avant tout envoi au modèle.
- **Capture de stderr à la demande** : `ezsh run -- <commande>` garde la fin de la sortie d'erreur pour un diagnostic plus précis.
- **Mode hors ligne pour le développement** : `EZSH_MOCK_LLM=1` simule le modèle, sans clé ni réseau.

---

## Installation

### Installateur en une ligne (Linux, macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/Waddle-io/ezShell/main/install.sh | bash
```

Le script installe ezShell dans `~/.local/share/ezshell` (environnement virtuel dédié) et place les commandes dans `~/.local/bin`. Relisez-le avant de l'exécuter si vous préférez : [`install.sh`](install.sh).

### Depuis les sources

```bash
git clone https://github.com/Waddle-io/ezShell.git
cd ezShell
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Prérequis : Python 3.10 ou plus récent. La fenêtre de bureau nécessite aussi Tk (`sudo apt install python3-tk` sur Debian/Ubuntu).

---

## Configuration

Créez une clé gratuite sur la [console Groq](https://console.groq.com/keys), puis choisissez une option :

```bash
# 1. Enregistrer la clé dans ~/.ezshell/config.json
ezsh --set-key gsk_votre_cle

# 2. Ou l'exporter dans votre shell
export GROQ_API_KEY="gsk_votre_cle"
```

Un fichier `.env.local` (ou `.env`) dans le dossier courant est aussi lu ; pratique quand vous travaillez dans le dépôt.

Vérifier la clé :

```bash
ezsh --check-key
```

### Variables d'environnement

| Variable | Rôle |
|---|---|
| `GROQ_API_KEY` | Clé API Groq |
| `EZSHELL_MODEL` / `EZSH_MODEL` | Modèle à utiliser (défaut : `openai/gpt-oss-120b`). `--model` fait la même chose ponctuellement. |
| `EZSHELL_LANG` | Force la langue de l'interface et des réponses (`fr` ou `en`) ; sinon déduite de `$LANG` |
| `EZSH_STATE_DIR` | Dossier d'état par terminal (défaut : `$XDG_RUNTIME_DIR/ezsh`, sinon `/tmp/ezsh-<uid>`) |
| `EZSH_MOCK_LLM` | Simule le modèle : `1`, `high`, `uncertain`, `offline`, `quota`, `trial`, `invalid`, `error`, `slow` |

---

## Utilisation

### 1. Intégration au shell (recommandé)

```bash
# Ajoute automatiquement la ligne d'init dans ~/.zshrc ou ~/.bashrc
ezsh init --install

# Ou à la main, selon votre shell :
eval "$(ezsh init zsh)"     # ~/.zshrc
eval "$(ezsh init bash)"    # ~/.bashrc
ezsh init fish | source     # ~/.config/fish/config.fish
```

Rechargez le shell (`source ~/.zshrc`), puis :

- **Après une erreur**, appuyez sur `Alt+E` : ezShell analyse la dernière commande et son code de sortie.
- **Avec du texte dans la ligne de saisie**, `Alt+E` le traite comme une question en langage naturel.
- **Pour un diagnostic plus riche**, lancez la commande via `ezsh run -- <commande>` : la fin de stderr est conservée et envoyée (après masquage).

Touches du panneau :

| Touche | Action |
|---|---|
| `Entrée` | Insérer la commande dans le prompt (risque faible ou moyen, une seule ligne) |
| `y` | Insérer une commande à risque élevé ou sur plusieurs lignes |
| `e` | Modifier la commande avant de l'insérer |
| `c` | Copier dans le presse-papiers |
| `/` | Poser une autre question |
| `q` / `Échap` | Fermer sans rien insérer |

`ezsh suggest [--ask "question"]` ouvre le même panneau sans raccourci clavier.

### 2. Fenêtre de bureau et interface terminal

```bash
ezsh              # fenêtre de bureau si un affichage est disponible, sinon interface terminal
ezsh "question"   # ouvre la fenêtre avec cette question
ezsh --tui        # interface plein terminal (SSH, serveurs sans affichage)
ezsh --gui        # force la fenêtre de bureau
ezsh --wrapper    # ancien mode : REPL qui enveloppe un shell (!ask, !fix, !config, !help)
```

### 3. Commandes ponctuelles

```bash
ezsh --explain "docker: Error response from daemon: port is already allocated"
ezsh -c "pytest tests/"   # exécute une commande via ezShell et diagnostique un échec
ezsh --version
```

`ezsh --help` liste toutes les options. `ezshell` est un alias de `ezsh`.

---

## Sécurité et confidentialité

- **Rien n'est exécuté sans vous** : le flux `Alt+E` écrit seulement la commande dans le prompt. La commande échouée n'est jamais rejouée.
- **Secrets masqués avant envoi** ([`src/core/redact.py`](src/core/redact.py)) et **contexte minimal** : OS, shell, dossier courant, dernière commande, code de sortie, fin de stderr.
- **Évaluation du risque** ([`src/core/risk.py`](src/core/risk.py)) : règles locales (suppression récursive, `sudo`, écriture disque, `curl | sh`…) combinées à l'avis du modèle ; c'est le niveau le plus élevé qui l'emporte.
- **Nettoyage de la commande** ([`src/core/sanitize.py`](src/core/sanitize.py)) : séquences de contrôle et sauts de ligne retirés avant insertion.
- **État local et privé** : les fichiers d'état sont dans un dossier `0700` propre à votre utilisateur. Le contenu des requêtes n'est pas journalisé.

---

## Architecture

```text
ezShell/
├── pyproject.toml          # Packaging et commandes (ezsh, ezshell)
├── install.sh              # Installateur en une ligne
├── DEVELOPMENT.md          # Spécification et feuille de route technique
├── tests/
└── src/
    ├── main.py             # Point d'entrée CLI (run, suggest, init, options)
    ├── app.py              # Mode --wrapper : REPL au-dessus d'un shell PTY
    ├── i18n.py             # Textes FR / EN et détection de la langue
    ├── core/
    │   ├── shell_hook.py   # Hooks Zsh / Bash / Fish et raccourci Alt+E
    │   ├── capture.py      # `ezsh run` et lecture de la dernière commande
    │   ├── suggest.py      # Orchestration : contexte → masquage → modèle → risque
    │   ├── provider.py     # Fournisseurs de modèle (Groq, simulé)
    │   ├── schema.py       # Validation de la réponse JSON du modèle
    │   ├── risk.py         # Classification du risque des commandes
    │   ├── sanitize.py     # Nettoyage de la commande avant insertion
    │   ├── redact.py       # Masquage des secrets
    │   ├── config.py       # Configuration (fichier, variables, .env.local)
    │   ├── context.py      # Contexte système (OS, git, historique)
    │   ├── groq_client.py  # Client Groq des interfaces GUI / TUI / wrapper
    │   ├── assistant.py    # Diagnostic pour les interfaces GUI / TUI / wrapper
    │   ├── safety.py       # Garde-fous du mode wrapper
    │   ├── prompts.py      # Prompts système
    │   └── pty_shell.py    # Pseudo-terminal du mode wrapper
    └── ui/
        ├── inline.py       # Panneau Alt+E (`ezsh suggest`)
        ├── panel.py        # Rendu du panneau inline
        ├── gui_window.py   # Fenêtre de bureau CustomTkinter
        ├── chat_tui.py     # Interface plein terminal Textual
        ├── render.py       # Rendu Rich (CLI, wrapper)
        ├── prompt.py       # Prompt du mode wrapper
        └── logo.py         # Logo et bannière d'accueil
```

---

## Développement

```bash
pip install -e . -r requirements-dev.txt
pytest                      # tests
ruff check src tests        # lint
EZSH_MOCK_LLM=1 ezsh suggest --ask "lister les gros fichiers"   # tester sans clé
```

Voir [`CONTRIBUTING.md`](CONTRIBUTING.md) pour les conventions et [`DEVELOPMENT.md`](DEVELOPMENT.md) pour la conception détaillée.

---

## Licence

Distribué sous licence MIT.
