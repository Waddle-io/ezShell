from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class RiskLevel(str, Enum):
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"


@dataclass
class SafetyReport:
    command: str
    risk_level: RiskLevel
    reason: str = ""
    requires_explicit_confirmation: bool = False


# Patterns classified as DANGEROUS (high risk of data loss or system corruption)
DANGEROUS_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+/(?:\s|$|\*)"),
        "Recursive force removal targeting root filesystem (/)",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+(?:~|\$HOME)(?:/(?:\s|$|\*))?"),
        "Recursive force removal targeting user home directory",
    ),
    (
        re.compile(r"\bmkfs(?:\.\w+)?\s+/dev/"),
        "Filesystem formatting command targeting block device",
    ),
    (
        re.compile(r"\bdd\s+.*of=/dev/(?:sd[a-z]|nvme\d+n\d+|vd[a-z]|hd[a-z])"),
        "Direct disk overwrite using dd targeting raw block device",
    ),
    (
        re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),
        "Fork bomb pattern detected",
    ),
    (
        re.compile(r"\bchmod\s+-[a-zA-Z]*R[a-zA-Z]*\s+(?:777|000)\s+/"),
        "Massive permission change on root directory",
    ),
    (
        re.compile(r">\s*/dev/(?:sd[a-z]|nvme\d+n\d+|kmem|mem)"),
        "Redirection overwriting raw device or memory",
    ),
]

# Patterns classified as WARNING (sensitive, network pipelining, or broad modification)
WARNING_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(r"\b(?:curl|wget)\s+.*\|\s*(?:bash|sh|zsh|sudo)"),
        "Executing remote script directly from URL into shell",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*\s+"),
        "Recursive deletion command",
    ),
    (
        re.compile(r"\b(?:shutdown|reboot|poweroff|init\s+0)\b"),
        "System reboot or shutdown command",
    ),
    (
        re.compile(r"\bkillall\s+-9\b|\bpkill\s+-9\b"),
        "Force terminating multiple processes",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\b"),
        "Hard reset will discard all uncommitted changes in git repository",
    ),
    (
        re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f[a-zA-Z]*\b"),
        "Force removing untracked files in git repository",
    ),
]


class SafetyGuard:
    """Evaluates commands for safety before execution."""

    @staticmethod
    def inspect(command: str) -> SafetyReport:
        cmd_clean = command.strip()

        # Check dangerous patterns first
        for pattern, reason in DANGEROUS_PATTERNS:
            if pattern.search(cmd_clean):
                return SafetyReport(
                    command=cmd_clean,
                    risk_level=RiskLevel.DANGEROUS,
                    reason=reason,
                    requires_explicit_confirmation=True,
                )

        # Check warning patterns
        for pattern, reason in WARNING_PATTERNS:
            if pattern.search(cmd_clean):
                return SafetyReport(
                    command=cmd_clean,
                    risk_level=RiskLevel.WARNING,
                    reason=reason,
                    requires_explicit_confirmation=False,
                )

        return SafetyReport(
            command=cmd_clean,
            risk_level=RiskLevel.SAFE,
            reason="Command is considered safe",
            requires_explicit_confirmation=False,
        )

