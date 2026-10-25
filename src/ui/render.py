from __future__ import annotations

import sys
from typing import Optional

from rich.box import ROUNDED
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from src import __version__
from src.core.assistant import AskResult, DiagnosticResult
from src.core.safety import RiskLevel, SafetyReport

# Vivid neon palette — high-contrast, no muted tones
custom_theme = Theme(
    {
        "info": "#00E5FF bold",       # electric cyan
        "warning": "#FFB800 bold",    # vivid amber
        "error": "#FF2A6D bold",      # neon red/pink
        "success": "#00FF88 bold",    # neon green
        "command": "#FACC15 bold",    # neon yellow
        "muted": "#94A3B8",           # cool grey (readable, not muddy)
        "accent": "#C084FC bold",     # vivid purple
        "highlight": "#00E5FF bold",  # electric cyan
    }
)

console = Console(theme=custom_theme, file=sys.stdout)


def render_banner(model_name: str, shell_name: str) -> None:
    """Renders a sleek, modern ezShell header banner."""
    console.print()

    title_text = Text()
    title_text.append("ezShell ", style="bold #00E5FF")
    title_text.append(f"v{__version__}", style="#94A3B8")
    title_text.append("  •  ", style="#475569")
    title_text.append("Model: ", style="#94A3B8")
    title_text.append(f"{model_name}", style="bold #C084FC")
    title_text.append("  •  ", style="#475569")
    title_text.append("Shell: ", style="#94A3B8")
    title_text.append(f"{shell_name}", style="#00FF88")

    subtitle_text = Text()
    subtitle_text.append("Type ", style="#94A3B8")
    subtitle_text.append("!ask <query>", style="bold #00E5FF")
    subtitle_text.append(" for instant AI help  •  ", style="#94A3B8")
    subtitle_text.append("!help", style="bold #C084FC")
    subtitle_text.append(" for commands  •  ", style="#94A3B8")
    subtitle_text.append("exit", style="#FF2A6D")
    subtitle_text.append(" to quit", style="#94A3B8")

    content = Table.grid(padding=(0, 0))
    content.add_row(title_text)
    content.add_row(subtitle_text)

    banner_panel = Panel(
        content,
        box=ROUNDED,
        border_style="#00E5FF",
        padding=(1, 2),
    )
    console.print(banner_panel)


def render_api_key_missing_card() -> None:
    """Renders an attractive notice card when GROQ_API_KEY is not configured."""
    text = Text()
    text.append("Groq AI Engine Inactive\n", style="bold #FFB800")
    text.append("ezShell will run commands normally, but automated error diagnosis is off.\n\n", style="#FFFFFF")
    text.append("To activate AI assistance:\n", style="#94A3B8")
    text.append("  1. Add to .env.local: ", style="#94A3B8")
    text.append("GROQ_API_KEY=gsk_...\n", style="bold #00E5FF")
    text.append("  2. Or configure via CLI: ", style="#94A3B8")
    text.append("ezshell --set-key <key>", style="bold #C084FC")

    panel = Panel(
        text,
        box=ROUNDED,
        border_style="#FFB800",
        padding=(0, 2),
    )
    console.print(panel)


