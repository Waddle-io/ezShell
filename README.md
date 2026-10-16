<div align="center">

# ezShell 

**Un terminal intelligent propulsé par Groq LLM (`llama-3.1-8b-instant`).**  
*Intercepte les erreurs en temps réel, explique la cause racine et propose des corrections prêtes à exécuter.*

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Licence](https://img.shields.io/badge/licence-MIT-green)
![Version](https://img.shields.io/badge/version-0.1.0-orange)
![Statut](https://img.shields.io/badge/statut-MVP-yellow)

[Fonctionnalités](#-fonctionnalités) · [Installation](#-installation) · [Configuration](#-configuration) · [Utilisation](#-utilisation) · [Tests](#-tests)

</div>

---

##  Présentation

`ezShell` enveloppe votre terminal interactif (Bash, Zsh) pour fournir une assistance IA immédiate à chaque erreur de commande. Inspiré d'outils comme *oh-my-zsh* et *Starship*, il associe un prompt moderne à la vitesse d'inférence fulgurante de Groq pour diagnostiquer vos pannes et proposer des commandes de résolution exécutables en une touche.

###  Fonctionnalités
-  **Diagnostic d'erreur instantané** : Analyse la cause racine de l'échec en français clair et concis.
-  **Suggestion de correction exécutable** : Propose la commande exacte pour réparer l'erreur. Appuyez sur `y` pour l'exécuter directement.
-  **Garde-fou de sécurité** : Détecte les commandes potentiellement destructrices (`rm -rf /`, `mkfs`, fork bombs) et avertit avant toute exécution.
-  **Questions en langage naturel (`!ask`)** : Posez vos questions système ou DevOps directement sans quitter le terminal.
-  **Interface moderne Starship / Tokyo Night** : Prompt 2 lignes, statut Git dynamique (`⎇ branch*`), autocomplétion des chemins et historique persistant.
-  **Configuration flexible** : Lecture hiérarchique depuis `.env.local`, variable d'environnement `GROQ_API_KEY` ou `~/.ezshell/config.json`.

---

##  Installation

```bash
# Cloner le dépôt
git clone https://github.com/Waddle-io/ezShell.git
cd ezShell

# Créer et activer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances et la CLI en mode éditable
pip install -r requirements.txt
pip install -e .
```

---

##  Configuration

Obtenez une clé API gratuite sur la [Console Groq](https://console.groq.com/keys).

Trois options pour configurer votre clé :

1. **Via la commande dédiée ezShell :**
   ```bash
   ezshell --set-key gsk_votre_cle_ici
   ```
2. **Via le fichier `.env.local` à la racine :**
   ```bash
   echo "GROQ_API_KEY=gsk_votre_cle_ici" >> .env.local
   ```
3. **Via variable d'environnement globale :**
   ```bash
   export GROQ_API_KEY="gsk_votre_cle_ici"
   ```

Vérifier la connectivité :
```bash
ezshell --check-key
```

---

##  Utilisation

### 1. Intégration Shell Automatique (Recommandé)

Activez ezShell directement dans votre terminal habituel (Zsh ou Bash) en une seule commande :

```bash
# Installation automatique dans votre ~/.zshrc ou ~/.bashrc
ezsh init --install

# Ou manuellement dans votre ~/.zshrc :
eval "$(ezsh init zsh)"

# Ou dans votre ~/.bashrc :
eval "$(ezsh init bash)"
```

Une fois installé :
- ezShell capture silencieusement la dernière commande exécutée et son code de sortie.
- **Raccourci magique `Alt+E`** : Ouvre instantanément l'assistant ezShell directement par-dessus votre terminal !

### 2. Assistant Graphique & Pop-up (Mode Launcher)

Lancez simplement :
```bash
ezsh
# ou
ezshell
```

- **Mode Launcher** : Barre de recherche immédiatement active, détection automatique de la dernière commande exécutée dans votre historique shell avec un bouton de diagnostic direct.
- **Mode Diagnostic** : Détection de la cause racine, proposition de la solution en ligne de commande `$ ...`, évaluation du niveau de risque et raccourcis (`[Enter]` pour exécuter, `[c]` pour copier, `[e]` pour éditer, `[Esc]` pour fermer).
- **Mode TUI dans le terminal** : `ezsh --tui` pour les serveurs distants ou sessions SSH sans affichage graphique.

### 3. Diagnostic direct en une ligne
```bash
ezshell --explain "docker: Error response from daemon: port is already allocated"
```

### 4. Exécution directe d'une commande
```bash
ezshell -c "pytest tests/"
```

---

## Tests

Exécuter la suite de tests avec `pytest` :
```bash
.venv/bin/pytest tests/ -v
```

---

## Architecture & Sécurité

- **Protection des données sensibles ([`src/core/redact.py`](file:///home/nuelo/waddle/ezShell/src/core/redact.py))** : Masque automatiquement les mots de passe, clés API (`gsk_...`, `sk-...`, `ghp_...`) et clés privées avant envoi à l'IA.
- **Garde-fous de sécurité ([`src/core/safety.py`](file:///home/nuelo/waddle/ezShell/src/core/safety.py))** : Inspecte toutes les commandes suggérées avant exécution pour bloquer toute commande destructrice.
- **Support bilingue FR/EN ([`src/i18n.py`](file:///home/nuelo/waddle/ezShell/src/i18n.py))** : Détection automatique de la langue système (`$LANG`, `EZSHELL_LANG`).

```text
ezShell/
├── setup.py              # Packaging et points d'entrée CLI (ezshell, ezsh, eszh)
├── requirements.txt      # Dépendances de production
├── tests/                # 30 tests unitaires passants
└── src/
    ├── main.py           # Point d'entrée CLI avec routage (init, gui, tui, explain)
    ├── i18n.py           # Catalogue bilingue FR / EN & auto-détection de locale
    ├── app.py            # Boucle REPL interactive et shell PTY
    ├── core/
    │   ├── shell_hook.py # Générateur de hooks shell pour Bash, Zsh, Fish (Alt+E)
    │   ├── redact.py     # Masquage automatique des secrets et identifiants
    │   ├── pty_shell.py  # Moteur pseudo-terminal (PTY) & nettoyage ANSI
    │   ├── groq_client.py# Client Groq avec retries et repli multi-modèles
    │   ├── assistant.py  # Logique de diagnostic et extraction JSON
    │   ├── safety.py     # Détection et classification des risques
    │   ├── context.py    # Détection OS, historique shell (.last_command) et git
    │   ├── prompts.py    # Prompts DevOps optimisés
    │   └── config.py     # Gestionnaire de configuration hiérarchique (.env.local)
    └── ui/
        ├── gui_window.py # Fenêtre Desktop CustomTkinter (Launcher dynamique)
        ├── chat_tui.py   # Modal TUI déplaçable Textual pour SSH / terminaux purs
        ├── logo.py       # Bannière de bienvenue bilingue et logo ASCII
        └── render.py     # Moteur de rendu Rich
```

---

##  Licence

Distribué sous licence MIT.
