"""
validate_input ノードのユニットテスト (Task 7.1)

Requirements: 2.2, 3.5
"""

from app.agent.nodes import validate_input


def make_state(**kwargs):
    base = {
        "category": "science",
        "question_count": 1,
        "source_type": "url",
        "source_value": "https://example.com",
        "selected_quote": "",
        "source_text": "",
        "source_title": "",
        "source_url": "",
        "selected_quote_final": "",
        "llm_raw_response": "",
        "result": None,
        "error_code": None,
        "error_status": None,
    }
    base.update(kwargs)
    return base


class TestValidateInput:
    def test_valid_input_returns_empty_dict(self):
        result = validate_input(make_state())
        assert result == {}

    def test_question_count_1_passes(self):
        result = validate_input(make_state(question_count=1))
        assert result == {}

    def test_question_count_2_returns_invalid_question_count(self):
        result = validate_input(make_state(question_count=2))
        assert result["error_code"] == "INVALID_QUESTION_COUNT"
        assert result["error_status"] == 400

    def test_question_count_0_returns_invalid_question_count(self):
        result = validate_input(make_state(question_count=0))
        assert result["error_code"] == "INVALID_QUESTION_COUNT"
        assert result["error_status"] == 400

    def test_question_count_5_returns_invalid_question_count(self):
        result = validate_input(make_state(question_count=5))
        assert result["error_code"] == "INVALID_QUESTION_COUNT"
        assert result["error_status"] == 400

    def test_source_type_category_returns_invalid_input(self):
        result = validate_input(make_state(source_type="category"))
        assert result["error_code"] == "INVALID_INPUT"
        assert result["error_status"] == 400

    def test_source_type_unknown_returns_invalid_input(self):
        result = validate_input(make_state(source_type="file"))
        assert result["error_code"] == "INVALID_INPUT"
        assert result["error_status"] == 400

    def test_empty_source_value_returns_invalid_input(self):
        result = validate_input(make_state(source_value=""))
        assert result["error_code"] == "INVALID_INPUT"
        assert result["error_status"] == 400

    def test_ftp_source_value_returns_invalid_input(self):
        result = validate_input(make_state(source_value="ftp://example.com"))
        assert result["error_code"] == "INVALID_INPUT"
        assert result["error_status"] == 400

    def test_no_scheme_source_value_returns_invalid_input(self):
        result = validate_input(make_state(source_value="example.com"))
        assert result["error_code"] == "INVALID_INPUT"
        assert result["error_status"] == 400

    def test_http_url_is_valid(self):
        result = validate_input(make_state(source_value="http://example.com"))
        assert result == {}

    def test_https_url_is_valid(self):
        result = validate_input(make_state(source_value="https://example.com/path?q=1"))
        assert result == {}
