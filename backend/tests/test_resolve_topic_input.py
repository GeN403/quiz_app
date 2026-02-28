"""
resolve_topic_input ノードのユニットテスト

Requirements: 8.1, 8.2, 8.3
"""

from unittest.mock import patch, MagicMock


def make_state(**kwargs):
    base = {
        "source_text": "これはテスト用のソーステキストです。" * 50,
        "source_title": "テストタイトル",
        "topic": None,
        "resolved_topic": None,
    }
    base.update(kwargs)
    return base


class TestResolveTopicInputNode:
    def test_topic_provided_skips_llm(self):
        """ケース①: topic が指定されている場合 LLM を呼ばずに resolved_topic にユーザー指定値を設定する (Requirements: 8.1)"""
        from app.agent.nodes import make_resolve_topic_input_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            node = make_resolve_topic_input_node("test-api-key")
            result = node(make_state(topic="プログラミング言語"))

        mock_cls.return_value.invoke.assert_not_called()
        assert result["resolved_topic"] == "プログラミング言語"
        assert "error_code" not in result

    def test_topic_not_provided_calls_llm(self):
        """ケース②: topic が None の場合 LLM を呼び出して resolved_topic を設定する (Requirements: 8.2)"""
        from app.agent.nodes import make_resolve_topic_input_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(text="テストトピック")
            mock_cls.return_value = mock_llm

            node = make_resolve_topic_input_node("test-api-key")
            result = node(make_state(topic=None))

        mock_llm.invoke.assert_called_once()
        assert result.get("resolved_topic") == "テストトピック"
        assert "error_code" not in result

    def test_llm_exception_returns_error(self):
        """ケース③: LLM が例外を発生させた場合 error_code=TOPIC_RESOLVE_FAILED を返す (Requirements: 8.3)"""
        from app.agent.nodes import make_resolve_topic_input_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = Exception("LLM error")
            mock_cls.return_value = mock_llm

            node = make_resolve_topic_input_node("test-api-key")
            result = node(make_state(topic=None))

        assert result["error_code"] == "TOPIC_RESOLVE_FAILED"
        assert result["error_status"] == 500


class TestResolveTopicInputNodeBoundary:
    """Task 5.2: 境界値テスト（任意）"""

    def test_llm_returns_long_text_truncated_to_20_chars(self):
        """ケース⑤: LLM が 25 文字を返した場合 resolved_topic が先頭 20 文字に切り詰められる (Requirements: 3.4)"""
        from app.agent.nodes import make_resolve_topic_input_node

        long_topic = "A" * 25  # 25 文字

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(text=long_topic)
            mock_cls.return_value = mock_llm

            node = make_resolve_topic_input_node("test-api-key")
            result = node(make_state(topic=None))

        assert result.get("resolved_topic") == "A" * 20

    def test_llm_returns_empty_string_returns_error(self):
        """ケース⑥: LLM が空文字を返した場合 error_code=TOPIC_RESOLVE_FAILED になる (Requirements: 3.7)"""
        from app.agent.nodes import make_resolve_topic_input_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(text="")
            mock_cls.return_value = mock_llm

            node = make_resolve_topic_input_node("test-api-key")
            result = node(make_state(topic=None))

        assert result["error_code"] == "TOPIC_RESOLVE_FAILED"
        assert result["error_status"] == 500

    def test_llm_returns_whitespace_only_returns_error(self):
        """ケース⑥': LLM が空白のみを返した場合 error_code=TOPIC_RESOLVE_FAILED になる (Requirements: 3.7)"""
        from app.agent.nodes import make_resolve_topic_input_node

        with patch("app.agent.nodes.ChatGoogleGenerativeAI") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(text="   ")
            mock_cls.return_value = mock_llm

            node = make_resolve_topic_input_node("test-api-key")
            result = node(make_state(topic=None))

        assert result["error_code"] == "TOPIC_RESOLVE_FAILED"
        assert result["error_status"] == 500
