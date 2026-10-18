"""
ezShell LLM Client Abstraction
================================
Defines the ``LLMClient`` Protocol — the common interface all provider
clients must implement — and the ``create_client()`` factory that
instantiates the right client based on the active ``EzShellConfig``.

Supported providers: groq, openai, anthropic, ollama.

---

Abstraction du client LLM d'ezShell
=====================================
Définit le Protocole ``LLMClient`` (interface commune à tous les providers)
et la fabrique ``create_client()`` qui instancie le bon client en fonction
de la configuration active.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generator, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.core.config import EzShellConfig


@runtime_checkable
class LLMClient(Protocol):
    """Common interface that every provider client must satisfy.

    All methods mirror the ``GroqClient`` interface so that ``ShellAssistant``
    and ``ChatSession`` remain provider-agnostic.
    """

    def validate_connection(self) -> bool:
        """Return ``True`` if the provider is reachable and the key is valid."""
        ...

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Multi-turn chat completion — returns the full assistant reply."""
        ...

    def complete(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Single-turn completion — returns the full assistant reply."""
        ...

    def stream_complete(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Generator[str, None, None]:
        """Streaming completion — yields text chunks as they arrive."""
        ...


def create_client(config: "EzShellConfig") -> LLMClient:
    """Instantiate the correct LLM client for the active provider.

    Args:
        config (EzShellConfig): Fully loaded configuration object.

    Returns:
        LLMClient: A ready-to-use client instance.

    Raises:
        ValueError: If ``config.provider`` is not a recognised value.
        ImportError: If the required optional package for the chosen
            provider is not installed (e.g. ``openai``, ``anthropic``).
    """
    provider = config.provider

    if provider == "groq":
        from src.core.groq_client import GroqClient
        return GroqClient(api_key=config.get_effective_api_key())

    if provider == "openai":
        from src.core.openai_client import OpenAIClient
        return OpenAIClient(api_key=config.get_effective_api_key())

    if provider == "anthropic":
        from src.core.anthropic_client import AnthropicClient
        return AnthropicClient(api_key=config.get_effective_api_key())

    if provider == "ollama":
        from src.core.ollama_client import OllamaClient
        return OllamaClient(base_url=config.ollama_base_url)

    raise ValueError(
        f"Unknown provider '{provider}'. "
        f"Supported providers: groq, openai, anthropic, ollama."
    )


__all__ = ["LLMClient", "create_client"]

