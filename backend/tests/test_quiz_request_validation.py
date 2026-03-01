"""
QuizRequest バリデーターと RequestValidationError ハンドラのユニットテスト (Task 7.1)

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11, 2.6
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.schemas.requests import QuizRequest


# ---------------------------------------------------------------------------
# QuizRequest 直接バリデーションテスト（モデルの単体テスト）
# ---------------------------------------------------------------------------

class TestQuizRequestNewFields:
    """新フィールドのモデルレベルバリデーション（Requirements: 1.1〜1.9, 2.6）"""

    def test_all_new_fields_optional_omitted(self):
        """4フィールドを省略したリクエストが正常に通る（後方互換性: Req 1.9）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com")
        assert req.difficulty is None
        assert req.length is None
        assert req.genre is None
        assert req.topic is None

    def test_valid_difficulty_easy(self):
        """difficulty='easy' が受け入れられる（Req 1.1）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", difficulty="easy")
        assert req.difficulty == "easy"

    def test_valid_difficulty_normal(self):
        """difficulty='normal' が受け入れられる（Req 1.1）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", difficulty="normal")
        assert req.difficulty == "normal"

    def test_valid_difficulty_hard(self):
        """difficulty='hard' が受け入れられる（Req 1.1）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", difficulty="hard")
        assert req.difficulty == "hard"

    def test_invalid_difficulty_raises_value_error(self):
        """difficulty に無効値で ValueError（INVALID_DIFFICULTY）が送出される（Req 1.5）"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            QuizRequest(category="science", source_type="url", source_value="https://example.com", difficulty="extreme")
        errors = exc_info.value.errors()
        assert any("INVALID_DIFFICULTY" in str(e) for e in errors)

    def test_valid_length_short(self):
        """length='short' が受け入れられる（Req 1.2）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", length="short")
        assert req.length == "short"

    def test_valid_length_medium(self):
        """length='medium' が受け入れられる（Req 1.2）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", length="medium")
        assert req.length == "medium"

    def test_valid_length_long(self):
        """length='long' が受け入れられる（Req 1.2）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", length="long")
        assert req.length == "long"

    def test_invalid_length_raises_value_error(self):
        """length に無効値で ValueError（INVALID_LENGTH）が送出される（Req 1.6）"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            QuizRequest(category="science", source_type="url", source_value="https://example.com", length="tiny")
        errors = exc_info.value.errors()
        assert any("INVALID_LENGTH" in str(e) for e in errors)

    def test_genre_within_50_chars(self):
        """genre が 50 文字以内で受け入れられる（Req 1.3）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", genre="a" * 50)
        assert req.genre == "a" * 50

    def test_genre_over_50_chars_raises_value_error(self):
        """genre が 50 文字超で ValueError（GENRE_TOO_LONG）が送出される（Req 1.7）"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            QuizRequest(category="science", source_type="url", source_value="https://example.com", genre="a" * 51)
        errors = exc_info.value.errors()
        assert any("GENRE_TOO_LONG" in str(e) for e in errors)

    def test_topic_within_100_chars(self):
        """topic が 100 文字以内で受け入れられる（Req 1.4）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", topic="a" * 100)
        assert req.topic == "a" * 100

    def test_topic_over_100_chars_raises_value_error(self):
        """topic が 100 文字超で ValueError（TOPIC_TOO_LONG）が送出される（Req 1.8）"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            QuizRequest(category="science", source_type="url", source_value="https://example.com", topic="a" * 101)
        errors = exc_info.value.errors()
        assert any("TOPIC_TOO_LONG" in str(e) for e in errors)

    # --- trim → None 正規化テスト (Req 2.6) ---

    def test_empty_string_difficulty_normalized_to_none(self):
        """difficulty='' が None に正規化される（Req 2.6）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", difficulty="")
        assert req.difficulty is None

    def test_whitespace_only_difficulty_normalized_to_none(self):
        """difficulty='  ' が None に正規化される（Req 2.6）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", difficulty="   ")
        assert req.difficulty is None

    def test_empty_string_length_normalized_to_none(self):
        """length='' が None に正規化される（Req 2.6）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", length="")
        assert req.length is None

    def test_empty_string_genre_normalized_to_none(self):
        """genre='' が None に正規化される（Req 2.6）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", genre="")
        assert req.genre is None

    def test_empty_string_topic_normalized_to_none(self):
        """topic='' が None に正規化される（Req 2.6）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", topic="")
        assert req.topic is None

    def test_whitespace_genre_normalized_to_none_skips_length_check(self):
        """genre=spaces が None に正規化されるため GENRE_TOO_LONG は発生しない（Req 2.6）"""
        req = QuizRequest(category="science", source_type="url", source_value="https://example.com", genre="   ")
        assert req.genre is None


# ---------------------------------------------------------------------------
# HTTP エンドポイントレベルのテスト（RequestValidationError ハンドラ確認）
# ---------------------------------------------------------------------------

def create_test_app():
    """generate-quiz エンドポイントを含むテスト用アプリを生成"""
    from app.api.router import create_api_router
    from app.main import app as main_app
    return main_app


@pytest.fixture
def client():
    """テストクライアント（main.py のアプリをそのまま使用）"""
    app = create_test_app()
    return TestClient(app, raise_server_exceptions=False)


class TestRequestValidationErrorHandler:
    """RequestValidationError ハンドラの HTTP レベルテスト（Req 1.10, 1.11）"""

    def test_invalid_difficulty_returns_422_with_code(self, client):
        """difficulty 無効値 → 422 {"detail": "INVALID_DIFFICULTY"}（Req 1.10）"""
        response = client.post("/generate-quiz", json={
            "category": "science",
            "source_type": "url",
            "source_value": "https://example.com",
            "difficulty": "extreme",
        })
        assert response.status_code == 422
        assert response.json() == {"detail": "INVALID_DIFFICULTY"}

    def test_invalid_length_returns_422_with_code(self, client):
        """length 無効値 → 422 {"detail": "INVALID_LENGTH"}（Req 1.10）"""
        response = client.post("/generate-quiz", json={
            "category": "science",
            "source_type": "url",
            "source_value": "https://example.com",
            "length": "tiny",
        })
        assert response.status_code == 422
        assert response.json() == {"detail": "INVALID_LENGTH"}

    def test_genre_too_long_returns_422_with_code(self, client):
        """genre 50文字超 → 422 {"detail": "GENRE_TOO_LONG"}（Req 1.10）"""
        response = client.post("/generate-quiz", json={
            "category": "science",
            "source_type": "url",
            "source_value": "https://example.com",
            "genre": "a" * 51,
        })
        assert response.status_code == 422
        assert response.json() == {"detail": "GENRE_TOO_LONG"}

    def test_topic_too_long_returns_422_with_code(self, client):
        """topic 100文字超 → 422 {"detail": "TOPIC_TOO_LONG"}（Req 1.10）"""
        response = client.post("/generate-quiz", json={
            "category": "science",
            "source_type": "url",
            "source_value": "https://example.com",
            "topic": "a" * 101,
        })
        assert response.status_code == 422
        assert response.json() == {"detail": "TOPIC_TOO_LONG"}

    def test_missing_category_returns_default_422_list_format(self, client):
        """既存フィールド（category）欠落 → FastAPI デフォルトの 422 リスト形式（Req 1.11）"""
        response = client.post("/generate-quiz", json={
            "source_type": "url",
            "source_value": "https://example.com",
        })
        assert response.status_code == 422
        # デフォルト形式はリスト形式の detail
        body = response.json()
        assert isinstance(body["detail"], list), "既存フィールドのエラーはリスト形式であること"

    def test_new_fields_omitted_passes_validation(self, client):
        """新フィールド省略で 422 にならない（バリデーション通過: Req 1.9）"""
        # 400 (ドメイン検証失敗) は想定内、422 でなければOK
        response = client.post("/generate-quiz", json={
            "category": "science",
            "source_type": "url",
            "source_value": "https://example.com",
        })
        assert response.status_code != 422
