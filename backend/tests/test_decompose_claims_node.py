"""
decompose_claims ノードのユニットテスト

Task 3.1, 3.2
Requirements: 1.1, 1.2, 1.3, 1.4, 4.6
"""

import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def make_raw_response(**kwargs):
    """LLM が返す QuizData 互換 JSON 文字列を生成する"""
    base = {
        "question": "Python は静的型付け言語でしょうか？",
        "answer": "いいえ",
        "Alternative Solutions/Correctness Judgment Criteria": "型ヒントは実行時に強制されない",
        "explanation": "Python は動的型付け言語です。",
        "source": {"title": "テスト", "url": "https://example.com", "quote": ""},
    }
    base.update(kwargs)
    return json.dumps(base, ensure_ascii=False)


def make_state(**kwargs):
    base: dict = {
        "llm_raw_response": make_raw_response(),
    }
    base.update(kwargs)
    return base


def _make_llm_mock(claims_list):
    """ChatGoogleGenerativeAI をモックして claims_list を LLM 応答として返す"""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content=json.dumps(claims_list, ensure_ascii=False)
    )
    return mock_llm


# ---------------------------------------------------------------------------
# Task 3.1: quiz_text の構築と LLM 呼び出し
# ---------------------------------------------------------------------------

class TestDecomposeClaimsNodeQuizText:
    def test_quiz_text_starts_with_question_section(self):
        """quiz_text が QUESTION: で始まる"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock([{"text": "主張A"}])
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert "quiz_text" in result
        assert result["quiz_text"].startswith("QUESTION:")

    def test_quiz_text_contains_all_three_sections(self):
        """quiz_text に QUESTION / EXPLANATION / ALTERNATIVE の 3 セクションが含まれる"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock([{"text": "主張A"}])
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        qt = result["quiz_text"]
        assert "QUESTION:" in qt
        assert "EXPLANATION:" in qt
        assert "ALTERNATIVE:" in qt
        assert "---" in qt

    def test_quiz_text_contains_question_content(self):
        """quiz_text に question フィールドの内容が含まれる"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock([{"text": "主張A"}])
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert "Python は静的型付け言語でしょうか？" in result["quiz_text"]

    def test_quiz_text_contains_explanation_content(self):
        """quiz_text に explanation フィールドの内容が含まれる"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock([{"text": "主張A"}])
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert "Python は動的型付け言語です。" in result["quiz_text"]

    def test_quiz_text_contains_alternative_content(self):
        """quiz_text に alternative フィールドの内容が含まれる"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock([{"text": "主張A"}])
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert "型ヒントは実行時に強制されない" in result["quiz_text"]


# ---------------------------------------------------------------------------
# Task 3.2: claim_id 付与・件数制限・リセット
# ---------------------------------------------------------------------------

class TestDecomposeClaimsNodeClaimIds:
    def test_claim_id_starts_from_c0001(self):
        """claim_id が C0001 から始まる"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock([{"text": "主張A"}])
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert result["claims"][0]["claim_id"] == "C0001"

    def test_claim_ids_are_sequential(self):
        """複数主張の claim_id が C0001, C0002, C0003 の連番になる"""
        from app.agent.nodes import make_decompose_claims_node

        claims_list = [{"text": "主張1"}, {"text": "主張2"}, {"text": "主張3"}]
        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock(claims_list)
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        claims = result["claims"]
        assert len(claims) == 3
        assert claims[0]["claim_id"] == "C0001"
        assert claims[1]["claim_id"] == "C0002"
        assert claims[2]["claim_id"] == "C0003"

    def test_claim_ids_are_zero_padded_4_digits(self):
        """claim_id がゼロ埋め 4 桁形式（C0001〜）になる"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock([{"text": "主張A"}])
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        cid = result["claims"][0]["claim_id"]
        assert len(cid) == 5          # "C" + 4 digits
        assert cid[0] == "C"
        assert cid[1:].isdigit()

    def test_claims_truncated_to_max_5(self):
        """7 件の主張リストを渡しても最大 5 件に切り詰められる"""
        from app.agent.nodes import make_decompose_claims_node

        claims_list = [{"text": f"主張{i}"} for i in range(1, 8)]  # 7件
        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock(claims_list)
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert len(result["claims"]) == 5
        assert result["claims"][4]["claim_id"] == "C0005"

    def test_exactly_5_claims_not_truncated(self):
        """ちょうど 5 件の場合は切り詰めなし"""
        from app.agent.nodes import make_decompose_claims_node

        claims_list = [{"text": f"主張{i}"} for i in range(1, 6)]  # 5件
        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock(claims_list)
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert len(result["claims"]) == 5

    def test_claim_text_matches_llm_output(self):
        """各 claim の text フィールドが LLM 出力と一致する"""
        from app.agent.nodes import make_decompose_claims_node

        claims_list = [
            {"text": "Python は動的型付け言語である"},
            {"text": "型ヒントは実行時には強制されない"},
        ]
        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock(claims_list)
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        claims = result["claims"]
        assert claims[0]["text"] == "Python は動的型付け言語である"
        assert claims[1]["text"] == "型ヒントは実行時には強制されない"


class TestDecomposeClaimsNodeResetFields:
    def test_evidence_list_reset_to_empty(self):
        """evidence_list が [] にリセットされる (Requirements: 4.6)"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock([{"text": "主張A"}])
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert result["evidence_list"] == []

    def test_verification_results_reset_to_empty(self):
        """verification_results が [] にリセットされる (Requirements: 4.6)"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock([{"text": "主張A"}])
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert result["verification_results"] == []


# ---------------------------------------------------------------------------
# Task 3.2: エラーハンドリング
# ---------------------------------------------------------------------------

class TestDecomposeClaimsNodeErrors:
    def test_zero_claims_returns_claim_decompose_failed(self):
        """LLM が空配列を返した場合 CLAIM_DECOMPOSE_FAILED エラーを返す (Requirements: 1.4)"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = _make_llm_mock([])
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "CLAIM_DECOMPOSE_FAILED"
        assert result["error_status"] == 500

    def test_invalid_llm_raw_response_returns_error(self):
        """llm_raw_response が不正な JSON の場合エラーを返す"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            node = make_decompose_claims_node("test-key")
            result = node(make_state(llm_raw_response="invalid json {{{"))

        assert "error_code" in result
        assert result.get("error_status") is not None

    def test_llm_unauthenticated_returns_api_key_invalid(self):
        """LLM が Unauthenticated 例外を返した場合 GEMINI_API_KEY_INVALID を返す"""
        from app.agent.nodes import make_decompose_claims_node
        from google.api_core import exceptions as google_exceptions

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = google_exceptions.Unauthenticated("auth error")
            mock_cls.return_value = mock_llm
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "GEMINI_API_KEY_INVALID"
        assert result["error_status"] == 401

    def test_llm_permission_denied_returns_error(self):
        """LLM が PermissionDenied 例外を返した場合 GEMINI_API_KEY_PERMISSION_DENIED を返す"""
        from app.agent.nodes import make_decompose_claims_node
        from google.api_core import exceptions as google_exceptions

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = google_exceptions.PermissionDenied("perm error")
            mock_cls.return_value = mock_llm
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "GEMINI_API_KEY_PERMISSION_DENIED"
        assert result["error_status"] == 403

    def test_llm_resource_exhausted_returns_rate_limit(self):
        """LLM が ResourceExhausted 例外を返した場合 GEMINI_RATE_LIMIT を返す"""
        from app.agent.nodes import make_decompose_claims_node
        from google.api_core import exceptions as google_exceptions

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = google_exceptions.ResourceExhausted("rate limit")
            mock_cls.return_value = mock_llm
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "GEMINI_RATE_LIMIT"
        assert result["error_status"] == 429

    def test_llm_service_unavailable_returns_error(self):
        """LLM が ServiceUnavailable 例外を返した場合 GEMINI_SERVICE_UNAVAILABLE を返す"""
        from app.agent.nodes import make_decompose_claims_node
        from google.api_core import exceptions as google_exceptions

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = google_exceptions.ServiceUnavailable("unavailable")
            mock_cls.return_value = mock_llm
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "GEMINI_SERVICE_UNAVAILABLE"
        assert result["error_status"] == 503

    def test_llm_deadline_exceeded_returns_timeout(self):
        """LLM が DeadlineExceeded 例外を返した場合 GEMINI_TIMEOUT を返す"""
        from app.agent.nodes import make_decompose_claims_node
        from google.api_core import exceptions as google_exceptions

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = google_exceptions.DeadlineExceeded("timeout")
            mock_cls.return_value = mock_llm
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "GEMINI_TIMEOUT"
        assert result["error_status"] == 504

    def test_llm_generic_exception_returns_service_unavailable(self):
        """LLM が予期しない例外を返した場合 GEMINI_SERVICE_UNAVAILABLE を返す"""
        from app.agent.nodes import make_decompose_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = Exception("unexpected error")
            mock_cls.return_value = mock_llm
            node = make_decompose_claims_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "GEMINI_SERVICE_UNAVAILABLE"
        assert result["error_status"] == 503
