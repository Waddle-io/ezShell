from __future__ import annotations

import argparse
import os
import sys


def _version() -> str:
    from src import __version__

    return __version__


def build_arg_parser() -> argparse.ArgumentParser:
    from src.core.config import DEFAULT_MODEL

    parser = argparse.ArgumentParser(
        prog="ezshell",
        description="ezShell: An intelligent terminal assistant with real-time Groq AI diagnostics and GUI window.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Show what's new and update ezShell after confirmation (add --yes to skip the prompt).",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="With --update: do not ask for confirmation.",
    )
    parser.add_argument(
        "--check-key",
        action="store_true",
        help="Check that the ezShell service is reachable (or your Groq key with EZSH_DIRECT=1).",
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
        "--install-hook",
        action="store_true",
        help="Automatically install ezShell hook into your active ~/.zshrc or ~/.bashrc.",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Optional prompt or error to diagnose immediately upon opening.",
    )
    return parser


def _fast_dispatch(argv: list) -> "int | None":
    """Sous-commandes légères : aucun import lourd (objectif de démarrage < 200 ms)."""
    if not argv:
        return None
    cmd = argv[0]
    if cmd in ("--version", "-V"):
        from src.core.updater import version_hint

        print(f"ezshell {_version()}")
        hint = version_hint()  # lit le cache local : aucun appel réseau
        if hint:
            print(hint)
        return 0
    if cmd == "--update":
        from src.core.updater import run_update

        rest = set(argv[1:])
        return run_update(yes=bool(rest & {"--yes", "-y"}))
    if cmd == "run":
        from src.core.capture import run_and_capture

        rest = argv[1:]
        if rest and rest[0] == "--":
            rest = rest[1:]
        return run_and_capture(rest)
    if cmd == "init" and not ({"--install", "-i", "--uninstall", "-u"} & set(argv[1:])):
        # Exécuté à chaque ouverture de terminal : aucun import lourd.
        from src.core.shell_hook import detect_current_shell, get_hook_script

        shells = [a for a in argv[1:] if not a.startswith("-")]
        sys.stdout.write(get_hook_script(shells[0] if shells else detect_current_shell()))
        sys.stdout.flush()
        return 0
    if cmd == "login":
        from src.core.auth_client import AuthClient
        return AuthClient().login()
    if cmd == "logout":
        from src.core.auth_client import AuthClient
        return AuthClient().logout()
    if cmd in ("usage", "quota"):
        from src.core.auth_client import AuthClient
        return AuthClient().usage()
    if cmd == "suggest":
        ask, free, it = None, [], iter(argv[1:])
        for a in it:
            if a.startswith("--ask="):
                ask = a[len("--ask=") :]
            elif a == "--ask":
                ask = next(it, None)
            else:
                free.append(a)
        if ask is None and free:
            ask = " ".join(free)
        if ask is None:  # hook PowerShell : la ligne passe par l'environnement (pas de souci de quoting)
            ask = os.environ.get("EZSH_ASK") or None
        from src.ui.inline import run_inline

        return run_inline(ask)
    return None


