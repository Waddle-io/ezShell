"""
ezShell Shell Integration & Hook Generator
==========================================

Generates, installs, and uninstalls non-intrusive shell hooks for Bash, Zsh, Fish,
and PowerShell (5.1 & Core 7+).
The hooks automatically capture the last executed command and its exit code
into the per-terminal state directory, enabling instant AI error diagnosis
and configurable shell shortcuts.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from src.core.config import EzShellConfig
from src.core.keybindings import KeybindingConfig, format_shell_trigger

MARKER_START = "# >>> ezShell integration >>>"
MARKER_END = "# <<< ezShell integration <<<"

_STATE_PREAMBLE = """export EZSH_SESSION="$$"
if [ -z "$EZSH_STATE_DIR" ]; then
    if [ -n "$XDG_RUNTIME_DIR" ] && [ -w "$XDG_RUNTIME_DIR" ]; then
        EZSH_STATE_DIR="$XDG_RUNTIME_DIR/ezsh"
    else
        EZSH_STATE_DIR="${TMPDIR:-/tmp}/ezsh-$(id -u 2>/dev/null || echo $$)"
    fi
    export EZSH_STATE_DIR
fi
( umask 077; mkdir -p "$EZSH_STATE_DIR" ) 2>/dev/null
"""


def _build_zsh_hook(kb: KeybindingConfig) -> str:
    widget_binding = ""
    if kb.trigger_enabled:
        stmt, _ = format_shell_trigger(kb.trigger_key, "zsh")
        widget_binding = f"""# ezShell shortcut ({kb.trigger_key}) : l'interface s'affiche sur /dev/tty,
