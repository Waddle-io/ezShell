from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


DEFAULT_CONFIG_DIR = Path.home() / ".ezshell"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_MODEL = "llama-3.1-8b-instant"


@dataclass
class EzShellConfig:
    """Configuration settings for ezShell."""

    groq_api_key: Optional[str] = None
    model: str = DEFAULT_MODEL
    temperature: float = 0.2
    max_tokens: int = 1024
    auto_suggest_fix: bool = True
    stream_explanation: bool = True
    max_history_items: int = 100

    @classmethod
    def load(cls, cwd: Optional[Path] = None, config_path: Optional[Path] = None) -> EzShellConfig:
        """Loads configuration in order of precedence:
        1. Local .env.local or .env in current working directory
        2. Environment variables (GROQ_API_KEY, EZSHELL_MODEL, etc.)
        3. User config file (~/.ezshell/config.json or custom config_path)
        4. Default values
        """
        # 1. Load local .env files if present
        current_dir = cwd or Path.cwd()
        env_local = current_dir / ".env.local"
        env_default = current_dir / ".env"
        if env_local.is_file():
            load_dotenv(dotenv_path=env_local, override=False)
        elif env_default.is_file():
            load_dotenv(dotenv_path=env_default, override=False)

        # 2. Base dict from user config JSON file if it exists
        data: dict = {}
        target_config = config_path or DEFAULT_CONFIG_PATH
        if target_config.is_file():
            try:
                with open(target_config, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    if isinstance(file_data, dict):
                        data.update(file_data)
            except Exception:
                pass

        # 3. Environment variables take precedence over config file
        env_key = os.environ.get("GROQ_API_KEY")
        if env_key:
            data["groq_api_key"] = env_key

        env_model = os.environ.get("EZSHELL_MODEL")
        if env_model:
            data["model"] = env_model

        # Filter fields matching dataclass
        valid_keys = {"groq_api_key", "model", "temperature", "max_tokens", "auto_suggest_fix", "stream_explanation", "max_history_items"}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}

        return cls(**filtered_data)

    def save(self, path: Optional[Path] = None) -> None:
        """Persists the current configuration to disk."""
        target_path = path or DEFAULT_CONFIG_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    def get_effective_api_key(self) -> Optional[str]:
        """Returns the active Groq API key or None."""
        return self.groq_api_key or os.environ.get("GROQ_API_KEY")
