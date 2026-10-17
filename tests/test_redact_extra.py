import pytest

from src.core.redact import redact_secrets

CASES = [
    "postgresql://neondb_owner:SuperSecret99@ep-cool-123.neon.tech/db?sslmode=require",
    "mysql://root:hunter2@localhost:3306/app",
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk123",
    "github_pat_11ABCDEFG0abcdefghijklmnopqrstuvwxyz",
    "gho_abcdefghijklmnopqrstuvwxyz0123456789",
    "xoxb-1234567890-abcdefghij",
    "sk_live_abcdefghijklmnop1234",
    "ezd_abcdefghijklmnopqrstuvwxyz_0123456789",
]
SECRET_BITS = (
    "SuperSecret99",
    "hunter2",
    "eyJhbGci",
    "11ABCDEFG0",
    "abcdefghijklmnopqrstuvwxyz",
    "1234567890-abc",
    "abcdefghijklmnop1234",
)


@pytest.mark.parametrize("raw", CASES)
def test_secret_is_masked(raw):
    out = redact_secrets(f"échec : {raw} fin")
    assert "REDACTED" in out
    assert not any(bit in out for bit in SECRET_BITS)


def test_plain_text_untouched():
    t = "fatal: unable to access 'https://github.com/x/y.git/': Could not resolve host"
    assert redact_secrets(t) == t
