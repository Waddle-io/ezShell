"""
ezShell Shell Integration & Hook Generator
==========================================

Generates and installs non-intrusive shell hooks for Bash, Zsh, and Fish.
The hooks automatically capture the last executed command and its exit code
into ``~/.ezshell/.last_command`` and ``~/.ezshell/.last_exit_code``, enabling
instant error diagnosis and the global Alt+E keyboard shortcut.

---

Générateur et installateur d'intégration shell d'ezShell
========================================================

Génère et installe des hooks légers pour Bash, Zsh et Fish.
Les hooks capturent automatiquement la dernière commande exécutée et son code
de retour dans ``~/.ezshell/.last_command`` et ``~/.ezshell/.last_exit_code``,
permettant le diagnostic immédiat et le raccourci clavier Alt+E.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

_STATE_PREAMBLE = """export EZSH_SESSION="$$"
if [ -z "$EZSH_STATE_DIR" ]; then
    if [ -n "$XDG_RUNTIME_DIR" ]; then EZSH_STATE_DIR="$XDG_RUNTIME_DIR/ezsh"; else EZSH_STATE_DIR="${TMPDIR:-/tmp}/ezsh-$(id -u)"; fi
    export EZSH_STATE_DIR
fi
( umask 077; mkdir -p "$EZSH_STATE_DIR" ) 2>/dev/null
"""

ZSH_HOOK = """# ---------------------------------------------------------------------------
# ezShell Integration for Zsh  (état par terminal ; insertion dans le prompt)
# ---------------------------------------------------------------------------
""" + _STATE_PREAMBLE + """__ezshell_preexec() {
    __EZSHELL_LAST_CMD="$1"
}

__ezshell_precmd() {
    local exit_code=$?
    [[ -z "$__EZSHELL_LAST_CMD" ]] && return
    case "$__EZSHELL_LAST_CMD" in
        "ezsh suggest"*|"ezshell suggest"*|clear|exit|history*) ;;
        *)
            printf "%s" "$__EZSHELL_LAST_CMD" > "$EZSH_STATE_DIR/$EZSH_SESSION.cmd" 2>/dev/null
            printf "%d" "$exit_code" > "$EZSH_STATE_DIR/$EZSH_SESSION.code" 2>/dev/null
            case "$__EZSHELL_LAST_CMD" in
                "ezsh run "*|"ezshell run "*) ;;
                *) rm -f "$EZSH_STATE_DIR/$EZSH_SESSION.run.json" 2>/dev/null ;;
            esac
            ;;
    esac
    unset __EZSHELL_LAST_CMD
}

autoload -Uz add-zsh-hook 2>/dev/null
add-zsh-hook preexec __ezshell_preexec 2>/dev/null
add-zsh-hook precmd __ezshell_precmd 2>/dev/null

# Alt+E : l'interface s'affiche sur /dev/tty, la commande choisie est placée dans le prompt (jamais exécutée).
# Si la ligne de saisie contient du texte, il est utilisé comme question en langage naturel.
__ezshell_widget() {
    local out
    zle -I
    out="$(command ezsh suggest ${BUFFER:+--ask="$BUFFER"} </dev/tty)"
    if [[ $? -eq 0 && -n "$out" ]]; then
        BUFFER="$out"
        CURSOR=${#BUFFER}
    fi
    zle reset-prompt 2>/dev/null || true
}
zle -N __ezshell_widget 2>/dev/null || true
bindkey '\\ee' __ezshell_widget 2>/dev/null || true
# ---------------------------------------------------------------------------
"""

BASH_HOOK = """# ---------------------------------------------------------------------------
# ezShell Integration for Bash  (état par terminal ; insertion dans le prompt)
# ---------------------------------------------------------------------------
""" + _STATE_PREAMBLE + """__ezshell_prompt_command() {
    local exit_code=$?
    local last_cmd
    last_cmd=$(HISTTIMEFORMAT= history 1 2>/dev/null | sed -e 's/^[ ]*[0-9]*[ ]*//')
    [[ -z "$last_cmd" ]] && return
    # Ne rien refaire si la ligne d'historique n'a pas changé (prompt vide).
    local hist_id
    hist_id=$(HISTTIMEFORMAT= history 1 2>/dev/null | awk '{print $1}')
    [[ "$hist_id" == "$__EZSHELL_LAST_HIST_ID" ]] && return
    __EZSHELL_LAST_HIST_ID="$hist_id"
    case "$last_cmd" in
        "ezsh suggest"*|"ezshell suggest"*|clear|exit|history*) ;;
        *)
            printf "%s" "$last_cmd" > "$EZSH_STATE_DIR/$EZSH_SESSION.cmd" 2>/dev/null
            printf "%d" "$exit_code" > "$EZSH_STATE_DIR/$EZSH_SESSION.code" 2>/dev/null
            case "$last_cmd" in
                "ezsh run "*|"ezshell run "*) ;;
                *) rm -f "$EZSH_STATE_DIR/$EZSH_SESSION.run.json" 2>/dev/null ;;
            esac
            ;;
    esac
}

