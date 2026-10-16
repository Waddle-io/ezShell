from __future__ import annotations

import argparse
import os
import sys

from src.app import EzShellApp
from src.core.assistant import ShellAssistant
from src.core.config import DEFAULT_MODEL, EzShellConfig
from src.core.context import SystemContext
from src.core.groq_client import GroqClient
from src.ui.chat_tui import EzShellChatApp
from src.ui.logo import show_welcome_banner
from src.ui.render import (
    console,
    render_banner,
    render_error,
    render_error_card,
    render_info,
    render_success,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ezshell",
        description="ezShell: An intelligent terminal assistant with real-time Groq AI diagnostics and GUI window.",
    )
    parser.add_argument(
        "--check-key",
        action="store_true",
        help="Check whether the configured Groq API key is valid and can connect.",
    )
    parser.add_argument(
        "--set-key",
        type=str,
        metavar="KEY",
        help="Save a Groq API key to your personal ezShell configuration (~/.ezshell/config.json).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=f"Override LLM model (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--explain",
        type=str,
        metavar="ERROR_TEXT",
        help="Diagnose an error message directly without entering the interactive shell session.",
    )
    parser.add_argument(
        "-c",
        "--command",
        type=str,
        metavar="CMD",
        help="Execute a single command through ezShell and exit.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Force open the desktop graphical assistant window.",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Open in terminal TUI popup mode instead of the desktop GUI window.",
    )
    parser.add_argument(
        "--wrapper",
        action="store_true",
        help="Run ezShell in classic shell wrapper REPL mode.",
    )
    parser.add_argument(
        "--logo",
        action="store_true",
        help="Display the official ezShell ASCII art logo and welcome overview.",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Optional prompt or error to diagnose immediately upon opening.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    config = EzShellConfig.load()
    if args.model:
        config.model = args.model

    # Flag: --logo
    if args.logo:
        show_welcome_banner(force=True)
        return 0

    # Flag: --set-key
    if args.set_key:
        config.groq_api_key = args.set_key.strip()
        config.save()
        render_success("Groq API key saved successfully to ~/.ezshell/config.json")
        return 0

    # Flag: --check-key
    if args.check_key:
        api_key = config.get_effective_api_key()
        if not api_key:
            render_error(
                "No API key found. Set GROQ_API_KEY in .env.local or run 'ezshell --set-key <your-key>'."
            )
            return 1
        with console.status("[cyan]Verifying Groq API credentials...[/cyan]", spinner="dots"):
            client = GroqClient(api_key=api_key)
            valid = client.validate_connection()

        if valid:
            render_success("Groq API key is valid and connected!")
            return 0
        else:
            render_error("Groq API key validation failed. Please verify your credentials.")
            return 1

    # Flag: --explain
    if args.explain:
        if not config.get_effective_api_key():
            render_error("GROQ_API_KEY is required for --explain.")
            return 1
        assistant = ShellAssistant(config=config)
        context = SystemContext.collect()
        with console.status("[cyan]Analyzing error message...[/cyan]", spinner="dots"):
            try:
                diag = assistant.diagnose_failure(
                    command="(manual input)",
                    exit_code=1,
                    error_output=args.explain,
                    context=context,
                )
                render_error_card(diag)
                return 0
            except Exception as e:
                render_error(f"Analysis failed: {e}")
                return 1

    # Flag: -c / --command
    if args.command:
        app = EzShellApp(config=config)
        return app.execute_single_command(args.command)

    # Automatic first-time install greeting banner
    show_welcome_banner(force=False)

    # Mode: Wrapper REPL
    if args.wrapper:
        app = EzShellApp(config=config)
        app.run()
        return 0

    # Mode: Terminal TUI
    if args.tui:
        chat_app = EzShellChatApp(config=config)
        chat_app.run()
        return 0

    # Default Mode: Desktop Graphical Window (with fallback to TUI)
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if has_display or args.gui:
        if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" in os.environ:
            os.environ["DISPLAY"] = ":0"
        try:
            from src.ui.gui_window import EzShellDesktopApp

            gui_app = EzShellDesktopApp(
                config=config,
                initial_query=args.query,
            )
            gui_app.mainloop()
            return 0
        except Exception:
            # If GUI fails to open (e.g. headless or X connection refused), fallback to TUI
            pass

    chat_app = EzShellChatApp(config=config)
    chat_app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
