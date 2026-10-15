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
    """Builds a Starship-inspired 2-line prompt with Tokyo Night palette, git status, and exit badges."""
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

    # Git branch segment
    git_segment = ""
    if context.git_branch:
        dirty_indicator = '<style fg="#e0af68">*</style>' if context.git_is_dirty else ""
        git_segment = (
            f' <style fg="#565f89">on</style> '
            f'<style fg="#9ece6a">⎇ {context.git_branch}</style>{dirty_indicator}'
        )

    # Exit code badge (only shown on failure)
    exit_badge = ""
    if last_exit_code != 0:
        exit_badge = f' <style fg="#f7768e">[✘ {last_exit_code}]</style>'

    arrow_color = "#7dcfff" if last_exit_code == 0 else "#f7768e"

    return HTML(
        f'<style fg="#3b4261">╭─</style> <style fg="#e0af68">⚡</style> '
        f'<style fg="#bb9af7"><b>{user}</b></style> '
        f'<style fg="#565f89">in</style> '
        f'<style fg="#7aa2f7"><b>{display_cwd}</b></style>'
        f'{git_segment}'
        f'{exit_badge}\n'
        f'<style fg="#3b4261">╰─</style><style fg="{arrow_color}"><b>❯</b></style> '
    )


def create_prompt_session(history_file: Optional[Path] = None) -> PromptSession:
    """Creates a configured prompt_toolkit PromptSession with Tokyo Night styles."""
    hist_path = history_file or (Path.home() / ".ezshell_history")
    hist_path.parent.mkdir(parents=True, exist_ok=True)

    history = FileHistory(str(hist_path))
    completer = EzShellCompleter()

    style = Style.from_dict(
        {
            # Autocompletion popup styling
            "completion-menu": "bg:#1a1b26 #c0caf5",
            "completion-menu.completion": "bg:#1a1b26 #c0caf5",
            "completion-menu.completion.current": "bg:#7aa2f7 #1a1b26 bold",
            "completion-menu.meta": "bg:#24283b #565f89 italic",
            # Fish-style auto-suggestions
            "auto-suggestion": "#565f89 italic",
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
