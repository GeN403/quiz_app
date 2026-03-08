"""
QuizSetRepository の単体テスト
"""

from __future__ import annotations

import pytest
import aiosqlite
from pydantic import ValidationError

from app.db.database import init_db
from app.repository.quiz_set import InvalidSavedQuizIdError, QuizSetRepository
from app.schemas.quiz_set import CreateQuizSetRequest


def _make_saved_quiz_row(idx: int, saved_at: str) -> tuple[str, str, str, str, int, str, str]:
    saved_quiz_id = f"saved-{idx}"
    return (
        saved_quiz_id,
        f"pkg-{idx}",
        saved_at,
        f"topic-{idx}",
        idx,
        '{"mode":"keyword","category":"x","source_url":"","selected_quote":"","question_count":1,"keyword":"kw"}',
        '{"package_id":"pkg","question":"q","answer":"a"}',
    )


async def _insert_saved_quiz(db: aiosqlite.Connection, idx: int, saved_at: str) -> str:
    row = _make_saved_quiz_row(idx, saved_at)
    await db.execute(
        """
        INSERT INTO saved_quizzes
        (id, generation_result_id, saved_at, topic, question_count, input_params, answer_package)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        row,
    )
    await db.commit()
    return row[0]


@pytest.fixture
async def repo_and_db():
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        yield QuizSetRepository(db), db


class TestCreateQuizSetRequestValidation:
    def test_duplicate_saved_quiz_ids_raise_validation_error(self):
        with pytest.raises(ValidationError):
            CreateQuizSetRequest(name="重複ケース", saved_quiz_ids=["a", "a"])


class TestQuizSetRepository:
    async def test_create_inserts_quiz_sets_and_items(self, repo_and_db):
        repo, db = repo_and_db
        id1 = await _insert_saved_quiz(db, 1, "2026-01-01T00:00:00+00:00")
        id2 = await _insert_saved_quiz(db, 2, "2026-01-02T00:00:00+00:00")

        result = await repo.create(CreateQuizSetRequest(name="セットA", saved_quiz_ids=[id1, id2]))

        assert result.id
        assert result.created_at
        async with db.execute("SELECT COUNT(*) FROM quiz_sets WHERE id = ?", (result.id,)) as cursor:
            assert (await cursor.fetchone())[0] == 1
        async with db.execute("SELECT COUNT(*) FROM quiz_set_items WHERE quiz_set_id = ?", (result.id,)) as cursor:
            assert (await cursor.fetchone())[0] == 2

    async def test_create_raises_for_missing_saved_quiz_id(self, repo_and_db):
        repo, db = repo_and_db
        existing = await _insert_saved_quiz(db, 1, "2026-01-01T00:00:00+00:00")

        with pytest.raises(InvalidSavedQuizIdError):
            await repo.create(
                CreateQuizSetRequest(name="セットB", saved_quiz_ids=[existing, "missing-id"])
            )

    async def test_get_by_id_returns_deleted_item_when_saved_quiz_deleted(self, repo_and_db):
        repo, db = repo_and_db
        id_old = await _insert_saved_quiz(db, 1, "2026-01-01T00:00:00+00:00")
        id_new = await _insert_saved_quiz(db, 2, "2026-01-03T00:00:00+00:00")

        created = await repo.create(
            CreateQuizSetRequest(name="セットC", saved_quiz_ids=[id_old, id_new])
        )

        await db.execute("DELETE FROM saved_quizzes WHERE id = ?", (id_new,))
        await db.commit()

        detail = await repo.get_by_id(created.id)
        assert detail is not None
        assert len(detail.items) == 2
        assert detail.items[0].saved_quiz_id == id_old
        assert detail.items[0].is_deleted is False
        assert detail.items[1].saved_quiz_id == id_new
        assert detail.items[1].is_deleted is True
        assert detail.items[1].saved_at is None
        assert detail.items[1].topic is None
        assert detail.items[1].question_count is None

    async def test_delete_by_id_cascades_items_but_keeps_saved_quizzes(self, repo_and_db):
        repo, db = repo_and_db
        id1 = await _insert_saved_quiz(db, 1, "2026-01-01T00:00:00+00:00")
        id2 = await _insert_saved_quiz(db, 2, "2026-01-02T00:00:00+00:00")
        created = await repo.create(CreateQuizSetRequest(name="セットD", saved_quiz_ids=[id1, id2]))

        deleted = await repo.delete_by_id(created.id)

        assert deleted is True
        async with db.execute("SELECT COUNT(*) FROM quiz_set_items WHERE quiz_set_id = ?", (created.id,)) as cursor:
            assert (await cursor.fetchone())[0] == 0
        async with db.execute("SELECT COUNT(*) FROM saved_quizzes") as cursor:
            assert (await cursor.fetchone())[0] == 2

    async def test_saved_quizzes_delete_is_not_blocked_by_fk(self, repo_and_db):
        repo, db = repo_and_db
        saved_quiz_id = await _insert_saved_quiz(db, 1, "2026-01-01T00:00:00+00:00")
        await repo.create(CreateQuizSetRequest(name="セットE", saved_quiz_ids=[saved_quiz_id]))

        await db.execute("DELETE FROM saved_quizzes WHERE id = ?", (saved_quiz_id,))
        await db.commit()

        async with db.execute("SELECT COUNT(*) FROM saved_quizzes WHERE id = ?", (saved_quiz_id,)) as cursor:
            assert (await cursor.fetchone())[0] == 0
