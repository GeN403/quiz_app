"""Claim/evidence shaping."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .constants import ALLOWED_CLAIM_TYPES, ALLOWED_EVIDENCE_STATUSES
from .sanitize import contains_sensitive, new_error, sanitize_text


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_claim_type(claim: dict[str, Any]) -> str:
    raw = str(claim.get("claim_type", "fact")).lower()
    return raw if raw in ALLOWED_CLAIM_TYPES else "other"


def normalize_evidence_status(evidence: dict[str, Any]) -> str:
    raw = str(evidence.get("evidence_status", "ok")).lower()
    if raw in ALLOWED_EVIDENCE_STATUSES:
        return raw
    quote = str(evidence.get("quote", "") or "")
    return "ok" if quote else "unknown"


def build_claims(
    claims: list[dict[str, Any]],
    evidence_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_by_claim: dict[str, list[dict[str, Any]]] = {}
    enum_errors: list[dict[str, Any]] = []
    for evidence in evidence_list:
        claim_id = str(evidence.get("claim_id", ""))
        if claim_id:
            evidence_by_claim.setdefault(claim_id, []).append(evidence)

    out: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = str(claim.get("claim_id", ""))
        raw_claim_type = str(claim.get("claim_type", "fact")).lower()
        normalized_claim_type = normalize_claim_type(claim)
        if raw_claim_type not in ALLOWED_CLAIM_TYPES:
            enum_errors.append(
                new_error(
                    "INVALID_ENUM_VALUE",
                    f"invalid claim_type: {raw_claim_type}",
                    False,
                    "manual_review",
                )
            )

        evidences: list[dict[str, Any]] = []
        for idx, evidence in enumerate(evidence_by_claim.get(claim_id, []), 1):
            excerpt = str(evidence.get("quote", "") or "")
            if contains_sensitive(excerpt):
                excerpt = sanitize_text(excerpt)
            raw_status = str(evidence.get("evidence_status", "ok")).lower()
            status = normalize_evidence_status(evidence)
            if raw_status not in ALLOWED_EVIDENCE_STATUSES and "evidence_status" in evidence:
                enum_errors.append(
                    new_error(
                        "INVALID_ENUM_VALUE",
                        f"invalid evidence_status: {raw_status}",
                        False,
                        "manual_review",
                    )
                )
            failure_reason = None if status == "ok" else str(evidence.get("failure_reason") or "evidence unavailable")
            evidences.append(
                {
                    "url": str(evidence.get("url", "")),
                    "excerpt_text": excerpt,
                    "excerpt_locator": f"evidence:{idx}",
                    "fetched_at": str(evidence.get("retrieved_at") or iso_now()),
                    "evidence_status": status,
                    "failure_reason": failure_reason,
                }
            )

        out.append(
            {
                "claim_id": claim_id,
                "claim_text": str(claim.get("text", "")),
                "claim_type": normalized_claim_type,
                "evidences": evidences,
            }
        )

    return out, enum_errors
