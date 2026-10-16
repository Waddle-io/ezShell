from __future__ import annotations

import getpass
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class CommandHistoryEntry:
    command: str
    exit_code: int
    timestamp: float


@dataclass
class SystemContext:
    os_name: str
    os_version: str
    architecture: str
    current_user: str
    current_directory: str
    shell_name: str
    git_branch: Optional[str] = None
    git_is_dirty: Optional[bool] = None
    recent_history: List[CommandHistoryEntry] = field(default_factory=list)

    @classmethod
    def collect(cls, history: Optional[List[CommandHistoryEntry]] = None) -> SystemContext:
        """Collects current runtime environment and system context."""
        os_name = platform.system()
        os_version = platform.release()

        # Extract Linux distro name if available
        if os_name == "Linux":
            try:
                import distro  # type: ignore
                distro_name = distro.name(pretty=True)
                if distro_name:
                    os_name = distro_name
            except Exception:
                if Path("/etc/os-release").is_file():
                    try:
                        with open("/etc/os-release", "r") as f:
                            for line in f:
                                if line.startswith("PRETTY_NAME="):
                                    os_name = line.split("=", 1)[1].strip().strip('"')
                                    break
                    except Exception:
                        pass
        elif os_name == "Darwin":
            os_name = f"macOS {platform.mac_ver()[0]}"

        # Git context
        git_branch = None
        git_is_dirty = None
        if shutil.which("git"):
            try:
                # Check branch
                branch_proc = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                )
                if branch_proc.returncode == 0:
                    git_branch = branch_proc.stdout.strip()

                    # Check dirty status
                    status_proc = subprocess.run(
                        ["git", "status", "--porcelain"],
                        capture_output=True,
                        text=True,
                        timeout=1.0,
                    )
                    git_is_dirty = bool(status_proc.stdout.strip())
            except Exception:
                pass

        shell_path = os.environ.get("SHELL", "/bin/bash")
        shell_name = Path(shell_path).name

        return cls(
            os_name=os_name,
            os_version=os_version,
            architecture=platform.machine(),
            current_user=getpass.getuser(),
            current_directory=str(Path.cwd()),
            shell_name=shell_name,
            git_branch=git_branch,
            git_is_dirty=git_is_dirty,
            recent_history=history or [],
        )

    def to_prompt_context(self) -> str:
        """Formats the system context as a concise string for LLM prompts."""
        lines = [
            f"OS: {self.os_name} ({self.architecture})",
            f"Shell: {self.shell_name}",
            f"Current Directory: {self.current_directory}",
            f"User: {self.current_user}",
        ]
        if self.git_branch:
            dirty_str = " (uncommitted changes)" if self.git_is_dirty else " (clean)"
            lines.append(f"Git Branch: {self.git_branch}{dirty_str}")

        if self.recent_history:
            recent_str = " -> ".join(
                f"`{entry.command}` (exit: {entry.exit_code})"
                for entry in self.recent_history[-3:]
            )
            lines.append(f"Recent Commands: {recent_str}")

        return "\n".join(lines)


def get_last_shell_command() -> Optional[str]:
    """Retrieves the last non-ezShell command executed by the user.

    Inspects in priority order:
    1. ~/.ezshell/.last_command (marker written by shell hook)
    2. $HISTFILE
    3. ~/.zsh_history (handles Zsh extended format ': <timestamp>:0;<cmd>')
    4. ~/.bash_history
    5. ~/.histfile

    Returns:
        Optional[str]: The command string, or None if no command history found.
    """
    candidates = []

    # 1. ezShell runtime marker
    ez_marker = Path.home() / ".ezshell" / ".last_command"
    if ez_marker.is_file():
        candidates.append(ez_marker)

    # 2. $HISTFILE
    histfile = os.environ.get("HISTFILE")
    if histfile and Path(histfile).is_file():
        candidates.append(Path(histfile))

    # 3. Standard shell history paths
    home = Path.home()
    for p in [home / ".zsh_history", home / ".bash_history", home / ".histfile", home / ".zhistory"]:
        if p.is_file():
            candidates.append(p)

    ignored_prefixes = ("ezsh", "ezshell", "eszh", "clear", "exit", "history")

    for p in candidates:
        try:
            with open(p, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - 8192))
                content = f.read().decode("utf-8", errors="ignore")
                lines = content.splitlines()

                for raw_line in reversed(lines):
                    line = raw_line.strip()
                    # Zsh extended history format: ': 1712345678:0;command'
                    if line.startswith(":") and ";" in line:
                        line = line.split(";", 1)[1].strip()

                    if not line:
                        continue

                    parts = line.split()
                    if not parts:
                        continue
                    cmd_name = parts[0]
                    base_cmd = Path(cmd_name).name

                    # Ignore ezshell aliases and system navigation commands
                    if base_cmd in ignored_prefixes or cmd_name in ignored_prefixes:
                        continue
                    if any(x in line for x in ("ezshell", "ezsh", "eszh")):
                        continue

                    return line
        except Exception:
            continue

    return None


def get_last_exit_code() -> Optional[int]:
    """Retrieves the last command's exit code from ~/.ezshell/.last_exit_code.

    Returns:
        Optional[int]: The exit code (e.g. 0, 1, 127), or None if not available.
    """
    marker = Path.home() / ".ezshell" / ".last_exit_code"
    if marker.is_file():
        try:
            val = marker.read_text(encoding="utf-8").strip()
            return int(val)
        except Exception:
            pass
    return None


