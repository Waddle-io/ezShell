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


@dataclass
class DiagnosticResult:
    command: str
    exit_code: int
    summary: str
    explanation: str
    suggested_fix: Optional[str]
    fix_description: str
    safety_report: Optional[SafetyReport] = None


@dataclass
class AskResult:
    question: str
    summary: str
    explanation: str
    suggested_fix: Optional[str]
    fix_description: str
    safety_report: Optional[SafetyReport] = None


@dataclass
class ChatMessageResult:
    content: str
    suggested_commands: list[str]
    safety_reports: list[SafetyReport]


def extract_json_payload(raw_response: str) -> dict:
    """Extracts JSON object from text, handling markdown fences and edge cases."""
    clean = raw_response.strip()

    # Try direct parse
    try:
        return json.loads(clean)
    except Exception:
        pass

    # Try removing markdown code blocks (```json ... ```)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Try finding outermost curly brackets
    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(clean[start : end + 1])
        except Exception:
            pass

    # Fallback structure if JSON parsing completely fails
    return {
        "summary": "Diagnostic completed",
        "explanation": clean,
        "suggested_fix": None,
        "fix_description": "",
    }


class ShellAssistant:
    """Orchestrates error analysis, prompt generation, LLM querying, and safety validation."""

    def __init__(self, config: Optional[EzShellConfig] = None, client: Optional[GroqClient] = None):
        self.config = config or EzShellConfig.load()
        self._client = client

    @property
    def client(self) -> GroqClient:
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
        """Diagnoses a failed terminal command and suggests a fix."""
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
        """Answers a user's natural language terminal query."""
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
    """Extracts shell/bash commands from markdown code blocks in text."""
    matches = re.findall(
        r"```(?:bash|sh|shell|zsh)?\s*\n(.*?)\n```",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    commands: list[str] = []
    for m in matches:
        cmd = m.strip()
        if cmd and not cmd.startswith("#"):
            commands.append(cmd)
    return commands


class ChatSession:
    """Manages an ongoing multi-turn interactive conversation with Groq."""

    def __init__(
        self,
        config: Optional[EzShellConfig] = None,
        client: Optional[GroqClient] = None,
        context: Optional[SystemContext] = None,
    ):
        self.config = config or EzShellConfig.load()
        self._client = client
        self.context = context or SystemContext.collect()
        self.messages: list[dict[str, str]] = []
        self._init_session()

    @property
    def client(self) -> GroqClient:
        if self._client is None:
            api_key = self.config.get_effective_api_key()
            self._client = GroqClient(api_key=api_key)
        return self._client

    def _init_session(self) -> None:
        sys_prompt = build_chat_system_prompt(self.context.to_prompt_context())
        self.messages = [{"role": "system", "content": sys_prompt}]

    def send_message(self, user_text: str) -> ChatMessageResult:
        """Sends a user message, receives the AI response, and extracts any suggested commands."""
        self.messages.append({"role": "user", "content": user_text})

        response_text = self.client.chat(
            messages=self.messages,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        self.messages.append({"role": "assistant", "content": response_text})

        commands = extract_bash_commands(response_text)
        safety_reports = [SafetyGuard.inspect(cmd) for cmd in commands]

        return ChatMessageResult(
            content=response_text,
            suggested_commands=commands,
            safety_reports=safety_reports,
        )

    def clear(self) -> None:
        """Resets the conversation history while preserving the system environment."""
        self._init_session()

