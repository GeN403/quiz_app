"""
resolve_seed バリデーションと統合テスト (Task 5.2)

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.schemas.requests import QuizRequest


# ---------------------------------------------------------------------------
# スキーマ単体テスト (Pydantic バリデーション)
# ---------------------------------------------------------------------------

class TestResolveSeedSchema:
    """QuizRequest の resolve_seed フィールドのバリデーションテスト"""

    def test_none_is_valid(self):
        """省略時（None）は有効であること（Req 5.1）"""
        req = QuizRequest(category="natural_science")
        assert req.resolve_seed is None

    def test_zero_is_valid(self):
        """0 は有効な seed として扱われること（Req 5.5: 0 は None と別扱い）"""
        req = QuizRequest(category="natural_science", resolve_seed=0)
        assert req.resolve_seed == 0

    def test_positive_int_is_valid(self):
        """正の整数は有効であること"""
        req = QuizRequest(category="natural_science", resolve_seed=42)
        assert req.resolve_seed == 42

    def test_negative_int_is_valid(self):
        """負の整数は有効であること"""
        req = QuizRequest(category="natural_science", resolve_seed=-1)
        assert req.resolve_seed == -1

    def test_int32_max_is_valid(self):
        """32-bit 上限値（2,147,483,647）は有効であること（Req 5.5）"""
        req = QuizRequest(category="natural_science", resolve_seed=2_147_483_647)
        assert req.resolve_seed == 2_147_483_647

    def test_int32_min_is_valid(self):
        """32-bit 下限値（-2,147,483,648）は有効であること（Req 5.5）"""
        req = QuizRequest(category="natural_science", resolve_seed=-2_147_483_648)
        assert req.resolve_seed == -2_147_483_648

    def test_above_int32_max_raises(self):
        """32-bit 上限超過は ValueError を発生させること（Req 5.5）"""
        with pytest.raises(Exception):
            QuizRequest(category="natural_science", resolve_seed=2_147_483_648)

    def test_below_int32_min_raises(self):
        """32-bit 下限未満は ValueError を発生させること（Req 5.5）"""
        with pytest.raises(Exception):
            QuizRequest(category="natural_science", resolve_seed=-2_147_483_649)

    def test_float_rejected(self):
        """float 値は StrictInt により型エラーで拒否されること（Req 5.5）"""
        with pytest.raises(Exception):
            QuizRequest(category="natural_science", resolve_seed=1.5)

    def test_float_one_rejected(self):
        """1.0（整数に見えるfloat）も StrictInt により拒否されること（Req 5.5 回帰）"""
        with pytest.raises(Exception):
            QuizRequest(category="natural_science", resolve_seed=1.0)

    def test_string_rejected(self):
        """文字列は StrictInt により型エラーで拒否されること（Req 5.5）"""
        with pytest.raises(Exception):
            QuizRequest(category="natural_science", resolve_seed="abc")


# ---------------------------------------------------------------------------
# エンドポイント統合テスト（FastAPI TestClient）
# ---------------------------------------------------------------------------

def make_mock_response():
    """LLM 呼び出しをモックするためのダミークイズデータ"""
    return [
        {
            "question": "テスト問題",
            "answer": "テスト答え",
            "Alternative Solutions/Correctness Judgment Criteria": "なし",
            "explanation": "テスト解説",
            "source": {
                "title": "テストタイトル",
                "url": "https://example.com/test",
                "quote": "テスト引用"
            }
        }
    ]


BASE_REQUEST = {
    "category": "natural_science",
    "source_type": "url",
    "source_value": "https://example.com/test",
    "question_count": 1,
}

MOCK_RESOLVED = {
    "url": "https://example.com/test",
    "title": "テストタイトル",
    "text": "テスト引用を含む長い本文テキスト",
    "quotes": ["テスト引用"],
}


@pytest.fixture
def client():
    return TestClient(app)


def _patch_external(monkeypatch):
    """LLM / SourceResolver の外部呼び出しをモック"""
    import app.api.routes.generate_quiz as gq_module

    mock_resolver_instance = MagicMock()
    mock_resolver_instance.fetch_and_parse.return_value = MOCK_RESOLVED
    mock_resolver_instance.verify_quote.return_value = True

    monkeypatch.setattr(gq_module, "SourceResolver",
                        lambda *a, **kw: mock_resolver_instance)
    monkeypatch.setattr(gq_module, "call_llm_with_retry",
                        lambda *a, **kw: "[{\"question\":\"Q\",\"answer\":\"A\",\"Alternative Solutions/Correctness Judgment Criteria\":\"none\",\"explanation\":\"E\",\"source\":{\"title\":\"T\",\"url\":\"https://example.com/test\",\"quote\":\"テスト引用\"}}]")
    monkeypatch.setattr(gq_module, "parse_json_with_retry",
                        lambda *a, **kw: make_mock_response())
    monkeypatch.setattr(gq_module, "validate_url_domain", lambda *a, **kw: None)


class TestResolveSeedEndpoint:
    """resolve_seed を含むエンドポイント統合テスト"""

    def test_seed_zero_returns_200_with_resolved_config(self, client, monkeypatch):
        """resolve_seed=0 で 200 かつ resolved_config を含むこと（Req 5.3, 6.1, 6.2）"""
        _patch_external(monkeypatch)
        resp = client.post("/generate-quiz", json={**BASE_REQUEST, "resolve_seed": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert "resolved_config" in data
        assert data["resolved_config"]["seed"] == 0

    def test_seed_positive_returns_200_with_resolved_config(self, client, monkeypatch):
        """正の resolve_seed で 200 かつ resolved_config を含むこと（Req 5.3, 6.1）"""
        _patch_external(monkeypatch)
        resp = client.post("/generate-quiz", json={**BASE_REQUEST, "resolve_seed": 42})
        assert resp.status_code == 200
        data = resp.json()
        assert "resolved_config" in data
        assert data["resolved_config"]["seed"] == 42

    def test_resolved_config_has_required_fields(self, client, monkeypatch):
        """resolved_config に seed / difficulty / length / genre が含まれること（Req 6.2）"""
        _patch_external(monkeypatch)
        resp = client.post("/generate-quiz", json={**BASE_REQUEST, "resolve_seed": 99})
        assert resp.status_code == 200
        rc = resp.json()["resolved_config"]
        assert "seed" in rc
        assert "difficulty" in rc
        assert "length" in rc
        assert "genre" in rc

    def test_no_seed_omits_resolved_config(self, client, monkeypatch):
        """resolve_seed 省略時は resolved_config がレスポンスに含まれないこと（Req 6.3）"""
        _patch_external(monkeypatch)
        resp = client.post("/generate-quiz", json=BASE_REQUEST)
        assert resp.status_code == 200
        assert "resolved_config" not in resp.json()

    def test_explicit_difficulty_honored(self, client, monkeypatch):
        """resolve_seed 指定 + difficulty 明示時は resolved_config.difficulty がユーザー指定値と一致すること（Req 5.2）"""
        _patch_external(monkeypatch)
        resp = client.post("/generate-quiz", json={
            **BASE_REQUEST,
            "resolve_seed": 42,
            "difficulty": "hard",
        })
        assert resp.status_code == 200
        assert resp.json()["resolved_config"]["difficulty"] == "hard"

    def test_same_seed_same_resolved_config(self, client, monkeypatch):
        """同一 seed の 2 回リクエストで resolved_config の全フィールドが一致すること（Req 5.4）"""
        _patch_external(monkeypatch)
        payload = {**BASE_REQUEST, "resolve_seed": 12345}
        resp1 = client.post("/generate-quiz", json=payload)
        resp2 = client.post("/generate-quiz", json=payload)
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["resolved_config"] == resp2.json()["resolved_config"]

    def test_resolved_config_difficulty_in_candidates(self, client, monkeypatch):
        """resolved_config.difficulty が有効値（easy/normal/hard）であること（Req 5.3）"""
        _patch_external(monkeypatch)
        resp = client.post("/generate-quiz", json={**BASE_REQUEST, "resolve_seed": 7})
        assert resp.status_code == 200
        assert resp.json()["resolved_config"]["difficulty"] in ("easy", "normal", "hard")

    def test_resolved_config_length_in_candidates(self, client, monkeypatch):
        """resolved_config.length が有効値（short/medium/long）であること（Req 5.3）"""
        _patch_external(monkeypatch)
        resp = client.post("/generate-quiz", json={**BASE_REQUEST, "resolve_seed": 7})
        assert resp.status_code == 200
        assert resp.json()["resolved_config"]["length"] in ("short", "medium", "long")


class TestResolveSeedValidationErrors:
    """resolve_seed のバリデーションエラーテスト（Req 5.5, 5.6）"""

    def test_above_int32_returns_invalid_seed(self, client):
        """32-bit 上限超過は {"detail": "INVALID_SEED"} (HTTP 422) を返すこと（Req 5.5, 5.6）"""
        resp = client.post("/generate-quiz", json={
            **BASE_REQUEST,
            "resolve_seed": 2_147_483_648,
        })
        assert resp.status_code == 422
        assert resp.json()["detail"] == "INVALID_SEED"

    def test_below_int32_returns_invalid_seed(self, client):
        """32-bit 下限未満は {"detail": "INVALID_SEED"} (HTTP 422) を返すこと（Req 5.5, 5.6）"""
        resp = client.post("/generate-quiz", json={
            **BASE_REQUEST,
            "resolve_seed": -2_147_483_649,
        })
        assert resp.status_code == 422
        assert resp.json()["detail"] == "INVALID_SEED"

    def test_string_returns_invalid_seed(self, client):
        """文字列は {"detail": "INVALID_SEED"} (HTTP 422) を返すこと（Req 5.6）"""
        resp = client.post("/generate-quiz", json={
            **BASE_REQUEST,
            "resolve_seed": "abc",
        })
        assert resp.status_code == 422
        assert resp.json()["detail"] == "INVALID_SEED"

    def test_float_returns_invalid_seed(self, client):
        """float（1.5）は {"detail": "INVALID_SEED"} (HTTP 422) を返すこと（Req 5.6）"""
        resp = client.post("/generate-quiz", json={
            **BASE_REQUEST,
            "resolve_seed": 1.5,
        })
        assert resp.status_code == 422
        assert resp.json()["detail"] == "INVALID_SEED"

    def test_float_one_returns_invalid_seed(self, client):
        """1.0（整数に見えるfloat）は {"detail": "INVALID_SEED"} (HTTP 422) を返すこと（Req 5.6 回帰）"""
        resp = client.post("/generate-quiz", json={
            **BASE_REQUEST,
            "resolve_seed": 1.0,
        })
        assert resp.status_code == 422
        assert resp.json()["detail"] == "INVALID_SEED"
