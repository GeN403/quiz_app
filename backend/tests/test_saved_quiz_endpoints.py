"""
保存済みクイズ CRUD エンドポイントの統合テスト（Task 3 / 9.2 対応）

httpx.AsyncClient とインメモリ DB を使用してテストする。
"""

import pytest
import aiosqlite
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.database import init_db
from app.api.routes.saved_quizzes import create_saved_quizzes_router

# ---------------------------------------------------------------------------
# テストデータ
# ---------------------------------------------------------------------------

VALID_PAYLOAD = {
    "input_params": {
        "mode": "keyword",
        "category": "科学",
        "source_url": "",
        "selected_quote": "",
        "question_count": 5,
        "keyword": "宇宙",
    },
    "answer_package": {
        "package_id": "pkg_test001",
        "question": "宇宙の年齢は？",
        "answer": "138億年",
    },
}


def make_payload(package_id: str = "pkg_test001") -> dict:
    payload = {**VALID_PAYLOAD}
    payload["answer_package"] = {**VALID_PAYLOAD["answer_package"], "package_id": package_id}
    return payload


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """インメモリ DB を持つ FastAPI テストクライアント"""
    app = FastAPI()

    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        app.state.db = db
        app.include_router(create_saved_quizzes_router())

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


# ---------------------------------------------------------------------------
# Task 3.1 — POST /saved-quizzes
# ---------------------------------------------------------------------------


class TestPostSavedQuizzes:
    async def test_save_returns_201(self, client):
        res = await client.post("/saved-quizzes", json=make_payload())
        assert res.status_code == 201

    async def test_save_response_has_id_and_saved_at(self, client):
        res = await client.post("/saved-quizzes", json=make_payload())
        body = res.json()
        assert "id" in body
        assert "saved_at" in body

    async def test_save_duplicate_returns_409(self, client):
        await client.post("/saved-quizzes", json=make_payload("pkg_dup"))
        res = await client.post("/saved-quizzes", json=make_payload("pkg_dup"))
        assert res.status_code == 409
        assert res.json()["detail"] == "DUPLICATE_GENERATION_RESULT"

    async def test_save_invalid_schema_returns_422(self, client):
        bad_payload = {
            "input_params": {
                "mode": "keyword",
                "category": "x",
                "source_url": "",
                "selected_quote": "",
                "question_count": 1,
            },
            "answer_package": {},  # package_id なし
        }
        res = await client.post("/saved-quizzes", json=bad_payload)
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# Task 3.2 — GET /saved-quizzes
# ---------------------------------------------------------------------------


class TestGetSavedQuizzes:
    async def test_list_returns_200(self, client):
        res = await client.get("/saved-quizzes")
        assert res.status_code == 200

    async def test_list_empty_by_default(self, client):
        res = await client.get("/saved-quizzes")
        assert res.json() == {"items": []}

    async def test_list_returns_saved_items(self, client):
        await client.post("/saved-quizzes", json=make_payload("pkg_a"))
        await client.post("/saved-quizzes", json=make_payload("pkg_b"))
        res = await client.get("/saved-quizzes")
        items = res.json()["items"]
        assert len(items) == 2

    async def test_list_item_includes_question_and_answer(self, client):
        await client.post("/saved-quizzes", json=make_payload("pkg_question_answer"))
        res = await client.get("/saved-quizzes")
        item = res.json()["items"][0]
        assert item["question"] == VALID_PAYLOAD["answer_package"]["question"]
        assert item["answer"] == VALID_PAYLOAD["answer_package"]["answer"]

    async def test_list_items_saved_at_desc_order(self, client):
        await client.post("/saved-quizzes", json=make_payload("pkg_first"))
        await client.post("/saved-quizzes", json=make_payload("pkg_second"))
        res = await client.get("/saved-quizzes")
        items = res.json()["items"]
        # 後に保存した方が先頭
        assert items[0]["generation_result_id"] == "pkg_second"
        assert items[1]["generation_result_id"] == "pkg_first"


# ---------------------------------------------------------------------------
# Task 3.2 — GET /saved-quizzes/{id}
# ---------------------------------------------------------------------------


class TestGetSavedQuizDetail:
    async def test_detail_returns_200(self, client):
        save_res = await client.post("/saved-quizzes", json=make_payload())
        record_id = save_res.json()["id"]
        res = await client.get(f"/saved-quizzes/{record_id}")
        assert res.status_code == 200

    async def test_detail_includes_input_params_and_answer_package(self, client):
        save_res = await client.post("/saved-quizzes", json=make_payload())
        record_id = save_res.json()["id"]
        res = await client.get(f"/saved-quizzes/{record_id}")
        body = res.json()
        assert "input_params" in body
        assert "answer_package" in body
        assert body["answer_package"]["package_id"] == "pkg_test001"

    async def test_detail_not_found_returns_404(self, client):
        res = await client.get("/saved-quizzes/nonexistent-id")
        assert res.status_code == 404
        assert res.json()["detail"] == "SAVED_QUIZ_NOT_FOUND"


# ---------------------------------------------------------------------------
# Task 3.3 — DELETE /saved-quizzes/{id}
# ---------------------------------------------------------------------------


class TestDeleteSavedQuiz:
    async def test_delete_returns_204(self, client):
        save_res = await client.post("/saved-quizzes", json=make_payload())
        record_id = save_res.json()["id"]
        res = await client.delete(f"/saved-quizzes/{record_id}")
        assert res.status_code == 204

    async def test_delete_removes_record(self, client):
        save_res = await client.post("/saved-quizzes", json=make_payload())
        record_id = save_res.json()["id"]
        await client.delete(f"/saved-quizzes/{record_id}")
        res = await client.get(f"/saved-quizzes/{record_id}")
        assert res.status_code == 404

    async def test_delete_not_found_returns_404(self, client):
        res = await client.delete("/saved-quizzes/nonexistent-id")
        assert res.status_code == 404
