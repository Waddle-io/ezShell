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
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

STDERR_TAIL_BYTES = 4096


def state_dir() -> Path:
    """Dossier d'état par utilisateur (0700), identique à celui calculé par les hooks."""
    override = os.environ.get("EZSH_STATE_DIR")
    if override:
        base = Path(override)
    else:
        runtime = os.environ.get("XDG_RUNTIME_DIR")
        base = (
            Path(runtime) / "ezsh"
            if runtime
            else Path(tempfile.gettempdir()) / f"ezsh-{os.getuid()}"
        )
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    return base


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
    try:
        proc = subprocess.Popen(argv, stderr=subprocess.PIPE)
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
    try:
        code = proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        code = 130
    t.join(timeout=2)
    _store(argv, code, bytes(tail))
    return code


def _store(argv: List[str], code: int, tail: bytes) -> None:
    import shlex

    payload = {
        "command": " ".join(shlex.quote(a) for a in argv),
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
