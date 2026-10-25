<div align="center">

# ezShell

**Ton terminal t'explique ses erreurs.**
Une commande échoue ? `Alt+E` explique la cause et place une correction dans ton prompt. Tu relis, tu valides : rien n'est exécuté sans toi.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Licence](https://img.shields.io/badge/licence-MIT-green)
![Version](https://img.shields.io/badge/version-0.3.0-orange)

[Site](https://ezshell.vercel.app) · [Fonctionnalités](#fonctionnalités) · [Installation](#installation) · [Utilisation](#utilisation) · [Licence](#licence)

<img src="docs/preview.webp" alt="Aperçu d'ezShell : après « npm run dev » qui échoue avec « vite: command not found », le panneau ezShell explique que vite n'est pas installé et propose la commande npm install -D vite" width="860">

</div>

---

## Fonctionnalités

- **Diagnostic de la dernière erreur** : la cause probable, en français ou en anglais selon ta locale.
- **Correction insérée dans le prompt** : la commande arrive dans ta ligne de saisie ; c'est toi qui appuies sur Entrée.
- **Langage naturel** : tape ta demande (« lister les ports ouverts ») puis `Alt+E` pour obtenir la commande.
- **Niveau de risque** : faible, moyen ou élevé. Les règles locales d'ezShell relèvent le niveau si le modèle le sous-estime, et une commande à risque élevé exige une confirmation explicite (`y`).
- **Sans clé API** : ezShell passe par son service hébergé ; ton appareil reçoit un jeton anonyme avec un quota quotidien gratuit.
- **Secrets masqués** : mots de passe, clés API, jetons, identifiants dans les URL et clés privées sont masqués avant l'envoi, puis une seconde fois sur le serveur.
- **bash, zsh et fish** sur Linux et macOS, **PowerShell** sur Windows (bêta). Une fenêtre de bureau et une interface plein terminal sont aussi disponibles.

---

## Installation

Prérequis : Python 3.10 ou plus récent.

```bash
pipx install ezshell
```

Puis branche ezShell sur ton shell, en ajoutant la ligne correspondante à la fin de ton fichier de configuration :

| Shell | Fichier | Ligne |
|---|---|---|
| zsh | `~/.zshrc` | `eval "$(ezsh init zsh)"` |
| bash | `~/.bashrc` | `eval "$(ezsh init bash)"` |
| fish | `~/.config/fish/config.fish` | `ezsh init fish \| source` |
| PowerShell (Windows) | `$PROFILE` | `Invoke-Expression (& ezsh init powershell \| Out-String)` |

Pour bash, zsh et PowerShell, `ezsh init --install` ajoute la ligne à ta place. Ouvre ensuite un nouveau terminal.

**Windows (bêta) :** installe Python 3.10+ et [pipx](https://pipx.pypa.io/stable/), puis la même commande `pipx install` dans PowerShell (5.1 ou 7, avec PSReadLine). Si PowerShell refuse de charger ton profil, autorise les scripts locaux pour ton compte : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Sous WSL, suis simplement les instructions Linux.

**Mettre à jour :** lance `ezsh --update`. ezShell affiche les nouveautés, te demande confirmation (réponse par défaut : non), puis met à jour. Ajoute `--yes` pour passer la confirmation dans un script. Quand une nouvelle version existe, une ligne discrète te le rappelle au plus une fois par jour ; `EZSH_NO_UPDATE_CHECK=1` la désactive. Sous Windows, la commande à lancer dans un nouveau terminal t'est affichée (un programme ne peut pas se remplacer pendant qu'il tourne). Si tu as installé ezShell depuis l'URL git avant la version 0.2.0, réinstalle une dernière fois : `pipx install --force ezshell`.

<details>
<summary>Autres méthodes d'installation</summary>

**Dernière version de développement** (pas encore publiée sur PyPI) : `pipx install git+https://github.com/Waddle-io/ezShell.git`

**Installateur en une ligne** (installe dans `~/.local/share/ezshell`, commandes dans `~/.local/bin`) :

```bash
curl -fsSL https://raw.githubusercontent.com/Waddle-io/ezShell/main/install.sh | bash
```

**Depuis les sources :**

```bash
git clone https://github.com/Waddle-io/ezShell.git
cd ezShell
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

La fenêtre de bureau nécessite Tk (`sudo apt install python3-tk` sur Debian/Ubuntu).
</details>

Désinstaller : retire la ligne `ezsh init` de ton fichier de configuration, puis `pipx uninstall ezshell`.

---

## Utilisation

### Dans ton terminal (`Alt+E`)

Lance une commande qui échoue (par exemple `git psuh`), puis appuie sur `Alt+E`.

| Touche | Action |
|---|---|
| `Entrée` | Insérer la commande dans le prompt (risque faible ou moyen) |
| `y` | Insérer une commande à risque élevé ou sur plusieurs lignes |
| `e` | Modifier la commande avant de l'insérer |
| `c` | Copier dans le presse-papiers |
| `/` | Poser une autre question |
| `q` / `Échap` | Fermer sans rien insérer |

Pour un diagnostic plus précis, lance la commande via `ezsh run` : la fin de sa sortie d'erreur est gardée (et masquée) pour l'analyse.

```bash
ezsh run -- npm run build
```

`ezsh suggest --ask "trouver les fichiers de plus de 1 Go"` ouvre le même panneau sans raccourci.

### Raccourcis clavier et personnalisation (V3)

ezShell propose un gestionnaire discret de raccourcis clavier pour consulter, personnaliser et détecter les conflits avec le terminal :

```bash
ezsh shortcuts                # Ouvre le menu de configuration interactif
ezsh shortcuts --list         # Affiche la liste des raccourcis et leur statut
ezsh shortcuts --set-trigger alt+s # Personnalise le déclencheur shell (ex: Alt+S, Alt+E, Ctrl+Space)
ezsh shortcuts --disable      # Désactive le déclencheur shell sans toucher aux fonctions de capture
ezsh shortcuts --enable       # Réactive le déclencheur shell
ezsh shortcuts --reset        # Rétablit les raccourcis par défaut
```

### Authentification & Quotas (V3)

```bash
ezsh login                    # Connexion sécurisée (flux OAuth Device Authorization RFC 8628)
ezsh logout                   # Déconnexion et révocation de session
ezsh usage                    # Affiche le quota journalier consommé, restant et l'heure de renouvellement
```

### Autres modes

```bash
ezsh                 # fenêtre de bureau (interface terminal si aucun affichage)
ezsh --tui           # interface plein terminal, pratique en SSH
ezsh --explain "docker: Error response from daemon: port is already allocated"
ezsh --check-key     # vérifie que le service ezShell répond
ezsh --version
ezsh init --install  # installe automatiquement l'intégration dans votre shell
ezsh init --uninstall # désinstalle proprement et de manière réversible l'intégration
```

`ezsh --help` liste toutes les options.

### Configuration

Aucune configuration n'est nécessaire. Variables utiles :

| Variable | Rôle |
|---|---|
| `EZSHELL_LANG` | Force la langue (`fr` ou `en`) ; sinon déduite de `$LANG` |
| `EZSH_API_URL` | URL du service (défaut : `https://ezshell.vercel.app`) |
| `EZSH_DIRECT=1` | Appelle Groq directement avec ta propre clé (`GROQ_API_KEY` ou `ezsh --set-key`) |
| `EZSH_MODEL` | Modèle en mode direct (défaut : `openai/gpt-oss-120b`) |
| `EZSH_STATE_DIR` | Dossier d'état par terminal (défaut : `$XDG_RUNTIME_DIR/ezsh`, `%LOCALAPPDATA%\ezsh` sous Windows) |
| `EZSH_MOCK_LLM=1` | Simule le modèle, sans réseau (développement) |

### Interfaces Web (V3)

- **Activation d'un terminal (`/activate`)** : saisie ou validation du code d'autorisation (RFC 8628).
- **Dashboard utilisateur (`/dashboard`)** : consultation du compte, jauge de consommation quotidienne en direct, gestion et révocation des appareils autorisés.
- **Console d'administration (`/admin`)** : tableau de bord réservé aux administrateurs (`ADMIN_EMAILS`) pour la gestion des utilisateurs (changement de plan, quota personnalisé, bannissement), statistiques globales d'usage, interrupteur d'urgence Kill Switch, et journal d'audit (`audit_logs`).

### Configuration du serveur web (Next.js)

Variables d'environnement disponibles pour le backend hébergé :

| Variable | Description |
|---|---|
| `DATABASE_URL` | Chaîne de connexion PostgreSQL (ex: Neon) |
| `TOKEN_PEPPER` | Clé secrète de hachage HMAC-SHA256 pour les jetons et sessions |
| `ADMIN_EMAILS` | Liste d'adresses email d'administrateurs séparées par des virgules |
| `GITHUB_CLIENT_ID` | Identifiant client de l'application GitHub OAuth |
| `GITHUB_CLIENT_SECRET` | Secret client de l'application GitHub OAuth |
| `RESEND_API_KEY` | Clé d'API Resend pour l'envoi des liens magiques |
| `EMAIL_FROM` | Adresse d'expédition des e-mails (ex: `ezShell <auth@ezshell.dev>`) |
| `PUBLIC_BASE_URL` | URL publique de l'application web (ex: `https://ezshell.vercel.app`) |

---

## Confidentialité

Rien n'est envoyé tant que tu n'appuies pas sur `Alt+E`. Sont alors envoyés : ton OS et ton shell, le dossier courant (avec `~` à la place de ton nom), la dernière commande, son code de sortie et, si tu passes par `ezsh run`, la fin de sa sortie d'erreur (4 Ko max). Le service ne conserve pas le contenu des requêtes : seulement un jeton d'appareil haché et des compteurs de quota.

---

## Développement

```bash
pip install -e . -r requirements-dev.txt
pytest
ruff check src tests
EZSH_MOCK_LLM=1 ezsh suggest --ask "lister les gros fichiers"
```

Le service hébergé (Next.js + Postgres) est dans [`web/`](web/README.md). Voir aussi [`CONTRIBUTING.md`](CONTRIBUTING.md) et [`DEVELOPMENT.md`](DEVELOPMENT.md).

---

## Licence

Distribué sous licence [MIT](LICENSE). © 2026 Salomon.