def render_error_card(result: DiagnosticResult) -> None:
    """Renders the AI diagnostic card matching the official ezShell reference design."""
    console.print()

    elements = []

    # 1. User Query row: > explain this error
    query_text = Text()
    query_text.append("> ", style="bold #00E5FF")
    query_text.append(f"explain this error: {result.command}", style="#F1F5F9")
    elements.append(query_text)
    elements.append(Text(""))

    # 2. Section: CAUSE
    cause_lbl = Text("CAUSE\n", style="bold #64748B")
    cause_body = result.summary or result.explanation or "Unknown root cause."
    elements.append(cause_lbl)
    elements.append(Text(f"{cause_body}\n", style="#CAD5E2"))

    # 3. Section: FIX
    if result.suggested_fix:
        fix_lbl = Text("FIX", style="bold #64748B")
        elements.append(fix_lbl)

        cmd_text = Text()
        cmd_text.append("$  ", style="#64748B")
        cmd_text.append(result.suggested_fix.strip(), style="bold #00E5FF")

        fix_panel = Panel(
            cmd_text,
            box=ROUNDED,
            border_style="#182739",
            style="on #070D16",
            padding=(0, 1),
        )
        elements.append(fix_panel)

    # 4. Section: RISK
    report = result.safety_report
    if report:
        if report.risk_level == RiskLevel.DANGEROUS:
            dot_color = "#FF2A6D"
            risk_label = "HIGH RISK"
        elif report.risk_level == RiskLevel.WARNING:
            dot_color = "#FFB800"
            risk_label = "MEDIUM RISK"
        else:
            dot_color = "#00FF88"
            risk_label = "LOW RISK"
        reason = report.reason or "Only changes your local environment."
    else:
        dot_color = "#00FF88"
        risk_label = "LOW RISK"
        reason = "Only changes your local environment."

    risk_text = Text()
    risk_text.append("● ", style=f"bold {dot_color}")
    risk_text.append(f"{risk_label}  ", style=f"bold {dot_color}")
    risk_text.append(f"{reason}\n", style="#7B8C9F")
    elements.append(risk_text)

    # 5. Divider & Footer
    elements.append(Rule(style="#152232"))
    elements.append(Text("ASK ANOTHER QUESTION\n", style="bold #64748B"))

    footer = Text()
    footer.append("[Enter  run]  ", style="bold #FFFFFF on #0E1724")
    footer.append("[c  copy]  ", style="bold #FFFFFF on #0E1724")
    footer.append("[e  edit]  ", style="bold #FFFFFF on #0E1724")
    footer.append("[q  close]", style="bold #FFFFFF on #0E1724")
    elements.append(footer)

    outer_panel = Panel(
        Group(*elements),
        title="[bold #00E5FF]>_[/bold #00E5FF] [bold #FFFFFF]ezShell[/bold #FFFFFF]",
        subtitle="[dim #64748B][Esc] to close[/dim #64748B]",
        border_style="#00E5FF",
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print(outer_panel)
    console.print()


def render_ask_card(result: AskResult) -> None:
    """Renders the response card for an '!ask' query."""
    console.print()

    elements = []

    if result.explanation:
        elements.append(Markdown(result.explanation))

    if result.suggested_fix:
        fix_title = Text()
        fix_title.append("\n› Recommended Command", style="bold #00E5FF")
        if result.fix_description:
            fix_title.append(f"  ({result.fix_description})", style="italic #94A3B8")
        elements.append(fix_title)

        syntax = Syntax(
            result.suggested_fix.strip(),
            lexer="bash",
            theme="monokai",
            line_numbers=False,
            padding=(1, 2),
            background_color="#0F172A",
        )
        elements.append(syntax)

    if result.safety_report and result.safety_report.risk_level != RiskLevel.SAFE:
        level_style = "bold #FF2A6D" if result.safety_report.risk_level == RiskLevel.DANGEROUS else "bold #FFB800"
        elements.append(
            f"\n[{level_style}]SAFETY WARNING:[/{level_style}] {result.safety_report.reason}"
        )

    panel = Panel(
        Group(*elements),
        title=f"[bold #00E5FF] ? {result.question} [/bold #00E5FF]",
        border_style="#00E5FF",
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)


def render_info(message: str) -> None:
    """Renders a styled info message."""
    console.print(f"[#00E5FF]i[/] [#FFFFFF]{message}[/]")


def render_success(message: str) -> None:
    """Renders a styled success message."""
    console.print(f"[#00FF88]✔[/] [bold #FFFFFF]{message}[/]")


def render_warning(message: str) -> None:
    """Renders a styled warning message."""
    console.print(f"[#FFB800]![/] [bold #FFB800]{message}[/]")


def render_error(message: str) -> None:
    """Renders a styled error message."""
    console.print(f"[#FF2A6D]✖[/] [bold #FF2A6D]{message}[/]")


def prompt_fix_action(
    fix_command: str,
    safety_report: Optional[SafetyReport] = None,
) -> str:
    """Prompts the user to decide whether to run the suggested fix command.
    Returns: 'run', 'edit', or 'skip'
    """
    if safety_report and safety_report.risk_level == RiskLevel.DANGEROUS:
        console.print(
            f"\n[bold #FF2A6D][!] DANGEROUS COMMAND DETECTED:[/] [bold #FFFFFF]{safety_report.reason}[/]"
        )
        try:
            confirmation = console.input(
                "Type [bold #FF2A6D]'CONFIRM'[/] to execute this command or press Enter to skip: "
            ).strip()
            return "run" if confirmation == "CONFIRM" else "skip"
        except (KeyboardInterrupt, EOFError):
            return "skip"

    try:
        choice = console.input(
            "\n[bold #00FF88]› Execute fix?[/] [[bold #00E5FF]y[/]es / [bold #94A3B8]N[/]o / [bold #C084FC]e[/]dit]: "
        ).strip().lower()

        if choice in ("y", "yes"):
            return "run"
        elif choice in ("e", "edit"):
            return "edit"
        return "skip"
    except (KeyboardInterrupt, EOFError):
        return "skip"
