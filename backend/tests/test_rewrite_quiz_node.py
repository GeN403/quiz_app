"""Unit tests for rewrite_quiz node."""

import json
from unittest.mock import MagicMock, patch

from app.agent.ports.llm import LLMPortError


def make_state(**kwargs):
    base = {
        "quiz_text": (
            "QUESTION:\nIs Python a high-level language?\n\n"
            "---\n\nEXPLANATION:\nPython is a high-level language.\n\n"
            "---\n\nALTERNATIVE:\nProvide another hint"
        ),
        "verification_results": [
            {
                "claim_id": "C0001",
                "verdict": "fail",
                "reason": "Explanation is insufficient",
            }
        ],
        "verification_attempts": 0,
    }
    base.update(kwargs)
    return base


REWRITTEN_QUIZ = {
    "question": "Is Python a high-level language?",
    "answer": "Yes",
    "Alternative Solutions/Correctness Judgment Criteria": "Paraphrase criteria",
    "explanation": "Python is a high-level language.",
    "source": {"url": "https://example.com", "quote": "Python is a high-level language."},
}


def _make_llm_response(quiz_dict=None) -> str:
    d = quiz_dict if quiz_dict is not None else REWRITTEN_QUIZ
    return json.dumps(d, ensure_ascii=False)


class TestRewriteQuizNodeAttempts:
    @patch("app.agent.nodes.rewrite_quiz.GeminiLLMAdapter")
    def test_verification_attempts_incremented_by_1(self, mock_adapter_cls):
        from app.agent.nodes import make_rewrite_quiz_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _make_llm_response()
        mock_adapter_cls.return_value = mock_adapter

        node = make_rewrite_quiz_node("test-key")
        result = node(make_state(verification_attempts=0))

        assert result["verification_attempts"] == 1

    @patch("app.agent.nodes.rewrite_quiz.GeminiLLMAdapter")
    def test_verification_attempts_incremented_from_nonzero(self, mock_adapter_cls):
        from app.agent.nodes import make_rewrite_quiz_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _make_llm_response()
        mock_adapter_cls.return_value = mock_adapter

        node = make_rewrite_quiz_node("test-key")
        result = node(make_state(verification_attempts=2))

        assert result["verification_attempts"] == 3


class TestRewriteQuizNodeRawResponse:
    @patch("app.agent.nodes.rewrite_quiz.GeminiLLMAdapter")
    def test_llm_raw_response_updated(self, mock_adapter_cls):
        from app.agent.nodes import make_rewrite_quiz_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _make_llm_response()
        mock_adapter_cls.return_value = mock_adapter

        node = make_rewrite_quiz_node("test-key")
        result = node(make_state())

        assert "llm_raw_response" in result
        assert isinstance(result["llm_raw_response"], str)

    @patch("app.agent.nodes.rewrite_quiz.GeminiLLMAdapter")
    def test_llm_raw_response_is_parseable_json(self, mock_adapter_cls):
        from app.agent.nodes import make_rewrite_quiz_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _make_llm_response()
        mock_adapter_cls.return_value = mock_adapter

        node = make_rewrite_quiz_node("test-key")
        result = node(make_state())

        parsed = json.loads(result["llm_raw_response"])
        assert isinstance(parsed, dict)

    @patch("app.agent.nodes.rewrite_quiz.GeminiLLMAdapter")
    def test_llm_raw_response_contains_question_key(self, mock_adapter_cls):
        from app.agent.nodes import make_rewrite_quiz_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.return_value = _make_llm_response()
        mock_adapter_cls.return_value = mock_adapter

        node = make_rewrite_quiz_node("test-key")
        result = node(make_state())

        parsed = json.loads(result["llm_raw_response"])
        assert "question" in parsed


class TestRewriteQuizNodeErrors:
    @patch("app.agent.nodes.rewrite_quiz.GeminiLLMAdapter")
    def test_unauthenticated_returns_api_key_invalid(self, mock_adapter_cls):
        from app.agent.nodes import make_rewrite_quiz_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = LLMPortError("GEMINI_API_KEY_INVALID", 401, "auth error")
        mock_adapter_cls.return_value = mock_adapter

        node = make_rewrite_quiz_node("test-key")
        result = node(make_state())

        assert result["error_code"] == "GEMINI_API_KEY_INVALID"
        assert result["error_status"] == 401

    @patch("app.agent.nodes.rewrite_quiz.GeminiLLMAdapter")
    def test_resource_exhausted_returns_rate_limit(self, mock_adapter_cls):
        from app.agent.nodes import make_rewrite_quiz_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = LLMPortError("GEMINI_RATE_LIMIT", 429, "rate limit")
        mock_adapter_cls.return_value = mock_adapter

        node = make_rewrite_quiz_node("test-key")
        result = node(make_state())

        assert result["error_code"] == "GEMINI_RATE_LIMIT"
        assert result["error_status"] == 429

    @patch("app.agent.nodes.rewrite_quiz.GeminiLLMAdapter")
    def test_generic_exception_returns_service_unavailable(self, mock_adapter_cls):
        from app.agent.nodes import make_rewrite_quiz_node

        mock_adapter = MagicMock()
        mock_adapter.invoke.side_effect = Exception("unexpected error")
        mock_adapter_cls.return_value = mock_adapter

        node = make_rewrite_quiz_node("test-key")
        result = node(make_state())

        assert result["error_code"] == "GEMINI_SERVICE_UNAVAILABLE"
        assert result["error_status"] == 503
