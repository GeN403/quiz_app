"""
parse_output ノードのユニットテスト (Task 7.4)

Requirements: 2.6, 2.7, 3.1, 3.2, 3.6, 4.7
"""

import json

from app.agent.nodes import parse_output

VALID_JSON = json.dumps({
    "question": "What is the capital of France?",
    "answer": "Paris",
    "Alternative Solutions/Correctness Judgment Criteria": "None",
    "explanation": "Paris is the capital city of France.",
    "source": {
        "title": "Old LLM Title",
        "url": "https://llm-generated-url.com",
        "quote": "LLM generated quote",
    },
})


def make_state(**kwargs):
    base = {
        "llm_raw_response": VALID_JSON,
        "source_url": "https://server-url.com",
        "source_title": "Server Title",
        "selected_quote_final": "Server quote",
        "result": None,
        "error_code": None,
        "error_status": None,
    }
    base.update(kwargs)
    return base


class TestParseOutput:
    def test_valid_json_returns_result(self):
        result = parse_output(make_state())
        assert "error_code" not in result
        assert "result" in result
        assert result["result"] is not None

    def test_source_url_overwritten_with_server_value(self):
        result = parse_output(make_state())
        assert result["result"]["source"]["url"] == "https://server-url.com"

    def test_source_title_overwritten_with_server_value(self):
        result = parse_output(make_state())
        assert result["result"]["source"]["title"] == "Server Title"

    def test_source_quote_overwritten_with_server_value(self):
        result = parse_output(make_state())
        assert result["result"]["source"]["quote"] == "Server quote"

    def test_llm_source_values_completely_ignored(self):
        result = parse_output(make_state())
        source = result["result"]["source"]
        # LLM の値が使われていないこと
        assert source["url"] != "https://llm-generated-url.com"
        assert source["title"] != "Old LLM Title"
        assert source["quote"] != "LLM generated quote"

    def test_invalid_json_returns_ai_invalid_json(self):
        result = parse_output(make_state(llm_raw_response="not valid json {{{"))
        assert result["error_code"] == "AI_INVALID_JSON"
        assert result["error_status"] == 500

    def test_empty_response_returns_ai_invalid_json(self):
        result = parse_output(make_state(llm_raw_response=""))
        assert result["error_code"] == "AI_INVALID_JSON"
        assert result["error_status"] == 500

    def test_array_response_returns_ai_invalid_json(self):
        # parse_output は配列を受け付けない（単一オブジェクトのみ）
        array_json = json.dumps([{"question": "Q?", "answer": "A"}])
        result = parse_output(make_state(llm_raw_response=array_json))
        assert result["error_code"] == "AI_INVALID_JSON"
        assert result["error_status"] == 500

    def test_pydantic_validation_failure_returns_ai_invalid_json(self):
        # 必須フィールドが欠けている JSON
        incomplete_json = json.dumps({
            "question": "Q?",
            # answer, explanation, etc. が欠けている
            "source": {"title": "T", "url": "https://u.com", "quote": ""},
        })
        result = parse_output(make_state(llm_raw_response=incomplete_json))
        assert result["error_code"] == "AI_INVALID_JSON"
        assert result["error_status"] == 500

    def test_result_contains_all_required_keys(self):
        result = parse_output(make_state())
        quiz = result["result"]
        assert "question" in quiz
        assert "answer" in quiz
        assert "Alternative Solutions/Correctness Judgment Criteria" in quiz
        assert "explanation" in quiz
        assert "source" in quiz

    def test_source_contains_required_subkeys(self):
        result = parse_output(make_state())
        source = result["result"]["source"]
        assert "title" in source
        assert "url" in source
        assert "quote" in source

    def test_empty_selected_quote_final_sets_empty_quote(self):
        result = parse_output(make_state(selected_quote_final=""))
        assert result["result"]["source"]["quote"] == ""
