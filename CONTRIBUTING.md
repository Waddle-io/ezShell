# Guide Développeur & Passation (ezShell)

Bienvenue sur le projet **ezShell** ! Ce document résume l'architecture, l'état d'avancement du Jour 1 et les tâches prioritaires pour le Jour 2.

---

## 1. Démarrage Rapide (Pour tester en local)

```bash
# 1. Cloner et se placer dans le projet
git clone https://github.com/Waddle-io/ezShell.git
cd ezShell

# 2. Créer l'environnement virtuel Python (>= 3.10)
python3 -m venv .venv
source .venv/bin/activate

# 3. Installer le projet et les outils de développement
pip install -e . -r requirements-dev.txt

# 4. Aucune clé n'est nécessaire : le CLI passe par le service hébergé.
#    Pour travailler hors ligne : export EZSH_MOCK_LLM=1
ezsh --check-key

# 5. Lancer les tests et le lint
pytest
ruff check src tests

# Windows / PowerShell : pwsh existe aussi sous Linux et macOS, ce qui permet de tester le hook :
#   pwsh -NoProfile -NoExit -Command 'Invoke-Expression (& ezsh init powershell | Out-String)'
```

---

## 2. État du Projet (Achevé en Jour 1)

Le cœur applicatif et l'expérience utilisateur ont été finalisés et testés :

1. **Launcher Dynamique (`src/ui/gui_window.py`)** :
   - Fini le texte statique ou les fausses erreurs hardcodées.
   - Saisie immédiate avec détection de la dernière commande du terminal.
   - Commande recommandée affichée en haut, boutons `[Enter]` (exécuter), `[c]` (copier), `[e]` (éditer), `[Esc]` (fermer).
   - Nettoyage du markdown brut renvoyé par l'IA pour un rendu sobre et lisible.
   - Palette sobre développeur (bleu royal `#3B82F6`, gris ardoise, zéro cyberpunk).

2. **Détection d'Historique (`src/core/context.py`)** :
   - Lit l'historique shell réel (`.bash_history`, `.zsh_history`, `$HISTFILE`, et `~/.ezshell/.last_command`).
   - Isole la commande précédente et son code de sortie ($?).

3. **Hooks Shell Automatiques (`src/core/shell_hook.py`)** :
   - Commande d'installation en une ligne : `ezsh init --install`.
   - Compatible Zsh et Bash.
   - Raccourci universel configuré : **`Alt+E`** pour ouvrir ezShell directement depuis le terminal.

4. **Sécurité & Masquage des Secrets (`src/core/redact.py`)** :
   - Caviarde automatiquement les clés API (`gsk_`, `sk-`, `ghp_`, `AKIA`), mots de passe (`DB_PASSWORD=...`) et tokens avant envoi au LLM.

5. **Internationalisation (`src/i18n.py`)** :
   - Support bilingue intégral (Français / Anglais) avec auto-détection de la locale système.

6. **Tests Automatisés (`tests/`)** :
   - Des tests unitaires couvrant la sécurité, le shell PTY, les prompts, les hooks, la configuration et la détection d'historique.

---

## 3. Feuille de Route Jour 2 (Tâches pour demain)

Voici les 3 chantiers prioritaires à finaliser :

### 1. Script d'installation universel en 1 ligne (`install.sh`)
Permettre à tout utilisateur d'installer ezShell sans cloner manuellement :
```bash
curl -fsSL https://raw.githubusercontent.com/Waddle-io/ezShell/main/install.sh | bash
```
Le script doit :
- Vérifier la présence de Python 3.10+ et Tkinter.
- Créer un venv isolé dans `~/.local/share/ezshell/venv`.
- Installer ezShell et créer un symlink dans `~/.local/bin/ezsh`.
- Proposer l'ajout de `eval "$(ezsh init <shell>)"` dans le `.bashrc` ou `.zshrc`.

### 2. Modernisation du Packaging (`pyproject.toml`)
- Remplacer `setup.py` par un `pyproject.toml` moderne conforme aux standards PEP 517 / PEP 621 (Hatchling ou Flit).
- Déclarer les entrypoints : `ezsh = "src.main:main"`, `ezshell = "src.main:main"`.
- Tester la construction du paquet avec `python -m build`.

### 3. Tests multi-environnements & Publication
- Tester sur Ubuntu / Debian, Fedora et macOS.
- Préparer la publication sur PyPI (`pip install ezshell-ai`).

---

## 4. Architecture des Fichiers

```text
ezShell/
├── src/
│   ├── main.py           # Point d'entrée CLI (routage des commandes)
│   ├── app.py            # REPL interactif
│   ├── i18n.py           # Catalogue bilingue FR / EN
│   ├── core/
│   │   ├── shell_hook.py # Générateur et installateur de hooks shell
│   │   ├── redact.py     # Masquage des secrets et tokens
│   │   ├── pty_shell.py  # Moteur pseudo-terminal (PTY)
│   │   ├── groq_client.py# Client Groq (gestion retries et fallback)
│   │   ├── assistant.py  # Orchestrateur de diagnostic et sessions
│   │   ├── safety.py     # Garde-fou (commandes dangereuses)
│   │   ├── context.py    # Détection OS, historique shell et git
│   │   ├── prompts.py    # Ingénierie des prompts LLM
│   │   └── config.py     # Gestionnaire de configuration hiérarchique
│   └── ui/
│       ├── gui_window.py # Fenêtre Desktop CustomTkinter (Launcher & Diag)
│       ├── chat_tui.py   # Modal TUI Textual (pour SSH)
│       ├── logo.py       # Bannière de bienvenue
│       └── render.py     # Moteur de rendu Rich
├── tests/                # Tests unitaires et e2e (pytest)
├── assets/               # Logo et icônes
├── web/                  # Service hébergé (Next.js + Postgres)
└── README.md             # Documentation publique
```