if [[ \";$PROMPT_COMMAND;\" != *\";__ezshell_prompt_command;\"* ]]; then
    PROMPT_COMMAND=\"__ezshell_prompt_command${PROMPT_COMMAND:+;$PROMPT_COMMAND}\"
fi

# Alt+E : interface sur /dev/tty ; la commande choisie remplace la ligne (READLINE_LINE), jamais exécutée.
__ezshell_widget() {
    local out
    out="$(command ezsh suggest ${READLINE_LINE:+--ask="$READLINE_LINE"} </dev/tty)"
    if [[ $? -eq 0 && -n "$out" ]]; then
        READLINE_LINE="$out"
        READLINE_POINT=${#READLINE_LINE}
    fi
}
bind -x '"\\ee": __ezshell_widget' 2>/dev/null || true
# ---------------------------------------------------------------------------
"""

FISH_HOOK = """# ---------------------------------------------------------------------------
# ezShell Integration for Fish
# ---------------------------------------------------------------------------
set -gx EZSH_SESSION $fish_pid
if test -z "$EZSH_STATE_DIR"
    if test -n "$XDG_RUNTIME_DIR"
        set -gx EZSH_STATE_DIR "$XDG_RUNTIME_DIR/ezsh"
    else
        set -gx EZSH_STATE_DIR (string join '' (test -n "$TMPDIR"; and echo $TMPDIR; or echo /tmp) "/ezsh-"(id -u))
    end
end
mkdir -p -m 700 "$EZSH_STATE_DIR" 2>/dev/null

function __ezshell_postexec --on-event fish_postexec
    set -l exit_code $status
    set -l last_cmd $argv[1]
    switch $last_cmd
        case 'ezsh suggest*' 'ezshell suggest*' 'clear' 'exit' 'history*'
            return
    end
    printf "%s" "$last_cmd" > "$EZSH_STATE_DIR/$EZSH_SESSION.cmd" 2>/dev/null
    printf "%d" "$exit_code" > "$EZSH_STATE_DIR/$EZSH_SESSION.code" 2>/dev/null
    switch $last_cmd
        case 'ezsh run *' 'ezshell run *'
        case '*'
            rm -f "$EZSH_STATE_DIR/$EZSH_SESSION.run.json" 2>/dev/null
    end
end

function __ezshell_widget
    set -l buf (commandline)
    set -l out
    if test -n "$buf"
        set out (command ezsh suggest --ask="$buf" </dev/tty)
    else
        set out (command ezsh suggest </dev/tty)
    end
    if test $status -eq 0; and test -n "$out"
        commandline -r -- $out
        commandline -C (string length -- $out)
    end
    commandline -f repaint
end
bind \\ee __ezshell_widget 2>/dev/null
# ---------------------------------------------------------------------------
"""


POWERSHELL_HOOK = r"""# ---------------------------------------------------------------------------
# ezShell Integration for PowerShell (5.1 et 7, avec PSReadLine)
# ---------------------------------------------------------------------------
$env:EZSH_SESSION = "$PID"
$env:EZSH_SHELL = "powershell"
# Même dossier que celui calculé par ezsh (src/core/capture.py:state_dir) ; pwsh marche aussi
# sous Linux et macOS.
if (-not $env:EZSH_STATE_DIR) {
    if ($env:LOCALAPPDATA) { $env:EZSH_STATE_DIR = Join-Path $env:LOCALAPPDATA 'ezsh' }
    elseif ($env:XDG_RUNTIME_DIR) { $env:EZSH_STATE_DIR = Join-Path $env:XDG_RUNTIME_DIR 'ezsh' }
    else { $env:EZSH_STATE_DIR = Join-Path ([IO.Path]::GetTempPath()) "ezsh-$(id -u)" }
}
New-Item -ItemType Directory -Force -Path $env:EZSH_STATE_DIR -ErrorAction SilentlyContinue | Out-Null

# On enrobe le prompt existant (starship, oh-my-posh...) une seule fois, sans le remplacer.
if (-not $global:__ezshell_hooked) {
    $global:__ezshell_hooked = $true
    $global:__ezshell_orig_prompt = $function:prompt
    $global:__ezshell_last_id = (Get-History -Count 1).Id
}

function global:prompt {
    $ok = $?
    $native = $global:LASTEXITCODE
    $h = Get-History -Count 1
    if ($h -and $h.Id -ne $global:__ezshell_last_id) {
        $global:__ezshell_last_id = $h.Id
        $line = $h.CommandLine
        if ($line -notmatch '^\s*(ezsh|ezshell)(\.exe)?\s+suggest' -and $line -notmatch '^\s*(clear|cls|exit)\s*$') {
            # $? dit si la commande a réussi. Si la dernière commande de la ligne est un programme
            # natif, $LASTEXITCODE donne son vrai code ; sinon (cmdlet en échec) on note 1.
            $code = 0
            if (-not $ok) {
                $code = 1
                try {
                    $ast = [System.Management.Automation.Language.Parser]::ParseInput($line, [ref]$null, [ref]$null)
                    $cmds = $ast.FindAll({ $args[0] -is [System.Management.Automation.Language.CommandAst] }, $true)
                    $name = if ($cmds) { @($cmds)[-1].GetCommandName() } else { $null }
                    $info = if ($name) { Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1 } else { $null }
                    if ($info -and $info.CommandType -eq 'Application' -and $native) { $code = $native }
                } catch { }
            }
            $dir = $env:EZSH_STATE_DIR
            [IO.File]::WriteAllText((Join-Path $dir "$env:EZSH_SESSION.cmd"), $line)
            [IO.File]::WriteAllText((Join-Path $dir "$env:EZSH_SESSION.code"), "$code")
            if ($line -notmatch '^\s*(ezsh|ezshell)(\.exe)?\s+run\s') {
                Remove-Item (Join-Path $dir "$env:EZSH_SESSION.run.json") -ErrorAction SilentlyContinue
            }
        }
    }
    $global:LASTEXITCODE = $native
    & $global:__ezshell_orig_prompt
}

# Alt+E : le panneau s'affiche dans la console ; la commande choisie remplace la ligne (jamais exécutée).
# Si la ligne contient du texte, il est envoyé comme question en langage naturel.
if (Get-Command Set-PSReadLineKeyHandler -ErrorAction SilentlyContinue) { try {
    Set-PSReadLineKeyHandler -Chord 'Alt+e' -BriefDescription 'ezShell' -Description 'ezShell : expliquer la derniere erreur' -ScriptBlock {
        $line = $null; $cursor = $null
        [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)
        $prevEncoding = [Console]::OutputEncoding
        $env:PYTHONIOENCODING = 'utf-8'
        $env:EZSH_ASK = $line
        $env:EZSH_ALT_SCREEN = '1'
        try {
            [Console]::OutputEncoding = [Text.Encoding]::UTF8
            $out = & ezsh suggest
            $code = $LASTEXITCODE
        } finally {
            [Console]::OutputEncoding = $prevEncoding
            Remove-Item Env:EZSH_ASK, Env:EZSH_ALT_SCREEN -ErrorAction SilentlyContinue
        }
        if ($code -eq 0 -and $out) {
            [Microsoft.PowerShell.PSConsoleReadLine]::RevertLine()
            [Microsoft.PowerShell.PSConsoleReadLine]::Insert((@($out) -join ' '))
        }
        [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
    }
} catch { } }  # session non interactive (CI, scripts) : pas de raccourci, le reste fonctionne
# ---------------------------------------------------------------------------
"""

POWERSHELL_INIT_LINE = "Invoke-Expression (& ezsh init powershell | Out-String)"
_POWERSHELL_NAMES = ("powershell", "pwsh")


def detect_current_shell() -> str:
    """Shell de l'utilisateur : zsh, bash, fish ou powershell (bash par défaut sous Unix)."""
    if os.environ.get("EZSH_SHELL") in _POWERSHELL_NAMES:
        return "powershell"
    shell_env = os.environ.get("SHELL", "").lower()
    if "zsh" in shell_env:
        return "zsh"
    if "fish" in shell_env:
        return "fish"
    if "bash" in shell_env:
        return "bash"
    if os.name == "nt":
        return "powershell"

    # Fallback to checking existing rc files
    home = Path.home()
    if (home / ".zshrc").exists():
        return "zsh"
    return "bash"


def get_hook_script(shell_name: str) -> str:
    """Script d'intégration pour 'zsh', 'bash', 'fish' ou 'powershell' (alias 'pwsh')."""
    s = shell_name.strip().lower()
    if s == "zsh":
        return ZSH_HOOK
    if s == "fish":
        return FISH_HOOK
    if s in _POWERSHELL_NAMES:
        return POWERSHELL_HOOK
    return BASH_HOOK


def init_line(shell_name: str) -> str:
    """Ligne à ajouter au fichier de configuration du shell."""
    if shell_name in _POWERSHELL_NAMES:
        return POWERSHELL_INIT_LINE
    if shell_name == "fish":
        return "ezsh init fish | source"
    return f'eval "$(ezsh init {shell_name})"'


def reload_hint(shell_name: str, rc_file: Path) -> str:
    """Commande pour recharger la configuration dans le terminal courant."""
    if shell_name in _POWERSHELL_NAMES:
        return ". $PROFILE"
    return f"source {rc_file}"


def powershell_profiles() -> List[Path]:
    """$PROFILE de chaque PowerShell installé (5.1 et 7 n'utilisent pas le même fichier).

    On demande le chemin à PowerShell lui-même : le dossier Documents peut être redirigé (OneDrive).
    """
    paths: List[Path] = []
    for exe in ("pwsh", "powershell"):
        if not shutil.which(exe):
            continue
        try:
            out = subprocess.run(
                [exe, "-NoLogo", "-NoProfile", "-Command", "$PROFILE"],
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if out and Path(out) not in paths:
            paths.append(Path(out))
    return paths


def _append_line(rc_file: Path, line: str) -> Tuple[bool, str]:
    """Ajoute la ligne d'init si elle n'y est pas déjà (lignes commentées ignorées)."""
    try:
        if rc_file.is_file():
            content = rc_file.read_text(encoding="utf-8", errors="ignore")
            active = [
                ln for ln in content.splitlines() if not ln.lstrip().startswith("#")
            ]
            if any("ezsh init" in ln or "ezshell init" in ln for ln in active):
                return True, f"ezShell hook is already present in {rc_file}"
        rc_file.parent.mkdir(parents=True, exist_ok=True)
        with open(rc_file, "a", encoding="utf-8") as f:
            f.write(f"\n# ezShell auto-diagnostic hook\n{line}\n")
        return True, f"ezShell hook successfully added to {rc_file}!"
    except OSError as e:
        return False, f"Failed to write to {rc_file}: {e}"


def install_hook(shell_name: Optional[str] = None) -> Tuple[bool, str, Path]:
    """Ajoute la ligne d'init au fichier de configuration du shell.

    Returns:
        Tuple[bool, str, Path]: (succès, message, fichier modifié)
    """
    target_shell = (shell_name or detect_current_shell()).lower()
    home = Path.home()

    if target_shell in _POWERSHELL_NAMES:
        profiles = powershell_profiles()
        if not profiles:
            return False, "PowerShell not found (powershell or pwsh).", home
        results = [_append_line(p, POWERSHELL_INIT_LINE) for p in profiles]
        ok = all(r[0] for r in results)
        msg = "\n".join(r[1] for r in results)
        if ok:
            msg += (
                "\nIf PowerShell refuses to load your profile, allow local scripts with: "
                "Set-ExecutionPolicy -Scope CurrentUser RemoteSigned"
            )
        return ok, msg, profiles[0]

    if target_shell == "zsh":
        rc_file = home / ".zshrc"
    elif target_shell == "fish":
        rc_file = home / ".config" / "fish" / "config.fish"
    else:
        rc_file = home / ".bashrc"
    ok, msg = _append_line(rc_file, init_line(target_shell))
    return ok, msg, rc_file


__all__ = [
    "detect_current_shell",
    "get_hook_script",
    "init_line",
    "install_hook",
    "powershell_profiles",
    "reload_hint",
]
