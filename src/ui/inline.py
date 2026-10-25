"""Flux inline : `ezsh suggest`.

L'interface s'affiche sur le terminal (/dev/tty sous Unix, la console CONOUT$/CONIN$ sous
Windows) ; seule la commande finale sort sur stdout, que la fonction shell récupère.

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
    UpdateRequired,
    get_provider,
)
from src.core.schema import InvalidResponse
from src.core.suggest import Suggestion, build_request, detect_lang, get_suggestion
from src.ui.panel import loading_text, message_panel, result_panel, tr

IS_WINDOWS = os.name == "nt"
WIN_CONSOLE = -2  # pseudo-descripteur : les touches se lisent via msvcrt, pas via un fd

if IS_WINDOWS:  # pragma: no cover - exécuté sur la CI Windows
    import msvcrt

    termios = None  # type: ignore
else:
    import termios
    import tty as _tty


def _enable_vt(stream: TextIO) -> None:
    """Active les séquences ANSI sur la console Windows (effacement de ligne, couleurs)."""
    try:  # pragma: no cover - Windows uniquement
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = msvcrt.get_osfhandle(stream.fileno())
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def open_tty() -> Tuple[Optional[TextIO], Optional[int]]:
    """(flux d'écriture, lecteur de touches) sur le terminal, même si stdout est capturé."""
    if IS_WINDOWS:  # pragma: no cover - Windows uniquement
        try:
            out = open("CONOUT$", "w", buffering=1, encoding="utf-8", errors="replace")
        except OSError:
            return None, None
        _enable_vt(out)
        return out, WIN_CONSOLE
    try:
        fd = os.open("/dev/tty", os.O_RDWR)
        return os.fdopen(os.dup(fd), "w", buffering=1, encoding="utf-8"), fd
    except OSError:
        return None, None


@contextmanager
def raw_mode(fd: int):
    if fd == WIN_CONSOLE:  # msvcrt lit déjà touche par touche, sans écho
        yield
        return
    old = termios.tcgetattr(fd)
    try:
        _tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# Touches étendues de la console Windows (préfixe \x00 ou \xe0)
_WIN_SPECIAL = {"K": "left", "M": "right", "G": "home", "O": "end", "S": "ignore"}


def _read_key_windows() -> str:  # pragma: no cover - Windows uniquement
    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        return _WIN_SPECIAL.get(msvcrt.getwch(), "ignore")
    return {"\r": "enter", "\n": "enter", "\x03": "ctrl-c", "\x08": "backspace", "\x1b": "esc"}.get(
        ch, ch
    )


def read_key(fd: int) -> str:
    """Une touche : enter, esc, backspace, left, right, home, end, ctrl-c, ou le caractère."""
    if fd == WIN_CONSOLE:
        return _read_key_windows()
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
    if IS_WINDOWS:  # clip.exe lit l'UTF-16 avec BOM : accents et symboles conservés
        try:
            data = b"\xff\xfe" + text.encode("utf-16-le")
            subprocess.run(["clip"], input=data, check=True, timeout=2)
            return True
        except Exception:
            return False
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
    except UpdateRequired:
        return "update_required", {}
    except MissingKey:
        return "nokey", {}
    except InvalidResponse:
        return "invalid", {}
    except ProviderError:
        return "error", {}


def run_inline(ask: Optional[str] = None, provider: Optional[LLMProvider] = None) -> int:
    """0 : commande écrite sur stdout ; 1 : annulé ; 2 : environnement inadapté (pas de tty)."""
    out, fd = open_tty()
    if out is None or fd is None:
        print("ezsh: terminal interactif requis (pas de /dev/tty ni de console).", file=sys.stderr)
        return 2
    # PSReadLine redessine le prompt à sa position d'origine : le hook PowerShell demande
    # l'écran alternatif pour que le panneau ne décale pas la ligne de saisie.
    alt = os.environ.get("EZSH_ALT_SCREEN") == "1"
    if alt:
        out.write("\x1b[?1049h\x1b[H")
        out.flush()
    try:
        return _run_inline(out, fd, ask, provider)
    finally:
        if alt:
            out.write("\x1b[?1049l")
            out.flush()


def _run_inline(out: TextIO, fd: int, ask: Optional[str], provider: Optional[LLMProvider]) -> int:
    from rich.console import Console
    lang = detect_lang()
    t = tr(lang)
    width = min(80, shutil.get_terminal_size((80, 24)).columns)
    console = Console(
        file=out,
        force_terminal=True,
        legacy_windows=False,  # VT activé sur la console Windows : rendu ANSI partout
        width=width,
        highlight=False,
        markup=False,
        emoji=False,
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
    _update_notice(console)

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


def _update_notice(console) -> None:
    """Une ligne discrète, au plus une fois par jour, si une nouvelle version existe."""
    try:
        from src.core.updater import take_notice

        line = take_notice()
        if line:
            console.print(line, style="dim")
    except Exception:  # le rappel ne doit jamais gêner le panneau
        pass


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
