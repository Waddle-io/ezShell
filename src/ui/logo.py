from __future__ import annotations

import os
from pathlib import Path
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

INSTALL_MARKER_PATH = Path.home() / ".ezshell" / ".installed"


def is_first_install() -> bool:
    """Checks if ezShell is being run for the first time by the user."""
    return not INSTALL_MARKER_PATH.exists()


def mark_as_installed() -> None:
    """Creates the marker file indicating ezShell has been installed and welcomed."""
    try:
        INSTALL_MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
        INSTALL_MARKER_PATH.touch(exist_ok=True)
    except Exception:
        pass


def _gradient(text: str, r1: int, g1: int, b1: int, r2: int, g2: int, b2: int) -> str:
    """Applies a horizontal truecolor gradient across a string of characters."""
    n = max(len(text) - 1, 1)
    result = ""
    for i, ch in enumerate(text):
        t = i / n
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        result += f"\033[38;2;{r};{g};{b}m{ch}"
    return result + "\033[0m"


def _vertical_gradient_lines(
    lines: List[str],
    r1: int, g1: int, b1: int,
    r2: int, g2: int, b2: int,
) -> List[str]:
    """Applies a vertical truecolor gradient across multiple lines."""
    n = max(len(lines) - 1, 1)
    result = []
    for i, line in enumerate(lines):
        t = i / n
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        result.append(f"\033[38;2;{r};{g};{b}m{line}\033[0m")
    return result


def render_logo_ascii() -> List[str]:
    """Renders the official ezShell logo as high-quality hand-crafted ASCII art.

    The logo is the iconic "C>" terminal prompt shape: a rounded bracket "C"
    with a chevron ">" and cursor bar "=" inside. Uses ANSI truecolor for a
    cyan-to-blue vertical gradient that mimics the metallic 3D look.
    """
    # Raw ASCII art lines (no color) -- hand-crafted to match the logo.png shape
    raw = [
        r"            ██████████████████████████            ",
        r"        ████▀▀                      ▀▀████        ",
        r"      ███▀    ████████████████████████    ▀███      ",
        r"    ███▀    ███▀                    ▀███    ▀███    ",
        r"   ███    ███▀                        ▀███    ███   ",
        r"  ███    ███                            ███    ███  ",
        r"  ███   ███      ██▄                    ███   ███  ",
        r"  ███   ███       ████▄                 ███   ███  ",
        r"  ███   ███        █████▄    ████████   ███   ███  ",
        r"  ███   ███       ████▀                 ███   ███  ",
        r"  ███   ███      ██▀                    ███   ███  ",
        r"  ███    ███                            ███    ███  ",
        r"   ███    ███▄                        ▄███    ███   ",
        r"    ███▄    ███▄                    ▄███    ▄███    ",
        r"      ███▄    ████████████████████████    ▄███      ",
        r"        ████▄▄                      ▄▄████        ",
        r"            ██████████████████████████            ",
    ]

    # Apply a vertical gradient: bright cyan (#00E5FF) -> deep blue (#0066FF)
    return _vertical_gradient_lines(
        raw,
        r1=0, g1=229, b1=255,    # top: Electric Cyan
        r2=0, g2=102, b2=255,    # bottom: Deep Blue
    )


def render_logo_compact() -> str:
    """Returns a compact single-line colored logo mark for prompts and headers."""
    c = "\033[1;38;2;0;229;255m"   # Bold Electric Cyan
    b = "\033[1;38;2;0;136;255m"   # Bold Deep Blue
    r = "\033[0m"
    return f"{c}[{b}>{c}_{b}]{r}"


def render_logo_mini() -> List[str]:
    """Returns a smaller 9-line logo variant for tighter terminal widths."""
    raw = [
        r"      ▄▄████████████████▄▄      ",
        r"    ██▀  ██████████████  ▀██    ",
        r"  ██▀  ██▀            ▀██  ▀██  ",
        r"  ██  ██    ██▄          ██  ██  ",
        r"  ██  ██     ████  ████  ██  ██  ",
        r"  ██  ██    ██▀          ██  ██  ",
        r"  ██▄  ██▄            ▄██  ▄██  ",
        r"    ██▄  ██████████████  ▄██    ",
        r"      ▀▀████████████████▀▀      ",
    ]
    return _vertical_gradient_lines(
        raw,
        r1=0, g1=229, b1=255,
        r2=0, g2=102, b2=255,
    )


def render_title_text() -> str:
    """Returns the 'ezShell' title as a gradient text string."""
    return _gradient(
        "  e z S h e l l",
        r1=0, g1=229, b1=255,
        r2=0, g2=255, b2=136,
    )


def show_welcome_banner(force: bool = False) -> None:
    """Displays the welcome screen with the official ASCII logo on first installation.

    Shows a side-by-side layout: the hand-crafted ASCII art logo on the left
    and a rich info card with usage instructions on the right.
    """
    if not force and not is_first_install():
        return

    console = Console()
    console.print()

    # Choose logo size based on terminal width
    term_width = console.width or 80
    if term_width >= 90:
        logo_lines = render_logo_ascii()
    else:
        logo_lines = render_logo_mini()

    logo_block = "\n".join(logo_lines)

    info_card = """[bold #00E5FF]ezShell v0.1.0[/bold #00E5FF]
[dim #94A3B8]Intelligent Terminal Assistant[/dim #94A3B8]
[dim #94A3B8]Powered by Groq AI[/dim #94A3B8]

[bold #FFFFFF]Welcome to your new terminal superpower![/bold #FFFFFF]
ezShell gives you instant AI diagnostics, command
generation, and an interactive desktop assistant
window right from your CLI.

[bold #00FF88]› How to use:[/bold #00FF88]
  [bold #00E5FF]ezsh[/bold #00E5FF]               Desktop Assistant window
  [bold #00E5FF]ezsh --tui[/bold #00E5FF]         In-terminal TUI popup
  [bold #00E5FF]ezsh --set-key[/bold #00E5FF]     Configure your Groq API key
  [bold #00E5FF]ezsh -c <cmd>[/bold #00E5FF]      Single command with AI assist
  [bold #00E5FF]ezsh --help[/bold #00E5FF]        List all options

[italic #94A3B8]Press Esc or Ctrl+C to close popup windows.[/italic #94A3B8]
"""

    grid = Table.grid(padding=(0, 3))
    grid.add_column(justify="center", vertical="middle")
    grid.add_column(vertical="middle")

    grid.add_row(
        Text.from_ansi(logo_block),
        Panel(
            info_card.strip(),
            border_style="#00E5FF",
            padding=(1, 2),
        ),
    )

    console.print(grid)
    console.print()
    mark_as_installed()
