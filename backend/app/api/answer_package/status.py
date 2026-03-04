"""Warnings/errors/status helpers."""

from __future__ import annotations

from typing import Any

from .constants import ALLOWED_RECOMMENDED_NEXT_ACTIONS, TOP_LEVEL_REQUIRED_FIELDS
from .sanitize import new_error


def calculate_warning_metrics(claims: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    total_claims = len(claims)
    if total_claims == 0:
        ratio = 1.0
    else:
        unverifiable_claims = sum(
            1
            for claim in claims
            if not any(evidence.get("evidence_status") == "ok" for evidence in claim.get("evidences", []))
        )
        ratio = unverifiable_claims / total_claims

    warning_level = "high" if ratio >= 0.30 else "none"
    warnings = {
        "warning_level": warning_level,
        "messages": ["unverifiable_evidence_ratio ? 0.30 ??"] if warning_level == "high" else [],
    }
    thresholds = {
        "unverifiable_evidence_ratio": ratio,
        "high_warning_ratio": 0.30,
        "formula": "unverifiable_claims/total_claims",
    }
    return warnings, thresholds


def build_error_envelope(final_state: dict[str, Any]) -> list[dict[str, Any]]:
    code = final_state.get("error_code")
    if not code:
        return []
    status = int(final_state.get("error_status") or 500)
    retryable = status in {429, 500, 503, 504}
    action = "retry_with_new_sources" if retryable else "manual_review"
    return [new_error(str(code), str(code), retryable, action)]


def normalize_recommended_actions(errors: list[dict[str, Any]]) -> None:
    for err in errors:
        if err["recommended_next_action"] not in ALLOWED_RECOMMENDED_NEXT_ACTIONS:
            err["recommended_next_action"] = "manual_review"


def missing_required_fields(payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for key in TOP_LEVEL_REQUIRED_FIELDS:
        value = payload.get(key)
        if value is None:
            missing.append(key)
            continue
        if key in {"question", "answer", "claims", "logs"} and not value:
            missing.append(key)
            continue
        if key == "alternative_answer_policy" and isinstance(value, dict) and not value.get("rule_text"):
            missing.append(key)
    return missing


def determine_status(
    final_state: dict[str, Any],
    missing_fields: list[str],
    errors: list[dict[str, Any]],
) -> str:
    if final_state.get("error_code"):
        return "failed"
    if missing_fields or errors:
        return "partial"
    return "complete"
