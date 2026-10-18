"""
ezShell Groq API Client
========================
This module wraps the official ``groq`` Python SDK to provide a thin,
opinionated interface for the language-model calls that power ezShell.
It surfaces a minimal API — :meth:`GroqClient.chat`,
:meth:`GroqClient.complete`, and :meth:`GroqClient.stream_complete` — and
translates every ``groq`` SDK exception into a narrow hierarchy of
application-specific errors so that callers never need to import from
``groq`` directly.

The underlying :class:`groq.Groq` SDK client is created lazily on first use
and reused for subsequent calls, avoiding redundant TCP handshakes.

Exception hierarchy
-------------------
::

    GroqClientError          (base — unexpected / uncategorised errors)
    ├── GroqAuthError        (missing or invalid API key)
    ├── GroqRateLimitError   (quota exceeded)
    └── GroqConnectionError  (network / DNS / timeout failure)

Usage example::

    from ezShell.src.core.groq_client import GroqClient

    client = GroqClient(api_key="gsk_...")
    reply = client.complete(
        prompt="List the files in /tmp",
        system_prompt="You are a helpful shell assistant.",
    )
    print(reply)

---

Client Groq pour ezShell
==========================
Ce module encapsule le SDK Python officiel ``groq`` afin d'exposer une
interface légère et ciblée pour les appels au modèle de langage utilisés
par ezShell.  Il traduit chaque exception du SDK en une hiérarchie
d'erreurs propre à l'application, de sorte que les appelants n'aient
jamais à importer directement depuis ``groq``.
"""

from __future__ import annotations

import os
from typing import Generator, Optional

import groq
from groq import Groq

from .config import DEFAULT_MODEL

# ---------------------------------------------------------------------------
# Application-level exception hierarchy
# ---------------------------------------------------------------------------


class GroqClientError(Exception):
    """Base exception for all errors raised by :class:`GroqClient`.

    Catch this class to handle any Groq-related failure regardless of the
    specific root cause.  More specific sub-classes are also available for
    callers that need fine-grained error handling.
    """


class GroqAuthError(GroqClientError):
    """Raised when API key is missing, malformed, or rejected by the server.

    This exception is raised in two scenarios:

    * At construction time when no API key can be found in either the
      constructor argument or the ``GROQ_API_KEY`` environment variable.
    * At request time when the Groq API returns an ``AuthenticationError``
      or ``PermissionDeniedError`` (e.g. the key has been revoked).
    """


class GroqRateLimitError(GroqClientError):
    """Raised when the Groq API rate limit or token quota is exceeded.

    Callers should implement back-off / retry logic when catching this
    exception, or prompt the user to wait before retrying.
    """


class GroqConnectionError(GroqClientError):
    """Raised on network-level failures when contacting the Groq API.

    Covers DNS resolution failures, TCP connection refusal, TLS errors, and
    request timeouts.  The underlying :class:`groq.APIConnectionError` is
    chained as the ``__cause__`` for inspection.
    """


# ---------------------------------------------------------------------------
# Main client class
# ---------------------------------------------------------------------------


