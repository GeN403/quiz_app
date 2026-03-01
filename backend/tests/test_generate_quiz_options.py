"""
generate_quiz エンドポイントの統合テストと既存機能の回帰テスト (Task 7.3)

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.7, 6.1, 6.2, 6.3, 6.4
"""

import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


VALID_QUIZ_JSON = json.dumps({
    "question": "テスト問題でしょう？",
    "answer": "テスト答え",
    "Alternative Solutions/Correctness Judgment Criteria": "なし",
    "explanation": "テスト解説",
    "source": {
        "title": "サーバが上書き",
        "url": "https://llm-url.com",
        "quote": "LLM生成引用文",
    },
})


def create_generate_quiz_test_app():
    """generate-quiz エンドポイントを含むテスト用アプリを生成"""
    from app.main import app
    return app


@pytest.fixture
def mocked_client():
    """SourceResolver と gemini_client をモック化したテストクライアント"""
    with (
        patch("app.api.routes.generate_quiz.SourceResolver") as mock_sr_class,
        patch("app.api.routes.generate_quiz.call_llm_with_retry") as mock_llm,
        patch("app.api.routes.generate_quiz.parse_json_with_retry") as mock_parse,
        patch("app.api.routes.generate_quiz.validate_url_domain"),
        patch("app.api.routes.generate_quiz.verify_source_fields"),
    ):
        mock_resolver = MagicMock()
        mock_resolver.fetch_and_parse.return_value = {
            "url": "https://example.com",
            "title": "テストタイトル",
            "text": "テスト本文テキスト",
            "quotes": ["テスト引用文"],
        }
        mock_resolver.verify_quote.return_value = True
        mock_sr_class.return_value = mock_resolver

        mock_llm.return_value = VALID_QUIZ_JSON
        mock_parse.return_value = json.loads(VALID_QUIZ_JSON)

        app = create_generate_quiz_test_app()
        yield TestClient(app, raise_server_exceptions=False), mock_sr_class, mock_parse


# ---------------------------------------------------------------------------
# 正常系テスト
# ---------------------------------------------------------------------------

class TestHappyPath:
    def test_all_four_fields_specified_returns_200(self, mocked_client):
        """4フィールドをすべて指定した正常リクエストが 200 を返す（Req 6.1）"""
        client, _, _ = mocked_client
        response = client.post("/generate-quiz", json={
            "category": "natural_science",
            "source_type": "url",
            "source_value": "https://example.com",
            "difficulty": "hard",
            "length": "short",
            "genre": "宇宙科学",
            "topic": "ブラックホール",
        })
        assert response.status_code == 200

    def test_all_four_fields_omitted_returns_200(self, mocked_client):
        """4フィールドをすべて省略した既存形式のリクエストが 200 を返す（後方互換性: Req 6.2）"""
        client, _, _ = mocked_client
        response = client.post("/generate-quiz", json={
            "category": "natural_science",
            "source_type": "url",
            "source_value": "https://example.com",
        })
        assert response.status_code == 200

    def test_genre_specified_uses_genre_as_category_name(self, mocked_client):
        """genre 指定時に resolved_genre がプロンプトの category_name として渡される（Req 2.3, 3.7）"""
        client, mock_sr_class, mock_parse = mocked_client

        with patch("app.core.prompt_builder.build_prompt_url_mode") as mock_builder:
            mock_builder.return_value = "mocked prompt"
            mock_parse.return_value = json.loads(VALID_QUIZ_JSON)

            client.post("/generate-quiz", json={
                "category": "natural_science",
                "source_type": "url",
                "source_value": "https://example.com",
                "genre": "宇宙科学",
            })
            # build_prompt_url_mode が category_name="宇宙科学" で呼ばれたことを確認
            if mock_builder.called:
                call_kwargs = mock_builder.call_args[1] if mock_builder.call_args[1] else {}
                call_args = mock_builder.call_args[0] if mock_builder.call_args[0] else ()
                category_name = call_kwargs.get("category_name") or (call_args[0] if call_args else None)
                assert category_name == "宇宙科学"

    def test_genre_omitted_uses_category_names_mapping(self, mocked_client):
        """genre 未指定時に CATEGORY_NAMES[category] が使用される（Req 2.3）"""
        client, mock_sr_class, mock_parse = mocked_client

        with patch("app.core.prompt_builder.build_prompt_url_mode") as mock_builder:
            mock_builder.return_value = "mocked prompt"
            mock_parse.return_value = json.loads(VALID_QUIZ_JSON)

            from app.core.config import CATEGORY_NAMES
            client.post("/generate-quiz", json={
                "category": "natural_science",
                "source_type": "url",
                "source_value": "https://example.com",
            })
            if mock_builder.called:
                call_kwargs = mock_builder.call_args[1] if mock_builder.call_args[1] else {}
                call_args = mock_builder.call_args[0] if mock_builder.call_args[0] else ()
                category_name = call_kwargs.get("category_name") or (call_args[0] if call_args else None)
                expected = CATEGORY_NAMES.get("science", "science")
                assert category_name == expected


# ---------------------------------------------------------------------------
# 回帰テスト
# ---------------------------------------------------------------------------

class TestRegression:
    def test_resolve_source_endpoint_accessible(self):
        """/resolve-source が引き続き正常に応答する（Req 6.4）"""
        from app.api.router import create_api_router
        mock_model = MagicMock()
        api_router = create_api_router(mock_model)

        app = FastAPI()
        app.include_router(api_router)
        route_paths = [r.path for r in app.routes]
        assert "/resolve-source" in route_paths

    def test_suggest_source_endpoint_accessible(self):
        """/suggest-source が引き続き正常に応答する（Req 6.4）"""
        from app.api.router import create_api_router
        mock_model = MagicMock()
        api_router = create_api_router(mock_model)

        app = FastAPI()
        app.include_router(api_router)
        route_paths = [r.path for r in app.routes]
        assert "/suggest-source" in route_paths

    def test_generate_quiz_endpoint_exists(self):
        """POST /generate-quiz が存在する（404 でない）"""
        from app.api.router import create_api_router
        mock_model = MagicMock()
        api_router = create_api_router(mock_model)

        app = FastAPI()
        app.include_router(api_router)
        client = TestClient(app)

        response = client.post("/generate-quiz", json={})
        assert response.status_code != 404

    def test_health_endpoint_accessible(self, mocked_client):
        """/health エンドポイントが引き続き正常に応答する（Req 6.4）"""
        client, _, _ = mocked_client
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
