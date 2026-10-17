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
from pathlib import Path
from typing import Optional, Tuple

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


def detect_current_shell() -> str:
    """Detects the current user shell name (zsh, bash, fish, etc.).

    Returns:
        str: 'zsh', 'bash', 'fish', or 'bash' as default.
    """
    shell_env = os.environ.get("SHELL", "").lower()
    if "zsh" in shell_env:
        return "zsh"
    if "fish" in shell_env:
        return "fish"
    if "bash" in shell_env:
        return "bash"

    # Fallback to checking existing rc files
    home = Path.home()
    if (home / ".zshrc").exists():
        return "zsh"
    return "bash"


def get_hook_script(shell_name: str) -> str:
    """Returns the shell hook snippet for the specified shell.

    Args:
        shell_name (str): Target shell ('zsh', 'bash', or 'fish').

    Returns:
        str: Shell script code.
    """
    s = shell_name.strip().lower()
    if s == "zsh":
        return ZSH_HOOK
    if s == "fish":
        return FISH_HOOK
    return BASH_HOOK


def install_hook(shell_name: Optional[str] = None) -> Tuple[bool, str, Path]:
    """Appends ezShell init snippet to the user's shell rc file.

    Args:
        shell_name (Optional[str]): Explicit shell target ('zsh', 'bash'), or auto-detected.

    Returns:
        Tuple[bool, str, Path]: (success, message, rc_file_path)
    """
    target_shell = shell_name or detect_current_shell()
    home = Path.home()

    if target_shell == "zsh":
        rc_file = home / ".zshrc"
    elif target_shell == "fish":
        rc_file = home / ".config" / "fish" / "config.fish"
    else:
        rc_file = home / ".bashrc"

    init_line = f'eval "$(ezsh init {target_shell})"'

    # Check if already installed
    if rc_file.is_file():
        try:
            content = rc_file.read_text(encoding="utf-8", errors="ignore")
            if "ezsh init" in content or "ezshell init" in content:
                return (True, f"ezShell hook is already present in {rc_file}", rc_file)
        except Exception as e:
            return (False, f"Could not read {rc_file}: {e}", rc_file)

    # Append to rc file
    try:
        rc_file.parent.mkdir(parents=True, exist_ok=True)
        with open(rc_file, "a", encoding="utf-8") as f:
            f.write(f"\n# ezShell auto-diagnostic hook\n{init_line}\n")
        return (True, f"ezShell hook successfully added to {rc_file}!", rc_file)
    except Exception as e:
        return (False, f"Failed to write to {rc_file}: {e}", rc_file)


__all__ = ["detect_current_shell", "get_hook_script", "install_hook"]

