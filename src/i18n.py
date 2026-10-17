"""
ezShell Internationalization (i18n) — Bilingual FR/EN Support
==============================================================

Provides all user-facing strings in both English and French.
The active language is resolved from the environment ($LANG, $LANGUAGE, $LC_ALL),
falling back to English when no French locale is detected.

---

Module d'internationalisation bilingue d'ezShell (FR / EN)
===========================================================

Fournit toutes les chaînes visibles par l'utilisateur en anglais et en français.
La langue active est détectée depuis les variables d'environnement ($LANG, etc.),
avec repli sur l'anglais si aucune locale française n'est trouvée.
"""
from __future__ import annotations

import locale
import os
from enum import Enum
from typing import Optional


class Lang(str, Enum):
    """Supported interface languages.

    Langues d'interface prises en charge.
    """

    EN = "en"
    FR = "fr"


def detect_language() -> Lang:
    """Auto-detects the system language and returns the matching Lang variant.

    Checks, in order:
      1. EZSHELL_LANG environment variable (allows explicit override)
      2. $LANGUAGE, $LANG, $LC_ALL, $LC_MESSAGES environment variables
      3. Python locale.getlocale()

    Returns ``Lang.FR`` if a French locale is found, ``Lang.EN`` otherwise.

    Returns:
        Lang: The detected interface language.

    ---

    Détecte automatiquement la langue système et retourne la variante Lang correspondante.

    Vérifie, dans l'ordre :
      1. Variable d'environnement EZSHELL_LANG (remplace tout le reste si présente)
      2. $LANGUAGE, $LANG, $LC_ALL, $LC_MESSAGES
      3. Python locale.getlocale()

    Retourne ``Lang.FR`` si une locale française est détectée, ``Lang.EN`` sinon.
    """
    # 1. Explicit override via EZSHELL_LANG=fr or EZSHELL_LANG=en
    override = os.environ.get("EZSHELL_LANG", "").strip().lower()
    if override.startswith("fr"):
        return Lang.FR
    if override.startswith("en"):
        return Lang.EN

    # 2. Standard locale environment variables
    for var in ("LANGUAGE", "LANG", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(var, "").lower()
        if val.startswith("fr"):
            return Lang.FR

    # 3. Python locale fallback
    try:
        lang_code, _ = locale.getlocale()
        if lang_code and lang_code.lower().startswith("fr"):
            return Lang.FR
    except Exception:
        pass

    return Lang.EN


# ---------------------------------------------------------------------------
# Bilingual string catalogue
# All user-facing text lives here — never hardcode UI strings in other modules.
# ---------------------------------------------------------------------------

# Each key maps to a dict with "en" and "fr" entries.
_STRINGS: dict[str, dict[str, str]] = {
    # --- Generic UI ---
    "app_title": {
        "en": "ezShell",
        "fr": "ezShell",
    },
    "esc_to_close": {
        "en": "to close",
        "fr": "pour fermer",
    },
    "thinking": {
        "en": "› ezShell thinking...",
        "fr": "› ezShell analyse...",
    },

    # --- Diagnostic Card ---
    "section_cause": {
        "en": "CAUSE",
        "fr": "CAUSE",
    },
    "section_explanation": {
        "en": "EXPLANATION",
        "fr": "EXPLICATION",
    },
    "section_fix": {
        "en": "SUGGESTED COMMAND",
        "fr": "COMMANDE RECOMMANDEE",
    },
    "section_ask": {
        "en": "ASK ANOTHER QUESTION",
        "fr": "POSER UNE AUTRE QUESTION",
    },
    "risk_low": {
        "en": "LOW RISK",
        "fr": "RISQUE FAIBLE",
    },
    "risk_medium": {
        "en": "MEDIUM RISK",
        "fr": "RISQUE MODERE",
    },
    "risk_high": {
        "en": "HIGH RISK",
        "fr": "RISQUE ELEVE",
    },
    "risk_reason_default": {
        "en": "Only affects your local environment.",
        "fr": "N'affecte que votre environnement local.",
    },

    # --- Action Pills ---
    "action_run": {
        "en": "run",
        "fr": "executer",
    },
    "action_copy": {
        "en": "copy",
        "fr": "copier",
    },
    "action_edit": {
        "en": "edit",
        "fr": "modifier",
    },
    "action_close": {
        "en": "close",
        "fr": "fermer",
    },

    # --- Input Placeholder ---
    "input_placeholder": {
        "en": "Type a question or error to diagnose... (Enter to ask)",
        "fr": "Tapez une question ou une erreur à diagnostiquer... (Entrée pour envoyer)",
    },

    # --- Command Execution ---
    "cmd_success": {
        "en": "› Command finished (exit 0)",
        "fr": "› Commande terminée (code 0)",
    },
    "cmd_no_output": {
        "en": "(No output)",
        "fr": "(Aucune sortie)",
    },

    # --- Welcome Banner ---
    "welcome_title": {
        "en": "ezShell v0.1.0",
        "fr": "ezShell v0.1.0",
    },
    "welcome_subtitle": {
        "en": "Intelligent Terminal Assistant\nPowered by Groq AI",
        "fr": "Assistant de terminal intelligent\nAlimenté par Groq AI",
    },
    "welcome_body": {
        "en": "Welcome to your new terminal superpower!\nezShell gives you instant AI diagnostics, command\ngeneration, and an interactive desktop assistant\nwindow right from your CLI.",
        "fr": "Bienvenue dans votre nouveau superpouvoir terminal !\nezShell vous offre des diagnostics IA instantanés,\nla génération de commandes et une fenêtre assistant\ndirectement depuis votre ligne de commande.",
    },
    "welcome_how_to_use": {
        "en": "› How to use:",
        "fr": "› Comment utiliser :",
    },
    "welcome_cmd_desktop": {
        "en": "Desktop Assistant window",
        "fr": "Fenêtre assistant bureau",
    },
    "welcome_cmd_tui": {
        "en": "In-terminal TUI popup",
        "fr": "Popup TUI dans le terminal",
    },
    "welcome_cmd_setkey": {
        "en": "Configure your Groq API key",
        "fr": "Configurer votre clé API Groq",
    },
    "welcome_cmd_single": {
        "en": "Single command with AI assist",
        "fr": "Commande unique avec assistance IA",
    },
    "welcome_cmd_help": {
        "en": "List all options",
        "fr": "Lister toutes les options",
    },
    "welcome_footer": {
        "en": "Press Esc or Ctrl+C to close popup windows.",
        "fr": "Appuyez sur Echap ou Ctrl+C pour fermer les fenêtres popup.",
    },

    # --- Errors ---
    "error_no_api_key": {
        "en": "GROQ_API_KEY is missing. Run 'ezsh --set-key <key>' to configure.",
        "fr": "GROQ_API_KEY manquante. Lancez 'ezsh --set-key <cle>' pour configurer.",
    },
    "error_invalid_key": {
        "en": "Groq rejected the API key (invalid or revoked). Create a new one at "
        "console.groq.com/keys, then run 'ezsh --set-key <key>'.",
        "fr": "Groq refuse la clé API (invalide ou révoquée). Créez-en une sur "
        "console.groq.com/keys, puis lancez 'ezsh --set-key <clé>'.",
    },
    "error_api_generic": {
        "en": "Error querying Groq AI: ",
        "fr": "Erreur lors de la requête Groq AI : ",
    },

    # --- GUI Top-bar context ---
    "btn_clear": {
        "en": "Clear",
        "fr": "Effacer",
    },
    "btn_send": {
        "en": "Send ›",
        "fr": "Envoyer ›",
    },

    # --- GUI Welcome card ---
    "gui_welcome_title": {
        "en": "ezShell AI Assistant",
        "fr": "Assistant IA ezShell",
    },
    "gui_welcome_desc": {
        "en": "Ask questions, diagnose errors, or describe any task you need executed.",
        "fr": "Posez des questions, diagnostiquez des erreurs ou décrivez une tâche à exécuter.",
    },

    # --- Quick suggestion chips (GUI) ---
    "suggestion_ports": {
        "en": "List listening ports on system",
        "fr": "Lister les ports en écoute",
    },
    "suggestion_disk": {
        "en": "Show disk space for current folder",
        "fr": "Afficher l'espace disque du dossier courant",
    },
    "suggestion_docker": {
        "en": "Clean up unused docker containers",
        "fr": "Nettoyer les conteneurs Docker inutilisés",
    },
    "suggestion_git": {
        "en": "Undo last git commit keeping changes",
        "fr": "Annuler le dernier commit git en gardant les modifications",
    },

    # --- TUI context bar ---
    "tui_move_hint": {
        "en": "[Drag / Alt+Arrows] Move  •  [Esc] Close",
        "fr": "[Drag / Alt+Flèches] Déplacer  •  [Echap] Fermer",
    },
    "tui_no_key_msg": {
        "en": "ezShell requires a Groq API key to activate AI diagnostics & chat.\nGet a free key at https://console.groq.com and paste it below:",
        "fr": "ezShell nécessite une clé API Groq pour activer les diagnostics IA.\nObtenez une clé gratuite sur https://console.groq.com et collez-la ci-dessous :",
    },

    # --- Safety guard reasons (user-facing) ---
    "safe_reason_default": {
        "en": "Command is considered safe",
        "fr": "La commande est considérée sans danger",
    },

    # --- Launcher & History Detection ---
    "last_cmd_detected": {
        "en": "Last command detected in terminal:",
        "fr": "Dernière commande détectée dans le terminal :",
    },
    "btn_diagnose_error": {
        "en": "Diagnose this error",
        "fr": "Diagnostiquer cette erreur",
    },
    "btn_explain_command": {
        "en": "Explain command",
        "fr": "Expliquer la commande",
    },
    "quick_suggestions": {
        "en": "QUICK ACTIONS",
        "fr": "ACTIONS RAPIDES",
    },
    "action_ports_title": {
        "en": "Ports & Processes",
        "fr": "Ports & Processus",
    },
    "action_ports_desc": {
        "en": "Find listening ports & active PIDs",
        "fr": "Trouver les ports en écoute et PIDs",
    },
    "action_disk_title": {
        "en": "Disk Usage",
        "fr": "Espace Disque",
    },
    "action_disk_desc": {
        "en": "Analyze current folder space usage",
        "fr": "Analyser la taille du dossier courant",
    },
    "action_docker_title": {
        "en": "Docker Cleanup",
        "fr": "Nettoyage Docker",
    },
    "action_docker_desc": {
        "en": "Prune unused containers & images",
        "fr": "Purger conteneurs et images orphelines",
    },
    "action_git_title": {
        "en": "Undo Git Commit",
        "fr": "Annuler Commit Git",
    },
    "action_git_desc": {
        "en": "Rollback commit without losing code",
        "fr": "Rollback commit sans perdre de code",
    },
    "status_ready": {
        "en": "Ready for commands and diagnostics",
        "fr": "Prêt pour vos commandes et diagnostics",
    },
    "status_footer_hint": {
        "en": "[↵ Enter] Ask / Run   [Esc] Close   [Alt+E] Shortcut",
        "fr": "[↵ Entrée] Poser / Exécuter   [Echap] Fermer   [Alt+E] Raccourci",
    },
}


class Translator:
    """Provides translated strings for a specific language.

    Usage::

        t = Translator(Lang.FR)
        print(t("section_cause"))  # → "CAUSE"
        print(t("welcome_title"))  # → "ezShell v0.1.0"

    The active language can also be initialised with auto-detection::

        t = Translator.auto()

    ---

    Fournit les chaînes traduites pour une langue donnée.
    Initialisation avec auto-détection : ``Translator.auto()``.
    """

    def __init__(self, lang: Lang = Lang.EN) -> None:
        """Initialises the translator with the given language.

        Args:
            lang: The language to use for all lookups. Defaults to English.
        """
        self.lang = lang

    @classmethod
    def auto(cls) -> "Translator":
        """Creates a Translator using the auto-detected system language.

        Returns:
            Translator: A new Translator instance for the detected language.
        """
        return cls(detect_language())

    def __call__(self, key: str, fallback: Optional[str] = None) -> str:
        """Looks up a translation by key.

        Args:
            key: The string key defined in the catalogue (e.g. ``"section_cause"``).
            fallback: Optional string returned if the key is not in the catalogue.
                      Defaults to the key itself if omitted.

        Returns:
            str: The translated string for the active language.
        """
        entry = _STRINGS.get(key)
        if entry is None:
            return fallback if fallback is not None else key
        return entry.get(self.lang.value, entry.get("en", key))

    def get(self, key: str, fallback: Optional[str] = None) -> str:
        """Alias for ``__call__`` — preferred for explicit usage.

        Args:
            key: Translation key.
            fallback: Optional fallback string.

        Returns:
            str: Translated string.
        """
        return self(key, fallback)


# ---------------------------------------------------------------------------
# Module-level convenience singleton — used across ui modules
# ---------------------------------------------------------------------------

#: Global translator instance, auto-detected from system locale.
#: Import this directly:  ``from src.i18n import t``
t: Translator = Translator.auto()


__all__ = ["Lang", "Translator", "detect_language", "t"]

