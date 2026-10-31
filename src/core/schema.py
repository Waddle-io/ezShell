"""Schéma de la réponse du modèle (DEVELOPMENT.md §5.2 / §8), validé avec pydantic.

On n'affiche jamais une réponse non validée : `parse_response` lève
`InvalidResponse` et l'appelant décide (un nouvel essai, puis échec propre).
"""

from __future__ import annotations

import json
import re
from typing import List, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from src.core.sanitize import strip_control

Risk = Literal["low", "medium", "high"]
Confidence = Literal["low", "medium", "high"]


class InvalidResponse(ValueError):
    """La réponse du modèle n'est pas un JSON conforme au schéma."""


class AskResponse(BaseModel):
    command: str = ""
    explanation: str = Field(default="", max_length=1200)
    cause: str = Field(default="", max_length=800)
    risk: Risk = "medium"
    risk_reason: str = Field(default="", max_length=400)
    assumptions: List[str] = Field(default_factory=list, max_length=8)
    confidence: Confidence = "medium"

    @field_validator("explanation", "cause", "risk_reason", mode="before")
    @classmethod
    def _clean_text(cls, v):
        return strip_control(str(v or ""), keep_newlines=True).strip()

    @field_validator("assumptions", mode="before")
    @classmethod
    def _clean_list(cls, v):
        if not isinstance(v, list):
            return []
        return [strip_control(str(x), keep_newlines=False).strip() for x in v][:8]


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    m = _FENCE.search(raw)
    if m:
        raw = m.group(1).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise InvalidResponse("aucun objet JSON dans la réponse")
    return raw[start : end + 1]


def parse_response(raw: str) -> AskResponse:
    try:
        return AskResponse.model_validate(json.loads(_extract_json(raw)))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise InvalidResponse(str(exc)) from exc
