import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from src.core.provider import (
    AskRequest,
    ProviderError,
    ProviderOffline,
    QuotaExceeded,
    UpdateRequired,
    get_provider,
)
from src.core.proxy_client import ProxyProvider, TokenStore

GOOD = json.dumps({"command": "ls", "explanation": "x", "risk": "low", "confidence": "high"})


class Stub:
    """Faux proxy : enregistre les requêtes reçues et rejoue des réponses scénarisées."""

    def __init__(self):
        self.requests = []
        self.ask_replies = [(200, GOOD)]
        self.ask_headers = {}
        self.register_replies = [(201, json.dumps({"device_token": "ezd_" + "t" * 43}))]
        stub = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get("content-length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                stub.requests.append((self.path, self.headers.get("authorization"), body))
                queue = (
                    stub.register_replies if self.path.endswith("register") else stub.ask_replies
                )
                status, text = queue.pop(0) if len(queue) > 1 else queue[0]
                self.send_response(status)
                self.send_header("content-type", "application/json")
                for k, v in stub.ask_headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(text.encode())

            def log_message(self, *a):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture
def stub():
    s = Stub()
    yield s
    s.server.shutdown()


@pytest.fixture
def provider(stub, tmp_path):
    return ProxyProvider(stub.url, TokenStore(tmp_path / "cfg" / "device.json"))


def req(**kw):
    base = dict(
        mode="explain_error",
        query="",
        os_name="linux",
        shell="bash",
        cwd="~",
        last_command="git push",
        exit_code=1,
        stderr_tail="rejected",
        lang="fr",
    )
    base.update(kw)
    return AskRequest(**base)


def test_registers_once_then_reuses_token(stub, provider):
    assert provider.ask(req()) == GOOD
    provider.ask(req())
    paths = [p for p, _, _ in stub.requests]
    assert paths == ["/api/v1/device/register", "/api/v1/ask", "/api/v1/ask"]
    assert stub.requests[1][1] == "Bearer ezd_" + "t" * 43


@pytest.mark.skipif(os.name == "nt", reason="droits POSIX : sous Windows, ACL du profil")
def test_token_file_is_private(provider):
    provider.ask(req())
    mode = provider.store.path.stat().st_mode & 0o777
    assert oct(mode) == "0o600"


def test_token_is_bound_to_server_url(tmp_path):
    store = TokenStore(tmp_path / "d.json")
    store.save("https://a.example", "ezd_x")
    assert store.load("https://a.example") == "ezd_x"
    assert store.load("https://b.example") is None


def test_payload_contains_context_but_no_api_key(stub, provider, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_" + "k" * 30)
    provider.ask(req(query="pourquoi ?"))
    _, _, body = stub.requests[1]
    assert body["mode"] == "explain_error" and body["context"]["last_command"] == "git push"
    assert "gsk_" not in json.dumps(stub.requests)


def test_401_triggers_single_reregistration(stub, provider):
    provider.ask(req())  # enregistre
    stub.ask_replies = [(401, '{"error":"unauthorized"}'), (200, GOOD)]
    assert provider.ask(req()) == GOOD
    assert [p for p, _, _ in stub.requests].count("/api/v1/device/register") == 2


def test_persistent_401_gives_up(stub, provider):
    stub.ask_replies = [(401, '{"error":"unauthorized"}')]
    with pytest.raises(ProviderError):
        provider.ask(req())


@pytest.mark.parametrize("scope", ["anonymous", "free", "burst"])
def test_429_maps_to_quota_exceeded(stub, provider, scope):
    stub.ask_replies = [(429, json.dumps({"scope": scope, "reset_at": "2026-10-18T00:00:00Z"}))]
    with pytest.raises(QuotaExceeded) as exc:
        provider.ask(req())
    assert exc.value.scope == scope and exc.value.reset_at == "2026-10-18T00:00:00Z"


@pytest.mark.parametrize("status", [400, 502, 503])
def test_server_errors_map_to_provider_error(stub, provider, status):
    stub.ask_replies = [(status, '{"error":"kill_switch"}')]
    with pytest.raises(ProviderError):
        provider.ask(req())


def test_unreachable_server_is_offline(tmp_path):
    p = ProxyProvider("http://127.0.0.1:9", TokenStore(tmp_path / "d.json"))
    with pytest.raises(ProviderOffline):
        p.ask(req())


@pytest.mark.parametrize("url", ["http://example.com", "ftp://x", "example.com"])
def test_refuses_insecure_or_invalid_urls(tmp_path, url):
    with pytest.raises(ProviderError):
        ProxyProvider(url, TokenStore(tmp_path / "d.json")).ask(req())


def test_get_provider_prefers_proxy_when_url_is_set(monkeypatch):
    monkeypatch.delenv("EZSH_MOCK_LLM", raising=False)
    monkeypatch.setenv("EZSH_API_URL", "https://ezshell.example")
    assert isinstance(get_provider(), ProxyProvider)
    monkeypatch.setenv("EZSH_MOCK_LLM", "1")
    assert not isinstance(get_provider(), ProxyProvider)  # le mock reste prioritaire


# ---------------------------------------------------------------- mises à jour (v2)
def test_en_tete_de_derniere_version_memorise_pour_le_rappel(stub, provider, tmp_path, monkeypatch):
    from src.core import updater

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    stub.ask_headers = {"x-ezsh-latest": "9.9.9"}
    provider.ask(req())
    assert updater.cached_latest() == "9.9.9"


def test_en_tete_invalide_ignore(stub, provider, tmp_path, monkeypatch):
    from src.core import updater

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    stub.ask_headers = {"x-ezsh-latest": "\x1b[31mpirate"}
    provider.ask(req())
    assert updater.cached_latest() is None


def test_426_leve_update_required_sans_reenregistrement(stub, provider):
    body = {"error": "update_required", "min_supported": "0.2.0", "latest": "0.3.0"}
    stub.ask_replies = [(426, json.dumps(body))]
    with pytest.raises(UpdateRequired) as exc:
        provider.ask(req())
    assert exc.value.min_supported == "0.2.0" and exc.value.latest == "0.3.0"
    assert sum(1 for path, _, _ in stub.requests if path.endswith("register")) == 1


def test_426_message_traduit():
    from src.core.chat_bridge import describe_error

    assert "ezsh --update" in describe_error(UpdateRequired("0.2.0", "0.3.0"))
