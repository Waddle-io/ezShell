from src.core.pty_shell import PTYExecutor, clean_ansi_escapes


def test_clean_ansi_escapes():
    raw = "\x1b[31;1mError: file not found\x1b[0m\r\nline 2\r\n"
    cleaned = clean_ansi_escapes(raw)
    assert "\x1b[" not in cleaned
    assert "Error: file not found" in cleaned
    assert "line 2" in cleaned


def test_pty_executor_success():
    res = PTYExecutor.execute("echo 'ezShell execution test'", forward_output=False)
    assert res.exit_code == 0
    assert "ezShell execution test" in res.stdout


def test_pty_executor_failure():
    res = PTYExecutor.execute("sh -c 'exit 42'", forward_output=False)
    assert res.exit_code == 42

