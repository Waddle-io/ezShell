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

ZSH_HOOK = """# ---------------------------------------------------------------------------
# ezShell Integration for Zsh
# ---------------------------------------------------------------------------
__ezshell_preexec() {
    export _EZSHELL_LAST_CMD="$1"
}

__ezshell_precmd() {
    local exit_code=$?
    if [[ -n "$_EZSHELL_LAST_CMD" ]]; then
        case "$_EZSHELL_LAST_CMD" in
            ezsh*|ezshell*|eszh*|clear|exit|history*) ;;
            *)
                mkdir -p "$HOME/.ezshell" 2>/dev/null
                printf "%s" "$_EZSHELL_LAST_CMD" > "$HOME/.ezshell/.last_command"
                printf "%d" "$exit_code" > "$HOME/.ezshell/.last_exit_code"
                ;;
        esac
        unset _EZSHELL_LAST_CMD
    fi
}

autoload -Uz add-zsh-hook 2>/dev/null
add-zsh-hook preexec __ezshell_preexec 2>/dev/null
add-zsh-hook precmd __ezshell_precmd 2>/dev/null

# Global shortcut Alt+e to launch ezShell
__ezshell_widget() {
    ezsh
    zle reset-prompt 2>/dev/null || true
}
zle -N __ezshell_widget 2>/dev/null || true
bindkey '\\ee' __ezshell_widget 2>/dev/null || true
# ---------------------------------------------------------------------------
"""

BASH_HOOK = """# ---------------------------------------------------------------------------
# ezShell Integration for Bash
# ---------------------------------------------------------------------------
__ezshell_prompt_command() {
    local exit_code=$?
    local last_cmd
    last_cmd=$(HISTTIMEFORMAT= history 1 2>/dev/null | sed -e 's/^[ ]*[0-9]*[ ]*//')
    if [[ -n "$last_cmd" ]]; then
        case "$last_cmd" in
            ezsh*|ezshell*|eszh*|clear|exit|history*) ;;
            *)
                mkdir -p "$HOME/.ezshell" 2>/dev/null
                printf "%s" "$last_cmd" > "$HOME/.ezshell/.last_command"
                printf "%d" "$exit_code" > "$HOME/.ezshell/.last_exit_code"
                ;;
        esac
    fi
}

if [[ ";$PROMPT_COMMAND;" != *";__ezshell_prompt_command;"* ]]; then
    PROMPT_COMMAND="__ezshell_prompt_command${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi

# Global shortcut Alt+e to launch ezShell
bind -x '"\\ee": ezsh' 2>/dev/null || true
# ---------------------------------------------------------------------------
"""

FISH_HOOK = """# ---------------------------------------------------------------------------
# ezShell Integration for Fish
# ---------------------------------------------------------------------------
function __ezshell_postexec --on-event fish_postexec
    set -l exit_code $status
    set -l last_cmd $argv[1]
    switch $last_cmd
        case 'ezsh*' 'ezshell*' 'eszh*' 'clear' 'exit' 'history*'
            return
        case '*'
            mkdir -p "$HOME/.ezshell" 2>/dev/null
            printf "%s" "$last_cmd" > "$HOME/.ezshell/.last_command"
            printf "%d" "$exit_code" > "$HOME/.ezshell/.last_exit_code"
    end
end

bind \\ee 'ezsh; commandline -f repaint' 2>/dev/null
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
