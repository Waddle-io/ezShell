"""Pont entre les interfaces GUI / TUI / --explain et le fournisseur de `Alt+E`.

Toutes les interfaces passent ainsi par le même chemin : proxy ezShell (ou Groq direct avec
EZSH_DIRECT=1, ou mode simulé), validation JSON, nettoyage, plancher de risque. Le résultat
est converti en `ChatMessageResult` pour que les interfaces existantes n'aient qu'à l'afficher.
"""

from __future__ import annotations

from typing import Optional

from src.core.assistant import ChatMessageResult
from src.core.provider import (
    LLMProvider,
    MissingKey,
    ProviderError,
    ProviderOffline,
    QuotaExceeded,
    get_provider,
)
from src.core.redact import redact_secrets
from src.core.safety import RiskLevel, SafetyReport
from src.core.schema import InvalidResponse
from src.core.suggest import build_request, detect_lang, get_suggestion
from src.ui.panel import tr

_RISK = {"low": RiskLevel.SAFE, "medium": RiskLevel.WARNING, "high": RiskLevel.DANGEROUS}


def ask(
    query: str = "",
    *,
    mode: str = "translate",
    command: str = "",
    provider: Optional[LLMProvider] = None,
) -> ChatMessageResult:
    """`mode` : translate (question libre), explain_error (dernier échec), explain_command."""
    if mode == "explain_error":
        req = build_request("")
        if command and not req.last_command:
            req.last_command = command
        if query:  # texte d'erreur fourni à la main (--explain)
            req.stderr_tail = redact_secrets(query)[-4096:]
            req.exit_code = req.exit_code if req.exit_code is not None else 1
    elif mode == "explain_command":
        req = build_request(command or query)
        req.mode = "explain_command"
    else:
        req = build_request(query)

    s = get_suggestion(req, provider or get_provider())
    parts = [s.response.explanation]
    if s.response.cause:
        parts.append(f"{tr(req.lang)['cause']} : {s.response.cause}")
    commands = [s.command] if s.command else []
    reports = [
        SafetyReport(
            command=s.command,
            risk_level=_RISK.get(s.risk, RiskLevel.WARNING),
            reason=s.risk_reason,
            requires_explicit_confirmation=s.risk == "high",
        )
    ] if s.command else []
    return ChatMessageResult(
        content="\n\n".join(p for p in parts if p),
        suggested_commands=commands,
        safety_reports=reports,
    )


def provider_label(provider: LLMProvider, config=None) -> str:
    """Libellé court du fournisseur actif, pour les barres d'état."""
    from urllib.parse import urlparse

    from src.core.provider import MockProvider
    from src.core.proxy_client import ProxyProvider

    if isinstance(provider, MockProvider):
        return "Mock · offline"
    if isinstance(provider, ProxyProvider):
        return f"ezShell · {urlparse(provider.base_url).hostname or 'proxy'}"
    model = getattr(provider, "model", "") or (config.get_effective_model() if config else "")
    return f"Groq · {model}".rstrip(" ·")


def describe_error(exc: Exception) -> str:
    """Message court et traduit pour une erreur du fournisseur (mêmes textes que `Alt+E`)."""
    t = tr(detect_lang())
    if isinstance(exc, ProviderOffline):
        return t["offline"]
    if isinstance(exc, QuotaExceeded):
        if exc.scope == "anonymous":
            return t["trial"]
        return t["quota"].format(scope=exc.scope, reset=exc.reset_at or "?")
    if isinstance(exc, MissingKey):
        return t["nokey"]
    if isinstance(exc, InvalidResponse):
        return t["invalid"]
    if isinstance(exc, ProviderError):
        return t["error"]
    return f"{t['error']} ({type(exc).__name__})"


__all__ = ["ask", "describe_error"]
