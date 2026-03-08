"""
Local battle endpoint integration tests (RED first)
"""

from __future__ import annotations

import aiosqlite
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes.quiz_sets import create_quiz_sets_router
from app.db.database import init_db


def _saved_quiz_payload(
    idx: int,
    saved_at: str,
    answer_package: str,
) -> tuple[str, str, str, str, int, str, str]:
    return (
        f"saved-{idx}",
        f"pkg-{idx}",
        saved_at,
        f"topic-{idx}",
        1,
        '{"mode":"keyword","category":"x","source_url":"","selected_quote":"","question_count":1,"keyword":"kw"}',
        answer_package,
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
            _saved_quiz_payload(
                1,
                "2026-01-01T00:00:00+00:00",
                '{"prompt":"Q1","choices":[{"id":"a","text":"A"},{"id":"b","text":"B"}],"correctChoiceId":"a"}',
            ),
        )
        await db.execute(
            """
            INSERT INTO saved_quizzes
            (id, generation_result_id, saved_at, topic, question_count, input_params, answer_package)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            _saved_quiz_payload(
                2,
                "2026-01-02T00:00:00+00:00",
                '{"question":"記述","answer":"A"}',
            ),
        )
        await db.commit()

        app.state.db = db
        app.include_router(create_quiz_sets_router())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


async def test_get_battle_ready_returns_aggregated_counts_and_questions(client):
    create_res = await client.post(
        "/quiz-sets",
        json={"name": "battle", "saved_quiz_ids": ["saved-1", "saved-2"]},
    )
    set_id = create_res.json()["id"]

    res = await client.get(f"/quiz-sets/{set_id}/battle-ready")

    assert res.status_code == 200
    body = res.json()
    assert body["set_id"] == set_id
    assert body["total_item_count"] == 2
    assert body["deleted_excluded_count"] == 0
    assert body["active_item_count"] == 2
    assert body["non_multiple_choice_excluded_count"] == 1
    assert body["eligible_question_count"] == 1
    assert body["startable"] is True
    assert body["reason_code"] is None
    assert len(body["questions"]) == 1


async def test_get_battle_ready_returns_reason_code_when_no_eligible_questions(client):
    create_res = await client.post(
        "/quiz-sets",
        json={"name": "battle-empty", "saved_quiz_ids": ["saved-2"]},
    )
    set_id = create_res.json()["id"]

    res = await client.get(f"/quiz-sets/{set_id}/battle-ready")

    assert res.status_code == 200
    body = res.json()
    assert body["startable"] is False
    assert body["eligible_question_count"] == 0
    assert body["reason_code"] == "NO_ELIGIBLE_MULTIPLE_CHOICE"


async def test_get_battle_ready_returns_404_for_unknown_set(client):
    res = await client.get("/quiz-sets/not-found/battle-ready")

    assert res.status_code == 404
    assert res.json()["detail"] == "QUIZ_SET_NOT_FOUND"
