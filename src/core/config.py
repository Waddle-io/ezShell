"""
ezShell Configuration Management
==================================
This module defines the ``EzShellConfig`` dataclass, which centralises every
user-configurable setting for the ezShell application.  Configuration is
resolved through a layered precedence chain so that more specific sources
always win over more general ones:

1. Local ``.env.local`` / ``.env`` file in the current working directory
2. Process-level environment variables (``GROQ_API_KEY``, ``EZSHELL_MODEL``)
3. Persisted user config file (``~/.ezshell/config.json`` or a custom path)
4. Hard-coded default values defined in this module

The :func:`EzShellConfig.load` classmethod merges all sources automatically,
while :func:`EzShellConfig.save` serialises the current settings back to
disk as JSON.

---

Gestion de la configuration d'ezShell
=======================================
Ce module définit le dataclass ``EzShellConfig``, qui centralise tous les
paramètres configurables par l'utilisateur pour l'application ezShell.
La configuration est résolue selon une chaîne de priorité : les sources
plus spécifiques remplacent toujours les sources plus générales.

1. Fichier ``.env.local`` / ``.env`` dans le répertoire de travail courant
2. Variables d'environnement du processus (``GROQ_API_KEY``, ``EZSHELL_MODEL``)
3. Fichier de configuration utilisateur persisté (``~/.ezshell/config.json``)
4. Valeurs par défaut définies dans ce module
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Default directory where ezShell stores its persistent configuration.
DEFAULT_CONFIG_DIR = Path.home() / ".ezshell"

#: Full path to the default JSON configuration file.
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"

#: Groq model identifier used when no model is specified by the user.
DEFAULT_MODEL = "openai/gpt-oss-120b"

#: Supported provider identifiers.
SUPPORTED_PROVIDERS: list[str] = ["groq", "openai", "anthropic", "ollama"]

#: Default model per provider.
PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "groq": DEFAULT_MODEL,
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
    "ollama": "llama3",
}


@dataclass
class EzShellConfig:
    """Centralised, immutable-style configuration for an ezShell session.

    All fields have sensible defaults so that ``EzShellConfig()`` is always
    a valid, usable configuration without any environment setup.

    Attributes:
        groq_api_key (Optional[str]): Groq platform API key used to
            authenticate requests.  When ``None``, the value is looked up
            from the ``GROQ_API_KEY`` environment variable at runtime via
            :meth:`get_effective_api_key`.
        model (str): Groq model identifier (e.g. ``"openai/gpt-oss-120b"``).
            Overridable via the ``EZSHELL_MODEL`` environment variable.
        temperature (float): Sampling temperature passed to the language
            model.  Lower values (closer to 0) produce more deterministic
            output; higher values increase creativity.  Default is ``0.2``.
        max_tokens (int): Maximum number of tokens the model may generate in
            a single response.  Default is ``1024``.
        auto_suggest_fix (bool): When ``True``, ezShell automatically
            proposes a corrected command after a shell error without waiting
            for an explicit user request.  Default is ``True``.
        stream_explanation (bool): When ``True``, model explanations are
            printed incrementally as tokens arrive rather than buffered and
            displayed all at once.  Default is ``True``.
        max_history_items (int): Maximum number of shell-command history
            entries retained in the session context sent to the model.
            Default is ``100``.
    """

    groq_api_key: Optional[str] = None
    model: str = DEFAULT_MODEL
    temperature: float = 0.2
    max_tokens: int = 1024
    auto_suggest_fix: bool = True
    stream_explanation: bool = True
    max_history_items: int = 100
    # --- multi-provider ---
    provider: str = "groq"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"

    @classmethod
    def load(cls, cwd: Optional[Path] = None, config_path: Optional[Path] = None) -> EzShellConfig:
        """Build an ``EzShellConfig`` instance by merging all configuration sources.

        Sources are applied from lowest to highest precedence so that each
        subsequent source can selectively override earlier values:

        1. User config JSON file (``~/.ezshell/config.json`` or *config_path*)
        2. Process environment variables (``GROQ_API_KEY``, ``EZSHELL_MODEL``)
        3. ``.env.local`` / ``.env`` dotenv file in *cwd* (loaded into the
           environment before step 2 is evaluated, but ``override=False``
           prevents it from overwriting already-set variables)
        4. Dataclass field defaults for any key not supplied by the above

        Args:
            cwd (Optional[Path]): Directory to search for ``.env.local`` /
                ``.env`` files.  Defaults to ``Path.cwd()`` when ``None``.
            config_path (Optional[Path]): Explicit path to a JSON config file.
                When ``None``, :data:`DEFAULT_CONFIG_PATH` is used.

        Returns:
            EzShellConfig: A fully initialised configuration object whose
            field values reflect the merged result of all available sources.
        """
        # 1. Load local .env files if present
        current_dir = cwd or Path.cwd()
        env_local = current_dir / ".env.local"
        env_default = current_dir / ".env"
        # Prefer .env.local over .env; override=False keeps already-set vars intact
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
                # Silently ignore malformed or unreadable config files so that
                # a corrupted file never prevents ezShell from starting.
                pass

        # 3. Environment variables take precedence over config file
        env_map = {
            "GROQ_API_KEY": "groq_api_key",
            "OPENAI_API_KEY": "openai_api_key",
            "ANTHROPIC_API_KEY": "anthropic_api_key",
            "EZSHELL_MODEL": "model",
            "EZSHELL_PROVIDER": "provider",
            "OLLAMA_BASE_URL": "ollama_base_url",
        }
        for env_var, field_name in env_map.items():
            val = os.environ.get(env_var)
            if val:
                data[field_name] = val

        valid_keys = {
            "groq_api_key", "model", "temperature", "max_tokens",
            "auto_suggest_fix", "stream_explanation", "max_history_items",
            "provider", "openai_api_key", "anthropic_api_key", "ollama_base_url",
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}

        return cls(**filtered_data)

    def save(self, path: Optional[Path] = None) -> None:
        """Persist the current configuration to a JSON file on disk.

        Args:
            path (Optional[Path]): Destination. Defaults to ``~/.ezshell/config.json``.

        Raises:
            OSError: If the file cannot be created or written.
        """
        target_path = path or DEFAULT_CONFIG_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    def get_effective_api_key(self) -> Optional[str]:
        """Return the API key for the currently active provider.

        Ollama is local — it requires no key and returns ``None``.

        Returns:
            Optional[str]: Active API key, or ``None``.
        """
        if self.provider == "openai":
            return self.openai_api_key or os.environ.get("OPENAI_API_KEY")
        if self.provider == "anthropic":
            return self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if self.provider == "ollama":
            return None
        # Default: groq
        return self.groq_api_key or os.environ.get("GROQ_API_KEY")

    def get_effective_model(self) -> str:
        """Return the model name to use for the active provider.

        If :attr:`model` is still the Groq default and the provider has
        changed, returns the canonical default for that provider.

        Returns:
            str: Model identifier for the active provider.
        """
        if self.model == DEFAULT_MODEL and self.provider in PROVIDER_DEFAULT_MODELS:
            return PROVIDER_DEFAULT_MODELS[self.provider]
        return self.model


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_CONFIG_DIR",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_MODEL",
    "SUPPORTED_PROVIDERS",
    "PROVIDER_DEFAULT_MODELS",
    "EzShellConfig",
]
