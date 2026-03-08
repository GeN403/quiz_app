"""
Local battle repository tests (RED first)
"""

from __future__ import annotations

import aiosqlite
import pytest

from app.db.database import init_db
from app.repository.quiz_set import QuizSetRepository
from app.schemas.quiz_set import CreateQuizSetRequest


def _saved_quiz_row(saved_quiz_id: str, saved_at: str, answer_package: str) -> tuple[str, str, str, str, int, str, str]:
    return (
        saved_quiz_id,
        f"pkg-{saved_quiz_id}",
        saved_at,
        f"topic-{saved_quiz_id}",
        1,
        '{"mode":"keyword","category":"x","source_url":"","selected_quote":"","question_count":1,"keyword":"kw"}',
        answer_package,
    )


async def _insert_saved_quiz(
    db: aiosqlite.Connection,
    saved_quiz_id: str,
    saved_at: str,
    answer_package: str,
) -> None:
    await db.execute(
        """
        INSERT INTO saved_quizzes
        (id, generation_result_id, saved_at, topic, question_count, input_params, answer_package)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        _saved_quiz_row(saved_quiz_id, saved_at, answer_package),
    )
    await db.commit()


@pytest.fixture
async def repo_and_db():
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        yield QuizSetRepository(db), db


async def test_get_battle_sources_returns_deleted_flags_and_answer_package(repo_and_db):
    repo, db = repo_and_db

    await _insert_saved_quiz(
        db,
        saved_quiz_id="saved-active",
        saved_at="2026-01-01T00:00:00+00:00",
        answer_package='{"prompt":"Q","choices":[{"id":"a","text":"A"},{"id":"b","text":"B"}],"correctChoiceId":"a"}',
    )
    await _insert_saved_quiz(
        db,
        saved_quiz_id="saved-deleted",
        saved_at="2026-01-02T00:00:00+00:00",
        answer_package='{"prompt":"Q2","choices":[{"id":"a","text":"A"},{"id":"b","text":"B"}],"correctChoiceId":"b"}',
    )

    created = await repo.create(
        CreateQuizSetRequest(name="battle-source", saved_quiz_ids=["saved-active", "saved-deleted"])
    )

    await db.execute("DELETE FROM saved_quizzes WHERE id = ?", ("saved-deleted",))
    await db.commit()

    data = await repo.get_battle_sources(created.id)

    assert data is not None
    set_id, set_name, rows = data
    assert set_id == created.id
    assert set_name == "battle-source"
    assert len(rows) == 2

    row_by_id = {row["saved_quiz_id"]: row for row in rows}
    assert row_by_id["saved-active"]["is_deleted"] is False
    assert row_by_id["saved-active"]["answer_package_json"] is not None
    assert row_by_id["saved-deleted"]["is_deleted"] is True
    assert row_by_id["saved-deleted"]["answer_package_json"] is None
