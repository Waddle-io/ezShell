"""Orchestration : contexte -> masquage -> modèle -> validation -> risque -> nettoyage."""

from __future__ import annotations

import locale
import os
import platform
from dataclasses import dataclass
from typing import Optional

from src.core.capture import read_last_run
from src.core.provider import AskRequest, LLMProvider
from src.core.redact import redact_secrets
from src.core.risk import assess, merge_risk
from src.core.sanitize import sanitize_command
from src.core.schema import AskResponse, InvalidResponse, parse_response


def detect_lang() -> str:
    forced = os.environ.get("EZSHELL_LANG")
    if forced:
        return "fr" if forced.lower().startswith("fr") else "en"
    lang = os.environ.get("LANG") or (locale.getlocale()[0] or "")
    return "fr" if lang.lower().startswith("fr") else "en"


def detect_shell() -> str:
    """Shell courant : EZSH_SHELL (posé par le hook), sinon $SHELL, sinon PowerShell."""
    forced = os.environ.get("EZSH_SHELL")
    if forced:
        return forced
    if os.environ.get("SHELL"):
        return os.path.basename(os.environ["SHELL"])
    if os.name == "nt":
        return "powershell"
    return "sh"


def build_request(query: str = "") -> AskRequest:
    """Contexte minimal et masqué. `query` donné => traduction ; sinon explication d'erreur."""
    last = read_last_run()
    shell = detect_shell()
    req = AskRequest(
        mode="translate" if query else "explain_error",
        query=redact_secrets(query),
        os_name=platform.system().lower(),
        shell=shell,
        cwd=os.getcwd().replace(os.path.expanduser("~"), "~", 1),
        lang=detect_lang(),
    )
    if last and not query:
        req.last_command = redact_secrets(last.command)
        req.exit_code = last.exit_code
        req.stderr_tail = redact_secrets(last.stderr_tail)[-4096:]
    return req


@dataclass
class Suggestion:
    response: AskResponse
    command: str  # nettoyée
    multiline: bool
    risk: str  # low | medium | high (après fusion règles/modèle)
    risk_reason: str
    risk_floor_applied: bool  # True si une règle a relevé le risque annoncé par le modèle
    no_output_captured: bool


def get_suggestion(req: AskRequest, provider: LLMProvider) -> Suggestion:
    """Valide la réponse (un nouvel essai si invalide), puis applique le plancher de risque."""
    last_err: Optional[Exception] = None
    resp: Optional[AskResponse] = None
    for _ in range(2):
        raw = provider.ask(req)
        try:
            resp = parse_response(raw)
            break
        except InvalidResponse as exc:
            last_err = exc
    if resp is None:
        raise InvalidResponse(str(last_err))

    safe = sanitize_command(resp.command)
    assessment = assess(safe.text) if safe.text else assess("")
    final, reason = merge_risk(assessment, resp.risk, resp.risk_reason)
    return Suggestion(
        response=resp,
        command=safe.text,
        multiline=safe.multiline,
        risk=final,
        risk_reason=reason,
        risk_floor_applied=(final != resp.risk),
        no_output_captured=(req.mode == "explain_error" and not req.stderr_tail),
    )
