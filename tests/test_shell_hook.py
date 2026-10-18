from src.core.shell_hook import get_hook_script, install_hook


def test_get_hook_script_zsh():
    script = get_hook_script("zsh")
    assert "__ezshell_preexec" in script
    assert "add-zsh-hook" in script
    assert "\\ee" in script


def test_get_hook_script_bash():
    script = get_hook_script("bash")
    assert "__ezshell_prompt_command" in script
    assert "PROMPT_COMMAND" in script
    assert "bind -x" in script


def test_install_hook_bash(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    bashrc = tmp_path / ".bashrc"

    ok, msg, rc_file = install_hook("bash")
    assert ok is True
    assert bashrc.is_file()
    assert 'eval "$(ezsh init bash)"' in bashrc.read_text()

    # Second install should detect it already exists
    ok2, msg2, _ = install_hook("bash")
    assert ok2 is True
    assert "already present" in msg2

