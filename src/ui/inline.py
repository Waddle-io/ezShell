"""Flux inline : `ezsh suggest`.

L'interface s'affiche sur /dev/tty ; seule la commande finale sort sur stdout.

Règles (DEVELOPMENT.md §1) : jamais d'exécution silencieuse (on n'exécute RIEN, on insère
dans le prompt via la fonction shell), le contenu des requêtes n'est jamais journalisé.
Deux modes de touches : *résultat* (⏎ c e / q Esc y) et *saisie* (⏎ envoie, Esc revient).
"""

from __future__ import annotations

import os
import select
import shutil
import subprocess
import sys
from contextlib import contextmanager
from typing import Optional, TextIO, Tuple

from src.core.provider import (
    LLMProvider,
    MissingKey,
    ProviderError,
    ProviderOffline,
    QuotaExceeded,
    get_provider,
)
from src.core.schema import InvalidResponse
from src.core.suggest import Suggestion, build_request, detect_lang, get_suggestion
from src.ui.panel import loading_text, message_panel, result_panel, tr

try:  # Unix uniquement (Windows hors MVP : D6)
    import termios
    import tty as _tty
except ImportError:  # pragma: no cover
    termios = None  # type: ignore


def open_tty() -> Tuple[Optional[TextIO], Optional[int]]:
    """(flux d'écriture, fd de lecture) sur le terminal de contrôle, sinon (stderr, None)."""
    try:
        fd = os.open("/dev/tty", os.O_RDWR)
        return os.fdopen(os.dup(fd), "w", buffering=1, encoding="utf-8"), fd
    except OSError:
        return (sys.stderr if sys.stderr.isatty() else None), None


@contextmanager
def raw_mode(fd: int):
    old = termios.tcgetattr(fd)
    try:
        _tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def read_key(fd: int) -> str:
    """Une touche : enter, esc, backspace, left, right, home, end, ctrl-c, ou le caractère."""
    b = os.read(fd, 1)
    if not b:
        return "esc"
    ch = b.decode("utf-8", errors="ignore")
    if ch in ("\r", "\n"):
        return "enter"
    if ch == "\x03":
        return "ctrl-c"
    if ch in ("\x7f", "\x08"):
        return "backspace"
    if ch == "\x1b":
        if not select.select([fd], [], [], 0.05)[0]:
            return "esc"
        seq = os.read(fd, 8).decode("utf-8", errors="ignore")
        return {
            "[D": "left",
            "[C": "right",
            "[H": "home",
            "[F": "end",
            "[1~": "home",
            "[4~": "end",
        }.get(seq, "ignore")
    if ch and ord(ch[0]) >= 0x80:  # début d'un caractère UTF-8 multi-octets
        need = 1 if b[0] >> 5 == 0b110 else 2 if b[0] >> 4 == 0b1110 else 3
        ch = (b + os.read(fd, need)).decode("utf-8", errors="ignore")
    return ch


def edit_line(fd: int, out: TextIO, prompt: str, initial: str = "") -> Optional[str]:
    """Mini éditeur de ligne (stdout reste libre). Retourne None si Échap."""
    buf, pos = list(initial), len(initial)

    def redraw() -> None:
        out.write("\r\x1b[2K" + prompt + "".join(buf))
        out.write("\r" + "\x1b[%dC" % (len(prompt) + pos) if len(prompt) + pos else "\r")
        out.flush()

    redraw()
    with raw_mode(fd):
        while True:
            k = read_key(fd)
            if k == "enter":
                out.write("\n")
                return "".join(buf).strip()
            if k in ("esc", "ctrl-c"):
                out.write("\n")
                return None
            if k == "backspace" and pos:
                del buf[pos - 1]
                pos -= 1
            elif k == "left":
                pos = max(0, pos - 1)
            elif k == "right":
                pos = min(len(buf), pos + 1)
            elif k == "home":
                pos = 0
            elif k == "end":
                pos = len(buf)
            elif len(k) >= 1 and k not in ("ignore", "backspace") and k.isprintable():
                buf.insert(pos, k)
                pos += 1
            redraw()


