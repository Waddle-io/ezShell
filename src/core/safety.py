from __future__ import annotations

"""
ezShell Command Safety Analysis
=================================
This module provides a lightweight, purely regex-based static analysis layer
that classifies shell commands into three risk tiers before they are executed
or presented to the user.  The analysis is **heuristic** — it cannot catch
every dangerous invocation — but it blocks the most common catastrophic
patterns (e.g. recursive root deletion, fork bombs, raw disk overwrites) and
warns about sensitive operations (e.g. running remote scripts, hard git resets).

Key components
--------------
* :class:`RiskLevel` — Enum with three levels: ``SAFE``, ``WARNING``, ``DANGEROUS``
* :class:`SafetyReport` — Dataclass returned by the inspection routine
* :data:`DANGEROUS_PATTERNS` — Compiled regex rules for high-risk commands
* :data:`WARNING_PATTERNS` — Compiled regex rules for sensitive commands
* :class:`SafetyGuard` — Stateless inspector that applies the ruleset

---

Analyse de sécurité des commandes ezShell
==========================================
Ce module fournit une couche d'analyse statique légère, basée uniquement sur
des expressions régulières, qui classe les commandes shell en trois niveaux
de risque avant leur exécution.  L'analyse est **heuristique** : elle ne
peut pas intercepter toutes les invocations dangereuses, mais elle bloque les
schémas catastrophiques les plus courants (suppression récursive de la
racine, bombes fork, écrasement de disque brut) et avertit des opérations
sensibles (exécution de scripts distants, réinitialisations git dures).
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class RiskLevel(str, Enum):
    """Three-tier classification of shell-command risk.

    Inherits from ``str`` so that ``RiskLevel`` values compare equal to their
    string counterparts and serialise cleanly to JSON without extra conversion.

    Attributes:
        SAFE: The command matched no known dangerous or warning pattern.
            It may still carry risk — no static analysis is exhaustive.
        WARNING: The command matched a pattern associated with irreversible or
            sensitive side-effects (e.g. recursive deletion, shutdown).
            The user should be informed but explicit confirmation is optional.
        DANGEROUS: The command matched a pattern that can cause immediate and
            severe damage (e.g. wiping the root filesystem, fork bombs).
            Explicit user confirmation is **required** before execution.
    """

    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"


@dataclass
class SafetyReport:
    """Structured result returned by :meth:`SafetyGuard.inspect`.

    Attributes:
        command (str): The shell command string that was analysed, stripped
            of leading and trailing whitespace.
        risk_level (RiskLevel): The severity tier assigned to the command
            after evaluating it against all known patterns.
        reason (str): Human-readable explanation of why the command was
            classified at its risk level.  Empty string for ``SAFE`` commands
            that matched no pattern (default ``""``).
        requires_explicit_confirmation (bool): When ``True``, the caller
            **must** obtain an affirmative acknowledgement from the user
            before proceeding with execution.  Set to ``True`` only for
            ``DANGEROUS`` commands.
    """

    command: str
    risk_level: RiskLevel
    reason: str = ""
    requires_explicit_confirmation: bool = False


# ---------------------------------------------------------------------------
# Danger ruleset — patterns that indicate high risk of data loss or system
# corruption.  Each entry is a (compiled_pattern, human_reason) tuple.
# Patterns are checked in order; the first match wins.
# ---------------------------------------------------------------------------

DANGEROUS_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        # Matches `rm -rf /`, `rm -fr /`, `rm -rf / *`, etc.
        # Any recursive (-r/-R) force (-f) removal whose target begins at /
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+/(?:\s|$|\*)"),
        "Recursive force removal targeting root filesystem (/)",
    ),
    (
        # Matches `rm -rf ~` and `rm -rf $HOME` (with optional trailing slash/glob)
        # Protects the user's entire home directory from accidental wipeout
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+(?:~|\$HOME)(?:/(?:\s|$|\*))?"),
        "Recursive force removal targeting user home directory",
    ),
    (
        # Matches `mkfs`, `mkfs.ext4`, `mkfs.vfat`, etc. followed by /dev/
        # Any filesystem-format command on a block device is immediately destructive
        re.compile(r"\bmkfs(?:\.\w+)?\s+/dev/"),
        "Filesystem formatting command targeting block device",
    ),
    (
        # Matches `dd ... of=/dev/sda`, `dd ... of=/dev/nvme0n1`, etc.
        # Writing directly to a raw block device destroys its existing contents
        re.compile(r"\bdd\s+.*of=/dev/(?:sd[a-z]|nvme\d+n\d+|vd[a-z]|hd[a-z])"),
        "Direct disk overwrite using dd targeting raw block device",
    ),
    (
        # Classic fork bomb: :(){ :|:& };:
        # This pattern exhausts process table slots and locks the system
        re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),
        "Fork bomb pattern detected",
    ),
    (
        # Matches `chmod -R 777 /` or `chmod -R 000 /`
        # Applying extreme permissions recursively from / compromises security
        re.compile(r"\bchmod\s+-[a-zA-Z]*R[a-zA-Z]*\s+(?:777|000)\s+/"),
        "Massive permission change on root directory",
    ),
    (
        # Matches `> /dev/sda`, `> /dev/mem`, `> /dev/kmem`, etc.
        # Shell output redirection into raw devices corrupts them silently
        re.compile(r">\s*/dev/(?:sd[a-z]|nvme\d+n\d+|kmem|mem)"),
        "Redirection overwriting raw device or memory",
    ),
]

# ---------------------------------------------------------------------------
# Warning ruleset — patterns that indicate sensitive, irreversible, or
# network-pipelining behaviour worth surfacing to the user before execution.
# ---------------------------------------------------------------------------

WARNING_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        # Matches `curl <url> | bash`, `wget <url> | sh`, etc.
        # Piping untrusted remote content directly into a shell interpreter
        # is a common supply-chain attack vector
        re.compile(r"\b(?:curl|wget)\s+.*\|\s*(?:bash|sh|zsh|sudo)"),
        "Executing remote script directly from URL into shell",
    ),
    (
        # Matches any `rm -r` or `rm -R` (without necessarily targeting /)
        # Recursive deletion is irreversible; the user should be made aware
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*\s+"),
        "Recursive deletion command",
    ),
    (
        # Matches `shutdown`, `reboot`, `poweroff`, `init 0`
        # These commands terminate the current session and may disrupt other users
        re.compile(r"\b(?:shutdown|reboot|poweroff|init\s+0)\b"),
        "System reboot or shutdown command",
    ),
    (
        # Matches `killall -9 <name>` and `pkill -9 <pattern>`
        # SIGKILL cannot be caught or ignored; it may leave resources in an
        # inconsistent state if sent to the wrong process
        re.compile(r"\bkillall\s+-9\b|\bpkill\s+-9\b"),
        "Force terminating multiple processes",
    ),
    (
        # Matches `git reset --hard`
        # Discards all staged and unstaged changes without any recycle-bin safety net
        re.compile(r"\bgit\s+reset\s+--hard\b"),
        "Hard reset will discard all uncommitted changes in git repository",
    ),
    (
        # Matches `git clean -f`, `git clean -fd`, `git clean -fx`, etc.
        # Permanently removes untracked files that are not in the git index
        re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f[a-zA-Z]*\b"),
        "Force removing untracked files in git repository",
    ),
]


class SafetyGuard:
    """Stateless command inspector that applies the DANGEROUS and WARNING rulesets.

    All inspection logic is encapsulated in the single static method
    :meth:`inspect`, which makes ``SafetyGuard`` trivially mockable in tests
    and thread-safe without any shared mutable state.

    Example::

        report = SafetyGuard.inspect("rm -rf /")
        if report.risk_level == RiskLevel.DANGEROUS:
            print(f"Blocked: {report.reason}")
    """

    @staticmethod
    def inspect(command: str) -> SafetyReport:
        """Classify a shell command string and return a :class:`SafetyReport`.

        The method first strips surrounding whitespace, then evaluates the
        command against :data:`DANGEROUS_PATTERNS` followed by
        :data:`WARNING_PATTERNS`.  The first matching pattern determines the
        result; subsequent patterns are not evaluated (short-circuit).

        Args:
            command (str): Raw shell command string to analyse.  May include
                flags, redirections, pipes, and multi-command chains.

        Returns:
            SafetyReport: A dataclass containing:

            * ``command`` — the stripped command string
            * ``risk_level`` — one of :attr:`RiskLevel.SAFE`,
              :attr:`RiskLevel.WARNING`, or :attr:`RiskLevel.DANGEROUS`
            * ``reason`` — human-readable explanation of the classification
            * ``requires_explicit_confirmation`` — ``True`` only for
              ``DANGEROUS`` commands

        Note:
            This method never raises; all exceptions are implicitly propagated
            from ``re.Pattern.search``, which is effectively infallible for
            valid pre-compiled patterns.
        """
        cmd_clean = command.strip()

        # Check dangerous patterns first — a DANGEROUS match short-circuits
        # the WARNING check because we already know the worst-case outcome
        for pattern, reason in DANGEROUS_PATTERNS:
            if pattern.search(cmd_clean):
                return SafetyReport(
                    command=cmd_clean,
                    risk_level=RiskLevel.DANGEROUS,
                    reason=reason,
                    requires_explicit_confirmation=True,
                )

        # Check warning patterns only when no DANGEROUS pattern matched
        for pattern, reason in WARNING_PATTERNS:
            if pattern.search(cmd_clean):
                return SafetyReport(
                    command=cmd_clean,
                    risk_level=RiskLevel.WARNING,
                    reason=reason,
                    requires_explicit_confirmation=False,
                )

        # No pattern matched — command is classified as safe
        return SafetyReport(
            command=cmd_clean,
            risk_level=RiskLevel.SAFE,
            reason="Command is considered safe",
            requires_explicit_confirmation=False,
        )


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

__all__ = [
    "RiskLevel",
    "SafetyReport",
    "SafetyGuard",
    "DANGEROUS_PATTERNS",
    "WARNING_PATTERNS",
]
