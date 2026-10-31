"""Panneau inline Rich (DEVELOPMENT.md §7.5) : un rendu par état, 80 colonnes max.

Le risque est TOUJOURS indiqué par un libellé texte (jamais par la seule couleur).
Tout le texte venant du modèle est déjà nettoyé (schema.py / sanitize.py) ; on désactive
en plus le markup Rich pour qu'un texte du modèle ne puisse pas styler l'écran.
"""

from __future__ import annotations

from typing import List

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

MAX_WIDTH = 80

T = {
    "fr": {
        "title": "ezShell",
        "cause": "Cause",
        "assume": "Hypothèses",
        "conf": "Confiance",
        "risk": {"low": "RISQUE FAIBLE", "medium": "RISQUE MOYEN", "high": "RISQUE ÉLEVÉ"},
        "confv": {"low": "faible", "medium": "moyenne", "high": "élevée"},
        "keys": "⏎ insérer · c copier · e éditer · / question · q quitter",
        "keys_high": "y insérer quand même · c copier · e éditer · / question · q quitter",
        "keys_multi": "y insérer (multiligne) · c copier · / question · q quitter",
        "keys_none": "/ poser une question · q quitter",
        "loading": "Analyse en cours…",
        "floor": "Risque relevé par les règles de sécurité d'ezShell.",
        "nooutput": "Sortie d'erreur non capturée : lance `ezsh run -- <commande>` pour de meilleurs diagnostics.",
        "uncertain": "Réponse incertaine : vérifie avant d'agir.",
        "multi": "Commande sur plusieurs lignes : rien ne sera exécuté à l'insertion.",
        "nolast": "Aucune commande récente. Pose une question en langage naturel.",
        "offline": "Hors ligne : impossible de joindre le service. Le terminal n'est pas bloqué.",
        "quota": "Limite atteinte ({scope}). Réinitialisation : {reset}.",
        "trial": "Limite d'essai atteinte. Crée un compte gratuit pour continuer (`ezsh login`, bientôt).",
        "update_required": "Cette version d'ezShell n'est plus prise en charge. Lance `ezsh --update`.",
        "pending": "Connexion en attente : valide le code {code} sur {url}.",
        "error": "Le service est indisponible pour le moment. Réessaie dans un instant.",
        "invalid": "Réponse du modèle illisible : rien n'est affiché ni inséré.",
        "nokey": "Aucune clé configurée. `ezsh --set-key <clé>` ou EZSH_MOCK_LLM=1 pour tester sans réseau.",
        "ask": "Ta question",
        "edit": "Édite puis ⏎ (Échap : annuler)",
        "copied": "Copié dans le presse-papiers.",
        "nocopy": "Aucun outil de presse-papiers trouvé.",
        "inserted": "Commande insérée : relis-la puis appuie sur Entrée.",
    },
    "en": {
        "title": "ezShell",
        "cause": "Cause",
        "assume": "Assumptions",
        "conf": "Confidence",
        "risk": {"low": "LOW RISK", "medium": "MEDIUM RISK", "high": "HIGH RISK"},
        "confv": {"low": "low", "medium": "medium", "high": "high"},
        "keys": "⏎ insert · c copy · e edit · / ask · q quit",
        "keys_high": "y insert anyway · c copy · e edit · / ask · q quit",
        "keys_multi": "y insert (multi-line) · c copy · / ask · q quit",
        "keys_none": "/ ask a question · q quit",
        "loading": "Analyzing…",
        "floor": "Risk raised by ezShell's safety rules.",
        "nooutput": "Error output not captured: run `ezsh run -- <command>` for better diagnostics.",
        "uncertain": "Uncertain answer: double-check before acting.",
        "multi": "Multi-line command: nothing is executed on insertion.",
        "nolast": "No recent command. Ask a question in plain language.",
        "offline": "Offline: the service is unreachable. Your terminal is not blocked.",
        "quota": "Limit reached ({scope}). Resets: {reset}.",
        "trial": "Trial limit reached. Create a free account to continue (`ezsh login`, coming soon).",
        "update_required": "This ezShell version is no longer supported. Run `ezsh --update`.",
        "pending": "Login pending: confirm code {code} at {url}.",
        "error": "The service is unavailable right now. Try again shortly.",
        "invalid": "Unreadable model answer: nothing is shown or inserted.",
        "nokey": "No key configured. `ezsh --set-key <key>` or EZSH_MOCK_LLM=1 to try offline.",
        "ask": "Your question",
        "edit": "Edit then ⏎ (Esc: cancel)",
        "copied": "Copied to clipboard.",
        "nocopy": "No clipboard tool found.",
        "inserted": "Command inserted: review it, then press Enter.",
    },
}

