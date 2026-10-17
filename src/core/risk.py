"""Moteur de risque (DEVELOPMENT.md §7.4).

    risque_final = max(niveau_règles, niveau_modèle)

Le modèle ne peut jamais abaisser un risque détecté par une règle.
Chaque règle a un identifiant, un niveau et une raison, et possède au moins
un cas positif et un cas négatif dans tests/test_risk.py.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

LOW, MEDIUM, HIGH = 0, 1, 2
_NAMES = {LOW: "low", MEDIUM: "medium", HIGH: "high"}
_LEVELS = {v: k for k, v in _NAMES.items()}

_SEPARATORS = {";", "&&", "||", "|", "&", "|&", "\n"}
_WRAPPERS = {"sudo", "doas", "env", "command", "nohup", "time", "nice", "exec", "builtin"}
_ROOTISH = {"/", "/*", "~", "~/", "~/*", "$HOME", "$HOME/", "$HOME/*", "${HOME}", "*", ".", ".."}


@dataclass(frozen=True)
class Rule:
    id: str
    level: int
    reason: str
    check: Callable[[List[str], str], bool]  # (tokens du segment, commande brute)


def _flags(tokens: List[str]) -> set:
    out = set()
    for t in tokens[1:]:
        if t.startswith("--"):
            out.add(t)
        elif t.startswith("-") and len(t) > 1:
            out.update(t[1:])
    return out


def _targets(tokens: List[str]) -> List[str]:
    return [t for t in tokens[1:] if not t.startswith("-")]


def _is(tokens: List[str], name: str) -> bool:
    return bool(tokens) and tokens[0].rsplit("/", 1)[-1] == name


def _rx(pattern: str, flags: int = re.IGNORECASE):
    compiled = re.compile(pattern, flags)
    return lambda tokens, raw: bool(compiled.search(raw))


def _rm_root(t, raw):
    if not _is(t, "rm"):
        return False
    f = _flags(t)
    recursive = "r" in f or "R" in f or "--recursive" in f
    return recursive and any(x in _ROOTISH for x in _targets(t))


def _rm_recursive(t, raw):
    if not _is(t, "rm"):
        return False
    f = _flags(t)
    return "r" in f or "R" in f or "--recursive" in f


def _find_delete(t, raw):
    return _is(t, "find") and (
        "-delete" in t or ("-exec" in t and any(x in ("rm", "shred") for x in t))
    )


def _git_force_push(t, raw):
    if not (_is(t, "git") and "push" in t):
        return False
    return any(x in ("--force", "-f") for x in t)


def _recursive_perm_root(t, raw):
    if not (_is(t, "chmod") or _is(t, "chown") or _is(t, "chgrp")):
        return False
    f = _flags(t)
    return ("R" in f or "--recursive" in f) and any(x in _ROOTISH for x in _targets(t))


def _recursive_perm(t, raw):
    if not (_is(t, "chmod") or _is(t, "chown") or _is(t, "chgrp")):
        return False
    f = _flags(t)
    return "R" in f or "--recursive" in f


def _overwrite_redirect(t, raw):
    # '>' sans '>>' et hors /dev/null, /dev/stderr, /dev/stdout, &1/&2
    for m in re.finditer(r"(?<![>&0-9])>(?!>)\s*([^\s|;&]+)", raw):
        target = m.group(1)
        if target not in ("/dev/null", "/dev/stderr", "/dev/stdout") and not target.startswith("&"):
            return True
    return False


RULES: Tuple[Rule, ...] = (
    # ---- high -----------------------------------------------------------
    Rule(
        "rm-rf-root",
        HIGH,
        "Suppression récursive de la racine, du dossier personnel ou de tout le dossier courant.",
        _rm_root,
    ),
    Rule(
        "mkfs",
        HIGH,
        "Formate un système de fichiers : toutes les données du périphérique sont perdues.",
        lambda t, r: bool(t) and t[0].startswith("mkfs"),
    ),
    Rule(
        "dd-device",
        HIGH,
        "dd écrit directement sur un périphérique bloc.",
        lambda t, r: _is(t, "dd") and any(re.match(r"of=/dev/", x) for x in t),
    ),
    Rule(
        "redirect-device",
        HIGH,
        "Redirection qui écrase un périphérique brut.",
        _rx(r">\s*/dev/(sd[a-z]|nvme\d|vd[a-z]|hd[a-z]|mem|kmem)"),
    ),
    Rule(
        "fork-bomb",
        HIGH,
        "Bombe fork : sature la table des processus.",
        _rx(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", 0),
    ),
    Rule(
        "perm-root",
        HIGH,
        "Changement récursif de permissions/propriétaire sur la racine ou le dossier personnel.",
        _recursive_perm_root,
    ),
    Rule(
        "curl-pipe-shell",
        HIGH,
        "Exécute directement un script téléchargé (curl/wget | sh).",
        _rx(r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z|da|k)?sh\b"),
    ),
    Rule(
        "git-force-push", HIGH, "Push forcé : peut écraser l'historique distant.", _git_force_push
    ),
    Rule(
        "sql-destructive",
        HIGH,
        "Instruction SQL destructrice (DROP / TRUNCATE).",
        _rx(r"\b(drop\s+(table|database|schema)|truncate\s+table)\b"),
    ),
    Rule("find-delete", HIGH, "find supprime les fichiers trouvés, sans corbeille.", _find_delete),
    # ---- medium ---------------------------------------------------------
    Rule("rm-recursive", MEDIUM, "Suppression récursive, irréversible.", _rm_recursive),
    Rule(
        "git-reset-hard",
        MEDIUM,
        "Perd les modifications non commitées.",
        _rx(r"\bgit\s+reset\s+--hard\b"),
    ),
    Rule(
        "git-clean-force",
        MEDIUM,
        "Supprime définitivement les fichiers non suivis.",
        _rx(r"\bgit\s+clean\s+-[a-z]*f"),
    ),
    Rule(
        "sudo",
        MEDIUM,
        "Exécution avec privilèges administrateur.",
        lambda t, r: (
            bool(t) and t[0] in ("sudo", "doas") or bool(re.search(r"(^|[;&|]\s*)sudo\s", r))
        ),
    ),
    Rule(
        "perm-recursive",
        MEDIUM,
        "Changement récursif de permissions ou de propriétaire.",
        _recursive_perm,
    ),
    Rule(
        "overwrite-redirect",
        MEDIUM,
        "Redirection '>' : écrase le fichier cible.",
        lambda t, r: _overwrite_redirect(t, r),
    ),
    Rule(
        "kill-force",
        MEDIUM,
        "Arrêt forcé de processus (SIGKILL).",
        lambda t, r: (
            (_is(t, "killall") or _is(t, "pkill") or _is(t, "kill"))
            and ("9" in _flags(t) or "-KILL" in t or "-SIGKILL" in t)
        ),
    ),
    Rule(
        "power",
        MEDIUM,
        "Arrête ou redémarre la machine.",
        lambda t, r: bool(t) and t[0] in ("shutdown", "reboot", "poweroff", "halt"),
    ),
    Rule(
        "eval-exec",
        MEDIUM,
        "Exécute du texte construit dynamiquement.",
        lambda t, r: bool(t) and t[0] == "eval",
    ),
    Rule("pip-system", MEDIUM, "Modifie le Python du système.", _rx(r"--break-system-packages")),
)

_RULES_BY_ID = {r.id: r for r in RULES}


@dataclass
class RiskAssessment:
    level: int = LOW
    hits: List[Tuple[str, str, int]] = field(default_factory=list)  # (rule_id, reason, level)
    parse_ok: bool = True

    @property
    def name(self) -> str:
        return _NAMES[self.level]

    @property
    def reason(self) -> str:
        if not self.hits:
            return "" if self.parse_ok else "Commande non analysable : prudence."
        worst = max(self.hits, key=lambda h: h[2])
        return worst[1]


def _split_segments(command: str) -> Tuple[List[List[str]], bool]:
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return [], False
    segments, current = [], []
    for tok in tokens:
        if tok in _SEPARATORS:
            if current:
                segments.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        segments.append(current)
    return segments, True


def _strip_wrappers(tokens: List[str]) -> List[str]:
    i = 0
    while i < len(tokens) and (tokens[i] in _WRAPPERS or re.match(r"^\w+=", tokens[i])):
        i += 1
    return tokens[i:] if i < len(tokens) else tokens


def _inner_commands(command: str) -> List[str]:
    inner = re.findall(r"\$\(([^()]*)\)", command)
    inner += re.findall(r"`([^`]*)`", command)
    return inner


def assess(command: str, _depth: int = 0) -> RiskAssessment:
    """Analyse une commande : pipes, &&, ;, sous-shells, sudo. Échec d'analyse => au moins moyen."""
    result = RiskAssessment()
    command = command or ""
    segments, ok = _split_segments(command.replace("\n", " ; "))
    if not ok:
        result.parse_ok = False
        result.level = MEDIUM

    candidates: List[Tuple[List[str], str]] = []
    for seg in segments:
        candidates.append((seg, command))  # avec sudo/env
        stripped = _strip_wrappers(seg)
        if stripped is not seg and stripped != seg:
            candidates.append((stripped, command))
    if not segments:
        candidates.append(([], command))

    seen = set()
    for tokens, raw in candidates:
        for rule in RULES:
            try:
                matched = rule.check(tokens, raw)
            except Exception:
                matched = False
            if matched and rule.id not in seen:
                seen.add(rule.id)
                result.hits.append((rule.id, rule.reason, rule.level))
                result.level = max(result.level, rule.level)

    if _depth < 3:
        for inner in _inner_commands(command):
            sub = assess(inner, _depth + 1)
            for h in sub.hits:
                if h[0] not in seen:
                    seen.add(h[0])
                    result.hits.append(h)
            result.level = max(result.level, sub.level)
    return result


def merge_risk(
    assessment: RiskAssessment, model_risk: Optional[str], model_reason: str = ""
) -> Tuple[str, str]:
    """risque_final = max(règles, modèle). Raison de la règle si elle est au moins aussi sévère."""
    m = _LEVELS.get((model_risk or "medium").lower(), MEDIUM)
    final = max(assessment.level, m)
    if assessment.hits and assessment.level >= m:
        return _NAMES[final], assessment.reason
    return _NAMES[final], model_reason or assessment.reason


__all__ = ["RULES", "Rule", "RiskAssessment", "assess", "merge_risk", "LOW", "MEDIUM", "HIGH"]
