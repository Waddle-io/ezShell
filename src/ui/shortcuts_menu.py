"""Interface CLI et menu de gestion des raccourcis clavier pour ezShell."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.config import EzShellConfig
from src.core.keybindings import (
    KeybindingConfig,
    check_key_conflict,
    normalize_key,
)

console = Console()


def display_shortcuts_table(kb: KeybindingConfig) -> None:
    """Affiche un tableau clair et structuré des raccourcis ezShell."""
    table = Table(title="⌨️  Raccourcis clavier ezShell", border_style="cyan", header_style="bold magenta")
    table.add_column("Action / Contexte", style="bold white")
    table.add_column("Touche(s)", style="bold cyan", justify="center")
    table.add_column("Statut", justify="center")
    table.add_column("Description", style="dim")

    status_trigger = "[bold green]Actif[/bold green]" if kb.trigger_enabled else "[bold red]Désactivé[/bold red]"
    table.add_row(
        "Déclencheur Shell",
        kb.trigger_key,
        status_trigger,
        "Ouvre le diagnostic ezShell ou pose une question depuis votre invite de commande.",
    )
    table.add_section()
    table.add_row(
        "Insérer la commande",
        kb.inline_confirm,
        "[green]Actif[/green]",
        "Place la commande suggérée dans l'invite (risque faible/moyen).",
    )
    table.add_row(
        "Éditer la commande",
        kb.inline_edit,
        "[green]Actif[/green]",
        "Permet de modifier la commande avant de l'insérer.",
    )
    table.add_row(
        "Copier dans le presse-papier",
        kb.inline_copy,
        "[green]Actif[/green]",
        "Copie la commande suggérée sans l'insérer.",
    )
    table.add_row(
        "Poser une question",
        kb.inline_ask,
        "[green]Actif[/green]",
        "Saisir une question en langage naturel pour obtenir une autre suggestion.",
    )
    table.add_row(
        "Confirmer risque élevé",
        kb.inline_high_risk,
        "[green]Actif[/green]",
        "Validation explicite requise pour les commandes potentiellement dangereuses.",
    )
    table.add_row(
        "Quitter / Annuler",
        kb.inline_quit,
        "[green]Actif[/green]",
        "Ferme l'assistant et restaure votre invite sans rien exécuter.",
    )

    console.print(table)


def run_interactive_shortcuts_menu(config: EzShellConfig) -> int:
    """Menu interactif simple pour configurer les raccourcis."""
    kb = config.get_keybindings()
    display_shortcuts_table(kb)

    console.print("\n[bold cyan]Options de configuration :[/bold cyan]")
    console.print("  [bold]1[/bold] - Modifier le raccourci déclencheur shell")
    status_action = "Désactiver" if kb.trigger_enabled else "Activer"
    console.print(f"  [bold]2[/bold] - {status_action} le raccourci déclencheur")
    console.print("  [bold]3[/bold] - Rétablir les raccourcis par défaut")
    console.print("  [bold]q[/bold] - Quitter")

    try:
        choice = input("\nVotre choix [1/2/3/q] : ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print("\nAnnulé.")
        return 0

    if choice == "1":
        try:
            new_key = input(f"Nouvelle touche pour le shell (actuel: {kb.trigger_key}, ex: Alt+S, Alt+E, Ctrl+Space) : ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if not new_key:
            console.print("[yellow]Aucune modification.[/yellow]")
            return 0
        return set_trigger_key(new_key, config)

    elif choice == "2":
        kb.trigger_enabled = not kb.trigger_enabled
        config.set_keybindings(kb)
        config.save()
        state_str = "activé" if kb.trigger_enabled else "désactivé"
        console.print(f"[bold green]✔ Raccourci déclencheur {state_str} avec succès ![/bold green]")
        _print_reload_reminder()
        return 0

    elif choice == "3":
        config.set_keybindings(KeybindingConfig())
        config.save()
        console.print("[bold green]✔ Raccourcis réinitialisés aux valeurs par défaut ![/bold green]")
        _print_reload_reminder()
        return 0

    return 0


def set_trigger_key(key: str, config: EzShellConfig) -> int:
    """Valide, normalise et enregistre la nouvelle combinaison de touches."""
    norm = normalize_key(key)
    valid, error, warning = check_key_conflict(norm)

    if not valid:
        console.print(f"[bold red]✘ Erreur :[/bold red] {error}")
        return 1

    if warning:
        console.print(f"[bold yellow]⚠️  {warning}[/bold yellow]")

    kb = config.get_keybindings()
    kb.trigger_key = norm
    kb.trigger_enabled = True
    config.set_keybindings(kb)
    config.save()

    console.print(f"[bold green]✔ Raccourci shell mis à jour vers [bold]{norm}[/bold] ![/bold green]")
    _print_reload_reminder()
    return 0


def _print_reload_reminder() -> None:
    from src.core.shell_hook import detect_current_shell
    shell = detect_current_shell()
    console.print(
        Panel(
            f"[cyan]Pour appliquer les changements à votre shell actif ({shell}) :[/cyan]\n"
            "1. Mettez à jour le fichier de configuration : [bold]ezsh init --install[/bold]\n"
            "2. Rechargez votre shell (ex: [bold]source ~/.bashrc[/bold], [bold]source ~/.zshrc[/bold] ou [bold]. $PROFILE[/bold])",
            title="Mise à jour du shell",
            border_style="blue",
        )
    )
