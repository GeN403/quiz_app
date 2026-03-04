"""Unit tests for decompose_claims node."""

import json
from unittest.mock import MagicMock, patch

from app.agent.ports.llm import LLMPortError


def make_raw_response(**kwargs) -> str:
    base = {
        "question": "Is Python dynamically typed?",
        "answer": "Yes",
        "Alternative Solutions/Correctness Judgment Criteria": "Paraphrase allowed",
        "explanation": "Python is dynamically typed.",
        "source": {"title": "Example", "url": "https://example.com", "quote": ""},
    }
    base.update(kwargs)
    return json.dumps(base, ensure_ascii=False)


def make_state(**kwargs):
    base = {
        "llm_raw_response": make_raw_response(),
    }
    base.update(kwargs)
    return base


def _claims_texts(n: int):
    return [{"text": f"claim-{i}"} for i in range(1, n + 1)]


class TestDecomposeClaimsNodeQuizText:
    @patch("app.agent.nodes.decompose_claims.GeminiLLMAdapter")
    def test_quiz_text_contains_sections(self, mock_adapter_cls):
        from app.agent.nodes import make_decompose_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = json.dumps(_claims_texts(1), ensure_ascii=False)
        mock_adapter_cls.return_value = mock_adapter

        node = make_decompose_claims_node("test-key")
        result = node(make_state())

        assert "quiz_text" in result
        qt = result["quiz_text"]
        assert qt.startswith("QUESTION:")
        assert "EXPLANATION:" in qt
        assert "ALTERNATIVE:" in qt
        assert "---" in qt


class TestDecomposeClaimsNodeClaims:
    @patch("app.agent.nodes.decompose_claims.GeminiLLMAdapter")
    def test_claim_ids_are_sequential(self, mock_adapter_cls):
        from app.agent.nodes import make_decompose_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = json.dumps(_claims_texts(3), ensure_ascii=False)
        mock_adapter_cls.return_value = mock_adapter

        node = make_decompose_claims_node("test-key")
        result = node(make_state())

        claims = result["claims"]
        assert [c["claim_id"] for c in claims] == ["C0001", "C0002", "C0003"]
        assert claims[0]["text"] == "claim-1"

    @patch("app.agent.nodes.decompose_claims.GeminiLLMAdapter")
    def test_claims_truncated_to_5(self, mock_adapter_cls):
        from app.agent.nodes import make_decompose_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = json.dumps(_claims_texts(7), ensure_ascii=False)
        mock_adapter_cls.return_value = mock_adapter

        node = make_decompose_claims_node("test-key")
        result = node(make_state())

        assert len(result["claims"]) == 5
        assert result["claims"][4]["claim_id"] == "C0005"

    @patch("app.agent.nodes.decompose_claims.GeminiLLMAdapter")
    def test_reset_fields_are_empty(self, mock_adapter_cls):
        from app.agent.nodes import make_decompose_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = json.dumps(_claims_texts(1), ensure_ascii=False)
        mock_adapter_cls.return_value = mock_adapter

        node = make_decompose_claims_node("test-key")
        result = node(make_state())

        assert result["evidence_list"] == []
        assert result["verification_results"] == []


class TestDecomposeClaimsNodeErrors:
    @patch("app.agent.nodes.decompose_claims.GeminiLLMAdapter")
    def test_invalid_llm_raw_response_returns_ai_invalid_json(self, mock_adapter_cls):
        from app.agent.nodes import make_decompose_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = json.dumps(_claims_texts(1), ensure_ascii=False)
        mock_adapter_cls.return_value = mock_adapter

        node = make_decompose_claims_node("test-key")
        result = node(make_state(llm_raw_response="invalid json {{{"))

        assert result["error_code"] == "AI_INVALID_JSON"
        assert result["error_status"] == 500

    @patch("app.agent.nodes.decompose_claims.GeminiLLMAdapter")
    def test_zero_claims_returns_claim_decompose_failed(self, mock_adapter_cls):
        from app.agent.nodes import make_decompose_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = "[]"
        mock_adapter_cls.return_value = mock_adapter

        node = make_decompose_claims_node("test-key")
        result = node(make_state())

        assert result["error_code"] == "CLAIM_DECOMPOSE_FAILED"
        assert result["error_status"] == 500

    @patch("app.agent.nodes.decompose_claims.GeminiLLMAdapter")
    def test_llm_port_errors_are_mapped(self, mock_adapter_cls):
        from app.agent.nodes import make_decompose_claims_node

        node = make_decompose_claims_node("test-key")

        for code, status in [
            ("GEMINI_API_KEY_INVALID", 401),
            ("GEMINI_API_KEY_PERMISSION_DENIED", 403),
            ("GEMINI_RATE_LIMIT", 429),
            ("GEMINI_SERVICE_UNAVAILABLE", 503),
            ("GEMINI_TIMEOUT", 504),
        ]:
            mock_adapter = MagicMock()
            mock_adapter.invoke.side_effect = LLMPortError(code, status, "err")
            mock_adapter_cls.return_value = mock_adapter

            result = node(make_state())
            assert result["error_code"] == code
            assert result["error_status"] == status

    @patch("app.agent.nodes.decompose_claims.GeminiLLMAdapter")
    def test_unexpected_error_returns_service_unavailable(self, mock_adapter_cls):
        from app.agent.nodes import make_decompose_claims_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = RuntimeError("boom")
        mock_adapter_cls.return_value = mock_adapter

        node = make_decompose_claims_node("test-key")
        result = node(make_state())

        assert result["error_code"] == "GEMINI_SERVICE_UNAVAILABLE"
        assert result["error_status"] == 503
