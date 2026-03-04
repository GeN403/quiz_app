"""Public builder entrypoint."""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from .claims import build_claims
from .logs import build_logs
from .policy import build_alternative_policy
from .status import (
    build_error_envelope,
    calculate_warning_metrics,
    determine_status,
    missing_required_fields,
    normalize_recommended_actions,
)


def build_answer_package(
    final_state: dict[str, Any],
    correlation_id: str,
    *,
    retention_limit: int = 500,
    retention_days: int | None = None,
) -> dict[str, Any]:
    result = dict(final_state.get("result") or {})
    env_days = os.getenv("ANSWER_PACKAGE_LOG_RETENTION_DAYS")
    if retention_days is None and env_days is not None:
        try:
            retention_days = int(env_days)
        except ValueError:
            retention_days = None

    claims, enum_errors = build_claims(
        list(final_state.get("claims") or []),
        list(final_state.get("evidence_list") or []),
    )
    package_id = f"pkg_{uuid4().hex[:12]}"

    warnings, thresholds = calculate_warning_metrics(claims)
    policy, policy_errors, policy_missing = build_alternative_policy(result)
    errors = build_error_envelope(final_state) + policy_errors + enum_errors
    normalize_recommended_actions(errors)

    logs = build_logs(
        list(final_state.get("verification_history") or []),
        correlation_id,
        package_id,
        retention_limit,
        retention_days,
    )

    payload: dict[str, Any] = {
        "package_id": package_id,
        "correlation_id": correlation_id,
        "status": "complete",  # provisional
        "missing_fields": [],
        "warnings": warnings,
        "errors": errors,
        "question": {"text": str(result.get("question", "") or "")},
        "answer": {
            "text": str(result.get("answer", "") or ""),
            "answer_type": "string",
        },
        "claims": claims,
        "alternative_answer_policy": policy,
        "thresholds": thresholds,
        "logs": logs,
    }

    payload["source"] = result.get("source", {})
    payload["explanation"] = result.get("explanation", "")
    payload["Alternative Solutions/Correctness Judgment Criteria"] = result.get(
        "Alternative Solutions/Correctness Judgment Criteria", ""
    )
    payload["verification"] = {
        "verdict": (final_state.get("verification_outcome") or {}).get("verdict", "pass"),
        "reason": (final_state.get("verification_outcome") or {}).get("reason", ""),
        "evidence_status": (final_state.get("verification_outcome") or {}).get("evidence_status", "ok"),
        "termination_reason": {
            "code": final_state.get("termination_reason_code"),
            "message": final_state.get("termination_reason_message"),
        },
        "attempts": max((int(s.get("attempt", 0)) for s in final_state.get("verification_history", []) or []), default=-1)
        + 1,
        "history": list(final_state.get("verification_history") or []),
    }

    missing = missing_required_fields(payload)
    if policy_missing and "alternative_answer_policy" not in missing:
        missing.append("alternative_answer_policy")

    payload["missing_fields"] = sorted(set(missing))
    payload["status"] = determine_status(final_state, payload["missing_fields"], payload["errors"])

    return payload
