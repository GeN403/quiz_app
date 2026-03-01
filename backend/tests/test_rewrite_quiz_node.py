"""
rewrite_quiz ノードのユニットテスト

Task 6 (Task 8.4 optional)
Requirements: 4.1, 4.3
"""

import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def make_state(**kwargs):
    base = {
        "quiz_text": (
            "QUESTION:\nPython は静的型付け言語でしょうか？\n\n"
            "---\n\nEXPLANATION:\nPython は動的型付け言語です。\n\n"
            "---\n\nALTERNATIVE:\n型ヒントは実行時に強制されない"
        ),
        "verification_results": [
            {
                "claim_id": "C0001",
                "verdict": "fail",
                "reason": "Python は動的型付けであるため記述が誤り",
            }
        ],
        "verification_attempts": 0,
    }
    base.update(kwargs)
    return base


REWRITTEN_QUIZ = {
    "question": "Python は動的型付け言語でしょうか？",
    "answer": "はい",
    "Alternative Solutions/Correctness Judgment Criteria": "型付け/型システム",
    "explanation": "Python は動的型付け言語です。型ヒントは実行時に強制されません。",
    "source": {"url": "https://example.com", "quote": "Python は動的型付け言語です。"},
}


def _make_llm_response(quiz_dict=None) -> MagicMock:
    d = quiz_dict if quiz_dict is not None else REWRITTEN_QUIZ
    return MagicMock(content=json.dumps(d, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Task 6: verification_attempts インクリメント
# ---------------------------------------------------------------------------

class TestRewriteQuizNodeAttempts:
    def test_verification_attempts_incremented_by_1(self):
        """verification_attempts が +1 インクリメントされる (Requirements: 4.3)"""
        from app.agent.nodes import make_rewrite_quiz_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_llm_response()
            mock_cls.return_value = mock_llm
            node = make_rewrite_quiz_node("test-key")
            result = node(make_state(verification_attempts=0))

        assert result["verification_attempts"] == 1

    def test_verification_attempts_incremented_from_nonzero(self):
        """verification_attempts が 2 の場合 3 にインクリメントされる"""
        from app.agent.nodes import make_rewrite_quiz_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_llm_response()
            mock_cls.return_value = mock_llm
            node = make_rewrite_quiz_node("test-key")
            result = node(make_state(verification_attempts=2))

        assert result["verification_attempts"] == 3


# ---------------------------------------------------------------------------
# Task 6: llm_raw_response の更新
# ---------------------------------------------------------------------------

class TestRewriteQuizNodeRawResponse:
    def test_llm_raw_response_updated_to_rewritten_quiz(self):
        """llm_raw_response が書き換えた QuizData 互換 JSON 文字列に更新される (Requirements: 4.1)"""
        from app.agent.nodes import make_rewrite_quiz_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_llm_response()
            mock_cls.return_value = mock_llm
            node = make_rewrite_quiz_node("test-key")
            result = node(make_state())

        assert "llm_raw_response" in result
        assert isinstance(result["llm_raw_response"], str)

    def test_llm_raw_response_is_parseable_json(self):
        """llm_raw_response が有効な JSON 文字列である（decompose_claims が再パース可能）"""
        from app.agent.nodes import make_rewrite_quiz_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_llm_response()
            mock_cls.return_value = mock_llm
            node = make_rewrite_quiz_node("test-key")
            result = node(make_state())

        parsed = json.loads(result["llm_raw_response"])
        assert isinstance(parsed, dict)

    def test_llm_raw_response_contains_question_key(self):
        """llm_raw_response に question キーが含まれる（QuizData 互換形式）"""
        from app.agent.nodes import make_rewrite_quiz_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_llm_response()
            mock_cls.return_value = mock_llm
            node = make_rewrite_quiz_node("test-key")
            result = node(make_state())

        parsed = json.loads(result["llm_raw_response"])
        assert "question" in parsed


# ---------------------------------------------------------------------------
# Task 6: エラーハンドリング (GEMINI_* パターン)
# ---------------------------------------------------------------------------

class TestRewriteQuizNodeErrors:
    def test_unauthenticated_returns_api_key_invalid(self):
        """Unauthenticated 例外で GEMINI_API_KEY_INVALID を返す"""
        from app.agent.nodes import make_rewrite_quiz_node
        from google.api_core import exceptions as google_exceptions

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = google_exceptions.Unauthenticated("auth error")
            mock_cls.return_value = mock_llm
            node = make_rewrite_quiz_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "GEMINI_API_KEY_INVALID"
        assert result["error_status"] == 401

    def test_resource_exhausted_returns_rate_limit(self):
        """ResourceExhausted 例外で GEMINI_RATE_LIMIT を返す"""
        from app.agent.nodes import make_rewrite_quiz_node
        from google.api_core import exceptions as google_exceptions

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = google_exceptions.ResourceExhausted("rate limit")
            mock_cls.return_value = mock_llm
            node = make_rewrite_quiz_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "GEMINI_RATE_LIMIT"
        assert result["error_status"] == 429

    def test_generic_exception_returns_service_unavailable(self):
        """予期しない例外で GEMINI_SERVICE_UNAVAILABLE を返す"""
        from app.agent.nodes import make_rewrite_quiz_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = Exception("unexpected error")
            mock_cls.return_value = mock_llm
            node = make_rewrite_quiz_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "GEMINI_SERVICE_UNAVAILABLE"
        assert result["error_status"] == 503
