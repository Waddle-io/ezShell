from __future__ import annotations

import sys
from typing import Optional

from rich.box import HEAVY_EDGE, ROUNDED
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from src.core.assistant import AskResult, DiagnosticResult
from src.core.safety import RiskLevel, SafetyReport


# Tokyo Night / Catppuccin inspired modern palette
custom_theme = Theme(
    {
        "info": "#7dcfff bold",
        "warning": "#e0af68 bold",
        "error": "#f7768e bold",
        "success": "#9ece6a bold",
        "command": "#73daca bold",
        "muted": "#565f89",
        "accent": "#bb9af7 bold",
        "highlight": "#7aa2f7 bold",
    }
)

console = Console(theme=custom_theme, file=sys.stdout)


def render_banner(model_name: str, shell_name: str) -> None:
    """Renders a sleek, modern ezShell header banner."""
    console.print()

    title_text = Text()
    title_text.append(" ⚡ ", style="bold #e0af68")
    title_text.append("ezShell ", style="bold #7dcfff")
    title_text.append("v0.1.0", style="#565f89")
    title_text.append("  •  ", style="#3b4261")
    title_text.append("Model: ", style="#565f89")
    title_text.append(f"{model_name}", style="bold #bb9af7")
    title_text.append("  •  ", style="#3b4261")
    title_text.append("Shell: ", style="#565f89")
    title_text.append(f"{shell_name}", style="#7aa2f7")

    subtitle_text = Text()
    subtitle_text.append("Type ", style="#565f89")
    subtitle_text.append("!ask <query>", style="bold #7dcfff")
    subtitle_text.append(" for instant AI help  •  ", style="#565f89")
    subtitle_text.append("!help", style="bold #bb9af7")
    subtitle_text.append(" for commands  •  ", style="#565f89")
    subtitle_text.append("exit", style="#f7768e")
    subtitle_text.append(" to quit", style="#565f89")

    content = Table.grid(padding=(0, 0))
    content.add_row(title_text)
    content.add_row(subtitle_text)

    banner_panel = Panel(
        content,
        box=ROUNDED,
        border_style="#3b4261",
        padding=(1, 2),
    )
    console.print(banner_panel)


def render_api_key_missing_card() -> None:
    """Renders an attractive notice card when GROQ_API_KEY is not configured."""
    text = Text()
    text.append("🔑  Groq AI Engine Inactive\n", style="bold #e0af68")
    text.append("ezShell will run commands normally, but automated error diagnosis is off.\n\n", style="#c0caf5")
    text.append("To activate AI assistance:\n", style="#565f89")
    text.append("  1. Add to .env.local: ", style="#565f89")
    text.append("GROQ_API_KEY=gsk_...\n", style="bold #7dcfff")
    text.append("  2. Or configure via CLI: ", style="#565f89")
    text.append("ezshell --set-key <key>", style="bold #bb9af7")

    panel = Panel(
        text,
        box=ROUNDED,
        border_style="#e0af68",
        padding=(0, 2),
    )
    console.print(panel)


def render_error_card(result: DiagnosticResult) -> None:
    """Renders a beautiful AI diagnostic card for a failed command."""
    console.print()

    elements = []

    # 1. Summary with icon
    if result.summary:
        summary_text = Text()
        summary_text.append("✦ Cause: ", style="bold #f7768e")
        summary_text.append(f"{result.summary}\n", style="bold #c0caf5")
        elements.append(summary_text)

    # 2. Markdown explanation
    if result.explanation:
        elements.append(Markdown(result.explanation))

    # 3. Suggested Fix
    if result.suggested_fix:
        fix_title = Text()
        fix_title.append("\n⚡ Suggested Fix", style="bold #9ece6a")
        if result.fix_description:
            fix_title.append(f"  ({result.fix_description})", style="italic #565f89")
        elements.append(fix_title)

        syntax = Syntax(
            result.suggested_fix.strip(),
            lexer="bash",
            theme="monokai",
            line_numbers=False,
            padding=(1, 2),
            background_color="#1a1b26",
        )
        elements.append(syntax)

    # 4. Safety alerts
    if result.safety_report and result.safety_report.risk_level != RiskLevel.SAFE:
        level_style = "bold #f7768e" if result.safety_report.risk_level == RiskLevel.DANGEROUS else "bold #e0af68"
        elements.append(
            f"\n[{level_style}]⚠ SAFETY WARNING:[/{level_style}] {result.safety_report.reason}"
        )

    panel = Panel(
        Group(*elements),
        title=f"[bold #f7768e] ✘ Command Failed (Exit Code {result.exit_code}) [/bold #f7768e]",
        subtitle=f"[dim #565f89] `{result.command}` [/dim #565f89]",
        border_style="#f7768e",
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)


