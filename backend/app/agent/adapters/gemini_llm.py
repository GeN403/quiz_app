"""Gemini adapter implementing LLMPort."""

from __future__ import annotations

from dataclasses import dataclass

from google.api_core import exceptions as google_exceptions
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.ports.llm import LLMPort, LLMPortError


@dataclass(frozen=True)
class GeminiLLMConfig:
    model: str = "gemini-2.0-flash-lite"
    temperature: float | None = None
    max_tokens: int | None = None


class GeminiLLMAdapter(LLMPort):
    """Thin adapter around ChatGoogleGenerativeAI with normalized errors."""

    def __init__(self, api_key: str, config: GeminiLLMConfig | None = None):
        self._api_key = api_key
        self._config = config or GeminiLLMConfig()

    def _build_llm(self) -> ChatGoogleGenerativeAI:
        kwargs: dict[str, object] = {
            "model": self._config.model,
            "google_api_key": self._api_key,
        }
        if self._config.temperature is not None:
            kwargs["temperature"] = self._config.temperature
        if self._config.max_tokens is not None:
            kwargs["max_tokens"] = self._config.max_tokens
        return ChatGoogleGenerativeAI(**kwargs)

    def invoke(self, prompt: str) -> str:
        try:
            response = self._build_llm().invoke(prompt)
            content = getattr(response, "content", None)
            if isinstance(content, str):
                return content
            text = getattr(response, "text", None)
            if isinstance(text, str):
                return text
            raise LLMPortError(
                error_code="GEMINI_EMPTY_RESPONSE",
                status_code=502,
                message="LLM returned empty response payload",
            )
        except google_exceptions.Unauthenticated as exc:
            raise LLMPortError("GEMINI_API_KEY_INVALID", 401, str(exc)) from exc
        except google_exceptions.PermissionDenied as exc:
            raise LLMPortError("GEMINI_API_KEY_PERMISSION_DENIED", 403, str(exc)) from exc
        except google_exceptions.ResourceExhausted as exc:
            raise LLMPortError("GEMINI_RATE_LIMIT", 429, str(exc)) from exc
        except (google_exceptions.ServiceUnavailable, google_exceptions.InternalServerError) as exc:
            raise LLMPortError("GEMINI_SERVICE_UNAVAILABLE", 503, str(exc)) from exc
        except google_exceptions.DeadlineExceeded as exc:
            raise LLMPortError("GEMINI_TIMEOUT", 504, str(exc)) from exc
        except LLMPortError:
            raise
        except Exception as exc:  # pragma: no cover
            raise LLMPortError("GEMINI_SERVICE_UNAVAILABLE", 503, str(exc)) from exc