_RISK_STYLE = {"low": "bold green", "medium": "bold yellow", "high": "bold white on red"}
_BORDER = {"low": "green", "medium": "yellow", "high": "red"}


def tr(lang: str) -> dict:
    return T.get(lang, T["en"])


def _wrap(body: List, title: str, border: str, footer: str) -> Panel:
    return Panel(
        Group(*body),
        title=title,
        title_align="left",
        subtitle=footer,
        subtitle_align="left",
        border_style=border,
        width=None,
        padding=(0, 1),
    )


def result_panel(s, lang: str) -> Panel:
    """`s` : suggest.Suggestion."""
    t = tr(lang)
    body: List = []
    if s.command:
        cmd = Text("$ ", style="bold cyan")
        cmd.append(s.command, style="bold")
        body.append(cmd)
    label = Text(f" {t['risk'][s.risk]} ", style=_RISK_STYLE[s.risk])
    if s.risk_reason:
        label.append(f"  {s.risk_reason}", style="default")
    body.append(label)
    if s.risk_floor_applied:
        body.append(Text(t["floor"], style="dim italic"))
    if s.response.explanation:
        body.append(Text(s.response.explanation))
    if s.response.cause:
        body.append(Text(f"{t['cause']} : {s.response.cause}", style="dim"))
    uncertain = s.response.confidence == "low" or not s.command
    if uncertain:
        body.append(Text(f"⚠ {t['uncertain']}", style="yellow"))
    if s.response.assumptions:
        body.append(Text(f"{t['assume']} : " + " · ".join(s.response.assumptions), style="dim"))
    body.append(Text(f"{t['conf']} : {t['confv'][s.response.confidence]}", style="dim"))
    if s.multiline:
        body.append(Text(f"⚠ {t['multi']}", style="yellow"))
    if s.no_output_captured:
        body.append(Text(f"ℹ {t['nooutput']}", style="dim"))
    if not s.command:
        footer = t["keys_none"]
    elif s.multiline:
        footer = t["keys_multi"]
    elif s.risk == "high":
        footer = t["keys_high"]
    else:
        footer = t["keys"]
    return _wrap(body, t["title"], _BORDER[s.risk], footer)


def message_panel(kind: str, lang: str, **kw) -> Panel:
    """États sans résultat : empty, offline, quota, trial, pending, error, invalid, nokey, update_required."""
    t = tr(lang)
    text = {
        "empty": t["nolast"],
        "offline": t["offline"],
        "trial": t["trial"],
        "error": t["error"],
        "invalid": t["invalid"],
        "nokey": t["nokey"],
        "update_required": t["update_required"],
        "quota": t["quota"].format(scope=kw.get("scope", "?"), reset=kw.get("reset") or "?"),
        "pending": t["pending"].format(code=kw.get("code", "????"), url=kw.get("url", "")),
    }[kind]
    border = "cyan" if kind in ("empty", "pending") else "yellow"
    footer = t["keys_none"] if kind in ("empty", "offline", "error", "invalid", "nokey", "update_required") else "q"
    return _wrap([Text(text)], t["title"], border, footer)


def loading_text(lang: str) -> str:
    return tr(lang)["loading"]
