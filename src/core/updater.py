"""Mise à jour d'ezShell : versions, nouveautés, rappel quotidien, installation.

Principes (docs/ezShell v2) :

* ``ezsh --update`` montre d'abord les nouveautés, demande confirmation (réponse par défaut : non),
  et ne lance l'installation qu'après un « oui » (ou ``--yes``).
* Le rappel de nouvelle version n'ajoute AUCUNE requête réseau : il se nourrit de l'en-tête
  ``x-ezsh-latest`` que le serveur renvoie déjà. Une ligne discrète, au plus une fois par jour,
  coupée par ``EZSH_NO_UPDATE_CHECK=1``. Rien n'est jamais fait à l'ouverture du terminal.
* Stdlib uniquement : pas d'import lourd, le démarrage reste rapide.
* Tout texte venant du réseau est nettoyé (ANSI, caractères de contrôle) avant affichage.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from src import __version__
from src.core.sanitize import strip_control

RELEASES_URL = "https://github.com/Waddle-io/ezShell/releases"
PYPI_JSON_URL = "https://pypi.org/pypi/ezshell/json"
NOTICE_INTERVAL_S = 24 * 3600
MAX_NOTE_LINES = 10
FETCH_TIMEOUT_S = 6.0

_YES = {"o", "oui", "y", "yes"}

T = {
    "fr": {
        "offline": "Impossible de joindre le service pour vérifier la version. Réessaie plus tard.",
        "uptodate": "Déjà à jour ({v}).",
        "header": "ezShell {old} → {new}",
        "important": "⚠ Important",
        "added": "Nouveautés",
        "fixed": "Corrections",
        "more": "… et {n} autres : {url}",
        "nonotes": "Pas de détail disponible : {url}",
        "ask": "Mettre à jour maintenant ? [o/N] ",
        "cancelled": "Mise à jour annulée.",
        "editable": "Installation de développement détectée : mets à jour avec `git pull`, rien n'a été modifié.",
        "need_confirm": "Aucun terminal interactif : rien n'a été installé. Relance avec `ezsh --update --yes`.",
        "manual": "Pour mettre à jour, ouvre un NOUVEAU terminal et lance :",
        "manual_win": "Sous Windows, ezsh ne peut pas se remplacer lui-même pendant qu'il tourne.",
        "running": "Mise à jour en cours…",
        "failed": "La mise à jour a échoué. Commande à lancer à la main :",
        "notpublished": "La version {v} n'est pas encore publiée sur PyPI. Réessaie plus tard.",
        "done": "Mis à jour : {old} → {new}. Ouvre un nouveau terminal pour en profiter.",
        "done_unknown": "Mise à jour terminée. Ouvre un nouveau terminal pour en profiter.",
        "notice": "Nouvelle version d'ezShell disponible ({old} → {new}) : lance `ezsh --update`.",
        "version_notice": "(nouvelle version disponible : {new} — `ezsh --update`)",
    },
    "en": {
        "offline": "Cannot reach the service to check the version. Try again later.",
        "uptodate": "Already up to date ({v}).",
        "header": "ezShell {old} → {new}",
        "important": "⚠ Important",
        "added": "What's new",
        "fixed": "Fixes",
        "more": "… and {n} more: {url}",
        "nonotes": "No details available: {url}",
        "ask": "Update now? [y/N] ",
        "cancelled": "Update cancelled.",
        "editable": "Development install detected: update with `git pull`, nothing was changed.",
        "need_confirm": "No interactive terminal: nothing was installed. Re-run with `ezsh --update --yes`.",
        "manual": "To update, open a NEW terminal and run:",
        "manual_win": "On Windows, ezsh cannot replace itself while it is running.",
        "running": "Updating…",
        "failed": "The update failed. Command to run by hand:",
        "notpublished": "Version {v} is not on PyPI yet. Try again later.",
        "done": "Updated: {old} → {new}. Open a new terminal to use it.",
        "done_unknown": "Update finished. Open a new terminal to use it.",
        "notice": "A new ezShell version is available ({old} → {new}): run `ezsh --update`.",
        "version_notice": "(new version available: {new} — `ezsh --update`)",
    },
}


def lang() -> str:
    forced = os.environ.get("EZSHELL_LANG")
    if forced:
        return "fr" if forced.lower().startswith("fr") else "en"
    return "fr" if (os.environ.get("LANG") or "").lower().startswith("fr") else "en"


# --------------------------------------------------------------------------- versions
def installed_version() -> str:
    return __version__


def parse_version(v: str) -> tuple:
    m = re.match(r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", v or "")
    return (int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0)) if m else (0, 0, 0)


def compare_versions(a: str, b: str) -> int:
    pa, pb = parse_version(a), parse_version(b)
    return (pa > pb) - (pa < pb)


def _is_version(v: object) -> bool:
    return isinstance(v, str) and re.fullmatch(r"\d+\.\d+\.\d+", v.strip()) is not None


# --------------------------------------------------------------------------- état local (rappel)
def state_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "ezshell" / "update.json"


def load_state(path: Optional[Path] = None) -> dict:
    try:
        data = json.loads((path or state_path()).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(data: dict, path: Optional[Path] = None) -> None:
    """Meilleur effort : un dossier en lecture seule ne doit jamais gêner l'outil."""
    target = path or state_path()
    try:
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        pass


