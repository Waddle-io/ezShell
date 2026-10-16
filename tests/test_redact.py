from src.core.redact import redact_secrets


def test_redact_groq_key():
    raw = "Failed running curl with key gsk_abc1234567890abcdef1234567890"
    redacted = redact_secrets(raw)
    assert "gsk_abc" not in redacted
    assert "[REDACTED_GROQ_KEY]" in redacted


def test_redact_openai_key():
    raw = "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456"
    redacted = redact_secrets(raw)
    assert "sk-abc" not in redacted


def test_redact_bearer_token():
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    redacted = redact_secrets(raw)
    assert "Bearer [REDACTED_TOKEN]" in redacted


def test_redact_passwords_and_tokens():
    raw = "export DB_PASSWORD='supersecret123' and token=987654321"
    redacted = redact_secrets(raw)
    assert "supersecret123" not in redacted
    assert "PASSWORD=[REDACTED]" in redacted


def test_redact_private_key():
    raw = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Y1+
-----END RSA PRIVATE KEY-----"""
    redacted = redact_secrets(raw)
    assert "[REDACTED_PRIVATE_KEY]" in redacted

