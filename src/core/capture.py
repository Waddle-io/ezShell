"""Capture de la dernière commande, de son code de sortie et de la fin de sa sortie d'erreur.

Prototype M0 (DEVELOPMENT.md §7.3). Deux sources, la plus riche gagne :

1. ``ezsh run -- <cmd>`` : exécute la commande, laisse stdout/stdin au terminal,
   recopie stderr en direct et en garde la fin (~4 Ko). Écrit ``<session>.run.json``.
2. Hooks shell (preexec/precmd, PROMPT_COMMAND) : écrivent uniquement la commande
   et le code de sortie (``<session>.cmd`` / ``<session>.code``) : pas de sortie.

Aucun contenu n'est envoyé ici : le masquage des secrets se fait avant l'envoi.
On ne rejoue JAMAIS la commande échouée (effets de bord).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

STDERR_TAIL_BYTES = 4096
IS_WINDOWS = os.name == "nt"


def state_dir() -> Path:
    """Dossier d'état par utilisateur (0700), identique à celui calculé par les hooks."""
    candidates = []
    override = os.environ.get("EZSH_STATE_DIR")
    if override:
        candidates.append(Path(override))

    if IS_WINDOWS:
        # Même chemin que le hook PowerShell : %LOCALAPPDATA%\ezsh (privé à l'utilisateur).
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        candidates.append(Path(local) / "ezsh")
    else:
        runtime = os.environ.get("XDG_RUNTIME_DIR")
        if runtime:
            candidates.append(Path(runtime) / "ezsh")
        candidates.append(Path(tempfile.gettempdir()) / f"ezsh-{os.getuid()}")
        candidates.append(Path.home() / ".ezshell" / "state")

    for candidate in candidates:
        try:
            candidate.mkdir(mode=0o700, parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue

    # Dernier recours
    fallback = Path(tempfile.gettempdir()) / "ezsh"
    fallback.mkdir(mode=0o700, parents=True, exist_ok=True)
    return fallback


def session_key() -> str:
    """Un état par terminal : EZSH_SESSION est exporté par les hooks (PID du shell)."""
    return os.environ.get("EZSH_SESSION") or str(os.getppid())


@dataclass
class LastRun:
    command: str
    exit_code: Optional[int]
    stderr_tail: str = ""
    cwd: str = ""
    captured_output: bool = False  # True si la sortie d'erreur a été capturée


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def run_and_capture(argv: List[str]) -> int:
    """Exécute ``argv`` en gardant la fin de stderr. Retourne le code de sortie de la commande."""
    if not argv:
        print("ezsh run: aucune commande fournie (usage : ezsh run -- <commande>)", file=sys.stderr)
        return 2
    tail = bytearray()
    lock = threading.Lock()
    launch = argv
    if IS_WINDOWS and not shutil.which(argv[0]):
        # Cmdlet ou alias PowerShell (Get-ChildItem, dir…) : on le lance via PowerShell.
        exe = shutil.which("pwsh") or shutil.which("powershell")
        if exe:
            launch = [exe, "-NoLogo", "-NoProfile", "-Command", _powershell_script(argv)]
    try:
        proc = subprocess.Popen(launch, stderr=subprocess.PIPE)
    except FileNotFoundError:
        msg = f"ezsh: commande introuvable : {argv[0]}\n"
        sys.stderr.write(msg)
        _store(argv, 127, msg.encode())
        return 127
    except PermissionError:
        msg = f"ezsh: permission refusée : {argv[0]}\n"
        sys.stderr.write(msg)
        _store(argv, 126, msg.encode())
        return 126

    def pump() -> None:
        assert proc.stderr is not None
        for chunk in iter(lambda: proc.stderr.read1(4096), b""):  # type: ignore[attr-defined]
            try:
                sys.stderr.buffer.write(chunk)
                sys.stderr.buffer.flush()
            except Exception:
                pass
            with lock:
                tail.extend(chunk)
                if len(tail) > STDERR_TAIL_BYTES:
                    del tail[: len(tail) - STDERR_TAIL_BYTES]

    t = threading.Thread(target=pump, daemon=True)
    t.start()
    # Ctrl+C arrive aussi à l'enfant (même terminal) : on le laisse décider de s'arrêter
    # au lieu de le tuer, pour ne pas casser les programmes qui gèrent SIGINT (REPL, psql…).
    while True:
        try:
            code = proc.wait()
            break
        except KeyboardInterrupt:
            continue
    if code < 0:  # tué par un signal (Unix) : convention shell 128 + n
        code = 128 - code
    t.join(timeout=2)
    _store(argv, code, bytes(tail))
    return code


def _ps_quote(arg: str) -> str:
    """Argument PowerShell : nu s'il est sûr (garde -Recurse comme paramètre), sinon '…'."""
    if re.fullmatch(r"[\w\-.:/\\=+,@%]+", arg):
        return arg
    return "'" + arg.replace("'", "''") + "'"


def _powershell_script(argv: List[str]) -> str:
    """Script PowerShell qui lance `argv` et reproduit les codes de sortie d'un shell :
    127 si la commande n'existe pas, le code du programme natif, sinon 1 en cas d'échec."""
    name = argv[0].replace("'", "''")
    return (
        f"if (-not (Get-Command -Name '{name}' -ErrorAction SilentlyContinue)) {{ "
        f"[Console]::Error.WriteLine('ezsh: commande introuvable : {name}'); exit 127 }}; "
        f"& {' '.join(_ps_quote(a) for a in argv)}; "
        "if (-not $?) { if ($LASTEXITCODE) { exit $LASTEXITCODE } else { exit 1 } }"
    )


def _store(argv: List[str], code: int, tail: bytes) -> None:
    if IS_WINDOWS:
        command = subprocess.list2cmdline(argv)
    else:
        import shlex

        command = " ".join(shlex.quote(a) for a in argv)
    payload = {
        "command": command,
        "exit_code": code,
        "stderr_tail": tail.decode("utf-8", errors="replace"),
        "cwd": os.getcwd(),
        "ts": time.time(),
    }
    try:
        _atomic_write(state_dir() / f"{session_key()}.run.json", json.dumps(payload))
    except OSError:
        pass  # la capture est un confort : ne jamais casser la commande


def _read(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def read_last_run() -> Optional[LastRun]:
    """Dernière commande de CE terminal. Utilise la capture ``run`` si elle est la plus récente."""
    d, key = state_dir(), session_key()
    cmd_p, code_p, run_p = d / f"{key}.cmd", d / f"{key}.code", d / f"{key}.run.json"

    run = None
    raw = _read(run_p)
    if raw:
        try:
            run = json.loads(raw)
        except json.JSONDecodeError:
            run = None

    # Les hooks suppriment run.json dès qu'une autre commande tourne :
    # s'il existe, c'est le plus récent.
    if run:
        return LastRun(
            run["command"],
            run.get("exit_code"),
            run.get("stderr_tail", ""),
            run.get("cwd", ""),
            True,
        )

    hook_cmd = (_read(cmd_p) or "").strip()
    hook_code = (_read(code_p) or "").strip()

    if hook_cmd:
        try:
            code = int(hook_code) if hook_code else None
        except ValueError:
            code = None
        return LastRun(hook_cmd, code, "", "", False)
    return None


__all__ = ["run_and_capture", "read_last_run", "LastRun", "state_dir", "session_key"]
