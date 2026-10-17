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


MORE = [
    ("sk-proj-abcdefghijklmnopqrstuvwxyz12", "abcdefghijklmnop"),
    ("sk-ant-api03-abcdefghijklmnopqrstuvwxyz", "abcdefghijklmnop"),
    ("AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIK7MDENGbPxRfiCY", "wJalrXUtn"),
    ('password="my secret phrase"', "secret phrase"),
    ("Authorization: Basic dXNlcjpwYXNzd29yZA==", "dXNlcjpw"),
    ("mysql -u root -pHunter22 app", "Hunter22"),
    ("docker login -u bob -p S3cretPass registry.io", "S3cretPass"),
    ("curl -u admin:S3cretPass https://x", "S3cretPass"),
    ("deploy --password=S3cretPass", "S3cretPass"),
    ("glpat-abcdefghijklmnopqrstu", "abcdefghijklmnop"),
    ("https://bob:S3cretPass@gitlab.com/x.git", "S3cretPass"),
]


@pytest.mark.parametrize("raw,secret", MORE)
def test_more_secrets_are_masked(raw, secret):
    out = redact_secrets(f"err: {raw} end")
    assert secret not in out and "REDACTED" in out


def test_url_credentials_keep_host_for_diagnosis():
    out = redact_secrets("fatal: https://bob:S3cretPass@gitlab.com/x.git not found")
    assert "gitlab.com/x.git" in out and "S3cretPass" not in out


def test_truncated_private_key_is_masked():
    body = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7" * 3
    assert "MIIEvQ" not in redact_secrets(body + "\n-----END PRIVATE KEY-----")
    assert "MIIEvQ" not in redact_secrets("-----BEGIN RSA PRIVATE KEY-----\n" + body)


def test_exit_codes_and_paths_untouched():
    t = "ls: cannot access '/tmp/token_dir': No such file (exit 2) -p 8080"
    assert redact_secrets(t) == t
