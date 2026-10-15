import json
from unittest.mock import MagicMock
from src.core.assistant import ShellAssistant, extract_json_payload
from src.core.config import EzShellConfig
from src.core.context import SystemContext
from src.core.safety import RiskLevel


def test_extract_json_payload_direct():
    payload = {"summary": "Package missing", "suggested_fix": "pip install foo"}
    result = extract_json_payload(json.dumps(payload))
    assert result["summary"] == "Package missing"
    assert result["suggested_fix"] == "pip install foo"


def test_extract_json_payload_markdown_blocks():
    text = """Here is the diagnostic:
```json
{
  "summary": "Port in use",
  "explanation": "Process already running on port 8000.",
  "suggested_fix": "kill $(lsof -t -i:8000)",
  "fix_description": "Terminates the process occupying port 8000"
}
```
Hope this helps!"""
    result = extract_json_payload(text)
    assert result["summary"] == "Port in use"
    assert result["suggested_fix"] == "kill $(lsof -t -i:8000)"


def test_assistant_diagnose_failure(mocker):
    mock_client = MagicMock()
    mock_client.complete.return_value = json.dumps(
        {
            "summary": "Git branch does not exist",
            "explanation": "You tried to checkout a branch that hasn't been created yet.",
            "suggested_fix": "git checkout -b feature-test",
            "fix_description": "Create and switch to the new branch",
        }
    )

    config = EzShellConfig(groq_api_key="gsk_mock")
    assistant = ShellAssistant(config=config, client=mock_client)
    context = SystemContext.collect()

    diag = assistant.diagnose_failure(
        command="git checkout feature-test",
        exit_code=1,
        error_output="error: pathspec 'feature-test' did not match any file(s) known to git",
        context=context,
    )

    assert diag.summary == "Git branch does not exist"
    assert diag.suggested_fix == "git checkout -b feature-test"
    assert diag.safety_report is not None
    assert diag.safety_report.risk_level == RiskLevel.SAFE


def test_assistant_diagnose_dangerous_fix(mocker):
    mock_client = MagicMock()
    mock_client.complete.return_value = json.dumps(
        {
            "summary": "Clean root disk space",
            "explanation": "Wipes disk completely.",
            "suggested_fix": "rm -rf /",
            "fix_description": "Dangerous wipe",
        }
    )

    config = EzShellConfig(groq_api_key="gsk_mock")
    assistant = ShellAssistant(config=config, client=mock_client)
    context = SystemContext.collect()

    diag = assistant.diagnose_failure(
        command="disk_cleanup",
        exit_code=1,
        error_output="No space left on device",
        context=context,
    )

    assert diag.safety_report is not None
    assert diag.safety_report.risk_level == RiskLevel.DANGEROUS

