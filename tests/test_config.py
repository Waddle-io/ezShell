from pathlib import Path

from src.core.config import DEFAULT_MODEL, EzShellConfig


def test_config_defaults():
    config = EzShellConfig()
    assert config.model == DEFAULT_MODEL
    assert config.temperature == 0.2
    assert config.auto_suggest_fix is True
    assert config.stream_explanation is True


def test_config_save_and_load(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    original = EzShellConfig(
        groq_api_key="gsk_test12345",
        model="llama-3.3-70b-versatile",
        temperature=0.5,
        max_tokens=2048,
    )
    original.save(path=cfg_file)

    assert cfg_file.exists()

    loaded = EzShellConfig.load(config_path=cfg_file, cwd=tmp_path)
    assert loaded.groq_api_key == "gsk_test12345"
    assert loaded.model == "llama-3.3-70b-versatile"


def test_config_effective_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    config = EzShellConfig(groq_api_key="direct_key")
    assert config.get_effective_api_key() == "direct_key"

    monkeypatch.setenv("GROQ_API_KEY", "env_key")
    config_empty = EzShellConfig(groq_api_key=None)
    assert config_empty.get_effective_api_key() == "env_key"
