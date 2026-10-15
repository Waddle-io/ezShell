from __future__ import annotations

import os
from typing import Generator, Optional
import groq
from groq import Groq


class GroqClientError(Exception):
    """Base exception for Groq client errors."""
    pass


class GroqAuthError(GroqClientError):
    """Raised when API key is missing or invalid."""
    pass


class GroqRateLimitError(GroqClientError):
    """Raised when rate limit is exceeded."""
    pass


class GroqConnectionError(GroqClientError):
    """Raised on connection or network failure."""
    pass


class GroqClient:
    """Wrapper around the official Groq SDK for ezShell."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise GroqAuthError(
                "No Groq API key found. Please set GROQ_API_KEY in your environment, "
                ".env.local, or ~/.ezshell/config.json."
            )
        self.timeout = timeout
        self._client: Optional[Groq] = None

    @property
    def client(self) -> Groq:
        if self._client is None:
            self._client = Groq(api_key=self.api_key, timeout=self.timeout)
        return self._client

    def validate_connection(self) -> bool:
        """Tests if the API key and connection are valid."""
        try:
            # Simple minimal completion to verify credentials
            self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except (groq.AuthenticationError, groq.PermissionDeniedError):
            return False
        except Exception:
            return False

    def complete(
        self,
        prompt: str,
        system_prompt: str,
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Executes a chat completion call and returns the text content."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except groq.AuthenticationError as e:
            raise GroqAuthError(f"Groq authentication failed: {e}") from e
        except groq.RateLimitError as e:
            raise GroqRateLimitError(f"Groq rate limit exceeded: {e}") from e
        except groq.APIConnectionError as e:
            raise GroqConnectionError(f"Network error connecting to Groq API: {e}") from e
        except groq.APIStatusError as e:
            raise GroqClientError(f"Groq API error (status {e.status_code}): {e}") from e
        except Exception as e:
            raise GroqClientError(f"Unexpected Groq error: {e}") from e

    def stream_complete(
        self,
        prompt: str,
        system_prompt: str,
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Generator[str, None, None]:
        """Streams chat completion chunks."""
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
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

