# ezShell v2 : support de Windows

> Statut : proposition · Cible : PowerShell 5.1 et 7 (avec PSReadLine)

## Contexte

La v1 tourne sur Linux et macOS (bash, zsh, fish). Sous Windows, ezShell fonctionne déjà **dans WSL**, puisque c'est un Linux.

Une partie du code est déjà portable :
- le service hébergé ;
- la validation des réponses ;
- le masquage des secrets ;
- la fenêtre de bureau et la TUI.

Ce qui manque, c'est l'intégration au shell natif et le panneau `Alt+E`, aujourd'hui écrits pour Unix (`/dev/tty`, `termios`, `pty`, `os.getuid`).

**Pourquoi PowerShell ?** Avec PSReadLine, il permet le même flux que bash et zsh : capturer la dernière commande et son code de sortie, lier `Alt+E`, puis insérer la correction dans la ligne de saisie sans l'exécuter. `cmd.exe` n'offre rien de tout ça sans outil tiers ; il est reporté à l'étape 3.

---

## Étape 1 : MVP PowerShell

Objectif : après `pipx install` puis `ezsh init powershell`, `Alt+E` fonctionne dans PowerShell comme sous Linux.

| Zone | Travail |
|---|---|
| Hook shell | `ezsh init powershell` enrobe la fonction `prompt` sans écraser celle de l'utilisateur. Il note la dernière commande (`Get-History -Count 1`), `$?` et `$LASTEXITCODE`, et pose `EZSH_SHELL=pwsh`. |
| Raccourci | `Set-PSReadLineKeyHandler -Chord Alt+e` lit la ligne en cours (`GetBufferState`), appelle `ezsh suggest`, puis remplace la ligne (`RevertLine` + `Insert`). Rien n'est exécuté. |
| Installation | `ezsh init --install` ajoute la ligne d'init à `$PROFILE`, sans doublon. |
| Panneau (`src/ui/inline.py`) | Une couche d'abstraction du terminal : `CONIN$` / `CONOUT$` et `msvcrt.getwch()` sous Windows, `/dev/tty` et `termios` ailleurs. |
| Dossier d'état (`src/core/capture.py`) | `%LOCALAPPDATA%\ezsh` au lieu de `/tmp/ezsh-<uid>` (`os.getuid()` n'existe pas sous Windows). |
| Presse-papiers | `clip.exe`. |
| Contexte (`src/core/suggest.py`) | Shell et OS détectés via `EZSH_SHELL` ; le modèle répond en syntaxe PowerShell. |
| Règles de risque (`src/core/risk.py`) | Ajouter les règles PowerShell (`Remove-Item -Recurse -Force`, `Format-Volume`, `iwr … \| iex`, `Set-ExecutionPolicy Unrestricted`, `reg delete`, `del /s /q`, `Stop-Process -Force`…), avec leurs tests. **Indispensable dès le MVP** : sans elles, le garde-fou ne protège plus rien sous Windows. |
| CI | Ajouter `windows-latest` à la matrice ; marquer les tests propres à Unix. |

**Fini quand :**
- sur un Windows réel, une commande qui échoue puis `Alt+E` affiche le panneau ;
- `Entrée` insère la correction dans la ligne sans l'exécuter ;
- une commande à risque élevé exige `y` ;
- la CI Windows est verte.

---

## Étape 2 : finitions

- **Exécution dans la GUI** : un repli `subprocess` remplace `PTYExecutor` (qui dépend de `pty` et `fcntl`).
- **`ezsh run`** : gérer Ctrl+C et les codes de sortie à la manière de Windows.
- **Mode `--wrapper`** : désactivé sous Windows avec un message clair (éventuellement `pywinpty` plus tard).
- **Encodage** : forcer l'UTF-8 dans la console pour les accents et les cadres du panneau.
- **Documentation** : README, page web (remplacer « Windows pas encore ») et section PowerShell dans `CONTRIBUTING.md`.

---

## Étape 3 : plus tard

- **`cmd.exe`** via [Clink](https://chrisant996.github.io/clink/), qui apporte un readline et des scripts Lua à cmd.
- **Installateur** : `install.ps1` en une ligne, ou un paquet winget / Scoop.
- **Windows Terminal** : profil ou extrait de configuration prêt à l'emploi.

---

## Risques et points ouverts

- **Tests sur une vraie machine** : le développement se fait sous Linux. La CI Windows exécutera la logique, mais le raccourci `Alt+E` dans PowerShell doit être validé à la main sur un Windows réel.
- **`Alt+E` déjà pris** : il peut entrer en conflit avec un raccourci existant de l'utilisateur ou du terminal. Prévoir une option pour changer la touche.
- **Politique d'exécution** : PowerShell peut bloquer `$PROFILE` (`ExecutionPolicy`). Le documenter, sans jamais la modifier à la place de l'utilisateur.
- **PowerShell 5.1** : il est livré avec une ancienne version de PSReadLine. Vérifier que `GetBufferState` et `Insert` y sont disponibles, sinon demander la mise à jour de PSReadLine.
