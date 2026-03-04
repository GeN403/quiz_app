"""Alternative answer policy builder."""

from __future__ import annotations

from typing import Any

from .sanitize import new_error


def build_alternative_policy(result: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    alt = str(result.get("Alternative Solutions/Correctness Judgment Criteria", "") or "").strip()
    if not alt:
        err = new_error(
            "ALT_POLICY_UNDEFINED",
            "Alternative answer policy is undefined",
            True,
            "rewrite_question",
        )
        policy = {
            "rule_text": "",
            "positive_examples": [],
            "negative_examples": [],
            "cannot_define_reason": "???????????????",
        }
        return policy, [err], True

    answer_text = str(result.get("answer", "") or "")
    policy = {
        "rule_text": alt,
        "positive_examples": [answer_text] if answer_text else [],
        "negative_examples": ["???????????????"],
        "cannot_define_reason": None,
    }
    return policy, [], False
