"""
保存済みクイズ Pydantic スキーマのユニットテスト (Task 1.2)

Requirements: 1.5, 5.5
"""

import pytest
from pydantic import ValidationError

from app.schemas.saved_quiz import (
    GenerationInputParams,
    SaveQuizRequest,
    SavedQuizListItem,
    SavedQuizDetail,
    SavedQuizResponse,
)

# ---------------------------------------------------------------------------
# テスト用フィクスチャデータ
# ---------------------------------------------------------------------------

VALID_INPUT_PARAMS = {
    "mode": "keyword",
    "category": "non_section",
    "source_url": "https://example.com/article",
    "selected_quote": "Python is a programming language.",
    "question_count": 1,
    "keyword": "Python",
}

VALID_ANSWER_PACKAGE = {
    "package_id": "pkg_abc123def456",
    "question": {"text": "What is Python?"},
    "answer": {"text": "A programming language", "answer_type": "string"},
    "explanation": "Python is a high-level language.",
    "status": "complete",
}


# ---------------------------------------------------------------------------
# GenerationInputParams
# ---------------------------------------------------------------------------


class TestGenerationInputParams:
    def test_valid_keyword_mode(self):
        params = GenerationInputParams(**VALID_INPUT_PARAMS)
        assert params.mode == "keyword"
        assert params.keyword == "Python"

    def test_valid_url_mode(self):
        params = GenerationInputParams(
            mode="url",
            category="non_section",
            source_url="https://example.com",
            selected_quote="some quote",
            question_count=2,
        )
        assert params.mode == "url"
        assert params.keyword is None

    def test_valid_category_mode(self):
        params = GenerationInputParams(
            mode="category",
            category="science",
            source_url="https://example.com",
            selected_quote="quote",
            question_count=1,
        )
        assert params.mode == "category"

    def test_optional_fields_default_none(self):
        params = GenerationInputParams(
            mode="url",
            category="non_section",
            source_url="https://example.com",
            selected_quote="quote",
            question_count=1,
        )
        assert params.difficulty is None
        assert params.length is None
        assert params.genre is None
        assert params.keyword is None

    def test_all_optional_fields(self):
        params = GenerationInputParams(
            mode="keyword",
            category="non_section",
            source_url="https://example.com",
            selected_quote="quote",
            question_count=3,
            difficulty="easy",
            length="short",
            genre="science",
            keyword="DNA",
        )
        assert params.difficulty == "easy"
        assert params.length == "short"
        assert params.genre == "science"

    def test_invalid_mode_raises(self):
        with pytest.raises(ValidationError):
            GenerationInputParams(
                mode="invalid",
                category="non_section",
                source_url="https://example.com",
                selected_quote="quote",
                question_count=1,
            )

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            GenerationInputParams(
                mode="url",
                # source_url missing
                category="non_section",
                selected_quote="quote",
                question_count=1,
            )


# ---------------------------------------------------------------------------
# SaveQuizRequest
# ---------------------------------------------------------------------------


class TestSaveQuizRequest:
    def test_valid_request(self):
        req = SaveQuizRequest(
            input_params=VALID_INPUT_PARAMS,
            answer_package=VALID_ANSWER_PACKAGE,
        )
        assert req.generation_result_id == "pkg_abc123def456"

    def test_generation_result_id_derived_from_package_id(self):
        """generation_result_id は answer_package.package_id と同一値"""
        req = SaveQuizRequest(
            input_params=VALID_INPUT_PARAMS,
            answer_package=VALID_ANSWER_PACKAGE,
        )
        assert req.generation_result_id == req.answer_package["package_id"]

    def test_missing_package_id_raises(self):
        ap = {k: v for k, v in VALID_ANSWER_PACKAGE.items() if k != "package_id"}
        with pytest.raises(ValidationError):
            SaveQuizRequest(input_params=VALID_INPUT_PARAMS, answer_package=ap)

    def test_empty_package_id_raises(self):
        ap = {**VALID_ANSWER_PACKAGE, "package_id": ""}
        with pytest.raises(ValidationError):
            SaveQuizRequest(input_params=VALID_INPUT_PARAMS, answer_package=ap)

    def test_missing_question_raises(self):
        ap = {k: v for k, v in VALID_ANSWER_PACKAGE.items() if k != "question"}
        with pytest.raises(ValidationError):
            SaveQuizRequest(input_params=VALID_INPUT_PARAMS, answer_package=ap)

    def test_missing_answer_raises(self):
        ap = {k: v for k, v in VALID_ANSWER_PACKAGE.items() if k != "answer"}
        with pytest.raises(ValidationError):
            SaveQuizRequest(input_params=VALID_INPUT_PARAMS, answer_package=ap)

    def test_no_generation_result_id_field(self):
        """SaveQuizRequest に generation_result_id フィールドは存在しない"""
        req = SaveQuizRequest(
            input_params=VALID_INPUT_PARAMS,
            answer_package=VALID_ANSWER_PACKAGE,
        )
        assert "generation_result_id" not in SaveQuizRequest.model_fields


# ---------------------------------------------------------------------------
# SavedQuizResponse
# ---------------------------------------------------------------------------


class TestSavedQuizResponse:
    def test_valid(self):
        resp = SavedQuizResponse(id="uuid-1", saved_at="2026-01-01T00:00:00")
        assert resp.id == "uuid-1"
        assert resp.saved_at == "2026-01-01T00:00:00"


# ---------------------------------------------------------------------------
# SavedQuizListItem
# ---------------------------------------------------------------------------


class TestSavedQuizListItem:
    def test_valid(self):
        item = SavedQuizListItem(
            id="uuid-1",
            generation_result_id="pkg_abc",
            saved_at="2026-01-01T00:00:00",
            topic="Python",
            question_count=2,
        )
        assert item.topic == "Python"
        assert item.question_count == 2


# ---------------------------------------------------------------------------
# SavedQuizDetail
# ---------------------------------------------------------------------------


class TestSavedQuizDetail:
    def test_valid(self):
        detail = SavedQuizDetail(
            id="uuid-1",
            generation_result_id="pkg_abc",
            saved_at="2026-01-01T00:00:00",
            input_params=VALID_INPUT_PARAMS,
            answer_package=VALID_ANSWER_PACKAGE,
        )
        assert detail.input_params.mode == "keyword"
        assert detail.answer_package["package_id"] == "pkg_abc123def456"
