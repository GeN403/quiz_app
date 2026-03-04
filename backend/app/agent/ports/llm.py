"""LLM port definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMPortError(Exception):
    """Normalized error emitted by LLM adapters."""

    error_code: str
    status_code: int
    message: str


class LLMPort(Protocol):
    """Boundary interface for LLM text generation."""

    def invoke(self, prompt: str) -> str:
        """Invoke LLM and return plain text response."""