def copy_to_clipboard(text: str) -> bool:
    for cmd in (
        ["pbcopy"],
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text.encode(), check=True, timeout=2)
                return True
            except Exception:
                continue
    return False


def _fetch(req, provider: LLMProvider, console, lang: str):
    """Retourne ('ok', Suggestion) ou (kind, kwargs) pour message_panel."""
    try:
        with console.status(loading_text(lang), spinner="dots"):
            return "ok", get_suggestion(req, provider)
    except ProviderOffline:
        return "offline", {}
    except QuotaExceeded as q:
        return ("trial" if q.scope == "anonymous" else "quota"), {
            "scope": q.scope,
            "reset": q.reset_at,
        }
    except MissingKey:
        return "nokey", {}
    except InvalidResponse:
        return "invalid", {}
    except ProviderError:
        return "error", {}


def run_inline(ask: Optional[str] = None, provider: Optional[LLMProvider] = None) -> int:
    """0 : commande écrite sur stdout ; 1 : annulé ; 2 : environnement inadapté (pas de tty)."""
    from rich.console import Console

    out, fd = open_tty()
    if out is None or fd is None or termios is None:
        print("ezsh: terminal interactif requis (pas de /dev/tty).", file=sys.stderr)
        return 2
    lang = detect_lang()
    t = tr(lang)
    width = min(80, shutil.get_terminal_size((80, 24)).columns)
    console = Console(
        file=out, force_terminal=True, width=width, highlight=False, markup=False, emoji=False
    )
    provider = provider or get_provider()

    query = (ask or "").strip()
    last_state: Tuple[str, object] = ("empty", {})

    def ask_model(q: str) -> Tuple[str, object]:
        return _fetch(build_request(q), provider, console, lang)

    # ouverture : question explicite, sinon dernière commande, sinon panneau vide
    from src.core.capture import read_last_run

    if query or read_last_run():
        last_state = ask_model(query)
    show(console, last_state, lang)

    while True:
        kind, payload = last_state
        with raw_mode(fd):
            key = read_key(fd)
        if key in ("q", "esc", "ctrl-c"):
            return 1
        if key == "/":
            q = edit_line(fd, out, f"{t['ask']} › ")
            if q:
                last_state = ask_model(q)
                show(console, last_state, lang)
            continue
        if kind != "ok":
            continue
        s: Suggestion = payload  # type: ignore[assignment]
        if not s.command:
            continue
        if key == "c":
            console.print(t["copied"] if copy_to_clipboard(s.command) else t["nocopy"], style="dim")
        elif key == "e":
            console.print(t["edit"], style="dim")
            edited = edit_line(
                fd, out, "$ ", s.command.replace("\n", " ; ") if s.multiline else s.command
            )
            if edited:
                return _emit(edited, console, t)
        elif key == "enter" and s.risk != "high" and not s.multiline:
            return _emit(s.command, console, t)
        elif key == "y" and (s.risk == "high" or s.multiline):
            return _emit(s.command, console, t)


def show(console, state: Tuple[str, object], lang: str) -> None:
    kind, payload = state
    console.print(
        result_panel(payload, lang)
        if kind == "ok"
        else message_panel(kind, lang, **(payload or {}))
    )  # type: ignore[arg-type]


def _emit(command: str, console, t: dict) -> int:
    from src.core.sanitize import sanitize_command

    safe = sanitize_command(command)
    if safe.multiline:  # garde-fou final : jamais de saut de ligne dans le prompt
        safe_text = " ; ".join(line.strip() for line in safe.text.splitlines() if line.strip())
    else:
        safe_text = safe.text
    console.print(t["inserted"], style="dim")
    sys.stdout.write(safe_text)
    sys.stdout.flush()
    return 0
