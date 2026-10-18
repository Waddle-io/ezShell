"""Hook PowerShell : script généré, ligne d'init, installation dans $PROFILE."""

import shutil
import subprocess
from pathlib import Path

import pytest

from src.core import shell_hook
from src.core.shell_hook import (
    POWERSHELL_INIT_LINE,
    detect_current_shell,
    get_hook_script,
    init_line,
    install_hook,
    reload_hint,
)


def test_powershell_and_pwsh_return_the_powershell_hook():
    script = get_hook_script("powershell")
    assert script == get_hook_script("pwsh")
    assert "Set-PSReadLineKeyHandler -Chord 'Alt+e'" in script
    assert '$env:EZSH_SHELL = "powershell"' in script
    # La commande est insérée dans la ligne, jamais exécutée
    assert "Insert(" in script and "AcceptLine" not in script


def test_init_lines_per_shell():
    assert init_line("powershell") == POWERSHELL_INIT_LINE
    assert init_line("fish") == "ezsh init fish | source"
    assert init_line("zsh") == 'eval "$(ezsh init zsh)"'
    assert reload_hint("powershell", Path("x")) == ". $PROFILE"


def test_detect_powershell_from_hook_env(monkeypatch):
    monkeypatch.setenv("EZSH_SHELL", "powershell")
    assert detect_current_shell() == "powershell"


def test_install_into_every_profile_without_duplicates(tmp_path, monkeypatch):
    profiles = [tmp_path / "PowerShell" / "p.ps1", tmp_path / "WindowsPowerShell" / "p.ps1"]
    monkeypatch.setattr(shell_hook, "powershell_profiles", lambda: profiles)
    ok, msg, first = install_hook("powershell")
    assert ok and first == profiles[0]
    for p in profiles:
        assert POWERSHELL_INIT_LINE in p.read_text()
    install_hook("pwsh")  # idempotent
    assert profiles[0].read_text().count(POWERSHELL_INIT_LINE) == 1
    assert "Set-ExecutionPolicy -Scope CurrentUser RemoteSigned" in msg


def test_commented_line_does_not_count_as_installed(tmp_path, monkeypatch):
    rc = tmp_path / ".bashrc"
    rc.write_text('# eval "$(ezsh init bash)"\n')
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    ok, msg, _ = install_hook("bash")
    assert ok and "added" in msg
    assert rc.read_text().count('eval "$(ezsh init bash)"') == 2


def test_no_powershell_found(monkeypatch):
    monkeypatch.setattr(shell_hook, "powershell_profiles", lambda: [])
    ok, msg, _ = install_hook("powershell")
    assert not ok and "PowerShell not found" in msg


@pytest.mark.skipif(
    not (shutil.which("pwsh") or shutil.which("powershell")), reason="PowerShell absent"
)
def test_hook_parses_in_real_powershell(tmp_path):
    exe = shutil.which("pwsh") or shutil.which("powershell")
    script = tmp_path / "hook.ps1"
    script.write_text(get_hook_script("powershell"), encoding="utf-8")
    check = (
        "$e=$null; [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{script}', [ref]$null, [ref]$e) | Out-Null; $e.Count"
    )
    out = subprocess.run(
        [exe, "-NoLogo", "-NoProfile", "-Command", check],
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout.strip()
    assert out == "0"
