from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import (
    Completer,
    Completion,
    PathCompleter,
    WordCompleter,
)
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from src.core.context import SystemContext


COMMON_COMMANDS = [
    "git",
    "docker",
    "docker-compose",
    "kubectl",
    "terraform",
    "python",
    "python3",
    "pip",
    "pytest",
    "npm",
    "yarn",
    "pnpm",
    "cargo",
    "rustc",
    "go",
    "curl",
    "wget",
    "ssh",
    "scp",
    "systemctl",
    "journalctl",
    "make",
    "grep",
    "find",
    "cat",
    "ls",
    "cd",
    "pwd",
    "export",
    "env",
    "chmod",
    "chown",
    "tar",
    "zip",
    "unzip",
    "df",
    "du",
    "top",
    "htop",
]

EZSHELL_BUILTINS = {
    "!ask": "Ask AI a natural language terminal question",
    "!explain": "Explain the last command output or error",
    "!fix": "Re-execute the last suggested fix",
    "!config": "View current ezShell configuration",
    "!help": "Show ezShell documentation and built-in commands",
    "exit": "Exit ezShell",
    "quit": "Exit ezShell",
    "clear": "Clear terminal screen",
}


class EzShellCompleter(Completer):
    """Hybrid completer combining ezShell builtins, common commands, and filesystem paths."""

    def __init__(self):
        self.cmd_completer = WordCompleter(COMMON_COMMANDS, ignore_case=True)
        self.path_completer = PathCompleter(expanduser=True)

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor

        # If user is typing an ezShell meta-command (!...)
        if text_before_cursor.startswith("!"):
            word = document.get_word_before_cursor()
            for cmd, desc in EZSHELL_BUILTINS.items():
                if cmd.startswith("!") and cmd.startswith(word):
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display=cmd,
                        display_meta=desc,
                    )
            return

        # Offer command completion if at the beginning of the line
        tokens = text_before_cursor.split()
        if len(tokens) <= 1 and not text_before_cursor.endswith(" "):
            yield from self.cmd_completer.get_completions(document, complete_event)

        # Always offer path completion
        yield from self.path_completer.get_completions(document, complete_event)


def get_prompt_text(context: SystemContext, last_exit_code: int = 0) -> HTML:
    """Builds a high-contrast, vivid 2-line prompt with bright neon accents."""
    user = context.current_user

    # Compact home directory representation
    cwd = context.current_directory
    home = str(Path.home())
    if cwd.startswith(home):
        display_cwd = "~" + cwd[len(home):]
    else:
        display_cwd = cwd

    # Truncate overly long paths
    parts = display_cwd.split("/")
    if len(parts) > 4:
        display_cwd = f".../{parts[-2]}/{parts[-1]}"

    # Git branch segment in vivid neon green
    git_segment = ""
    if context.git_branch:
        dirty_indicator = '<style fg="#FFB800"><b>*</b></style>' if context.git_is_dirty else ""
        git_segment = (
            f' <style fg="#FFFFFF">on</style> '
            f'<style fg="#00FF88"><b>⎇ {context.git_branch}</b></style>{dirty_indicator}'
        )

    # Exit code badge (vivid neon red on failure)
    exit_badge = ""
    if last_exit_code != 0:
        exit_badge = f' <style fg="#FF2A6D"><b>[✘ {last_exit_code}]</b></style>'

    arrow_color = "#00FF88" if last_exit_code == 0 else "#FF2A6D"

    return HTML(
        f'<style fg="#00E5FF"><b>╭─</b></style> '
        f'<style fg="#C084FC"><b>{user}</b></style> '
        f'<style fg="#FFFFFF">in</style> '
        f'<style fg="#FACC15"><b>{display_cwd}</b></style>'
        f'{git_segment}'
        f'{exit_badge}\n'
        f'<style fg="#00E5FF"><b>╰─</b></style><style fg="{arrow_color}"><b>❯</b></style> '
    )


def create_prompt_session(history_file: Optional[Path] = None) -> PromptSession:
    """Creates a configured prompt_toolkit PromptSession with high-contrast vibrant styles."""
    hist_path = history_file or (Path.home() / ".ezshell_history")
    hist_path.parent.mkdir(parents=True, exist_ok=True)

    history = FileHistory(str(hist_path))
    completer = EzShellCompleter()

    style = Style.from_dict(
        {
            # Autocompletion popup styling with vibrant accents
            "completion-menu": "bg:#0F172A #F8FAFC",
            "completion-menu.completion": "bg:#0F172A #F8FAFC",
            "completion-menu.completion.current": "bg:#00E5FF #0F172A bold",
            "completion-menu.meta": "bg:#1E293B #94A3B8 italic",
            # Fish-style auto-suggestions
            "auto-suggestion": "#64748B italic",
        }
    )

    kb = KeyBindings()

    @kb.add("c-space")
    def _insert_ask(event):
        """Ctrl+Space inserts '!ask ' at prompt."""
        event.current_buffer.insert_text("!ask ")

    return PromptSession(
        history=history,
        completer=completer,
        auto_suggest=AutoSuggestFromHistory(),
        style=style,
        key_bindings=kb,
    )
