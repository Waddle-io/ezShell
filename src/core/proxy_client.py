"""Client du proxy ezShell (DEVELOPMENT.md §6, M2) : le CLI ne voit jamais de clé Groq.

* Premier appel : ``POST /api/v1/device/register`` -> jeton d'appareil, stocké en 0600.
* Ensuite : ``POST /api/v1/ask`` avec ``Authorization: Bearer <jeton>``.
* Stdlib uniquement (urllib) : pas d'import lourd, le démarrage reste rapide.
* Jeton invalide (401) : on se ré-enregistre UNE fois, puis on abandonne.
* HTTPS obligatoire, sauf boucle locale (développement).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from src.core.provider import (
    AskRequest,
    LLMProvider,
    ProviderError,
    ProviderOffline,
    QuotaExceeded,
)

# À renseigner après le déploiement (ex. "https://ezshell.vercel.app"). Surchargé par EZSH_API_URL.
DEFAULT_API_URL = "https://ezshell.vercel.app"
TIMEOUT_S = 12.0
_LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def api_url() -> str:
    return (os.environ.get("EZSH_API_URL") or DEFAULT_API_URL).rstrip("/")


def _client_version() -> str:
    try:
        from importlib.metadata import version

        return version("ezshell")
    except Exception:
        return "0.1.0"


class TokenStore:
    """Jeton d'appareil dans ``$XDG_CONFIG_HOME/ezshell/device.json`` (0600). Trousseau : M3."""

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
            path = Path(base) / "ezshell" / "device.json"
        self.path = path

    def load(self, base_url: str) -> Optional[str]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        # Un jeton n'est valable que pour le serveur qui l'a émis.
        return data.get("token") if data.get("api_url") == base_url else None

    def save(self, base_url: str, token: str) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"api_url": base_url, "token": token}, fh)
        os.replace(tmp, self.path)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass


class ProxyProvider(LLMProvider):
    def __init__(self, base_url: Optional[str] = None, store: Optional[TokenStore] = None):
        self.base_url = (base_url or api_url()).rstrip("/")
        self.store = store or TokenStore()

    # -- HTTP ---------------------------------------------------------------
    def _check_url(self) -> None:
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in _LOOPBACK):
            return
        raise ProviderError("URL de l'API invalide (HTTPS requis)")

    def _post(self, path: str, payload: dict, token: Optional[str]) -> Tuple[int, str, dict]:
        headers = {"content-type": "application/json", "user-agent": f"ezshell/{_client_version()}"}
        if token:
            headers["authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            self.base_url + path, data=json.dumps(payload).encode(), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as resp:
                status, text = resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            status, text = exc.code, exc.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            raise ProviderOffline(type(exc).__name__) from exc
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {}
        return status, text, data if isinstance(data, dict) else {}

    def health(self) -> bool:
        """True si ``GET /api/v1/health`` répond 200 (aucun jeton nécessaire)."""
        try:
            self._check_url()
            with urllib.request.urlopen(self.base_url + "/api/v1/health", timeout=TIMEOUT_S) as r:
                return r.status == 200
        except (ProviderError, urllib.error.URLError, OSError):
            return False

    # -- Jeton ----------------------------------------------------------------
    def _register(self) -> str:
        status, _, data = self._post("/api/v1/device/register", {}, None)
        if status == 429:
            raise QuotaExceeded(str(data.get("scope", "register")), data.get("reset_at"))
        token = data.get("device_token")
        if status != 201 or not isinstance(token, str):
            raise ProviderError(f"enregistrement refusé ({status})")
        self.store.save(self.base_url, token)
        return token

    # -- LLMProvider ----------------------------------------------------------
    def ask(self, req: AskRequest) -> str:
        self._check_url()
        payload = {
            "mode": req.mode,
            "query": req.query,
            "lang": req.lang if req.lang in ("fr", "en") else "en",
            "client_version": _client_version(),
            "context": {
                "os": req.os_name,
                "shell": req.shell,
                "cwd": req.cwd,
                "last_command": req.last_command,
                "exit_code": req.exit_code,
                "stderr_tail": req.stderr_tail,
            },
        }
        token = self.store.load(self.base_url) or self._register()
        status, text, data = self._post("/api/v1/ask", payload, token)
        if status == 401:  # jeton révoqué ou base réinitialisée : un seul ré-enregistrement
            self.store.clear()
            status, text, data = self._post("/api/v1/ask", payload, self._register())

        if status == 200:
            return text
        if status == 429:
            raise QuotaExceeded(str(data.get("scope", "free")), data.get("reset_at"))
        raise ProviderError(f"{status} {data.get('error', '')}".strip())