def _utf8_console() -> None:
    """Console Windows : UTF-8 pour les accents et les cadres (sinon cp1252 / cp850)."""
    if os.name != "nt":
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _utf8_console()
    fast = _fast_dispatch(sys.argv[1:])
    if fast is not None:
        return fast

    from src.app import EzShellApp
    from src.core.config import EzShellConfig
    from src.core.groq_client import GroqClient
    from src.ui.chat_tui import EzShellChatApp
    from src.ui.logo import show_welcome_banner
    from src.ui.render import (
        console,
        render_error,
        render_info,
        render_success,
    )

    # Subcommand: init (e.g. `eval "$(ezsh init zsh)"` or `ezsh init --install`)
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        from src.core.shell_hook import (
            detect_current_shell,
            get_hook_script,
            install_hook,
            reload_hint,
        )

        remaining = sys.argv[2:]
        if "--uninstall" in remaining or "-u" in remaining:
            from src.core.shell_hook import uninstall_hook
            target_shells = [arg for arg in remaining if not arg.startswith("-")]
            shell_name = target_shells[0] if target_shells else None
            ok, msg, rc_path = uninstall_hook(shell_name)
            if ok:
                render_success(msg)
                shell = (shell_name or detect_current_shell()).lower()
                render_info(f"Reload your shell with: {reload_hint(shell, rc_path)}")
                return 0
            else:
                render_error(msg)
                return 1

        if "--install" in remaining or "-i" in remaining:
            target_shells = [arg for arg in remaining if not arg.startswith("-")]
            shell_name = target_shells[0] if target_shells else None
            ok, msg, rc_path = install_hook(shell_name)
            if ok:
                render_success(msg)
                shell = (shell_name or detect_current_shell()).lower()
                render_info(f"Reload your shell with: {reload_hint(shell, rc_path)}")
                return 0
            else:
                render_error(msg)
                return 1

        shell_name = remaining[0] if remaining else detect_current_shell()
        sys.stdout.write(get_hook_script(shell_name))
        sys.stdout.flush()
        return 0

    # Subcommand: shortcuts / keybindings
    if len(sys.argv) > 1 and sys.argv[1] in ("shortcuts", "keybindings"):
        from src.core.keybindings import KeybindingConfig
        from src.ui.shortcuts_menu import (
            display_shortcuts_table,
            run_interactive_shortcuts_menu,
            set_trigger_key,
        )

        config = EzShellConfig.load()
        remaining = sys.argv[2:]
        if not remaining:
            if sys.stdin.isatty():
                return run_interactive_shortcuts_menu(config)
            display_shortcuts_table(config.get_keybindings())
            return 0

        if "--list" in remaining:
            display_shortcuts_table(config.get_keybindings())
            return 0

        if "--enable" in remaining:
            kb = config.get_keybindings()
            kb.trigger_enabled = True
            config.set_keybindings(kb)
            config.save()
            render_success("✔ Raccourci déclencheur shell activé !")
            return 0

        if "--disable" in remaining:
            kb = config.get_keybindings()
            kb.trigger_enabled = False
            config.set_keybindings(kb)
            config.save()
            render_success("✔ Raccourci déclencheur shell désactivé !")
            return 0

        if "--reset" in remaining:
            config.set_keybindings(KeybindingConfig())
            config.save()
            render_success("✔ Raccourcis réinitialisés aux valeurs par défaut !")
            return 0

        if "--set-trigger" in remaining:
            idx = remaining.index("--set-trigger")
            if idx + 1 < len(remaining):
                key = remaining[idx + 1]
                return set_trigger_key(key, config)
            else:
                render_error("Argument manquant pour --set-trigger (ex: ezsh shortcuts --set-trigger Alt+S)")
                return 1

        display_shortcuts_table(config.get_keybindings())
        return 0

    parser = build_arg_parser()
    args = parser.parse_args()

    # Flag: --install-hook
    if args.install_hook:
        from src.core.shell_hook import detect_current_shell, install_hook, reload_hint

        ok, msg, rc_path = install_hook()
        if ok:
            render_success(msg)
            render_info(f"Reload your shell with: {reload_hint(detect_current_shell(), rc_path)}")
            return 0
        else:
            render_error(msg)
            return 1

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
        from src.core.provider import get_provider
        from src.core.proxy_client import ProxyProvider

        provider = get_provider(config)
        if isinstance(provider, ProxyProvider):
            with console.status("[cyan]Checking the ezShell service...[/cyan]", spinner="dots"):
                ok = provider.health()
            if ok:
                render_success(
                    f"ezShell service reachable ({provider.base_url}): no local key needed."
                )
                return 0
            render_error(f"ezShell service unreachable ({provider.base_url}).")
            return 1
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

    # Flag: --explain (même chemin que Alt+E : proxy, validation, plancher de risque)
    if args.explain:
        from src.core.chat_bridge import describe_error
        from src.core.provider import get_provider
        from src.core.redact import redact_secrets
        from src.core.suggest import build_request, get_suggestion
        from src.ui.panel import result_panel

        req = build_request("")
        req.mode = "explain_error"
        req.stderr_tail = redact_secrets(args.explain)[-4096:]
        if req.exit_code is None:
            req.exit_code = 1
        with console.status("[cyan]Analyzing error message...[/cyan]", spinner="dots"):
            try:
                suggestion = get_suggestion(req, get_provider(config))
            except Exception as e:
                render_error(describe_error(e))
                return 1
        console.print(result_panel(suggestion, req.lang))
        return 0

    # Flag: -c / --command
    if args.command:
        app = EzShellApp(config=config)
        return app.execute_single_command(args.command)

    # Automatic first-time install greeting banner
    show_welcome_banner(force=False)

    # Mode: Wrapper REPL (shell PTY : Unix uniquement)
    if args.wrapper:
        if os.name == "nt":
            render_error(
                "--wrapper is not available on Windows. Use Alt+E in PowerShell "
                "(ezsh init powershell), ezsh --tui or ezsh."
            )
            return 2
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
            import warnings

            warnings.filterwarnings("ignore", message=".*Given image is not CTkImage.*")

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
