import json
import sys

import pytest

from src.core import capture
from src.core.provider import MockProvider
from src.core.schema import InvalidResponse
from src.core.suggest import build_request, get_suggestion


@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("EZSH_STATE_DIR", str(tmp_path / "st"))
    monkeypatch.setenv("EZSH_SESSION", "t")
    monkeypatch.delenv("EZSH_MOCK_COMMAND", raising=False)
    return tmp_path / "st"


def test_run_captures_stderr_tail_and_exit_code(capfd):
    code = capture.run_and_capture(
        [sys.executable, "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(3)"]
    )
    assert code == 3
    run = capture.read_last_run()
    assert run.exit_code == 3 and "boom" in run.stderr_tail and run.captured_output
    assert "boom" in capfd.readouterr().err  # recopiée en direct


def test_stderr_tail_is_bounded():
    capture.run_and_capture([sys.executable, "-c", "import sys; sys.stderr.write('x'*20000)"])
    assert len(capture.read_last_run().stderr_tail) <= capture.STDERR_TAIL_BYTES


def test_unknown_command_gives_127():
    assert capture.run_and_capture(["definitely-not-a-command-xyz"]) == 127
    assert capture.read_last_run().exit_code == 127


def test_state_dir_is_private(state):
    capture.state_dir()
    assert oct(state.stat().st_mode & 0o777) == "0o700"


def test_hook_files_used_when_no_run(state):
    d = capture.state_dir()
    (d / "t.cmd").write_text("git push")
    (d / "t.code").write_text("1")
    run = capture.read_last_run()
    assert (run.command, run.exit_code, run.captured_output) == ("git push", 1, False)


def test_no_state_returns_none():
    assert capture.read_last_run() is None


def test_secrets_are_redacted_before_sending(state):
    d = capture.state_dir()
    (d / "t.run.json").write_text(
        json.dumps(
            {
                "command": "deploy",
                "exit_code": 1,
                "stderr_tail": "auth failed token=ghp_abcdefghijklmnopqrstuvwxyz0123456789AB",
                "cwd": "/",
            }
        )
    )
    req = build_request()
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789AB" not in req.stderr_tail


def test_mock_floor_raises_risk_announced_by_model():
    s = get_suggestion(build_request(), MockProvider("high"))
    assert s.risk == "high" and s.risk_floor_applied


def test_translate_mode_find_delete_is_high():
    assert (
        get_suggestion(
            build_request("supprime les logs de plus de 7 jours"), MockProvider("1")
        ).risk
        == "high"
    )


def test_invalid_response_retries_then_fails():
    calls = {"n": 0}

    class P(MockProvider):
        def ask(self, req):
            calls["n"] += 1
            return "pas du json"

    with pytest.raises(InvalidResponse):
        get_suggestion(build_request(), P())
    assert calls["n"] == 2  # un nouvel essai, puis échec propre


def test_injected_ansi_in_explanation_is_stripped():
    s = get_suggestion(build_request(), MockProvider("injection"))
    assert "\x1b" not in s.response.explanation
