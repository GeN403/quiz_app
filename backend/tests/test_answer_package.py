import copy

from app.api.answer_package import (
    ALLOWED_ACTION_TYPES,
    ALLOWED_CLAIM_TYPES,
    ALLOWED_EVIDENCE_STATUSES,
    ALLOWED_RECOMMENDED_NEXT_ACTIONS,
    build_answer_package,
)


def _make_final_state() -> dict:
    return {
        "result": {
            "question": "Q",
            "answer": "A",
            "Alternative Solutions/Correctness Judgment Criteria": "条件Aを満たす",
            "explanation": "E",
            "source": {
                "url": "https://example.com",
                "title": "t",
                "quote": "q",
            },
        },
        "claims": [{"claim_id": "C0001", "text": "Paris is capital"}],
        "evidence_list": [
            {
                "claim_id": "C0001",
                "evidence_id": "E0001",
                "url": "https://example.com",
                "quote": "Paris is the capital",
                "rank": 1,
                "retrieved_at": "2026-03-01T00:00:00+09:00",
            }
        ],
        "verification_history": [
            {
                "attempt": 0,
                "quiz_text": "Q",
                "claims": [{"claim_id": "C0001", "text": "Paris is capital"}],
                "evidence_list": [],
                "verification_results": [],
                "failed_claim_ids": [],
            }
        ],
        "verification_outcome": {
            "verdict": "pass",
            "reason": "ok",
            "evidence_status": "ok",
            "effective_competing_count": 0,
        },
    }


def test_build_answer_package_complete_has_required_top_level_fields():
    package = build_answer_package(_make_final_state(), "corr_test")

    assert package["status"] == "complete"
    assert package["missing_fields"] == []
    assert package["correlation_id"] == "corr_test"
    assert isinstance(package["package_id"], str)
    assert package["question"]["text"] == "Q"
    assert package["answer"]["text"] == "A"
    assert package["claims"][0]["claim_type"] in ALLOWED_CLAIM_TYPES


def test_build_answer_package_partial_when_alternative_policy_missing():
    final_state = _make_final_state()
    final_state["result"]["Alternative Solutions/Correctness Judgment Criteria"] = ""

    package = build_answer_package(final_state, "corr_test")

    assert package["status"] == "partial"
    assert "alternative_answer_policy" in package["missing_fields"]


def test_build_answer_package_failed_maps_error_envelope():
    final_state = _make_final_state()
    final_state["error_code"] = "GEMINI_TIMEOUT"
    final_state["error_status"] = 504

    package = build_answer_package(final_state, "corr_test")

    assert package["status"] == "failed"
    assert package["errors"]
    assert package["errors"][0]["recommended_next_action"] in ALLOWED_RECOMMENDED_NEXT_ACTIONS


def test_warning_level_high_when_unverifiable_ratio_exceeds_threshold():
    final_state = _make_final_state()
    final_state["evidence_list"] = []

    package = build_answer_package(final_state, "corr_test")

    assert package["thresholds"]["unverifiable_evidence_ratio"] >= 0.3
    assert package["warnings"]["warning_level"] == "high"


def test_logs_are_sorted_by_ts_start_then_log_id():
    final_state = _make_final_state()
    final_state["verification_history"] = [
        {
            "attempt": 2,
            "quiz_text": "Q2",
            "claims": [],
            "evidence_list": [],
            "verification_results": [],
            "failed_claim_ids": [],
        },
        {
            "attempt": 1,
            "quiz_text": "Q1",
            "claims": [],
            "evidence_list": [],
            "verification_results": [],
            "failed_claim_ids": [],
        },
    ]
    package = build_answer_package(final_state, "corr_test")
    logs = package["logs"]
    assert logs == sorted(logs, key=lambda x: (x["ts_start"], x["log_id"]))


def test_masking_applies_to_log_summaries_and_error_message():
    final_state = _make_final_state()
    final_state["error_code"] = "E_INTERNAL"
    final_state["error_status"] = 500
    final_state["verification_history"][0]["quiz_text"] = "contact me at test@example.com"

    package = build_answer_package(final_state, "corr_test")
    assert "example.com" not in package["logs"][0]["input_summary"]
    assert "example.com" not in package["errors"][0]["message"]


def test_excerpt_is_masked_only_when_sensitive_pattern_detected():
    final_state = _make_final_state()
    final_state["evidence_list"][0]["quote"] = "mail: test@example.com"

    package = build_answer_package(final_state, "corr_test")
    excerpt = package["claims"][0]["evidences"][0]["excerpt_text"]
    assert "example.com" not in excerpt


def test_enum_values_in_output_are_within_allowed_sets():
    package = build_answer_package(_make_final_state(), "corr_test")

    assert package["claims"][0]["evidences"][0]["evidence_status"] in ALLOWED_EVIDENCE_STATUSES
    assert package["logs"][0]["action_type"] in ALLOWED_ACTION_TYPES


def test_invalid_claim_type_is_rejected_with_standard_error_and_partial_status():
    final_state = _make_final_state()
    final_state["claims"][0]["claim_type"] = "invalid_claim_type"

    package = build_answer_package(final_state, "corr_test")

    assert package["status"] == "partial"
    assert any(error["error_code"] == "INVALID_ENUM_VALUE" for error in package["errors"])
    assert any(error["recommended_next_action"] == "manual_review" for error in package["errors"])


def test_log_retention_keeps_latest_and_records_disposal_audit():
    final_state = _make_final_state()
    final_state["verification_history"] = [
        {
            "attempt": 0,
            "quiz_text": "Q0",
            "claims": [],
            "evidence_list": [],
            "verification_results": [],
            "failed_claim_ids": [],
        },
        {
            "attempt": 1,
            "quiz_text": "Q1",
            "claims": [],
            "evidence_list": [],
            "verification_results": [],
            "failed_claim_ids": [],
        },
        {
            "attempt": 2,
            "quiz_text": "Q2",
            "claims": [],
            "evidence_list": [],
            "verification_results": [],
            "failed_claim_ids": [],
        },
    ]

    package = build_answer_package(final_state, "corr_test", retention_limit=2)

    assert len(package["logs"]) == 2
    assert any("retention_applied" in log["output_summary"] for log in package["logs"])
