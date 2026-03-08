"""
SQLite データベース初期化ユーティリティ
"""

import aiosqlite

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS saved_quizzes (
    id                   TEXT PRIMARY KEY,
    generation_result_id TEXT UNIQUE NOT NULL,
    saved_at             TEXT NOT NULL,
    topic                TEXT NOT NULL,
    question_count       INTEGER NOT NULL,
    input_params         TEXT NOT NULL,
    answer_package       TEXT NOT NULL
)
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_saved_quizzes_saved_at
ON saved_quizzes (saved_at DESC)
"""

_CREATE_QUIZ_SETS_TABLE = """
CREATE TABLE IF NOT EXISTS quiz_sets (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

_CREATE_QUIZ_SETS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_quiz_sets_created_at
ON quiz_sets (created_at DESC)
"""

_CREATE_QUIZ_SET_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS quiz_set_items (
    quiz_set_id   TEXT NOT NULL REFERENCES quiz_sets(id) ON DELETE CASCADE,
    saved_quiz_id TEXT NOT NULL,
    PRIMARY KEY (quiz_set_id, saved_quiz_id)
)
"""


async def init_db(db: aiosqlite.Connection) -> None:
    """テーブルとインデックスを作成する（冪等）。"""
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute(_CREATE_TABLE)
    await db.execute(_CREATE_INDEX)
    await db.execute(_CREATE_QUIZ_SETS_TABLE)
    await db.execute(_CREATE_QUIZ_SETS_INDEX)
    await db.execute(_CREATE_QUIZ_SET_ITEMS_TABLE)
    await db.commit()
