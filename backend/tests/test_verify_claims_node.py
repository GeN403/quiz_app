"""
verify_claims ノードのユニットテスト

Task 5.1, 5.2 (Task 8.3 optional)
Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.2, 4.4, 4.5, 5.1
"""

import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

MAX_VERIFICATION_RETRIES = 3


def make_state(**kwargs):
    base = {
        "claims": [{"claim_id": "C0001", "text": "Python は動的型付け言語である"}],
        "evidence_list": [
            {
                "claim_id": "C0001",
                "evidence_id": "E0001",
                "url": "https://example.com",
                "quote": "Python は動的型付け言語です。",
                "rank": 1,
            }
        ],
        "quiz_text": (
            "QUESTION:\nPython は静的型付け言語でしょうか？\n\n"
            "---\n\nEXPLANATION:\nPython は動的型付け言語です。\n\n"
            "---\n\nALTERNATIVE:\n型ヒントは実行時に強制されない"
        ),
        "verification_attempts": 0,
    }
    base.update(kwargs)
    return base


def _make_pass_response() -> MagicMock:
    return MagicMock(
        content=json.dumps({"verdict": "pass", "reason": "根拠により正確"})
    )


def _make_fail_response(reason: str = "根拠テキストに該当する記述がない") -> MagicMock:
    return MagicMock(
        content=json.dumps({"verdict": "fail", "reason": reason})
    )


# ---------------------------------------------------------------------------
# Task 5.1: 根拠なし自動 fail
# ---------------------------------------------------------------------------

class TestVerifyClaimsNodeAutoFail:
    def test_zero_evidence_yields_auto_fail_without_llm(self):
        """根拠 0 件の主張は LLM を呼ばず自動 fail になる (Requirements: 3.6)"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state(evidence_list=[]))

        mock_llm.invoke.assert_not_called()
        results = result.get("verification_results", [])
        assert len(results) == 1
        assert results[0]["verdict"] == "fail"

    def test_zero_evidence_auto_fail_reason_is_set(self):
        """根拠 0 件の場合、reason が「根拠が取得できないため検証不能」に設定される"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            node = make_verify_claims_node("test-key")
            result = node(make_state(evidence_list=[]))

        results = result["verification_results"]
        assert "根拠" in results[0]["reason"]

    def test_zero_evidence_auto_fail_claim_id_matches(self):
        """自動 fail の claim_id が入力と一致する"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            node = make_verify_claims_node("test-key")
            result = node(make_state(evidence_list=[]))

        assert result["verification_results"][0]["claim_id"] == "C0001"


# ---------------------------------------------------------------------------
# Task 5.1: LLM 判定（根拠あり）
# ---------------------------------------------------------------------------

class TestVerifyClaimsNodeLLMVerdict:
    def test_all_pass_returns_verification_results(self):
        """全主張 pass の場合 verification_results が返される (Requirements: 3.3)"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_pass_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state())

        assert "verification_results" in result
        assert result["verification_results"][0]["verdict"] == "pass"

    def test_all_pass_no_snapshot_in_history(self):
        """全 pass の場合 verification_history への追記なし（スナップショット不要）"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_pass_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state())

        assert "verification_history" not in result

    def test_fail_result_adds_snapshot_to_history(self):
        """fail があった場合 verification_history に [snapshot] が追記される (Requirements: 4.2)"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state())

        history = result.get("verification_history", [])
        assert len(history) == 1

    def test_snapshot_contains_all_required_fields(self):
        """スナップショットが全 6 フィールドを含む (Requirements: 4.5)"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state())

        snapshot = result["verification_history"][0]
        assert "attempt" in snapshot
        assert "quiz_text" in snapshot
        assert "claims" in snapshot
        assert "evidence_list" in snapshot
        assert "verification_results" in snapshot
        assert "failed_claim_ids" in snapshot

    def test_snapshot_attempt_equals_verification_attempts(self):
        """snapshot.attempt が state["verification_attempts"] の値と一致する"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state(verification_attempts=1))

        assert result["verification_history"][0]["attempt"] == 1

    def test_snapshot_failed_claim_ids_correct(self):
        """snapshot.failed_claim_ids が fail した claim_id のリストになる"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state())

        assert result["verification_history"][0]["failed_claim_ids"] == ["C0001"]

    def test_snapshot_quiz_text_matches_state(self):
        """snapshot.quiz_text が state["quiz_text"] と一致する"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            state = make_state()
            result = node(state)

        assert result["verification_history"][0]["quiz_text"] == state["quiz_text"]