def render_ask_card(result: AskResult) -> None:
    """Renders the response card for an '!ask' query."""
    console.print()

    elements = []

    if result.explanation:
        elements.append(Markdown(result.explanation))

    if result.suggested_fix:
        fix_title = Text()
        fix_title.append("\n⚡ Recommended Command", style="bold #7dcfff")
        if result.fix_description:
            fix_title.append(f"  ({result.fix_description})", style="italic #565f89")
        elements.append(fix_title)

        syntax = Syntax(
            result.suggested_fix.strip(),
            lexer="bash",
            theme="monokai",
            line_numbers=False,
            padding=(1, 2),
            background_color="#1a1b26",
        )
        elements.append(syntax)

    if result.safety_report and result.safety_report.risk_level != RiskLevel.SAFE:
        level_style = "bold #f7768e" if result.safety_report.risk_level == RiskLevel.DANGEROUS else "bold #e0af68"
        elements.append(
            f"\n[{level_style}]⚠ SAFETY WARNING:[/{level_style}] {result.safety_report.reason}"
        )

    panel = Panel(
        Group(*elements),
        title=f"[bold #7dcfff] ? {result.question} [/bold #7dcfff]",
        border_style="#7dcfff",
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)


def render_info(message: str) -> None:
    """Renders a styled info message."""
    console.print(f"[#7dcfff]ℹ[/] [dim #c0caf5]{message}[/]")


def render_success(message: str) -> None:
    """Renders a styled success message."""
    console.print(f"[#9ece6a]✔[/] [bold #c0caf5]{message}[/]")


def render_warning(message: str) -> None:
    """Renders a styled warning message."""
    console.print(f"[#e0af68]⚠[/] [bold #e0af68]{message}[/]")


def render_error(message: str) -> None:
    """Renders a styled error message."""
    console.print(f"[#f7768e]✖[/] [bold #f7768e]{message}[/]")


def prompt_fix_action(
    fix_command: str,
    safety_report: Optional[SafetyReport] = None,
) -> str:
    """Prompts the user to decide whether to run the suggested fix command.
    Returns: 'run', 'edit', or 'skip'
    """
    if safety_report and safety_report.risk_level == RiskLevel.DANGEROUS:
        console.print(
            f"\n[bold #f7768e]⚠ DANGEROUS COMMAND DETECTED:[/] [bold #c0caf5]{safety_report.reason}[/]"
        )
        try:
            confirmation = console.input(
                "Type [bold #f7768e]'CONFIRM'[/] to execute this command or press Enter to skip: "
            ).strip()
            return "run" if confirmation == "CONFIRM" else "skip"
        except (KeyboardInterrupt, EOFError):
            return "skip"

    try:
        choice = console.input(
            "\n[bold #9ece6a]▶ Execute fix?[/] [[bold #7dcfff]y[/]es / [bold #565f89]N[/]o / [bold #bb9af7]e[/]dit]: "
        ).strip().lower()

        if choice in ("y", "yes"):
            return "run"
        elif choice in ("e", "edit"):
            return "edit"
        return "skip"
    except (KeyboardInterrupt, EOFError):
        return "skip"
