"""Tests de non-régression V3 pour l'intégration shell et la gestion des raccourcis."""

from pathlib import Path

from src.core.config import EzShellConfig
from src.core.keybindings import (
    KeybindingConfig,
    check_key_conflict,
    format_shell_trigger,
    normalize_key,
)
from src.core.shell_hook import (
    MARKER_END,
    MARKER_START,
    get_hook_script,
    init_line,
    install_hook,
    uninstall_hook,
)


def test_keybinding_normalization_and_conflict_check():
    # Touches valides
    assert normalize_key("alt+e") == "Alt+E"
    assert normalize_key("ctrl+space") == "Ctrl+Space"
    assert normalize_key("alt+s") == "Alt+S"

    ok, err, warn = check_key_conflict("alt+e")
    assert ok and err is None

    # Conflits système interdits
    ok, err, _ = check_key_conflict("ctrl+c")
    assert not ok and "réservée" in err

    ok, err, _ = check_key_conflict("enter")
    assert not ok and "réservée" in err

    # Avertissement sur raccourci readline natif
    ok, err, warn = check_key_conflict("ctrl+r")
    assert ok and warn and "historique" in warn


def test_format_shell_trigger_per_shell():
    zsh_stmt, desc = format_shell_trigger("Alt+S", "zsh")
    assert "bindkey '\\es'" in zsh_stmt
    assert desc == "Alt+S"

    bash_stmt, _ = format_shell_trigger("Alt+S", "bash")
    assert 'bind -x \'"\\es": __ezshell_widget\'' in bash_stmt

    fish_stmt, _ = format_shell_trigger("Alt+S", "fish")
    assert "bind \\es __ezshell_widget" in fish_stmt

    pwsh_stmt, _ = format_shell_trigger("Alt+S", "powershell")
    assert "@('Alt+s', 'Alt+S', 'Escape,s', 'Escape,S')" in pwsh_stmt


def test_hook_generation_with_custom_keybindings():
    cfg = EzShellConfig()
    cfg.set_keybindings(KeybindingConfig(trigger_key="Alt+S", trigger_enabled=True))
    script = get_hook_script("bash", config=cfg)
    assert "\\es" in script
    assert "\\ee" not in script

    # Trigger désactivé
    cfg.set_keybindings(KeybindingConfig(trigger_enabled=False))
    script_disabled = get_hook_script("bash", config=cfg)
    assert "__ezshell_widget" not in script_disabled


def test_hook_install_idempotence_and_reversibility(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    for shell in ("bash", "zsh", "fish"):
        ok, msg, rc = install_hook(shell)
        assert ok
        content1 = rc.read_text(encoding="utf-8")
        assert MARKER_START in content1
        assert MARKER_END in content1
        assert content1.count(MARKER_START) == 1

        # Ré-installation : doit être strictement idempotent et sans doublon
        ok2, msg2, _ = install_hook(shell)
        assert ok2
        content2 = rc.read_text(encoding="utf-8")
        assert content2 == content1

        # Désinstallation : réversibilité complète
        ok3, msg3, _ = uninstall_hook(shell)
        assert ok3
        content3 = rc.read_text(encoding="utf-8")
        assert MARKER_START not in content3
        assert init_line(shell) not in content3


def test_powershell_uninstall(tmp_path, monkeypatch):
    profile = tmp_path / "Microsoft.PowerShell_profile.ps1"
    profile.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("src.core.shell_hook.powershell_profiles", lambda: [profile])

    ok, _, _ = install_hook("powershell")
    assert ok and MARKER_START in profile.read_text()

    ok2, _, _ = uninstall_hook("powershell")
    assert ok2 and MARKER_START not in profile.read_text()
