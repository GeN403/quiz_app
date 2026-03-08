"""
QuizSetRepository — SQLite を使ったクイズセットのデータアクセス層
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict
from uuid import uuid4

import aiosqlite

from app.schemas.quiz_set import (
    CreateQuizSetRequest,
    QuizSetDetail,
    QuizSetDetailItem,
    QuizSetListItem,
    QuizSetResponse,
)


class InvalidSavedQuizIdError(Exception):
    """指定した saved_quiz_id が saved_quizzes に存在しない場合に raise する"""


class BattleSourceRow(TypedDict):
    saved_quiz_id: str
    is_deleted: bool
    answer_package_json: str | None


class QuizSetRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def create(self, request: CreateQuizSetRequest) -> QuizSetResponse:
        placeholders = ", ".join(["?"] * len(request.saved_quiz_ids))
        sql = f"SELECT id FROM saved_quizzes WHERE id IN ({placeholders})"

        async with self._db.execute(sql, tuple(request.saved_quiz_ids)) as cursor:
            rows = await cursor.fetchall()

        existing_ids = {row[0] for row in rows}
        if len(existing_ids) != len(request.saved_quiz_ids):
            raise InvalidSavedQuizIdError("one or more saved_quiz_ids do not exist")

        set_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        await self._db.execute("BEGIN")
        try:
            await self._db.execute(
                """
                INSERT INTO quiz_sets (id, name, created_at)
                VALUES (?, ?, ?)
                """,
                (set_id, request.name, created_at),
            )
            await self._db.executemany(
                """
                INSERT INTO quiz_set_items (quiz_set_id, saved_quiz_id)
                VALUES (?, ?)
                """,
                [(set_id, saved_quiz_id) for saved_quiz_id in request.saved_quiz_ids],
            )
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise

        return QuizSetResponse(id=set_id, created_at=created_at)

    async def list_all(self) -> list[QuizSetListItem]:
        async with self._db.execute(
            """
            SELECT qs.id, qs.name, qs.created_at, COUNT(qsi.saved_quiz_id) AS quiz_count
            FROM quiz_sets qs
            LEFT JOIN quiz_set_items qsi ON qsi.quiz_set_id = qs.id
            GROUP BY qs.id, qs.name, qs.created_at
            ORDER BY qs.created_at DESC, qs.rowid DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            QuizSetListItem(
                id=row[0],
                name=row[1],
                created_at=row[2],
                quiz_count=row[3],
            )
            for row in rows
        ]

    async def get_by_id(self, set_id: str) -> QuizSetDetail | None:
        async with self._db.execute(
            """
            SELECT id, name, created_at
            FROM quiz_sets
            WHERE id = ?
            """,
            (set_id,),
        ) as cursor:
            set_row = await cursor.fetchone()

        if set_row is None:
            return None

        async with self._db.execute(
            """
            SELECT qsi.saved_quiz_id, sq.topic, sq.saved_at, sq.question_count,
                   CASE WHEN sq.id IS NULL THEN 1 ELSE 0 END AS is_deleted
            FROM quiz_set_items qsi
            LEFT JOIN saved_quizzes sq ON sq.id = qsi.saved_quiz_id
            WHERE qsi.quiz_set_id = ?
            ORDER BY sq.saved_at DESC
            """,
            (set_id,),
        ) as cursor:
            item_rows = await cursor.fetchall()

        items = [
            QuizSetDetailItem(
                saved_quiz_id=row[0],
                topic=row[1],
                saved_at=row[2],
                question_count=row[3],
                is_deleted=bool(row[4]),
            )
            for row in item_rows
        ]

        return QuizSetDetail(
            id=set_row[0],
            name=set_row[1],
            created_at=set_row[2],
            items=items,
        )

    async def get_battle_sources(self, set_id: str) -> tuple[str, str, list[BattleSourceRow]] | None:
        async with self._db.execute(
            """
            SELECT id, name
            FROM quiz_sets
            WHERE id = ?
            """,
            (set_id,),
        ) as cursor:
            set_row = await cursor.fetchone()

        if set_row is None:
            return None

        async with self._db.execute(
            """
            SELECT qsi.saved_quiz_id,
                   CASE WHEN sq.id IS NULL THEN 1 ELSE 0 END AS is_deleted,
                   sq.answer_package
            FROM quiz_set_items qsi
            LEFT JOIN saved_quizzes sq ON sq.id = qsi.saved_quiz_id
            WHERE qsi.quiz_set_id = ?
            ORDER BY qsi.saved_quiz_id ASC
            """,
            (set_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        source_rows: list[BattleSourceRow] = [
            {
                "saved_quiz_id": row[0],
                "is_deleted": bool(row[1]),
                "answer_package_json": row[2],
            }
            for row in rows
        ]

        return set_row[0], set_row[1], source_rows

    async def delete_by_id(self, set_id: str) -> bool:
        cursor = await self._db.execute(
            "DELETE FROM quiz_sets WHERE id = ?",
            (set_id,),
        )
        await self._db.commit()
        return cursor.rowcount > 0

