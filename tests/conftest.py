"""Configuration pytest commune."""

import os

# Tests qui pilotent un vrai bash/zsh ou un PTY : Unix uniquement.
collect_ignore = ["test_e2e_shell.py", "test_pty_shell.py"] if os.name == "nt" else []
