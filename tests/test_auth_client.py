"""Tests unitaires pour AuthClient (RFC 8628, login, logout, usage)."""

from src.core.auth_client import AuthClient
from src.core.proxy_client import TokenStore


def test_auth_client_logout(tmp_path):
    store_file = tmp_path / "token.json"
    store = TokenStore(store_file)
    store.save("https://test.api", "mock_token_123")
    assert store.load("https://test.api") == "mock_token_123"

    client = AuthClient(base_url="https://test.api", store=store)

    calls = []
    def mock_post(path, payload, token=None):
        calls.append((path, payload, token))
        return 200, {"success": True}

    client._post = mock_post
    ret = client.logout()

    assert ret == 0
    assert len(calls) == 1
    assert calls[0][0] == "/api/v1/auth/device/revoke"
    assert calls[0][2] == "mock_token_123"
    assert store.load("https://test.api") is None


def test_auth_client_usage(tmp_path):
    store = TokenStore(tmp_path / "token.json")
    client = AuthClient(base_url="https://test.api", store=store)

    client._get = lambda path, token=None: (
        200,
        {
            "account_type": "registered",
            "user": {"email": "test@ezshell.dev", "plan": "free"},
            "quota": {
                "tier": "free",
                "daily_limit": 25,
                "used_today": 7,
                "remaining_today": 18,
                "reset_at": "2026-10-26T00:00:00Z",
            },
        },
    )

    ret = client.usage()
    assert ret == 0


def test_auth_client_login_success(tmp_path, monkeypatch):
    store = TokenStore(tmp_path / "token.json")
    client = AuthClient(base_url="https://test.api", store=store)

    monkeypatch.setattr("webbrowser.open", lambda url: True)
    monkeypatch.setattr("time.sleep", lambda s: None)

    post_calls = []

    def mock_post(path, payload, token=None):
        post_calls.append((path, payload))
        if path == "/api/v1/auth/device/code":
            return 200, {
                "device_code": "mock_dev_code_xyz",
                "user_code": "WDLE-8492",
                "verification_uri": "https://test.api/activate",
                "verification_uri_complete": "https://test.api/activate?user_code=WDLE-8492",
                "interval": 1,
                "expires_in": 300,
                "device_token": "ezd_new_device_token_999",
            }
        if path == "/api/v1/auth/device/token":
            if len(post_calls) == 2:
                return 400, {"error": "authorization_pending"}
            return 200, {
                "token_type": "Bearer",
                "user": {"id": "usr_123", "email": "coder@ezshell.dev", "plan": "premium"},
            }
        return 400, {}

    client._post = mock_post
    ret = client.login()

    assert ret == 0
    assert store.load("https://test.api") == "ezd_new_device_token_999"
    assert len(post_calls) == 3


def test_auth_client_login_denied(tmp_path, monkeypatch):
    store = TokenStore(tmp_path / "token.json")
    client = AuthClient(base_url="https://test.api", store=store)

    monkeypatch.setattr("webbrowser.open", lambda url: True)
    monkeypatch.setattr("time.sleep", lambda s: None)

    def mock_post(path, payload, token=None):
        if path == "/api/v1/auth/device/code":
            return 200, {
                "device_code": "mock_code",
                "user_code": "CODE-1234",
                "verification_uri": "https://test.api/activate",
                "interval": 1,
                "expires_in": 60,
            }
        if path == "/api/v1/auth/device/token":
            return 403, {"error": "access_denied", "error_description": "Refusé par l'utilisateur"}
        return 400, {}

    client._post = mock_post
    ret = client.login()
    assert ret == 1
