"""
クイズセット CRUD エンドポイントの統合テスト
"""

from __future__ import annotations

import pytest
import aiosqlite
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes.quiz_sets import create_quiz_sets_router
from app.db.database import init_db


def _saved_quiz_payload(index: int, saved_at: str) -> tuple[str, str, str, str, int, str, str]:
    return (
        f"saved-{index}",
        f"pkg-{index}",
        saved_at,
        f"topic-{index}",
        index,
        '{"mode":"keyword","category":"x","source_url":"","selected_quote":"","question_count":1,"keyword":"kw"}',
        '{"package_id":"pkg","question":"q","answer":"a"}',
    )


@pytest.fixture
async def client():
    app = FastAPI()

    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        await db.execute(
            """
            INSERT INTO saved_quizzes
            (id, generation_result_id, saved_at, topic, question_count, input_params, answer_package)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            _saved_quiz_payload(1, "2026-01-01T00:00:00+00:00"),
        )
        await db.execute(
            """
            INSERT INTO saved_quizzes
            (id, generation_result_id, saved_at, topic, question_count, input_params, answer_package)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            _saved_quiz_payload(2, "2026-01-02T00:00:00+00:00"),
        )
        await db.commit()

        app.state.db = db
        app.include_router(create_quiz_sets_router())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac, db


class TestQuizSetEndpoints:
    async def test_post_quiz_sets_returns_201_and_persists(self, client):
        ac, db = client
        payload = {"name": "セットA", "saved_quiz_ids": ["saved-1", "saved-2"]}

        res = await ac.post("/quiz-sets", json=payload)

        assert res.status_code == 201
        body = res.json()
        assert "id" in body
        async with db.execute("SELECT COUNT(*) FROM quiz_sets WHERE id = ?", (body["id"],)) as cursor:
            assert (await cursor.fetchone())[0] == 1

    async def test_post_quiz_sets_missing_saved_quiz_id_returns_422(self, client):
        ac, _ = client
        payload = {"name": "セットB", "saved_quiz_ids": ["saved-1", "missing-id"]}

        res = await ac.post("/quiz-sets", json=payload)

        assert res.status_code == 422
        assert res.json()["detail"] == "INVALID_SAVED_QUIZ_ID"

    async def test_post_quiz_sets_duplicate_saved_quiz_ids_returns_422(self, client):
        ac, _ = client
        payload = {"name": "セットC", "saved_quiz_ids": ["saved-1", "saved-1"]}

        res = await ac.post("/quiz-sets", json=payload)

        assert res.status_code == 422

    async def test_get_quiz_sets_returns_created_at_desc_with_quiz_count(self, client):
        ac, _ = client
        await ac.post("/quiz-sets", json={"name": "先", "saved_quiz_ids": ["saved-1"]})
        await ac.post("/quiz-sets", json={"name": "後", "saved_quiz_ids": ["saved-1", "saved-2"]})

        res = await ac.get("/quiz-sets")

        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        assert items[0]["name"] == "後"
        assert items[0]["quiz_count"] == 2
        assert items[1]["quiz_count"] == 1

    async def test_get_quiz_set_by_id_returns_deleted_item_flag(self, client):
        ac, db = client
        create_res = await ac.post(
            "/quiz-sets", json={"name": "詳細", "saved_quiz_ids": ["saved-1", "saved-2"]}
        )
        set_id = create_res.json()["id"]

        await db.execute("DELETE FROM saved_quizzes WHERE id = ?", ("saved-2",))
        await db.commit()

        res = await ac.get(f"/quiz-sets/{set_id}")

        assert res.status_code == 200
        items = res.json()["items"]
        assert items[0]["saved_quiz_id"] == "saved-1"
        assert items[0]["is_deleted"] is False
        assert items[1]["saved_quiz_id"] == "saved-2"
        assert items[1]["is_deleted"] is True

    async def test_delete_quiz_set_returns_204_and_keeps_saved_quizzes(self, client):
        ac, db = client
        create_res = await ac.post(
            "/quiz-sets", json={"name": "削除", "saved_quiz_ids": ["saved-1", "saved-2"]}
        )
        set_id = create_res.json()["id"]

        delete_res = await ac.delete(f"/quiz-sets/{set_id}")

        assert delete_res.status_code == 204
        async with db.execute("SELECT COUNT(*) FROM quiz_set_items WHERE quiz_set_id = ?", (set_id,)) as cursor:
            assert (await cursor.fetchone())[0] == 0
        async with db.execute("SELECT COUNT(*) FROM saved_quizzes") as cursor:
            assert (await cursor.fetchone())[0] == 2

    async def test_get_unknown_quiz_set_returns_404(self, client):
        ac, _ = client

        res = await ac.get("/quiz-sets/not-found")

        assert res.status_code == 404
        assert res.json()["detail"] == "QUIZ_SET_NOT_FOUND"
