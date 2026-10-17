from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

from rich.panel import Panel

from src.core.assistant import ShellAssistant
from src.core.config import EzShellConfig
from src.core.context import CommandHistoryEntry, SystemContext
from src.core.pty_shell import PTYExecutor
from src.core.safety import RiskLevel, SafetyGuard
from src.ui.prompt import create_prompt_session, get_prompt_text
from src.ui.render import (
    console,
    prompt_fix_action,
    render_api_key_missing_card,
    render_ask_card,
    render_banner,
    render_error,
    render_error_card,
    render_info,
    render_success,
    render_warning,
)


class EzShellApp:
    """Main application orchestrator for ezShell interactive sessions."""

    def __init__(self, config: Optional[EzShellConfig] = None):
        self.config = config or EzShellConfig.load()
        self.assistant: Optional[ShellAssistant] = None
        self.history_entries: List[CommandHistoryEntry] = []
        self.last_exit_code: int = 0
        self.last_suggested_fix: Optional[str] = None

        if self.config.get_effective_api_key():
            self.assistant = ShellAssistant(config=self.config)

    def _handle_cd(self, args: List[str]) -> int:
        """Handles the 'cd' builtin command so directory changes persist."""
        target = args[0] if args else str(Path.home())
        if target == "~":
            target = str(Path.home())
        elif target == "-":
            target = os.environ.get("OLDPWD", str(Path.home()))

        expanded = os.path.expanduser(os.path.expandvars(target))
        try:
            old_pwd = os.getcwd()
            os.chdir(expanded)
            os.environ["OLDPWD"] = old_pwd
            os.environ["PWD"] = os.getcwd()
            return 0
        except Exception as e:
            render_error(f"cd: {e}")
            return 1

    def _handle_export(self, line: str) -> int:
        """Handles 'export KEY=VALUE' builtin."""
        parts = line[6:].strip().split("=", 1)
        if len(parts) == 2:
            key, val = parts[0].strip(), parts[1].strip().strip('"').strip("'")
            os.environ[key] = val
            render_success(f"Exported {key}={val}")
            return 0
        else:
            render_error("Usage: export KEY=VALUE")
            return 1

    def _show_help(self) -> None:
        """Displays ezShell usage guide."""
        help_text = """
[bold cyan]ezShell Built-in Commands:[/bold cyan]
  [bold]!ask <question>[/bold]    Ask AI any command-line, DevOps, or system question
  [bold]!fix[/bold]               Re-run or review the last suggested fix command
  [bold]!config[/bold]            Inspect active configuration and model settings
  [bold]!help[/bold]              Display this help overview
  [bold]clear[/bold]              Clear the terminal screen
  [bold]exit[/bold] or [bold]quit[/bold]      Leave ezShell

[bold cyan]Key Features:[/bold cyan]
    • Automatic failure detection with root cause diagnosis via Groq ([green]openai/gpt-oss-120b[/green])
  • One-click fix execution with built-in destructive command guard
  • Command and path autocompletion ([italic]Tab[/italic]), auto-suggestions ([italic]Right Arrow[/italic])
  • Press [bold]Ctrl+Space[/bold] to quickly begin an [bold]!ask[/bold] query
"""
        console.print(Panel(help_text.strip(), title="ezShell Help", border_style="cyan"))

    def _show_config(self) -> None:
        """Displays the active configuration."""
        has_key = bool(self.config.get_effective_api_key())
        masked_key = (
            f"...{self.config.get_effective_api_key()[-6:]}"
            if has_key and len(self.config.get_effective_api_key() or "") > 6
            else "[red]Not configured[/red]"
        )

        cfg_text = f"""
[bold cyan]Model:[/bold cyan] {self.config.model}
[bold cyan]API Key:[/bold cyan] {masked_key}
[bold cyan]Temperature:[/bold cyan] {self.config.temperature}
[bold cyan]Max Tokens:[/bold cyan] {self.config.max_tokens}
[bold cyan]Auto Suggest Fix:[/bold cyan] {self.config.auto_suggest_fix}
[bold cyan]Stream Explanation:[/bold cyan] {self.config.stream_explanation}
"""
        console.print(Panel(cfg_text.strip(), title="ezShell Configuration", border_style="cyan"))

    def execute_single_command(self, cmd_str: str) -> int:
        """Executes a single command line and returns the exit code."""
        cmd = cmd_str.strip()
        if not cmd:
            return 0

        # Builtin: cd
        if cmd == "cd" or cmd.startswith("cd "):
            args = cmd.split()[1:]
            code = self._handle_cd(args)
            self.last_exit_code = code
            return code

        # Builtin: export
        if cmd.startswith("export ") and "=" in cmd:
            code = self._handle_export(cmd)
            self.last_exit_code = code
            return code

        # Builtin: clear
        if cmd == "clear":
            console.clear()
            return 0

        # Standard execution via PTY
        result = PTYExecutor.execute(cmd, cwd=os.getcwd())
        self.last_exit_code = result.exit_code

        # Record in history
        import time
        self.history_entries.append(
            CommandHistoryEntry(command=cmd, exit_code=result.exit_code, timestamp=time.time())
        )
        if len(self.history_entries) > self.config.max_history_items:
            self.history_entries.pop(0)

        # Handle failure if command failed
        if result.exit_code != 0:
            self._handle_command_failure(result.command, result.exit_code, result.clean_output)

        return result.exit_code

    def _handle_command_failure(self, command: str, exit_code: int, clean_output: str) -> None:
        """Triggers AI diagnosis and presents fix options to the user."""
        if not self.config.get_effective_api_key():
            console.print(
                "\n[dim #3b4261]─[/] [#e0af68] Command failed[/] "
                "[dim #565f89]• Set GROQ_API_KEY in .env.local to enable instant AI fixes[/]\n"
            )
            return

        if self.assistant is None:
            self.assistant = ShellAssistant(config=self.config)

        context = SystemContext.collect(history=self.history_entries)

        with console.status(
            f"[cyan]Analyzing failure with Groq ({self.config.model})...[/cyan]",
            spinner="dots",
        ):
            try:
                diagnostic = self.assistant.diagnose_failure(
                    command=command,
                    exit_code=exit_code,
                    error_output=clean_output,
                    context=context,
                )
            except Exception as e:
                render_error(f"Error consulting Groq assistant: {e}")
                return

        # Render diagnostic card
        render_error_card(diagnostic)

        if diagnostic.suggested_fix and self.config.auto_suggest_fix:
            self.last_suggested_fix = diagnostic.suggested_fix
            action = prompt_fix_action(
                fix_command=diagnostic.suggested_fix,
                safety_report=diagnostic.safety_report,
            )
            if action == "run":
                console.print(f"[cyan]Executing fix:[/cyan] [bold]{diagnostic.suggested_fix}[/bold]\n")
                self.execute_single_command(diagnostic.suggested_fix)
            elif action == "edit":
                # Will return control back to prompt with suggested command as default
                render_info("Tip: Copy and edit the suggested fix command above.")

    def run(self) -> None:
        """Starts the interactive ezShell REPL loop."""
        initial_context = SystemContext.collect()
        render_banner(self.config.model, initial_context.shell_name)

        if not self.config.get_effective_api_key():
            render_api_key_missing_card()

        session = create_prompt_session()

        while True:
            try:
                context = SystemContext.collect(history=self.history_entries)
                prompt_html = get_prompt_text(context, self.last_exit_code)

                user_input = session.prompt(prompt_html)
                line = user_input.strip()

                if not line:
                    continue

                # Exit check
                if line in ("exit", "quit"):
                    console.print("[dim]Goodbye from ezShell![/dim]")
                    break

                # Builtin: help
                if line == "!help":
                    self._show_help()
                    continue

                # Builtin: config
                if line == "!config":
                    self._show_config()
                    continue

                # Builtin: fix
                if line == "!fix":
                    if self.last_suggested_fix:
                        console.print(f"[cyan]Running last suggested fix:[/cyan] {self.last_suggested_fix}\n")
                        self.execute_single_command(self.last_suggested_fix)
                    else:
                        render_info("No recent fix available.")
                    continue

                # Builtin: ask
                if line.startswith("!ask"):
                    query = line[4:].strip()
                    if not query:
                        render_info("Usage: !ask <your question here>")
                        continue
                    self._handle_ask(query, context)
                    continue

                # Standard command execution
                self.execute_single_command(line)

            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]ezShell session terminated.[/dim]")
                break
            except Exception as e:
                render_error(f"Unexpected error: {e}")

    def _handle_ask(self, query: str, context: SystemContext) -> None:
        """Handles natural language inquiry with AI assistant."""
        if not self.config.get_effective_api_key():
            render_error("Cannot execute !ask: GROQ_API_KEY is not configured.")
            return

        if self.assistant is None:
            self.assistant = ShellAssistant(config=self.config)

        with console.status(f"[cyan]Asking Groq ({self.config.model})...[/cyan]", spinner="dots"):
            try:
                result = self.assistant.ask(query, context)
            except Exception as e:
                render_error(f"Error querying Groq: {e}")
                return

        render_ask_card(result)

        if result.suggested_fix:
            self.last_suggested_fix = result.suggested_fix
            action = prompt_fix_action(
                fix_command=result.suggested_fix,
                safety_report=result.safety_report,
            )
            if action == "run":
                console.print(f"[cyan]Executing:[/cyan] [bold]{result.suggested_fix}[/bold]\n")
                self.execute_single_command(result.suggested_fix)