def checks_disabled() -> bool:
    return os.environ.get("EZSH_NO_UPDATE_CHECK", "").strip().lower() in {"1", "true", "yes", "on"}


def note_latest(latest: Optional[str], path: Optional[Path] = None) -> None:
    """Mémorise la dernière version annoncée par le serveur (en-tête `x-ezsh-latest`)."""
    if not _is_version(latest):
        return
    state = load_state(path)
    if state.get("latest") != latest.strip():
        state["latest"] = latest.strip()
        save_state(state, path)


def cached_latest(path: Optional[Path] = None) -> Optional[str]:
    latest = load_state(path).get("latest")
    return latest if _is_version(latest) else None


def take_notice(
    *, now: Optional[float] = None, path: Optional[Path] = None, installed: Optional[str] = None
) -> Optional[str]:
    """Ligne de rappel à afficher, ou None. Au plus une fois par jour ; consomme le créneau."""
    if checks_disabled():
        return None
    installed = installed or installed_version()
    state = load_state(path)
    latest = state.get("latest")
    if not _is_version(latest) or compare_versions(latest, installed) <= 0:
        return None
    now = time.time() if now is None else now
    last = state.get("last_notice")
    if isinstance(last, (int, float)) and 0 <= now - last < NOTICE_INTERVAL_S:
        return None
    state["last_notice"] = now
    save_state(state, path)
    return T[lang()]["notice"].format(old=installed, new=latest)


def version_hint(path: Optional[Path] = None) -> Optional[str]:
    """Pour `ezsh --version` : lit seulement le cache, sans réseau."""
    latest = cached_latest(path)
    if latest and compare_versions(latest, installed_version()) > 0 and not checks_disabled():
        return T[lang()]["version_notice"].format(new=latest)
    return None


# --------------------------------------------------------------------------- réseau
Opener = Callable[..., object]


def _get_json(url: str, timeout: float, opener: Opener) -> Optional[dict]:
    try:
        request = urllib.request.Request(url, headers={"user-agent": f"ezshell/{installed_version()}"})
        with opener(request, timeout=timeout) as resp:  # type: ignore[attr-defined]
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return data if isinstance(data, dict) else None
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def _clean(text: object, limit: int = 300) -> str:
    return strip_control(str(text), keep_newlines=False).strip()[:limit]


