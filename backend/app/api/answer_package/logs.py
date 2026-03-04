"""Log assembly and retention policy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .sanitize import sanitize_text


def parse_iso8601(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def apply_retention_policy(
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
            ts_start = parse_iso8601(str(log.get("ts_start", "")))
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


def build_logs(
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
        logs.append(
            {
                "log_id": f"log_{i:04d}",
                "ts_start": ts_start,
                "ts_end": ts_end,
                "action_type": "verify",
                "target": None,
                "result": "failure" if snap.get("failed_claim_ids") else "success",
                "input_summary": sanitize_text(quiz_text[:120]),
                "output_summary": sanitize_text(f"failed_claim_ids={snap.get('failed_claim_ids', [])}"),
                "package_id": package_id,
                "correlation_id": correlation_id,
                "revision": attempt,
                "diff_targets": ["question", "claims", "evidences", "answer"] if attempt >= 1 else [],
            }
        )

    logs.append(
        {
            "log_id": f"log_{len(logs)+1:04d}",
            "ts_start": (base + timedelta(seconds=9999)).isoformat(),
            "ts_end": (base + timedelta(seconds=9999, milliseconds=100)).isoformat(),
            "action_type": "packaging",
            "target": None,
            "result": "success",
            "input_summary": sanitize_text("assemble answer package"),
            "output_summary": sanitize_text("package assembled"),
            "package_id": package_id,
            "correlation_id": correlation_id,
            "revision": max((l["revision"] for l in logs), default=0),
            "diff_targets": [],
        }
    )

    logs = sorted(logs, key=lambda x: (x["ts_start"], x["log_id"]))
    kept, dropped_by_age, dropped_by_count = apply_retention_policy(logs, retention_limit, retention_days)

    if dropped_by_age > 0 or dropped_by_count > 0:
        revision = max((int(l.get("revision", 0)) for l in kept), default=0)
        max_ts = max((parse_iso8601(str(l.get("ts_start", ""))) for l in kept), default=datetime.now(timezone.utc))
        ts_audit = ((max_ts or datetime.now(timezone.utc)) + timedelta(milliseconds=1)).isoformat()
        kept.append(
            {
                "log_id": f"log_{len(logs)+1:04d}",
                "ts_start": ts_audit,
                "ts_end": ts_audit,
                "action_type": "packaging",
                "target": None,
                "result": "success",
                "input_summary": sanitize_text("retention policy"),
                "output_summary": sanitize_text(
                    f"retention_applied dropped_by_age={dropped_by_age} dropped_by_count={dropped_by_count}"
                ),
                "package_id": package_id,
                "correlation_id": correlation_id,
                "revision": revision,
                "diff_targets": [],
            }
        )
        kept = sorted(kept, key=lambda x: (x["ts_start"], x["log_id"]))
        if retention_limit > 0 and len(kept) > retention_limit:
            kept = kept[-retention_limit:]

    return kept
