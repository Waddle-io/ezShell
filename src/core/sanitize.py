"""Nettoyage des sorties du modèle avant affichage ou insertion dans le prompt.

Tout ce que renvoie le LLM est une donnée non fiable (DEVELOPMENT.md, règle 5) :
on retire les séquences ANSI et les caractères de contrôle, et on refuse
qu'un saut de ligne soit inséré dans la ligne de saisie (il l'exécuterait).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ANSI = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"  # CSI
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC
    r"|\x1b[@-Z\\-_]"  # autres séquences à 2 octets
)
_CTRL_KEEP_NL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_CTRL_ALL = re.compile(r"[\x00-\x1f\x7f]")


def strip_control(text: str, keep_newlines: bool = True) -> str:
    """Retire ANSI et caractères de contrôle (garde \\n et \\t si demandé)."""
    text = _ANSI.sub("", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if keep_newlines:
        return _CTRL_KEEP_NL.sub("", text)
    return _CTRL_ALL.sub(" ", text)


@dataclass(frozen=True)
class SafeCommand:
    text: str  # commande nettoyée (peut contenir des \n si multiline)
    multiline: bool  # True => ne jamais insérer dans le prompt sans confirmation


def sanitize_command(command: str) -> SafeCommand:
    cleaned = strip_control(command, keep_newlines=True).strip()
    return SafeCommand(text=cleaned, multiline="\n" in cleaned)
