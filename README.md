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

### 1. Session interactive (Recommandé)
Lancez simplement `ezshell` :
```bash
ezshell
```

Travaillez normalement dans votre shell :
```text
╭─ ⚡ nuelo in ~/waddle/ezShell on ⎇ main*
╰─❯ git comit -m "add feature"
git: 'comit' is not a git command. See 'git --help'.

╭────────────────────── ✘ Command Failed (Exit Code 1) ──────────────────────╮
│                                                                              │
│  ✦ Cause: Faute de frappe dans la sous-commande git 'comit'                  │
│                                                                              │
│  La commande a échoué car 'comit' n'est pas reconnu par Git.                 │
│                                                                              │
│  ⚡ Suggested Fix  (Corrige l'orthographe en 'commit')                        │
│                                                                              │
│    git commit -m "add feature"                                               │
│                                                                              │
╰─────────────────────  `git comit -m "add feature"`  ────────────────────────╯

 Execute fix? [yes / No / edit]: y
```

### 2. Commandes intégrées (Méta-commandes)
À l'intérieur d'ezShell :

| Commande | Description |
|---|---|
| `!ask <question>` | Interroge l'IA sur une commande ou un problème DevOps (`Ctrl+Space`) |
| `!fix` | Ré-affiche ou relance le dernier fix proposé |
| `!config` | Affiche la configuration active et le modèle Groq |
| `!help` | Affiche l'aide intégrée |
| `clear` | Efface l'écran |
| `exit` / `quit` | Quitte ezShell |

### 3. Diagnostic direct en une ligne
```bash
ezshell --explain "docker: Error response from daemon: port is already allocated"
```

### 4. Exécution directe d'une commande
```bash
ezshell -c "pytest tests/"
```

---

##  Tests

Exécuter la suite de tests avec `pytest` :
```bash
.venv/bin/pytest tests/ -v
```

---

##  Architecture & Sécurité

```text
ezShell/
├── setup.py              # Packaging et point d'entrée CLI `ezshell`
├── requirements.txt      # Dépendances de production
├── tests/                # Tests unitaires (config, safety, context, pty, assistant)
└── src/
    ├── main.py           # Point d'entrée CLI avec options
    ├── app.py            # Boucle REPL interactive et gestion des builtins
    ├── core/
    │   ├── pty_shell.py  # Moteur pseudo-terminal (PTY) & nettoyage ANSI
    │   ├── groq_client.py# Client Groq avec retries et gestion d'erreurs
    │   ├── assistant.py  # Logique de diagnostic et extraction JSON
    │   ├── safety.py     # Détection des commandes dangereuses
    │   ├── context.py    # Détection OS, shell, git et télémétrie locale
    │   ├── prompts.py    # System prompts spécialisés DevOps
    │   └── config.py     # Gestionnaire de configuration hiérarchique
    └── ui/
        ├── prompt.py     # Prompt prompt_toolkit 2 lignes style Starship
        └── render.py     # Moteur de rendu Rich avec palette Tokyo Night
```

---

##  Licence

Distribué sous licence MIT.