def fetch_release_info(
    base_url: str, installed: str, *, timeout: float = FETCH_TIMEOUT_S, opener: Opener = urllib.request.urlopen
) -> Optional[dict]:
    """`GET /api/v1/version?from=<installée>` → {latest, min_supported, releases:[…]} nettoyé, ou None."""
    data = _get_json(f"{base_url.rstrip('/')}/api/v1/version?from={installed}", timeout, opener)
    if not data or not _is_version(data.get("latest")):
        return None
    releases = []
    for r in data.get("releases") or []:
        if not isinstance(r, dict) or not _is_version(r.get("version")):
            continue
        releases.append(
            {
                "version": r["version"].strip(),
                "important": [_clean(x) for x in (r.get("important") or []) if isinstance(x, str)][:10],
                "added": [_clean(x) for x in (r.get("added") or []) if isinstance(x, str)][:20],
                "fixed": [_clean(x) for x in (r.get("fixed") or []) if isinstance(x, str)][:20],
            }
        )
    return {"latest": data["latest"].strip(), "min_supported": str(data.get("min_supported", "")), "releases": releases}


def pypi_latest(*, timeout: float = FETCH_TIMEOUT_S, opener: Opener = urllib.request.urlopen) -> Optional[str]:
    data = _get_json(PYPI_JSON_URL, timeout, opener)
    version = (data or {}).get("info", {}).get("version") if isinstance((data or {}).get("info"), dict) else None
    return version if _is_version(version) else None


# --------------------------------------------------------------------------- nouveautés
def collect_notes(releases: Sequence[dict]) -> Dict[str, List[str]]:
    """Notes cumulées (versions sautées), sans doublon ; l'ordre des versions est conservé."""
    merged: Dict[str, List[str]] = {"important": [], "added": [], "fixed": []}
    for r in sorted(releases, key=lambda x: parse_version(x["version"])):
        for key in merged:
            for line in r.get(key, []):
                if line and line not in merged[key]:
                    merged[key].append(line)
    return merged


def format_notes(old: str, new: str, releases: Sequence[dict], language: str) -> List[str]:
    t = T[language]
    notes = collect_notes(releases)
    lines = [t["header"].format(old=old, new=new), ""]
    total = sum(len(v) for v in notes.values())
    if not total:
        lines.append(t["nonotes"].format(url=RELEASES_URL))
        return lines
    budget = MAX_NOTE_LINES
    for key in ("important", "added", "fixed"):
        if not notes[key] or budget <= 0:
            continue
        lines.append(t[key])
        for item in notes[key][:budget]:
            lines.append(f"  • {item}")
        budget -= min(budget, len(notes[key]))
        lines.append("")
    shown = MAX_NOTE_LINES - budget
    if total > shown:
        lines.append(t["more"].format(n=total - shown, url=RELEASES_URL))
    while lines and lines[-1] == "":
        lines.pop()
    return lines


# --------------------------------------------------------------------------- installation
@dataclass
class InstallPlan:
    method: str  # pipx | pip | script | editable
    commands: List[List[str]] = field(default_factory=list)
    needs_pypi: bool = False


def _direct_url() -> Optional[dict]:
    try:
        from importlib.metadata import distribution

        raw = distribution("ezshell").read_text("direct_url.json")
        data = json.loads(raw) if raw else None
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _script_install_dir() -> Path:
    return Path(os.environ.get("EZSHELL_INSTALL_DIR") or Path.home() / ".local" / "share" / "ezshell")


def _file_url_path(url: str) -> Optional[Path]:
    if not url.startswith("file://"):
        return None
    from urllib.parse import unquote, urlparse

    path = unquote(urlparse(url).path)
    if os.name == "nt" and re.match(r"^/[A-Za-z]:", path):
        path = path[1:]
    return Path(path)


