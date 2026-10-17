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

# Patterns identifying sensitive credentials. L'ordre compte : les motifs spécifiques
# passent avant les motifs génériques (affectations), pour garder un libellé précis.
_PEM = r"(?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY(?: BLOCK)?"

SECRET_PATTERNS: List[Tuple[Pattern, str]] = [
    # Clés privées PEM complètes, puis fin de clé tronquée (stderr coupé à 4 Ko)
    (re.compile(rf"-----BEGIN {_PEM}-----[\s\S]*?(?:-----END {_PEM}-----|$)"), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(rf"\A[A-Za-z0-9+/=\s]{{40,}}-----END {_PEM}-----"), "[REDACTED_PRIVATE_KEY]"),
    # Identifiants dans une URL de connexion : postgresql://user:motdepasse@hote/db
    (
        re.compile(r"\b([a-z][a-z0-9+.-]*://)[^\s:@/]+:[^\s@/]+@", re.IGNORECASE),
        r"\1[REDACTED_CREDENTIALS]@",
    ),
    # En-têtes d'authentification (Bearer, Basic, Token)
    (
        re.compile(r"(?i)\b(authorization\s*[:=]\s*(?:basic|token|digest))\s+\S+"),
        r"\1 [REDACTED_TOKEN]",
    ),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_\-.~+/=]{16,}"), "Bearer [REDACTED_TOKEN]"),
    # Fournisseurs connus
    (re.compile(r"\bgsk_[A-Za-z0-9]{20,}"), "[REDACTED_GROQ_KEY]"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "[REDACTED_ANTHROPIC_KEY]"),
    (re.compile(r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}"), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,})"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"), "[REDACTED_GITLAB_TOKEN]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "[REDACTED_SLACK_TOKEN]"),
    (re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}"), "[REDACTED_STRIPE_KEY]"),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), "[REDACTED_GOOGLE_KEY]"),
    (re.compile(r"\bnpm_[A-Za-z0-9]{36}"), "[REDACTED_NPM_TOKEN]"),
    (re.compile(r"\bhf_[A-Za-z0-9]{30,}"), "[REDACTED_HF_TOKEN]"),
    (re.compile(r"\bez[du]_[A-Za-z0-9_-]{20,}"), "[REDACTED_EZSHELL_TOKEN]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "[REDACTED_JWT]"),
    # Mots de passe en option de ligne de commande : mysql -pSECRET, --password=x, sshpass -p x, curl -u u:p
    (re.compile(r"(\b(?:mysql|mysqldump|mariadb)\b[^\n]*?\s-p)(?!\s)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(--(?:password|passwd|pass|token|secret|api-key)[= ])(['\"]?)[^\s'\"]+\2"), r"\1[REDACTED]"),
    (re.compile(r"(\b(?:sshpass|docker\s+login|podman\s+login)\b[^\n]*?\s-p\s+)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(\bcurl\b[^\n]*?\s(?:-u|--user)\s+[^\s:]+:)\S+"), r"\1[REDACTED]"),
    # Affectations génériques : password=..., AWS_SECRET_ACCESS_KEY=..., DB_PASS: "a b c"
    (
        re.compile(
            r"(?i)\b([A-Za-z0-9_.-]*(?:password|passwd|passphrase|pwd|secret|token|api_?key"
            r"|access_?key|private_?key|client_?secret|credentials?|_pass)[A-Za-z0-9_]*)"
            r"(\s*[:=]\s*)(?:\"[^\"\n]{1,}\"|'[^'\n]{1,}'|[^\s'\",;]{4,})"
        ),
        r"\1\2[REDACTED]",
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

