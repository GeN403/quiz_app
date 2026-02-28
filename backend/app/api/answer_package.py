"""Answer package assembler for /generate-quiz-agent responses."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
import re
import os

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

_TOP_LEVEL_REQUIRED_FIELDS = [
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


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_text(text: str) -> str:
    masked = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    masked = PHONE_RE.sub("[REDACTED_PHONE]", masked)
    masked = TOKEN_RE.sub("[REDACTED_TOKEN]", masked)
    return masked


def _contains_sensitive(text: str) -> bool:
    return bool(EMAIL_RE.search(text) or PHONE_RE.search(text) or TOKEN_RE.search(text))


def _normalize_claim_type(claim: dict[str, Any]) -> str:
    raw = str(claim.get("claim_type", "fact")).lower()
    return raw if raw in ALLOWED_CLAIM_TYPES else "other"


def _normalize_evidence_status(evidence: dict[str, Any]) -> str:
    raw = str(evidence.get("evidence_status", "ok")).lower()
    if raw in ALLOWED_EVIDENCE_STATUSES:
        return raw
    quote = str(evidence.get("quote", "") or "")
    return "ok" if quote else "unknown"


def _new_error(error_code: str, message: str, retryable: bool, action: str) -> dict[str, Any]:
    return {
        "error_code": error_code,
        "message": _sanitize_text(message),
        "retryable": retryable,
        "recommended_next_action": action,
    }


def _build_claims(
    claims: list[dict[str, Any]],
    evidence_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_by_claim: dict[str, list[dict[str, Any]]] = {}
    enum_errors: list[dict[str, Any]] = []
    for e in evidence_list:
        cid = str(e.get("claim_id", ""))
        if cid:
            evidence_by_claim.setdefault(cid, []).append(e)

    out: list[dict[str, Any]] = []
    for claim in claims:
        cid = str(claim.get("claim_id", ""))
        raw_claim_type = str(claim.get("claim_type", "fact")).lower()
        normalized_claim_type = _normalize_claim_type(claim)
        if raw_claim_type not in ALLOWED_CLAIM_TYPES:
            enum_errors.append(
                _new_error(
                    "INVALID_ENUM_VALUE",
                    f"invalid claim_type: {raw_claim_type}",
                    False,
                    "manual_review",
                )
            )
        evidences: list[dict[str, Any]] = []
        for idx, ev in enumerate(evidence_by_claim.get(cid, []), 1):
            excerpt = str(ev.get("quote", "") or "")
            if _contains_sensitive(excerpt):
                excerpt = _sanitize_text(excerpt)
            raw_status = str(ev.get("evidence_status", "ok")).lower()
            status = _normalize_evidence_status(ev)
            if raw_status not in ALLOWED_EVIDENCE_STATUSES and "evidence_status" in ev:
                enum_errors.append(
                    _new_error(
                        "INVALID_ENUM_VALUE",
                        f"invalid evidence_status: {raw_status}",
                        False,
                        "manual_review",
                    )
                )
            failure_reason = None if status == "ok" else str(ev.get("failure_reason") or "evidence unavailable")
            evidences.append(
                {
                    "url": str(ev.get("url", "")),
                    "excerpt_text": excerpt,
                    "excerpt_locator": f"evidence:{idx}",
                    "fetched_at": str(ev.get("retrieved_at") or _iso_now()),
                    "evidence_status": status,
                    "failure_reason": failure_reason,
                }
            )
        out.append(
            {
                "claim_id": cid,
                "claim_text": str(claim.get("text", "")),
                "claim_type": normalized_claim_type,
                "evidences": evidences,
            }
        )
    return out, enum_errors


def _build_alternative_policy(result: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    alt = str(result.get("Alternative Solutions/Correctness Judgment Criteria", "") or "").strip()
    if not alt:
        err = _new_error(
            "ALT_POLICY_UNDEFINED",
            "Alternative answer policy is undefined",
            True,
            "rewrite_question",
        )
        policy = {
            "rule_text": "",
            "positive_examples": [],
            "negative_examples": [],
            "cannot_define_reason": "判定基準を生成できなかったため",
        }
        return policy, [err], True

    answer_text = str(result.get("answer", "") or "")
    policy = {
        "rule_text": alt,
        "positive_examples": [answer_text] if answer_text else [],
        "negative_examples": ["根拠に反する説明のみを返す回答"],
        "cannot_define_reason": None,
    }
    return policy, [], False


def _parse_iso8601(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _apply_retention_policy(
    logs: list[dict[str, Any]],
    retention_limit: int,
    retention_days: int | None,
) -> tuple[list[dict[str, Any]], int, int]:
    now = datetime.now(timezone.utc)
    dropped_by_age = 0
    kept = list(logs)
    if retention_days is not None and retention_days >= 0:
        threshold = now - timedelta(days=retention_days)
        filtered: list[dict[str, Any]] = []
        for log in kept:
            ts_start = _parse_iso8601(str(log.get("ts_start", "")))
            if ts_start and ts_start < threshold:
                dropped_by_age += 1
                continue
            filtered.append(log)
        kept = filtered

    dropped_by_count = 0
    if retention_limit > 0 and len(kept) > retention_limit:
        dropped_by_count = len(kept) - retention_limit
        kept = kept[-retention_limit:]
    return kept, dropped_by_age, dropped_by_count


def _build_logs(
    verification_history: list[dict[str, Any]],
    correlation_id: str,
    package_id: str,
    retention_limit: int,
    retention_days: int | None,
) -> list[dict[str, Any]]:
    base = datetime.now(timezone.utc)
    logs: list[dict[str, Any]] = []
    for i, snap in enumerate(verification_history, 1):
        attempt = int(snap.get("attempt", i - 1))
        ts_start = (base + timedelta(seconds=attempt)).isoformat()
        ts_end = (base + timedelta(seconds=attempt, milliseconds=500)).isoformat()
        quiz_text = str(snap.get("quiz_text", "") or "")
        log = {
            "log_id": f"log_{i:04d}",
            "ts_start": ts_start,
            "ts_end": ts_end,
            "action_type": "verify",
            "target": None,
            "result": "failure" if snap.get("failed_claim_ids") else "success",
            "input_summary": _sanitize_text(quiz_text[:120]),
            "output_summary": _sanitize_text(f"failed_claim_ids={snap.get('failed_claim_ids', [])}"),
            "package_id": package_id,
            "correlation_id": correlation_id,
            "revision": attempt,
            "diff_targets": ["question", "claims", "evidences", "answer"] if attempt >= 1 else [],
        }
        logs.append(log)

    logs.append(
        {
            "log_id": f"log_{len(logs)+1:04d}",
            "ts_start": (base + timedelta(seconds=9999)).isoformat(),
            "ts_end": (base + timedelta(seconds=9999, milliseconds=100)).isoformat(),
            "action_type": "packaging",
            "target": None,
            "result": "success",
            "input_summary": _sanitize_text("assemble answer package"),
            "output_summary": _sanitize_text("package assembled"),
            "package_id": package_id,
            "correlation_id": correlation_id,
            "revision": max((l["revision"] for l in logs), default=0),
            "diff_targets": [],
        }
    )

    logs = sorted(logs, key=lambda x: (x["ts_start"], x["log_id"]))
    kept, dropped_by_age, dropped_by_count = _apply_retention_policy(logs, retention_limit, retention_days)

    if dropped_by_age > 0 or dropped_by_count > 0:
        revision = max((int(l.get("revision", 0)) for l in kept), default=0)
        max_ts = max(
            (_parse_iso8601(str(l.get("ts_start", ""))) for l in kept),
            default=datetime.now(timezone.utc),
        )
        ts_audit = ((max_ts or datetime.now(timezone.utc)) + timedelta(milliseconds=1)).isoformat()
        audit_log = {
            "log_id": f"log_{len(logs)+1:04d}",
            "ts_start": ts_audit,
            "ts_end": ts_audit,
            "action_type": "packaging",
            "target": None,
            "result": "success",
            "input_summary": _sanitize_text("retention policy"),
            "output_summary": _sanitize_text(
                f"retention_applied dropped_by_age={dropped_by_age} dropped_by_count={dropped_by_count}"
            ),
            "package_id": package_id,
            "correlation_id": correlation_id,
            "revision": revision,
            "diff_targets": [],
        }
        kept.append(audit_log)
        kept = sorted(kept, key=lambda x: (x["ts_start"], x["log_id"]))
        if retention_limit > 0 and len(kept) > retention_limit:
            kept = kept[-retention_limit:]

    return kept


def _calculate_warning_metrics(claims: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    total_claims = len(claims)
    if total_claims == 0:
        ratio = 1.0
        unverifiable_claims = 0
    else:
        unverifiable_claims = sum(
            1
            for c in claims
            if not any(e.get("evidence_status") == "ok" for e in c.get("evidences", []))
        )
        ratio = unverifiable_claims / total_claims

    warning_level = "high" if ratio >= 0.30 else "none"
    warnings = {
        "warning_level": warning_level,
        "messages": ["unverifiable_evidence_ratio が 0.30 以上"] if warning_level == "high" else [],
    }
    thresholds = {
        "unverifiable_evidence_ratio": ratio,
        "high_warning_ratio": 0.30,
        "formula": "unverifiable_claims/total_claims",
    }
    return warnings, thresholds


def _build_error_envelope(final_state: dict[str, Any]) -> list[dict[str, Any]]:
    code = final_state.get("error_code")
    if not code:
        return []
    status = int(final_state.get("error_status") or 500)
    retryable = status in {429, 500, 503, 504}
    action = "retry_with_new_sources" if retryable else "manual_review"
    return [_new_error(str(code), str(code), retryable, action)]


def _missing_required_fields(payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for key in _TOP_LEVEL_REQUIRED_FIELDS:
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


def _determine_status(
    final_state: dict[str, Any],
    missing_fields: list[str],
    errors: list[dict[str, Any]],
) -> str:
    if final_state.get("error_code"):
        return "failed"
    if missing_fields or errors:
        return "partial"
    return "complete"


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

    claims, enum_errors = _build_claims(
        list(final_state.get("claims") or []),
        list(final_state.get("evidence_list") or []),
    )
    package_id = f"pkg_{uuid4().hex[:12]}"

    warnings, thresholds = _calculate_warning_metrics(claims)
    policy, policy_errors, policy_missing = _build_alternative_policy(result)
    errors = _build_error_envelope(final_state) + policy_errors + enum_errors
    for err in errors:
        if err["recommended_next_action"] not in ALLOWED_RECOMMENDED_NEXT_ACTIONS:
            err["recommended_next_action"] = "manual_review"

    logs = _build_logs(
        list(final_state.get("verification_history") or []),
        correlation_id,
        package_id,
        retention_limit,
        retention_days,
    )

    payload = {
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

    # backward-compatible fields
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

    missing_fields = _missing_required_fields(payload)
    if policy_missing and "alternative_answer_policy" not in missing_fields:
        missing_fields.append("alternative_answer_policy")

    payload["missing_fields"] = sorted(set(missing_fields))
    payload["status"] = _determine_status(final_state, payload["missing_fields"], payload["errors"])

    return payload
