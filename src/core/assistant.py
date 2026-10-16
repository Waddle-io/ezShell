"""
Core assistant module for ezShell — orchestrates LLM-based shell diagnostics and chat.

This module provides three main capabilities:
1. **Error diagnosis** (``ShellAssistant.diagnose_failure``): analyses a failed shell command,
   queries the Groq LLM, and returns a structured ``DiagnosticResult`` with a suggested fix.
2. **Natural-language queries** (``ShellAssistant.ask``): answers free-form terminal questions
   and returns a structured ``AskResult``.
3. **Multi-turn chat** (``ChatSession``): maintains a growing message history for an interactive
   conversation with context-aware system-environment injection.

All LLM responses are expected to be JSON objects.  ``extract_json_payload`` handles cases
where the model wraps the payload in markdown fences or adds surrounding prose.

---

Module principal de l'assistant ezShell — orchestre les diagnostics de shell et le chat via LLM.

Ce module fournit trois capacités principales :
1. **Diagnostic d'erreur** (``ShellAssistant.diagnose_failure``) : analyse une commande shell
   échouée, interroge le LLM Groq et retourne un ``DiagnosticResult`` structuré avec un
   correctif suggéré.
2. **Requêtes en langage naturel** (``ShellAssistant.ask``) : répond à des questions libres
   sur le terminal et retourne un ``AskResult`` structuré.
3. **Chat multi-tours** (``ChatSession``) : maintient un historique de messages croissant pour
   une conversation interactive avec injection du contexte système.

Toutes les réponses LLM sont censées être des objets JSON. ``extract_json_payload`` gère les
cas où le modèle enveloppe la charge utile dans des balises markdown ou ajoute du texte autour.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from src.core.config import EzShellConfig
from src.core.context import SystemContext
from src.core.groq_client import GroqClient
from src.core.prompts import (
    ASK_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_ask_prompt,
    build_chat_system_prompt,
    build_error_analysis_prompt,
)
from src.core.safety import RiskLevel, SafetyGuard, SafetyReport

__all__ = [
    "DiagnosticResult",
    "AskResult",
    "ChatMessageResult",
    "ShellAssistant",
    "ChatSession",
    "extract_json_payload",
    "extract_bash_commands",
]


@dataclass
class DiagnosticResult:
    """Structured result returned by ``ShellAssistant.diagnose_failure``.

    Attributes:
        command: The original shell command that failed.
        exit_code: The non-zero exit code returned by the failed command.
        summary: A single-sentence human-readable summary of the failure reason.
        explanation: A short markdown-formatted explanation of the root cause
            (typically 2–3 sentences).
        suggested_fix: An exact, executable shell command that should resolve
            the failure, or ``None`` if no automated fix is applicable.
        fix_description: A brief prose description of what ``suggested_fix`` does
            (e.g. ``"Installs the missing development headers"``).
        safety_report: A ``SafetyReport`` produced by ``SafetyGuard.inspect`` for
            ``suggested_fix``, or ``None`` when no fix was suggested.
    """

    command: str
    exit_code: int
    summary: str
    explanation: str
    suggested_fix: Optional[str]
    fix_description: str
    safety_report: Optional[SafetyReport] = None


@dataclass
class AskResult:
    """Structured result returned by ``ShellAssistant.ask``.

    Attributes:
        question: The original natural-language question posed by the user.
        summary: A short title or one-line summary of the answer.
        explanation: A brief technical explanation of the answer in markdown
            format (typically 2–3 sentences).
        suggested_fix: An exact shell command that answers or demonstrates the
            solution, or ``None`` if a command is not applicable.
        fix_description: A brief prose description of what ``suggested_fix`` does.
        safety_report: A ``SafetyReport`` produced by ``SafetyGuard.inspect`` for
            ``suggested_fix``, or ``None`` when no command was suggested.
    """

    question: str
    summary: str
    explanation: str
    suggested_fix: Optional[str]
    fix_description: str
    safety_report: Optional[SafetyReport] = None


@dataclass
class ChatMessageResult:
    """Structured result returned by ``ChatSession.send_message``.

    Attributes:
        content: The full raw text of the assistant's response, which may contain
            markdown-formatted prose, lists, and code blocks.
        suggested_commands: A list of shell commands extracted from bash/sh/zsh
            fenced code blocks within ``content``.
        safety_reports: A ``SafetyReport`` for each entry in ``suggested_commands``,
            in the same order, produced by ``SafetyGuard.inspect``.
    """

    content: str
    suggested_commands: list[str]
    safety_reports: list[SafetyReport]


def extract_json_payload(raw_response: str) -> dict:
    """Extract and parse a JSON object from a raw LLM completion string.

    The LLM may return the JSON payload wrapped in markdown code fences,
    preceded by conversational text, or as a bare JSON string.  This function
    applies three successive parsing strategies and falls back to a minimal
    structure if all strategies fail.

    Parsing strategies (applied in order):
    1. **Direct parse** — strip surrounding whitespace and attempt
       ``json.loads`` immediately.
    2. **Markdown fence extraction** — search for a ````` ```json … ``` `````
       or ```` ``` … ``` ```` block using a regex and parse its contents.
    3. **Brace extraction** — locate the first ``{`` and last ``}`` in the
       string and attempt to parse the substring they delimit.

    Args:
        raw_response: The raw completion string returned by the LLM, which may
            or may not be a valid standalone JSON document.

    Returns:
        A ``dict`` parsed from the JSON payload embedded in ``raw_response``.
        If all three parsing strategies fail, returns a fallback dict with the
        keys ``summary``, ``explanation``, ``suggested_fix``, and
        ``fix_description``, where ``explanation`` contains the raw response
        text verbatim.

    Notes:
        The function intentionally swallows all ``json.JSONDecodeError``
        exceptions — failures at each stage are silent so that the next
        strategy is attempted.  Only the final fallback surfaces the raw text
        to the caller.
    """
    clean = raw_response.strip()

    # Strategy 1: attempt a direct JSON parse of the stripped response
    try:
        return json.loads(clean)
    except Exception:
        pass

    # Strategy 2: extract the body of a markdown fenced code block (```json … ```)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Strategy 3: find the outermost pair of curly braces and parse the slice
    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(clean[start : end + 1])
        except Exception:
            pass

    # Fallback: return a minimal structure so callers always receive a dict
    return {
        "summary": "Diagnostic completed",
        "explanation": clean,
        "suggested_fix": None,
        "fix_description": "",
    }


class ShellAssistant:
    """Orchestrates error analysis, prompt generation, LLM querying, and safety validation.

    ``ShellAssistant`` is the primary entry-point for one-shot interactions with
    the Groq LLM.  It handles two use-cases:

    * **Failure diagnosis** (``diagnose_failure``): given a failed shell command
      and its output, it constructs a structured prompt, queries the LLM, parses
      the JSON response, and runs the suggested fix through ``SafetyGuard``.
    * **Natural-language queries** (``ask``): given a free-form question about the
      terminal or system, it follows the same pipeline using a different system
      prompt tuned for question-answering.

    The underlying ``GroqClient`` is instantiated lazily on first use so that
    the API key is not resolved until it is actually needed.
    """

    def __init__(
        self,
        config: Optional[EzShellConfig] = None,
        client: Optional[GroqClient] = None,
    ):
        """Initialise the ShellAssistant.

        Args:
            config: An ``EzShellConfig`` instance that supplies model settings and
                API key resolution.  When ``None``, configuration is loaded from
                the default sources via ``EzShellConfig.load()``.
            client: A pre-constructed ``GroqClient`` to use for LLM calls.  When
                ``None``, a client is created lazily on first access via the
                ``client`` property.  Pass an explicit client in tests to inject
                a mock or stub.
        """
        self.config = config or EzShellConfig.load()
        self._client = client

    @property
    def client(self) -> GroqClient:
        """Return the active ``GroqClient``, creating one lazily if necessary.

        The client is constructed on first access so that the API key lookup
        (which may read environment variables or config files) is deferred until
        an actual LLM call is about to be made.

        Returns:
            The shared ``GroqClient`` instance for this assistant.
        """
        if self._client is None:
            api_key = self.config.get_effective_api_key()
            self._client = GroqClient(api_key=api_key)
        return self._client

    def diagnose_failure(
        self,
        command: str,
        exit_code: int,
        error_output: str,
        context: SystemContext,
    ) -> DiagnosticResult:
        """Diagnose a failed terminal command and suggest a fix.

        Builds a structured prompt that includes the failed command, its exit
        code, stderr/stdout output, and system-environment metadata.  Sends the
        prompt to the Groq LLM, parses the JSON response, and validates any
        suggested fix command with ``SafetyGuard``.

        Args:
            command: The exact shell command string that was executed and failed.
            exit_code: The non-zero integer exit code returned by the command.
            error_output: Combined stderr (and optionally stdout) text produced
                by the failed command.  May be an empty string if the command
                produced no output before exiting.
            context: A ``SystemContext`` snapshot containing OS, shell, package
                manager, working directory, and other environment details that
                are embedded in the prompt to make the fix OS-specific.

        Returns:
            A ``DiagnosticResult`` populated with the LLM's diagnosis.
            The ``safety_report`` field is ``None`` when no fix is suggested.

        Raises:
            groq.APIError: If the underlying Groq API call fails (network error,
                auth failure, rate-limit, etc.).
        """
        prompt = build_error_analysis_prompt(
            command=command,
            exit_code=exit_code,
            error_output=error_output,
            system_context=context.to_prompt_context(),
        )

        raw_completion = self.client.complete(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        data = extract_json_payload(raw_completion)

        summary = data.get("summary", f"Command failed with exit code {exit_code}")
        explanation = data.get("explanation", raw_completion)
        suggested_fix = data.get("suggested_fix")
        fix_description = data.get("fix_description", "")

        # Only run safety inspection when a non-empty fix command was provided
        safety_report = None
        if suggested_fix and isinstance(suggested_fix, str) and suggested_fix.strip():
            suggested_fix = suggested_fix.strip()
            safety_report = SafetyGuard.inspect(suggested_fix)

        return DiagnosticResult(
            command=command,
            exit_code=exit_code,
            summary=summary,
            explanation=explanation,
            suggested_fix=suggested_fix,
            fix_description=fix_description,
            safety_report=safety_report,
        )

    def ask(self, question: str, context: SystemContext) -> AskResult:
        """Answer a user's natural-language terminal query.

        Constructs a prompt from the user's question and system-environment
        metadata, queries the Groq LLM with the ask-oriented system prompt,
        and parses the JSON response into an ``AskResult``.  Any suggested
        command is inspected by ``SafetyGuard`` before being returned.

        Args:
            question: The free-form natural-language question entered by the
                user (e.g. ``"how do I recursively find files larger than 1 GB?"``).
            context: A ``SystemContext`` snapshot providing OS, shell, working
                directory, and other metadata used to tailor the answer.

        Returns:
            An ``AskResult`` containing the LLM's answer, an optional executable
            command, and a ``SafetyReport`` for that command when one is present.

        Raises:
            groq.APIError: If the underlying Groq API call fails.
        """
        prompt = build_ask_prompt(
            question=question,
            system_context=context.to_prompt_context(),
        )

        raw_completion = self.client.complete(
            prompt=prompt,
            system_prompt=ASK_SYSTEM_PROMPT,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        data = extract_json_payload(raw_completion)

        summary = data.get("summary", "Terminal Assistant")
        explanation = data.get("explanation", raw_completion)
        suggested_fix = data.get("suggested_fix")
        fix_description = data.get("fix_description", "")

        # Only run safety inspection when a non-empty command was provided
        safety_report = None
        if suggested_fix and isinstance(suggested_fix, str) and suggested_fix.strip():
            suggested_fix = suggested_fix.strip()
            safety_report = SafetyGuard.inspect(suggested_fix)

        return AskResult(
            question=question,
            summary=summary,
            explanation=explanation,
            suggested_fix=suggested_fix,
            fix_description=fix_description,
            safety_report=safety_report,
        )


def extract_bash_commands(text: str) -> list[str]:
    """Extract shell commands from bash/sh/zsh/shell fenced code blocks in text.

    Scans ``text`` for markdown fenced code blocks whose language tag is one of
    ``bash``, ``sh``, ``shell``, or ``zsh`` (case-insensitive) and returns the
    trimmed body of each block.  Blocks whose content starts with ``#`` (i.e.
    comment-only blocks) are silently skipped.

    Args:
        text: A string that may contain zero or more markdown fenced code
            blocks, typically the raw assistant response from ``ChatSession``.

    Returns:
        A list of non-empty command strings extracted from matching code blocks,
        in the order they appear in ``text``.  Returns an empty list when no
        matching blocks are found.
    """
    matches = re.findall(
        r"```(?:bash|sh|shell|zsh)?\s*\n(.*?)\n```",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    commands: list[str] = []
    for m in matches:
        cmd = m.strip()
        # Skip empty captures and comment-only blocks
        if cmd and not cmd.startswith("#"):
            commands.append(cmd)
    return commands


class ChatSession:
    """Manage an ongoing multi-turn interactive conversation with the Groq LLM.

    ``ChatSession`` maintains a growing ``messages`` list that mirrors the
    OpenAI-compatible chat-completion message format (``{"role": ..., "content":
    ...}``).  The first message is always a system prompt built from
    ``CHAT_SYSTEM_PROMPT`` combined with live system-environment metadata.

    Each call to ``send_message`` appends the user's message, obtains an
    assistant reply via ``GroqClient.chat``, appends the reply, extracts any
    bash commands from the reply, and wraps everything in a
    ``ChatMessageResult``.

    Calling ``clear`` resets the history to just the initial system message,
    effectively starting a fresh conversation without creating a new session
    object.
    """

    def __init__(
        self,
        config: Optional[EzShellConfig] = None,
        client: Optional[GroqClient] = None,
        context: Optional[SystemContext] = None,
    ):
        """Initialise the ChatSession and inject the system environment prompt.

        Args:
            config: An ``EzShellConfig`` instance that supplies model settings
                and API key resolution.  When ``None``, configuration is loaded
                from the default sources via ``EzShellConfig.load()``.
            client: A pre-constructed ``GroqClient``.  When ``None``, a client
                is created lazily on first access.  Pass an explicit client in
                tests to inject a mock or stub.
            context: A ``SystemContext`` snapshot whose metadata is embedded in
                the system prompt so the LLM can give OS-specific advice.  When
                ``None``, context is collected from the live environment via
                ``SystemContext.collect()``.
        """
        self.config = config or EzShellConfig.load()
        self._client = client
        self.context = context or SystemContext.collect()
        # ``messages`` will be populated by ``_init_session``
        self.messages: list[dict[str, str]] = []
        self._init_session()

    @property
    def client(self) -> GroqClient:
        """Return the active ``GroqClient``, creating one lazily if necessary.

        Returns:
            The shared ``GroqClient`` instance for this chat session.
        """
        if self._client is None:
            api_key = self.config.get_effective_api_key()
            self._client = GroqClient(api_key=api_key)
        return self._client

    def _init_session(self) -> None:
        """Initialise (or reinitialise) the message history with the system prompt.

        Builds the context-aware system prompt by combining ``CHAT_SYSTEM_PROMPT``
        with the serialised ``SystemContext`` and stores it as the sole entry in
        ``self.messages``.  Called once during ``__init__`` and again by
        ``clear`` to reset the conversation.
        """
        sys_prompt = build_chat_system_prompt(self.context.to_prompt_context())
        # Replace the entire history with just the system message
        self.messages = [{"role": "system", "content": sys_prompt}]

    def send_message(self, user_text: str) -> ChatMessageResult:
        """Send a user message and receive the assistant's reply.

        Appends ``user_text`` to the message history, calls ``GroqClient.chat``
        with the full history, appends the assistant's reply, and then extracts
        any shell commands embedded in bash fenced code blocks within the reply.
        Each extracted command is also passed through ``SafetyGuard.inspect``.

        Args:
            user_text: The user's input message for this turn of the
                conversation.

        Returns:
            A ``ChatMessageResult`` containing the full assistant reply text,
            the list of extracted shell commands, and a parallel list of
            ``SafetyReport`` objects (one per command).

        Raises:
            groq.APIError: If the underlying Groq API call fails.
        """
        self.messages.append({"role": "user", "content": user_text})

        response_text = self.client.chat(
            messages=self.messages,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        # Persist the assistant reply so subsequent turns have full context
        self.messages.append({"role": "assistant", "content": response_text})

        commands = extract_bash_commands(response_text)
        # Inspect each suggested command for destructive or risky patterns
        safety_reports = [SafetyGuard.inspect(cmd) for cmd in commands]

        return ChatMessageResult(
            content=response_text,
            suggested_commands=commands,
            safety_reports=safety_reports,
        )

    def clear(self) -> None:
        """Reset the conversation history while preserving the system environment.

        Discards all user and assistant messages and re-injects the system
        prompt so the next ``send_message`` call starts a fresh conversation
        in the same ``SystemContext``.
        """
        self._init_session()
