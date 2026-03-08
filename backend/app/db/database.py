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


async def init_db(db: aiosqlite.Connection) -> None:
    """テーブルとインデックスを作成する（冪等）。"""
    await db.execute(_CREATE_TABLE)
    await db.execute(_CREATE_INDEX)
    await db.commit()