class GroqClient:
    """Thin, opinionated wrapper around the official Groq SDK for ezShell.

    The client is initialised with an API key and an optional timeout, then
    exposes three completion methods:

    * :meth:`chat` — multi-turn conversation with an explicit message list
    * :meth:`complete` — single prompt + system-prompt convenience wrapper
    * :meth:`stream_complete` — streaming generator variant of :meth:`complete`

    The underlying :class:`groq.Groq` SDK instance is created lazily via the
    :attr:`client` property and reused across calls.

    Example::

        client = GroqClient()  # reads GROQ_API_KEY from environment
        for chunk in client.stream_complete(
            prompt="Explain what `ls -la` does.",
            system_prompt="You are a concise shell tutor.",
        ):
            print(chunk, end="", flush=True)

    Args:
        api_key (Optional[str]): Groq platform API key.  When ``None``,
            the ``GROQ_API_KEY`` environment variable is used as a fallback.
        timeout (float): HTTP request timeout in seconds applied to every
            API call.  Default is ``15.0``.

    Raises:
        GroqAuthError: If no API key is available from either *api_key* or
            the environment at construction time.
    """

    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0):
        # Prefer the explicit argument; fall back to the environment variable
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise GroqAuthError(
                "No Groq API key found. Please set GROQ_API_KEY in your environment, "
                ".env.local, or ~/.ezshell/config.json."
            )
        self.timeout = timeout
        # Deferred until first use to avoid creating network connections at import time
        self._client: Optional[Groq] = None

    @property
    def client(self) -> Groq:
        """Lazily initialised :class:`groq.Groq` SDK instance.

        The instance is created on the first property access and cached for
        all subsequent calls, giving connection reuse without requiring the
        caller to manage the lifecycle explicitly.

        Returns:
            Groq: A configured ``groq.Groq`` client ready to make API calls.
        """
        if self._client is None:
            self._client = Groq(api_key=self.api_key, timeout=self.timeout)
        return self._client

    def validate_connection(self) -> bool:
        """Probe the Groq API to verify that the key and network are working.

        Sends a minimal one-token request to avoid unnecessary token
        consumption.  Any response — even an error response — from the server
        indicates network connectivity; only authentication and permission
        errors cause the method to return ``False``.

        Returns:
            bool: ``True`` if the API key is accepted and a response is
            received; ``False`` if authentication fails or any exception is
            raised (including network errors).
        """
        try:
            self.client.models.list()
            return True
        except (groq.AuthenticationError, groq.PermissionDeniedError):
            # Key is present but rejected by the server
            return False
        except Exception:
            # Network errors, timeouts, or other unexpected failures
            return False

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str = DEFAULT_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Send a multi-turn conversation to the Groq API and return the reply.

        This is the lowest-level completion method; callers supply a fully
        assembled message list, giving full control over the conversation
        history and system prompt.

        Args:
            messages (list[dict[str, str]]): Ordered list of message dicts,
                each with ``"role"`` (``"system"``, ``"user"``, or
                ``"assistant"``) and ``"content"`` keys, following the
                OpenAI Chat Completions format accepted by Groq.
            model (str): Groq model identifier to use for this request.
                Defaults to ``"openai/gpt-oss-120b"``.
            temperature (float): Sampling temperature in the range ``[0, 2]``.
                Lower values produce more focused, deterministic output.
                Defaults to ``0.2``.
            max_tokens (int): Maximum number of tokens the model may generate.
                Defaults to ``1024``.

        Returns:
            str: The model's text reply, or an empty string if the API
            returns a choice with no content.

        Raises:
            GroqAuthError: If the API key is rejected by the server.
            GroqRateLimitError: If the rate limit or token quota is exceeded.
            GroqConnectionError: If a network-level error prevents the
                request from reaching the API.
            GroqClientError: For any other API error (e.g. invalid model,
                server-side 5xx, unexpected SDK exception).
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except groq.AuthenticationError as e:
            raise GroqAuthError(f"Groq authentication failed: {e}") from e
        except groq.RateLimitError as e:
            raise GroqRateLimitError(f"Groq rate limit exceeded: {e}") from e
        except groq.NotFoundError:
            # If requested model is not found on account, fallback to available chat models
            for fallback_model in ("openai/gpt-oss-20b", "qwen/qwen3.8-27b"):
                if fallback_model != model:
                    try:
                        resp = self.client.chat.completions.create(
                            model=fallback_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        return resp.choices[0].message.content or ""
                    except Exception:
                        continue
            raise GroqClientError(
                f"Groq model '{model}' not found on account and fallbacks failed."
            )
        except groq.APIConnectionError as e:
            raise GroqConnectionError(f"Network error connecting to Groq API: {e}") from e
        except groq.APIStatusError as e:
            raise GroqClientError(f"Groq API error (status {e.status_code}): {e}") from e
        except Exception as e:
            raise GroqClientError(f"Unexpected Groq error: {e}") from e

    def complete(
        self,
        prompt: str,
        system_prompt: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Execute a single-turn completion with a dedicated system prompt.

        Convenience wrapper around :meth:`chat` that constructs a two-message
        conversation (system + user) and returns the model's reply as a plain
        string.  Use :meth:`chat` directly when you need to pass a richer
        conversation history.

        Args:
            prompt (str): The user-facing instruction or question to send to
                the model.
            system_prompt (str): Instruction placed in the ``"system"`` role
                that shapes the model's behaviour for this request.
            model (str): Groq model identifier.  Defaults to
                ``"openai/gpt-oss-120b"``.
            temperature (float): Sampling temperature.  Defaults to ``0.2``.
            max_tokens (int): Maximum tokens to generate.  Defaults to
                ``1024``.

        Returns:
            str: The model's text response.

        Raises:
            GroqAuthError: Propagated from :meth:`chat`.
            GroqRateLimitError: Propagated from :meth:`chat`.
            GroqConnectionError: Propagated from :meth:`chat`.
            GroqClientError: Propagated from :meth:`chat`.
        """
        # Assemble the standard two-message format expected by the Chat API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        return self.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)

    def stream_complete(
        self,
        prompt: str,
        system_prompt: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Generator[str, None, None]:
        """Stream a completion response as an iterable of text chunks.

        Opens a server-sent-events stream to the Groq API and yields each
        content delta as it arrives, enabling the caller to display tokens
        progressively rather than waiting for the full response.  The
        generator silently skips chunks whose ``delta.content`` is ``None``
        or empty (e.g. the final ``[DONE]`` sentinel).

        Args:
            prompt (str): The user-facing instruction or question.
            system_prompt (str): Instruction placed in the ``"system"`` role.
            model (str): Groq model identifier.  Defaults to
                ``"openai/gpt-oss-120b"``.
            temperature (float): Sampling temperature.  Defaults to ``0.2``.
            max_tokens (int): Maximum tokens to generate.  Defaults to
                ``1024``.

        Yields:
            str: Successive text deltas from the model as they are received.
                Each yielded string is a partial token or word fragment;
                concatenating all yielded values produces the full response.

        Raises:
            GroqAuthError: If the API key is rejected when the stream opens.
            GroqRateLimitError: If the rate limit is exceeded.
            GroqConnectionError: If the stream cannot be established due to a
                network error.
            GroqClientError: For any other unexpected SDK exception.
        """
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,  # Enable server-sent-events streaming mode
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                # Skip empty deltas (e.g. role-only chunks and the final sentinel)
                if delta:
                    yield delta
        except groq.AuthenticationError as e:
            raise GroqAuthError(f"Groq authentication failed: {e}") from e
        except groq.RateLimitError as e:
            raise GroqRateLimitError(f"Groq rate limit exceeded: {e}") from e
        except groq.APIConnectionError as e:
            raise GroqConnectionError(f"Network error connecting to Groq API: {e}") from e
        except Exception as e:
            raise GroqClientError(f"Unexpected Groq streaming error: {e}") from e


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

__all__ = [
    "GroqClientError",
    "GroqAuthError",
    "GroqRateLimitError",
    "GroqConnectionError",
    "GroqClient",
]