# ---------------------------------------------------------------------------
# Task 5.1: INTERNAL_SCHEMA_ERROR（reason が空 or None の fail）
# ---------------------------------------------------------------------------

class TestVerifyClaimsNodeSchemaError:
    def test_fail_with_empty_reason_returns_internal_schema_error(self):
        """verdict=fail かつ reason が空文字列のとき INTERNAL_SCHEMA_ERROR を返す (Requirements: 3.5)"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(
                content=json.dumps({"verdict": "fail", "reason": ""})
            )
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "INTERNAL_SCHEMA_ERROR"
        assert result["error_status"] == 500

    def test_fail_with_none_reason_returns_internal_schema_error(self):
        """verdict=fail かつ reason が null のとき INTERNAL_SCHEMA_ERROR を返す"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(
                content=json.dumps({"verdict": "fail", "reason": None})
            )
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state())

        assert result["error_code"] == "INTERNAL_SCHEMA_ERROR"
        assert result["error_status"] == 500


# ---------------------------------------------------------------------------
# Task 5.2: MAX_VERIFICATION_RETRIES チェック
# ---------------------------------------------------------------------------

class TestVerifyClaimsNodeMaxRetries:
    def test_max_retries_exceeded_returns_unknown_outcome(self):
        """verification_attempts >= MAX のとき unknown 終了理由を返す (Requirements: 5.1, 5.7)"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            # MAX_VERIFICATION_RETRIES = 3 なので attempts=3 で超過
            result = node(make_state(verification_attempts=MAX_VERIFICATION_RETRIES))

        assert result["verification_outcome"]["verdict"] == "unknown"
        assert result["termination_reason_code"] == "MAX_VERIFICATION_ATTEMPTS_REACHED"
        assert "最大" in result["termination_reason_message"]

    def test_max_retries_snapshot_is_added_before_error(self):
        """MAX 超過時でも snapshot が verification_history に追記される（記録保証）"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state(verification_attempts=MAX_VERIFICATION_RETRIES))

        # snapshot が先に追記されていること（reducer delta）
        assert len(result.get("verification_history", [])) == 1

    def test_attempts_below_max_no_max_error(self):
        """attempts < MAX のときは VERIFICATION_MAX_RETRIES_EXCEEDED が返らない"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(make_state(verification_attempts=MAX_VERIFICATION_RETRIES - 1))

        assert result.get("termination_reason_code") != "MAX_VERIFICATION_ATTEMPTS_REACHED"

    def test_max_attempts_uses_disambiguation_parameters(self):
        """max_attempts は固定定数ではなく設定オブジェクトから評価される"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(
                make_state(
                    verification_attempts=1,
                    disambiguation_parameters={"max_attempts": 1},
                )
            )

        assert result["verification_outcome"]["verdict"] == "unknown"
        assert result["termination_reason_code"] == "MAX_VERIFICATION_ATTEMPTS_REACHED"

    def test_invalid_disambiguation_parameters_returns_constraint_violation(self):
        """制約違反パラメータは一貫した失敗応答に変換される"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
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

    def test_max_retries_snapshot_keeps_retry_and_termination_metadata(self):
        """上限終了時、snapshot に retrieval_retry_count と終了理由コードが保存される"""
        from app.agent.nodes import make_verify_claims_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = _make_fail_response()
            mock_cls.return_value = mock_llm
            node = make_verify_claims_node("test-key")
            result = node(
                make_state(
                    verification_attempts=MAX_VERIFICATION_RETRIES,
                    retrieval_retry_count=2,
                )
            )

        snapshot = result["verification_history"][0]
        assert snapshot["retrieval_retry_count"] == 2
        assert snapshot["termination_reason_code"] == "MAX_VERIFICATION_ATTEMPTS_REACHED"
