"""Gestionnaire de raccourcis personnalisables pour ezShell.

Permet de :
- Consulter les raccourcis configurés et leurs actions
- Personnaliser les combinaisons de touches (shell trigger et navigation inline)
- Activer ou désactiver les raccourcis
- Détecter les conflits avec les raccourcis natifs du terminal et des shells
- Sauvegarder et recharger les préférences utilisateur
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Dict, Optional, Tuple

# Raccourcis réservés au fonctionnement vital du terminal / shell
RESERVED_SYSTEM_KEYS = {
    "ctrl+c": "Signal d'interruption système (SIGINT)",
    "ctrl+d": "Fin de fichier / Déconnexion shell (EOF)",
    "ctrl+z": "Suspension de tâche en arrière-plan (SIGTSTP)",
    "ctrl+\\": "Arrêt forcé avec core dump (SIGQUIT)",
    "ctrl+l": "Effacer l'écran du terminal (Clear screen)",
    "enter": "Validation de la ligne de commande",
    "return": "Validation de la ligne de commande",
    "tab": "Complétion automatique native du shell",
    "backspace": "Suppression de caractère",
}

# Raccourcis natifs standards readline / Emacs / Vi (avertissement de conflit)
READLINE_NATIVE_WARNINGS = {
    "ctrl+r": "Recherche inversée dans l'historique (bsearch)",
    "ctrl+a": "Début de ligne (Readline / Emacs)",
    "ctrl+e": "Fin de ligne (Readline / Emacs)",
    "ctrl+k": "Effacement jusqu'à la fin de ligne",
    "ctrl+u": "Effacement de la ligne",
    "ctrl+w": "Suppression du mot précédent",
    "alt+b": "Reculer d'un mot (Backward word)",
    "alt+f": "Avancer d'un mot (Forward word)",
    "alt+d": "Supprimer le mot suivant",
}


@dataclass
class KeybindingConfig:
    """Configuration des raccourcis clavier d'ezShell."""

    trigger_key: str = "Alt+E"
    trigger_enabled: bool = True
    inline_confirm: str = "enter"
    inline_edit: str = "e"
    inline_copy: str = "c"
    inline_ask: str = "/"
    inline_high_risk: str = "y"
    inline_quit: str = "q,esc"

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, object]]) -> KeybindingConfig:
        if not data or not isinstance(data, dict):
            return cls()
        valid = {
            "trigger_key",
            "trigger_enabled",
            "inline_confirm",
            "inline_edit",
            "inline_copy",
            "inline_ask",
            "inline_high_risk",
            "inline_quit",
        }
        filtered = {k: v for k, v in data.items() if k in valid}
        return cls(**filtered)


def normalize_key(key: str) -> str:
    """Normalise une chaîne de touches (ex: 'alt+e' -> 'Alt+E', 'ctrl+shift+x'...)."""
    parts = [p.strip().lower() for p in key.replace("-", "+").split("+") if p.strip()]
    normalized_parts = []
    modifiers = []
    final_key = ""
    for p in parts:
        if p in ("alt", "option", "meta"):
            modifiers.append("Alt")
        elif p in ("ctrl", "control"):
            modifiers.append("Ctrl")
        elif p in ("shift",):
            modifiers.append("Shift")
        else:
            final_key = p.upper() if len(p) == 1 else p.capitalize()
    if "Ctrl" in modifiers:
        normalized_parts.append("Ctrl")
    if "Alt" in modifiers:
        normalized_parts.append("Alt")
    if "Shift" in modifiers:
        normalized_parts.append("Shift")
    if final_key:
        normalized_parts.append(final_key)
    return "+".join(normalized_parts) if normalized_parts else key.strip()


def check_key_conflict(key: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Vérifie si une touche entre en conflit avec le terminal.

    Returns:
        (is_valid, error_reason, warning_note)
    """
    clean = key.strip().lower().replace("-", "+")
    # Vérification syntaxique de base
    if not clean:
        return False, "La combinaison de touches ne peut pas être vide.", None

    # Conflit bloquant système
    if clean in RESERVED_SYSTEM_KEYS:
        return (
            False,
            f"La combinaison '{key}' est réservée par le terminal : {RESERVED_SYSTEM_KEYS[clean]}.",
            None,
        )

    # Conflits avec des raccourcis natifs du shell (avertissement seulement)
    warning = None
    if clean in READLINE_NATIVE_WARNINGS:
        warning = f"Attention : '{key}' remplace le raccourci standard shell '{READLINE_NATIVE_WARNINGS[clean]}'."

    # Format accepté : Alt+[a-zA-Z0-9], Ctrl+Space, Alt+Space, etc.
    alt_match = re.match(r"^alt\+([a-z0-9])$", clean)
    ctrl_match = re.match(r"^ctrl\+([a-z0-9])$", clean)
    space_match = clean in ("alt+space", "ctrl+space")

    if not (alt_match or ctrl_match or space_match):
        return (
            False,
            f"Combinaison '{key}' non supportée. Utilisez un format comme 'Alt+E', 'Alt+S', 'Ctrl+Space'.",
            None,
        )

    return True, None, warning


def format_shell_trigger(trigger_key: str, shell: str) -> Tuple[str, str]:
    """Formate la déclaration du binding pour le shell demandé.

    Returns:
        (bind_statement, description)
    """
    clean = trigger_key.strip().lower().replace("-", "+")
    letter = ""
    is_alt = clean.startswith("alt+")
    is_ctrl = clean.startswith("ctrl+")

    if is_alt:
        letter = clean.split("+")[1]
    elif is_ctrl:
        letter = clean.split("+")[1]

    if shell == "zsh":
        if is_alt and len(letter) == 1:
            return f"bindkey '\\e{letter}' __ezshell_widget 2>/dev/null || true", f"Alt+{letter.upper()}"
        if clean == "ctrl+space":
            return "bindkey '^ ' __ezshell_widget 2>/dev/null || true", "Ctrl+Space"
        return f"bindkey '\\e{letter}' __ezshell_widget 2>/dev/null || true", trigger_key

    elif shell == "bash":
        if is_alt and len(letter) == 1:
            return f'bind -x \'"\\\\e{letter}": __ezshell_widget\' 2>/dev/null || true', f"Alt+{letter.upper()}"
        if clean == "ctrl+space":
            return 'bind -x \'"\\\\C-@": __ezshell_widget\' 2>/dev/null || true', "Ctrl+Space"
        return f'bind -x \'"\\\\e{letter}": __ezshell_widget\' 2>/dev/null || true', trigger_key

    elif shell == "fish":
        if is_alt and len(letter) == 1:
            return f"bind \\e{letter} __ezshell_widget 2>/dev/null", f"Alt+{letter.upper()}"
        if clean == "ctrl+space":
            return "bind -k nul __ezshell_widget 2>/dev/null", "Ctrl+Space"
        return f"bind \\e{letter} __ezshell_widget 2>/dev/null", trigger_key

    elif shell in ("powershell", "pwsh"):
        if is_alt and len(letter) == 1:
            upper = letter.upper()
            lower = letter.lower()
            chords = f"@('Alt+{lower}', 'Alt+{upper}', 'Escape,{lower}', 'Escape,{upper}')"
            return chords, f"Alt+{upper}"
        if clean == "ctrl+space":
            return "@('Ctrl+Spacebar')", "Ctrl+Space"
        return f"@('{trigger_key}')", trigger_key

    return "", trigger_key