def detect_install(
    *, direct_url: Optional[dict] = None, prefix: Optional[str] = None, executable: Optional[str] = None
) -> InstallPlan:
    du = _direct_url() if direct_url is None else direct_url
    prefix = prefix or sys.prefix
    exe = executable or sys.executable
    parts = {p.lower() for p in Path(prefix).parts}

    if du and (du.get("dir_info") or {}).get("editable"):
        root = _file_url_path(str(du.get("url", "")))
        if root is not None and root.resolve() == _script_install_dir().resolve() and (root / ".git").exists():
            # install.sh : clone git + venv dédié, installé en mode éditable.
            return InstallPlan(
                "script",
                [["git", "-C", str(root), "pull", "--ff-only"], [exe, "-m", "pip", "install", "--quiet", "-e", str(root)]],
            )
        return InstallPlan("editable")

    if "pipx" in parts and "venvs" in parts:
        if du and du.get("vcs_info"):  # installé depuis l'URL git : on bascule sur PyPI
            return InstallPlan("pipx", [["pipx", "install", "--force", "ezshell"]], needs_pypi=True)
        return InstallPlan("pipx", [["pipx", "upgrade", "ezshell"]], needs_pypi=True)

    return InstallPlan("pip", [[exe, "-m", "pip", "install", "--upgrade", "ezshell"]], needs_pypi=True)


def _printable(cmd: Sequence[str]) -> str:
    return " ".join(f'"{c}"' if " " in c else c for c in cmd)


def _version_after(exe: str, runner: Callable[..., object]) -> Optional[str]:
    try:
        out = runner(  # type: ignore[operator]
            [exe, "-c", "from src import __version__; print(__version__)"], capture_output=True, text=True, timeout=20
        )
        text = (getattr(out, "stdout", "") or "").strip()
        return text if _is_version(text) else None
    except Exception:
        return None


def run_update(
    *,
    yes: bool = False,
    base_url: Optional[str] = None,
    out: Callable[[str], None] = print,
    input_fn: Callable[[str], str] = input,
    interactive: Optional[bool] = None,
    fetch: Callable[..., Optional[dict]] = fetch_release_info,
    pypi: Callable[[], Optional[str]] = pypi_latest,
    runner: Callable[..., object] = subprocess.run,
    plan: Optional[InstallPlan] = None,
    state: Optional[Path] = None,
    windows: Optional[bool] = None,
) -> int:
    """0 : à jour / mis à jour / annulé · 1 : échec · 2 : confirmation impossible (non interactif)."""
    t = T[lang()]
    if base_url is None:
        from src.core.proxy_client import api_url

        base_url = api_url()
    installed = installed_version()
    if interactive is None:
        interactive = sys.stdin.isatty() and sys.stdout.isatty()
    windows = (os.name == "nt") if windows is None else windows

    info = fetch(base_url, installed)
    latest = info["latest"] if info else pypi()
    if not latest:
        out(t["offline"])
        return 1
    note_latest(latest, state)

    if compare_versions(latest, installed) <= 0:
        out(t["uptodate"].format(v=installed))
        return 0

    for line in format_notes(installed, latest, (info or {}).get("releases", []), lang()):
        out(line)
    out("")

    plan = plan or detect_install()
    if plan.method == "editable":
        out(t["editable"])
        return 1

    if not yes:
        if not interactive:
            out(t["need_confirm"])
            return 2
        if input_fn(t["ask"]).strip().lower() not in _YES:
            out(t["cancelled"])
            return 0

    manual_cmds = plan.commands
    if windows and plan.method in ("pip", "pipx"):
        out(t["manual_win"])
        out(t["manual"])
        for cmd in manual_cmds:
            out("  " + _printable(cmd))
        return 0

    if plan.needs_pypi:  # ne pas annoncer ni installer une version qui n'est pas (encore) sur PyPI
        published = pypi()
        if published is not None and compare_versions(published, latest) < 0:
            out(t["notpublished"].format(v=latest))
            return 1

    out(t["running"])
    for cmd in plan.commands:
        try:
            result = runner(cmd)  # type: ignore[operator]
            code = getattr(result, "returncode", 1)
        except OSError:
            code = 127
        if code != 0:
            out(t["failed"])
            for c in manual_cmds:
                out("  " + _printable(c))
            return 1

    new = _version_after(sys.executable, runner)
    out(t["done"].format(old=installed, new=new) if new else t["done_unknown"])
    return 0
