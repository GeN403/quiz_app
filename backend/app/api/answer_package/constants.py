"""Answer package constants."""

from __future__ import annotations

import re

ALLOWED_CLAIM_TYPES = {"fact", "definition", "number", "time", "other"}
ALLOWED_EVIDENCE_STATUSES = {
    "ok",
    "fetch_failed",
    "parse_failed",
    "paywalled",
    "blocked",
    "unknown",
}
ALLOWED_ACTION_TYPES = {
    "search",
    "fetch",
    "extract",
    "decompose",
    "verify",
    "rewrite",
    "packaging",
}
ALLOWED_RECOMMENDED_NEXT_ACTIONS = {
    "retry_with_new_sources",
    "rewrite_question",
    "manual_review",
    "change_topic",
}

TOP_LEVEL_REQUIRED_FIELDS = [
    "question",
    "answer",
    "claims",
    "alternative_answer_policy",
    "logs",
    "status",
    "package_id",
    "correlation_id",
]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b\d{2,4}[- ]\d{2,4}[- ]\d{3,4}\b")
TOKEN_RE = re.compile(r"(?i)bearer\s+[a-z0-9._\-]+")