# la commande choisie est insérée dans le prompt (jamais exécutée silencieusement).
__ezshell_widget() {{
    local out
    zle -I
    out="$(command ezsh suggest ${{BUFFER:+--ask="$BUFFER"}} </dev/tty)"
    if [[ $? -eq 0 && -n "$out" ]]; then
        BUFFER="$out"
        CURSOR=${{#BUFFER}}
    fi
    zle reset-prompt 2>/dev/null || true
}}
zle -N __ezshell_widget 2>/dev/null || true
{stmt}
"""

    return f"""# ---------------------------------------------------------------------------
# ezShell Integration for Zsh  (état par terminal ; insertion dans le prompt)
# ---------------------------------------------------------------------------
{_STATE_PREAMBLE}__ezshell_preexec() {{
    __EZSHELL_LAST_CMD="$1"
}}

__ezshell_precmd() {{
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
}}

autoload -Uz add-zsh-hook 2>/dev/null
add-zsh-hook preexec __ezshell_preexec 2>/dev/null
add-zsh-hook precmd __ezshell_precmd 2>/dev/null

{widget_binding}# ---------------------------------------------------------------------------
"""


def _build_bash_hook(kb: KeybindingConfig) -> str:
    widget_binding = ""
    if kb.trigger_enabled:
        stmt, _ = format_shell_trigger(kb.trigger_key, "bash")
        widget_binding = f"""# ezShell shortcut ({kb.trigger_key}) : interface sur /dev/tty ; insertion dans READLINE_LINE.
__ezshell_widget() {{
    local out
    out="$(command ezsh suggest ${{READLINE_LINE:+--ask="$READLINE_LINE"}} </dev/tty)"
    if [[ $? -eq 0 && -n "$out" ]]; then
        READLINE_LINE="$out"
        READLINE_POINT=${{#READLINE_LINE}}
    fi
}}
{stmt}
"""

    return f"""# ---------------------------------------------------------------------------
# ezShell Integration for Bash  (état par terminal ; insertion dans le prompt)
# ---------------------------------------------------------------------------
{_STATE_PREAMBLE}__ezshell_prompt_command() {{
    local exit_code=$?
    local last_cmd
    last_cmd=$(HISTTIMEFORMAT= history 1 2>/dev/null | sed -e 's/^[ ]*[0-9]*[ ]*//')
    [[ -z "$last_cmd" ]] && return
    local hist_id
    hist_id=$(HISTTIMEFORMAT= history 1 2>/dev/null | awk '{{print $1}}')
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
}}

if [[ \";$PROMPT_COMMAND;\" != *\";__ezshell_prompt_command;\"* ]]; then
    PROMPT_COMMAND=\"__ezshell_prompt_command${{PROMPT_COMMAND:+;$PROMPT_COMMAND}}\"
fi

{widget_binding}# ---------------------------------------------------------------------------
"""


def _build_fish_hook(kb: KeybindingConfig) -> str:
    widget_binding = ""
    if kb.trigger_enabled:
        stmt, _ = format_shell_trigger(kb.trigger_key, "fish")
        widget_binding = f"""function __ezshell_widget
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
{stmt}
"""

    return f"""# ---------------------------------------------------------------------------
# ezShell Integration for Fish
# ---------------------------------------------------------------------------
set -gx EZSH_SESSION $fish_pid
if test -z "$EZSH_STATE_DIR"
    if test -n "$XDG_RUNTIME_DIR" -a -w "$XDG_RUNTIME_DIR"
        set -gx EZSH_STATE_DIR "$XDG_RUNTIME_DIR/ezsh"
    else
        set -gx EZSH_STATE_DIR (string join '' (test -n "$TMPDIR"; and echo $TMPDIR; or echo /tmp) "/ezsh-"(id -u 2>/dev/null; or echo $fish_pid))
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

{widget_binding}# ---------------------------------------------------------------------------
"""


def _build_powershell_hook(kb: KeybindingConfig) -> str:
    widget_binding = ""
    if kb.trigger_enabled:
        chords, desc = format_shell_trigger(kb.trigger_key, "powershell")
        widget_binding = f"""# ezShell shortcut ({desc}) : console interaction via PSReadLine
if (-not (Get-Command Set-PSReadLineKeyHandler -ErrorAction SilentlyContinue)) {{
    Import-Module PSReadLine -ErrorAction SilentlyContinue
}}
if (Get-Command Set-PSReadLineKeyHandler -ErrorAction SilentlyContinue) {{
    try {{
        Set-PSReadLineKeyHandler -Chord {chords} -BriefDescription 'ezShell' -Description 'ezShell : expliquer la derniere erreur' -ScriptBlock {{
            $line = $null; $cursor = $null
            [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)
            $prevEncoding = [Console]::OutputEncoding
            $env:PYTHONIOENCODING = 'utf-8'
            $env:EZSH_ASK = $line
            $env:EZSH_ALT_SCREEN = '1'
            $global:LASTEXITCODE = 0
            try {{
                [Console]::OutputEncoding = [Text.Encoding]::UTF8
                $out = & ezsh suggest
                $code = $LASTEXITCODE
                $cmdOk = $?
            }} finally {{
                [Console]::OutputEncoding = $prevEncoding
                Remove-Item Env:EZSH_ASK, Env:EZSH_ALT_SCREEN -ErrorAction SilentlyContinue
            }}
            $text = if ($out -is [array]) {{ $out -join "`n" }} else {{ [string]$out }}
            $text = $text.Trim()
            if (($code -eq 0 -or $cmdOk) -and $text) {{
                [Microsoft.PowerShell.PSConsoleReadLine]::RevertLine()
                [Microsoft.PowerShell.PSConsoleReadLine]::Insert($text)
            }}
            [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
        }}
    }} catch {{ }}
}}
"""

    return f"""# ---------------------------------------------------------------------------
# ezShell Integration for PowerShell (5.1 et 7+, avec PSReadLine)
# ---------------------------------------------------------------------------
$env:EZSH_SESSION = "$PID"
$env:EZSH_SHELL = "powershell"
if (-not $env:EZSH_STATE_DIR) {{
    if ($env:LOCALAPPDATA) {{
        $env:EZSH_STATE_DIR = Join-Path $env:LOCALAPPDATA 'ezsh'
    }} elseif ($env:XDG_RUNTIME_DIR -and (Test-Path $env:XDG_RUNTIME_DIR)) {{
        $env:EZSH_STATE_DIR = Join-Path $env:XDG_RUNTIME_DIR 'ezsh'
    }} else {{
        $u = if ([Environment]::UserName) {{ [Environment]::UserName }} else {{ "$PID" }}
        $env:EZSH_STATE_DIR = Join-Path ([IO.Path]::GetTempPath()) "ezsh-$u"
    }}
}}
try {{
    [System.IO.Directory]::CreateDirectory($env:EZSH_STATE_DIR) | Out-Null
}} catch {{ }}

if (-not $global:__ezshell_hooked) {{
    $global:__ezshell_hooked = $true
    $global:__ezshell_orig_prompt = $function:prompt
    $global:__ezshell_last_id = (Get-History -Count 1).Id
}}

function global:prompt {{
    $ok = $?
    $native = $global:LASTEXITCODE
    $h = Get-History -Count 1
    if ($h -and $h.Id -ne $global:__ezshell_last_id) {{
        $global:__ezshell_last_id = $h.Id
        $line = $h.CommandLine
        if ($line -notmatch '^\\s*(ezsh|ezshell)(\\.exe)?\\s+suggest' -and $line -notmatch '^\\s*(clear|cls|exit)\\s*$') {{
            $code = 0
            if (-not $ok) {{
                $code = 1
                try {{
                    $ast = [System.Management.Automation.Language.Parser]::ParseInput($line, [ref]$null, [ref]$null)
                    $cmds = $ast.FindAll({{ $args[0] -is [System.Management.Automation.Language.CommandAst] }}, $true)
                    $name = if ($cmds) {{ @($cmds)[-1].GetCommandName() }} else {{ $null }}
                    $info = if ($name) {{ Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1 }} else {{ $null }}
                    if ($info -and $info.CommandType -eq 'Application' -and $native) {{ $code = $native }}
                }} catch {{ }}
            }}
            $dir = $env:EZSH_STATE_DIR
            try {{
                [IO.File]::WriteAllText((Join-Path $dir "$env:EZSH_SESSION.cmd"), $line)
                [IO.File]::WriteAllText((Join-Path $dir "$env:EZSH_SESSION.code"), "$code")
                if ($line -notmatch '^\\s*(ezsh|ezshell)(\\.exe)?\\s+run\\s') {{
                    Remove-Item (Join-Path $dir "$env:EZSH_SESSION.run.json") -ErrorAction SilentlyContinue
                }}
            }} catch {{ }}
        }}
    }}
    $global:LASTEXITCODE = $native
    if ($global:__ezshell_orig_prompt) {{
        & $global:__ezshell_orig_prompt
    }} else {{
        "PS $($executionContext.SessionState.Path.CurrentLocation)> "
    }}
}}

{widget_binding}# ---------------------------------------------------------------------------
"""


POWERSHELL_INIT_LINE = "Invoke-Expression (& ezsh init powershell | Out-String)"
_POWERSHELL_NAMES = ("powershell", "pwsh")


# Compatibilité des constantes existantes
ZSH_HOOK = _build_zsh_hook(KeybindingConfig())
BASH_HOOK = _build_bash_hook(KeybindingConfig())
FISH_HOOK = _build_fish_hook(KeybindingConfig())
POWERSHELL_HOOK = _build_powershell_hook(KeybindingConfig())


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


def get_hook_script(shell_name: str, config: Optional[EzShellConfig] = None) -> str:
    """Script d'intégration pour 'zsh', 'bash', 'fish' ou 'powershell' (alias 'pwsh')."""
    cfg = config or EzShellConfig.load()
    kb = cfg.get_keybindings()
    s = shell_name.strip().lower()
    if s == "zsh":
        return _build_zsh_hook(kb)
    if s == "fish":
        return _build_fish_hook(kb)
    if s in _POWERSHELL_NAMES:
        return _build_powershell_hook(kb)
    return _build_bash_hook(kb)


def init_line(shell_name: str) -> str:
    """Ligne à ajouter au fichier de configuration du shell."""
    s = shell_name.strip().lower()
    if s in _POWERSHELL_NAMES:
        return POWERSHELL_INIT_LINE
    if s == "fish":
        return "ezsh init fish | source"
    return f'eval "$(ezsh init {s})"'


def reload_hint(shell_name: str, rc_file: Path) -> str:
    """Commande pour recharger la configuration dans le terminal courant."""
    if shell_name in _POWERSHELL_NAMES:
        return ". $PROFILE"
    return f"source {rc_file}"


def powershell_profiles() -> List[Path]:
    """$PROFILE de chaque PowerShell installé (5.1 et 7 n'utilisent pas le même fichier)."""
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

    # Fallback si l'exécutable n'a pas répondu ou n'est pas dans le PATH
    if not paths:
        home = Path.home()
        if os.name == "nt":
            docs = home / "Documents"
            candidates = [
                docs / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
                docs / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
            ]
        else:
            candidates = [
                home / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1",
            ]
        for c in candidates:
            if c.exists() and c not in paths:
                paths.append(c)

    return paths


def _clean_content(content: str) -> str:
    """Supprime les blocs délimités ezShell ainsi que les anciennes lignes non balisées."""
    # 1. Supprime le bloc balisé si présent
    pattern = re.compile(
        rf"{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}\n?",
        re.DOTALL,
    )
    cleaned = pattern.sub("", content)

    # 2. Supprime également les anciennes lignes d'init historiques (sans marqueurs)
    lines = []
    skip_next_comment = False
    for line in cleaned.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == "# ezShell auto-diagnostic hook":
            skip_next_comment = True
            continue
        if skip_next_comment:
            skip_next_comment = False
            if "ezsh init" in stripped or "ezshell init" in stripped:
                continue
        if not stripped.startswith("#") and any(
            init_kw in stripped
            for init_kw in (
                'eval "$(ezsh init',
                'eval "$(ezshell init',
                "ezsh init fish | source",
                "Invoke-Expression (& ezsh init",
            )
        ):
            continue
        lines.append(line)

    result = "".join(lines)
    # Réduire les lignes blanches multiples à la fin
    result = re.sub(r"\n{3,}", "\n\n", result).rstrip()
    return result + "\n" if result else ""


def _install_block(rc_file: Path, target_line: str) -> Tuple[bool, str]:
    """Installe ou met à jour le bloc délimité ezShell dans le fichier rc."""
    try:
        content = ""
        if rc_file.is_file():
            content = rc_file.read_text(encoding="utf-8", errors="ignore")

        # Vérifier si exactement ce bloc est déjà présent
        block = f"{MARKER_START}\n# ezShell auto-diagnostic hook & keybindings\n{target_line}\n{MARKER_END}\n"
        if block in content:
            return True, f"ezShell hook is already present and up to date in {rc_file}"

        # Nettoyer les versions précédentes
        base = _clean_content(content)
        rc_file.parent.mkdir(parents=True, exist_ok=True)
        new_content = (base + "\n" if base and not base.endswith("\n") else base) + block
        rc_file.write_text(new_content, encoding="utf-8")
        return True, f"ezShell hook successfully added and installed in {rc_file}!"
    except OSError as e:
        return False, f"Failed to write to {rc_file}: {e}"


def _remove_block(rc_file: Path) -> Tuple[bool, str]:
    """Retire le bloc ezShell et les anciennes lignes du fichier rc."""
    try:
        if not rc_file.is_file():
            return True, f"File {rc_file} does not exist, nothing to remove."
        content = rc_file.read_text(encoding="utf-8", errors="ignore")
        cleaned = _clean_content(content)
        if cleaned == content:
            return True, f"No ezShell hook found in {rc_file}."
        rc_file.write_text(cleaned, encoding="utf-8")
        return True, f"ezShell hook successfully removed from {rc_file}."
    except OSError as e:
        return False, f"Failed to modify {rc_file}: {e}"


def _append_line(rc_file: Path, line: str) -> Tuple[bool, str]:
    """Fonction de compatibilité : délègue à _install_block."""
    return _install_block(rc_file, line)


def install_hook(shell_name: Optional[str] = None) -> Tuple[bool, str, Path]:
    """Ajoute ou met à jour le bloc d'init dans le fichier de configuration du shell."""
    target_shell = (shell_name or detect_current_shell()).lower()
    home = Path.home()

    if target_shell in _POWERSHELL_NAMES:
        profiles = powershell_profiles()
        if not profiles:
            return False, "PowerShell not found (powershell or pwsh).", home
        results = [_install_block(p, POWERSHELL_INIT_LINE) for p in profiles]
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
        # Bash : privilégier .bashrc, fallback .bash_profile si macOS
        rc_file = home / ".bashrc"
        if not rc_file.exists() and (home / ".bash_profile").exists():
            rc_file = home / ".bash_profile"

    ok, msg = _install_block(rc_file, init_line(target_shell))
    return ok, msg, rc_file


def uninstall_hook(shell_name: Optional[str] = None) -> Tuple[bool, str, Path]:
    """Désinstalle proprement l'intégration ezShell du shell."""
    target_shell = (shell_name or detect_current_shell()).lower()
    home = Path.home()

    if target_shell in _POWERSHELL_NAMES:
        profiles = powershell_profiles()
        if not profiles:
            return False, "PowerShell profile not found.", home
        results = [_remove_block(p) for p in profiles]
        ok = all(r[0] for r in results)
        return ok, "\n".join(r[1] for r in results), profiles[0]

    if target_shell == "zsh":
        rc_file = home / ".zshrc"
    elif target_shell == "fish":
        rc_file = home / ".config" / "fish" / "config.fish"
    else:
        rc_file = home / ".bashrc"
        if not rc_file.exists() and (home / ".bash_profile").exists():
            rc_file = home / ".bash_profile"

    ok, msg = _remove_block(rc_file)
    return ok, msg, rc_file


__all__ = [
    "detect_current_shell",
    "get_hook_script",
    "init_line",
    "install_hook",
    "uninstall_hook",
    "powershell_profiles",
    "reload_hint",
    "MARKER_START",
    "MARKER_END",
]
