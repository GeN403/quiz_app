"""Masking and error helpers."""

from __future__ import annotations

from typing import Any

from .constants import EMAIL_RE, PHONE_RE, TOKEN_RE


def sanitize_text(text: str) -> str:
    masked = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    masked = PHONE_RE.sub("[REDACTED_PHONE]", masked)
    masked = TOKEN_RE.sub("[REDACTED_TOKEN]", masked)
    return masked


def contains_sensitive(text: str) -> bool:
    return bool(EMAIL_RE.search(text) or PHONE_RE.search(text) or TOKEN_RE.search(text))


def new_error(error_code: str, message: str, retryable: bool, action: str) -> dict[str, Any]:
    return {
        "error_code": error_code,
        "message": sanitize_text(message),
        "retryable": retryable,
        "recommended_next_action": action,
    }
