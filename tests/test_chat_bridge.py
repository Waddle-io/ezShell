import json

import pytest

from src.core import chat_bridge
from src.core.provider import (
    AskRequest,
    LLMProvider,
    MockProvider,
    ProviderOffline,
    QuotaExceeded,
)
from src.core.proxy_client import ProxyProvider
from src.core.safety import RiskLevel


class Fixed(LLMProvider):
    def __init__(self, **data):
        self.data = data
        self.requests: list[AskRequest] = []

    def ask(self, req: AskRequest) -> str:
        self.requests.append(req)
        return json.dumps(self.data)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("EZSH_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("EZSH_SESSION", "t")
    monkeypatch.setenv("EZSHELL_LANG", "fr")


def test_question_becomes_translate_request_with_command_and_risk():
    p = Fixed(command="ls -la", explanation="Liste.", cause="", risk="low", confidence="high")
    r = chat_bridge.ask("lister les fichiers", provider=p)
    assert p.requests[0].mode == "translate"
    assert r.suggested_commands == ["ls -la"]
    assert r.safety_reports[0].risk_level == RiskLevel.SAFE
    assert r.content == "Liste."


def test_risk_floor_applies_to_gui_and_tui_too():
    p = Fixed(command="git push --force", explanation="x", risk="low")
    r = chat_bridge.ask("pousse", provider=p)
    assert r.safety_reports[0].risk_level == RiskLevel.DANGEROUS
    assert r.safety_reports[0].requires_explicit_confirmation


def test_explain_error_uses_given_command_when_nothing_captured():
    p = Fixed(command="", explanation="Port déjà pris.", cause="Docker")
    r = chat_bridge.ask(mode="explain_error", command="docker run -p 80:80 x", provider=p)
    req = p.requests[0]
    assert req.mode == "explain_error" and req.last_command == "docker run -p 80:80 x"
    assert r.suggested_commands == [] and "Docker" in r.content


def test_explain_command_mode():
    p = Fixed(command="", explanation="Affiche l'espace disque.")
    chat_bridge.ask(mode="explain_command", command="df -h", provider=p)
    assert p.requests[0].mode == "explain_command" and p.requests[0].query == "df -h"


def test_secrets_in_question_are_masked_before_sending():
    p = Fixed(command="", explanation="ok")
    chat_bridge.ask("pourquoi gsk_" + "a" * 30 + " échoue", provider=p)
    assert "gsk_" not in p.requests[0].query


@pytest.mark.parametrize(
    "exc,expected",
    [
        (ProviderOffline("x"), "Hors ligne"),
        (QuotaExceeded("anonymous"), "essai"),
        (QuotaExceeded("free", "demain"), "demain"),
    ],
)
def test_errors_are_readable(exc, expected):
    assert expected in chat_bridge.describe_error(exc)


def test_provider_label():
    assert chat_bridge.provider_label(MockProvider("1")).startswith("Mock")
    proxy = ProxyProvider("https://ezshell.vercel.app")
    assert chat_bridge.provider_label(proxy) == "ezShell · ezshell.vercel.app"


def test_proxy_is_the_default_without_any_env(monkeypatch):
    from src.core.provider import get_provider

    for var in ("EZSH_MOCK_LLM", "EZSH_API_URL", "EZSH_DIRECT"):
        monkeypatch.delenv(var, raising=False)
    p = get_provider()
    assert isinstance(p, ProxyProvider) and p.base_url == "https://ezshell.vercel.app"
