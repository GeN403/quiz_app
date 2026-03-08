"""
DB 初期化処理のユニットテスト (Task 1.1)

Requirements: 5.1, 5.2, 5.3
"""

import pytest
import aiosqlite

from app.db.database import init_db


@pytest.mark.asyncio
async def test_init_db_creates_table():
    """saved_quizzes テーブルが作成される"""
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='saved_quizzes'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "saved_quizzes"


@pytest.mark.asyncio
async def test_init_db_table_has_required_columns():
    """必須カラムがすべて存在する"""
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        cursor = await db.execute("PRAGMA table_info(saved_quizzes)")
        columns = {row[1] for row in await cursor.fetchall()}
        assert "id" in columns
        assert "generation_result_id" in columns
        assert "saved_at" in columns
        assert "topic" in columns
        assert "question_count" in columns
        assert "input_params" in columns
        assert "answer_package" in columns


@pytest.mark.asyncio
async def test_init_db_creates_index():
    """saved_at DESC インデックスが作成される"""
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_saved_quizzes_saved_at'"
        )
        row = await cursor.fetchone()
        assert row is not None


@pytest.mark.asyncio
async def test_init_db_is_idempotent():
    """2 回呼び出しても例外が発生しない (CREATE TABLE IF NOT EXISTS)"""
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        await init_db(db)  # 2 回目も正常終了


@pytest.mark.asyncio
async def test_init_db_generation_result_id_unique_constraint():
    """generation_result_id に UNIQUE 制約が設定されている"""
    async with aiosqlite.connect(":memory:") as db:
        await init_db(db)
        await db.execute(
            "INSERT INTO saved_quizzes VALUES (?,?,?,?,?,?,?)",
            ("id-1", "pkg-abc", "2026-01-01T00:00:00", "topic", 1, "{}", "{}"),
        )
        await db.commit()
        with pytest.raises(Exception):
            await db.execute(
                "INSERT INTO saved_quizzes VALUES (?,?,?,?,?,?,?)",
                ("id-2", "pkg-abc", "2026-01-02T00:00:00", "topic", 1, "{}", "{}"),
            )
            await db.commit()
