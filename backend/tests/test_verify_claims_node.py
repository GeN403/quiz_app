"""Unit tests for verify_claims node."""

import json
from unittest.mock import MagicMock, patch


def make_state(**kwargs):
    base = {
        "claims": [{"claim_id": "C0001", "text": "Python is dynamically typed"}],
        "evidence_list": [
            {
                "claim_id": "C0001",
                "evidence_id": "E0001",
                "url": "https://example.com",
                "quote": "Python is dynamically typed",
                "rank": 1,
            }
        ],
        "quiz_text": "QUESTION:
Q

---

EXPLANATION:
E

---

ALTERNATIVE:
A",
        "verification_attempts": 0,
    }
    base.update(kwargs)
    return base


def _resp(verdict: str, reason: str):
    return json.dumps({"verdict": verdict, "reason": reason}, ensure_ascii=False)


class TestVerifyClaimsNode:
    @patch("app.agent.nodes.verify_claims.GeminiLLMAdapter")
    def test_zero_evidence_auto_fail_without_llm(self, mock_adapter_cls):
        from app.agent.nodes import make_verify_claims_node

        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter

        node = make_verify_claims_node("test-key")
        result = node(make_state(evidence_list=[]))

        mock_adapter.invoke.assert_not_called()
        assert result["verification_results"][0]["verdict"] == "fail"

    @patch("app.agent.nodes.verify_claims.GeminiLLMAdapter")
    def test_all_pass_returns_pass_outcome(self, mock_adapter_cls):
        from app.agent.nodes import make_verify_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _resp("pass", "ok")
        mock_adapter_cls.return_value = mock_adapter

        node = make_verify_claims_node("test-key")
        result = node(make_state())

        assert result["verification_results"][0]["verdict"] == "pass"
        assert result["verification_outcome"]["verdict"] == "pass"
        assert "verification_history" not in result

    @patch("app.agent.nodes.verify_claims.GeminiLLMAdapter")
    def test_fail_adds_snapshot(self, mock_adapter_cls):
        from app.agent.nodes import make_verify_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _resp("fail", "contradicted")
        mock_adapter_cls.return_value = mock_adapter

        node = make_verify_claims_node("test-key")
        result = node(make_state())

        history = result.get("verification_history", [])
        assert len(history) == 1
        assert history[0]["failed_claim_ids"] == ["C0001"]

    @patch("app.agent.nodes.verify_claims.GeminiLLMAdapter")
    def test_fail_with_empty_reason_returns_internal_schema_error(self, mock_adapter_cls):
        from app.agent.nodes import make_verify_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _resp("fail", "")
        mock_adapter_cls.return_value = mock_adapter

        node = make_verify_claims_node("test-key")
        result = node(make_state())

        assert result["error_code"] == "INTERNAL_SCHEMA_ERROR"
        assert result["error_status"] == 500

    @patch("app.agent.nodes.verify_claims.GeminiLLMAdapter")
    def test_max_attempts_reached_returns_unknown(self, mock_adapter_cls):
        from app.agent.nodes import make_verify_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _resp("fail", "contradicted")
        mock_adapter_cls.return_value = mock_adapter

        node = make_verify_claims_node("test-key")
        result = node(make_state(verification_attempts=3))

        assert result["verification_outcome"]["verdict"] == "unknown"
        assert result["termination_reason_code"] == "MAX_VERIFICATION_ATTEMPTS_REACHED"

    @patch("app.agent.nodes.verify_claims.GeminiLLMAdapter")
    def test_invalid_disambiguation_parameters_returns_constraint_violation(self, mock_adapter_cls):
        from app.agent.nodes import make_verify_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _resp("fail", "contradicted")
        mock_adapter_cls.return_value = mock_adapter

        node = make_verify_claims_node("test-key")
        result = node(
            make_state(
                disambiguation_parameters={
                    "major_count_threshold": 5,
                    "minor_count_threshold": 5,
                }
            )
        )

        assert result["error_code"] == "PARAMETER_CONSTRAINT_VIOLATION"
        assert result["error_status"] == 400
