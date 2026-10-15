from __future__ import annotations

import os
import re
import select
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

try:
    import pty
    import termios
    import tty
    import struct
    import fcntl
    HAS_PTY = True
except ImportError:
    HAS_PTY = False

try:
    import pyte
    HAS_PYTE = True
except ImportError:
    HAS_PYTE = False


@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    clean_output: str


# Regex fallback for stripping ANSI escapes when pyte is not installed or for quick cleanup
ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def clean_ansi_escapes(raw_text: str) -> str:
    """Cleans ANSI escape sequences from text using pyte if available, or regex fallback."""
    if not raw_text:
        return ""

    if HAS_PYTE:
        try:
            screen = pyte.HistoryScreen(120, 50, history=500)
            stream = pyte.ByteStream(screen)
            stream.feed(raw_text.encode("utf-8", errors="replace"))

            lines = []
            for hist_line in screen.history.top:
                line_str = "".join(char.data for char in hist_line.values()).rstrip()
                if line_str:
                    lines.append(line_str)
            for screen_line in screen.display:
                line_str = screen_line.rstrip()
                if line_str:
                    lines.append(line_str)

            if lines:
                return "\n".join(lines)
        except Exception:
            pass

    # Regex fallback
    clean = ANSI_ESCAPE_RE.sub("", raw_text)
    # Normalize carriage returns and newlines
    clean = clean.replace("\r\n", "\n").replace("\r", "\n")
    # Remove excessive blank lines
    return "\n".join(line.rstrip() for line in clean.splitlines() if line.strip())


class PTYExecutor:
    """Executes commands using pseudo-terminals to preserve TTY behavior and capture output."""

    @staticmethod
    def _sync_window_size(master_fd: int):
        """Propagate current host terminal dimensions to the PTY."""
        if not HAS_PTY:
            return
        try:
            s = struct.pack("HHHH", 0, 0, 0, 0)
            size = fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, s)
            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, size)
        except Exception:
            pass

    @classmethod
    def execute(
        cls,
        command: str,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        forward_output: bool = True,
    ) -> CommandResult:
        """Executes a command with stdout on a PTY and stderr captured."""
        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        working_dir = cwd or os.getcwd()

        if not HAS_PTY:
            # Fallback for Windows or systems without pty
            return cls._execute_subprocess(command, run_env, working_dir, forward_output)

        master_fd, slave_fd = pty.openpty()
        cls._sync_window_size(master_fd)

        shell_path = run_env.get("SHELL", "/bin/bash")

        try:
            proc = subprocess.Popen(
                [shell_path, "-c", command],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=subprocess.PIPE,
                close_fds=True,
                env=run_env,
                cwd=working_dir,
                preexec_fn=os.setsid,
            )
        except Exception as e:
            os.close(slave_fd)
            os.close(master_fd)
            return CommandResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=str(e),
                clean_output=str(e),
            )

        # Close slave in parent process immediately
        os.close(slave_fd)

        stdout_chunks = []
        try:
            os.set_blocking(master_fd, False)
        except Exception:
            pass

        while proc.poll() is None:
            rlist, _, _ = select.select([master_fd], [], [], 0.05)
            if master_fd in rlist:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        stdout_chunks.append(data)
                        if forward_output:
                            sys.stdout.buffer.write(data)
                            sys.stdout.buffer.flush()
                except OSError:
                    break

        # Drain any remaining bytes from master
        while True:
            try:
                data = os.read(master_fd, 4096)
                if not data:
                    break
                stdout_chunks.append(data)
                if forward_output:
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
            except OSError:
                break

        try:
            os.close(master_fd)
        except OSError:
            pass

        # Capture stderr and returncode
        stderr_bytes = b""
        if proc.stderr:
            try:
                stderr_bytes = proc.stderr.read()
            except Exception:
                pass

        exit_code = proc.wait()

        stdout_str = b"".join(stdout_chunks).decode("utf-8", errors="replace")
        stderr_str = stderr_bytes.decode("utf-8", errors="replace")

        # Composite output for error diagnosis
        combined = f"{stdout_str}\n{stderr_str}".strip() if stderr_str else stdout_str.strip()
        clean = clean_ansi_escapes(stderr_str if stderr_str.strip() else combined)

        return CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            clean_output=clean,
        )

    @classmethod
    def _execute_subprocess(
        cls,
        command: str,
        env: Dict[str, str],
        cwd: str,
        forward_output: bool,
    ) -> CommandResult:
        """Standard subprocess execution fallback when PTY is unavailable."""
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=cwd,
            text=True,
        )

        stdout_chunks = []
        stderr_chunks = []

        # Read output
        stdout_str, stderr_str = proc.communicate()
        exit_code = proc.returncode

        if forward_output:
            if stdout_str:
                sys.stdout.write(stdout_str)
                sys.stdout.flush()
            if stderr_str:
                sys.stderr.write(stderr_str)
                sys.stderr.flush()

        combined = f"{stdout_str}\n{stderr_str}".strip() if stderr_str else stdout_str.strip()
        clean = clean_ansi_escapes(stderr_str if stderr_str.strip() else combined)

        return CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            clean_output=clean,
        )

