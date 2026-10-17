"""
ezShell Secret Redaction Module
===============================

Masks sensitive patterns (API keys, tokens, passwords, private keys) before
sending terminal context, failed commands, or stderr outputs to LLM providers.

---

Module de masquage des secrets d'ezShell
========================================

Masque les chaînes sensibles (clés d'API, jetons d'accès, mots de passe) avant
l'envoi du contexte de terminal ou des sorties d'erreurs aux modèles d'IA.
"""
from __future__ import annotations

import re
from typing import List, Pattern, Tuple

# Patterns identifying sensitive credentials
SECRET_PATTERNS: List[Tuple[Pattern, str]] = [
    # Groq API key (e.g. gsk_...)
    (re.compile(r"\bgsk_[a-zA-Z0-9]{20,}\b"), "[REDACTED_GROQ_KEY]"),
    # OpenAI API key (e.g. sk-...)
    (re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"), "[REDACTED_OPENAI_KEY]"),
    # GitHub personal access token (ghp_...)
    (re.compile(r"\bghp_[a-zA-Z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    # AWS access key ID
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # Bearer tokens in headers
    (re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9_\-\.]{20,}\b"), "Bearer [REDACTED_TOKEN]"),
    # Identifiants dans une URL de connexion : postgresql://user:motdepasse@hote/db
    (re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:@/]+:[^\s@/]+@[^\s'\"]+", re.IGNORECASE), "[REDACTED_URL_CREDENTIALS]"),
    # JWT (trois segments base64url)
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "[REDACTED_JWT]"),
    # GitHub (jetons fins et variantes gho_/ghu_/ghs_/ghr_), Slack, Stripe
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bgh[ousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "[REDACTED_SLACK_TOKEN]"),
    (re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b"), "[REDACTED_STRIPE_KEY]"),
    # Jetons d'appareil ezShell
    (re.compile(r"\bez[du]_[A-Za-z0-9_-]{20,}\b"), "[REDACTED_EZSHELL_TOKEN]"),
    # Generic assignments: password=..., token=..., secret=..., DB_PASSWORD=...
    (
        re.compile(r"(?i)\b([a-zA-Z0-9_]*(?:password|secret|token|api_?key|passwd))\s*[:=]\s*['\"]?([^\s'\"]{4,})['\"]?"),
        r"\1=[REDACTED]",
    ),
    # PEM Private Key headers
    (
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
]


def redact_secrets(text: str) -> str:
    """Masks secrets and sensitive tokens within the given text.

    Args:
        text (str): Raw string that may contain secrets.

    Returns:
        str: Sanitized string safe to send to LLM APIs or logs.

    ---

    Masque les secrets et tokens sensibles dans le texte fourni.
    """
    if not text:
        return ""

    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


__all__ = ["SECRET_PATTERNS", "redact_secrets"]

