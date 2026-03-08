"""
SavedQuizRepository — SQLite を使った保存済みクイズのデータアクセス層
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

import aiosqlite

from app.schemas.saved_quiz import (
    GenerationInputParams,
    SavedQuizDetail,
    SavedQuizListItem,
    SavedQuizResponse,
    SaveQuizRequest,
)

logger = logging.getLogger(__name__)


class DuplicateGenerationResultError(Exception):
    """generation_result_id の UNIQUE 制約違反時に raise する"""


def _derive_topic(params: GenerationInputParams) -> str:
    """input_params から topic を派生する。keyword → category → source_url → '無題'"""
    if params.keyword:
        return params.keyword
    if params.category:
        return params.category
    if params.source_url:
        return params.source_url
    return "無題"


class SavedQuizRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def save(self, request: SaveQuizRequest) -> SavedQuizResponse:
        """クイズを保存し、id と saved_at を返す。重複時は DuplicateGenerationResultError を raise する。"""
        record_id = str(uuid4())
        saved_at = datetime.now(timezone.utc).isoformat()
        topic = _derive_topic(request.input_params)
        input_params_json = request.input_params.model_dump_json()
        answer_package_json = json.dumps(request.answer_package, ensure_ascii=False)

        try:
            await self._db.execute(
                """
                INSERT INTO saved_quizzes
                (id, generation_result_id, saved_at, topic, question_count, input_params, answer_package)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    request.generation_result_id,
                    saved_at,
                    topic,
                    request.input_params.question_count,
                    input_params_json,
                    answer_package_json,
                ),
            )
            await self._db.commit()
        except aiosqlite.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise DuplicateGenerationResultError(request.generation_result_id) from e
            raise

        return SavedQuizResponse(id=record_id, saved_at=saved_at)

    async def get_by_id(self, record_id: str) -> SavedQuizDetail | None:
        """ID でレコードを取得する。存在しない場合は None を返す。"""
        async with self._db.execute(
            """
            SELECT id, generation_result_id, saved_at, input_params, answer_package
            FROM saved_quizzes
            WHERE id = ?
            """,
            (record_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        id_, gen_result_id, saved_at, input_params_json, answer_package_json = row
        return SavedQuizDetail(
            id=id_,
            generation_result_id=gen_result_id,
            saved_at=saved_at,
            input_params=GenerationInputParams.model_validate_json(input_params_json),
            answer_package=json.loads(answer_package_json),
        )

    async def delete_by_id(self, record_id: str) -> bool:
        """ID でレコードを削除する。削除成功で True、対象なしで False を返す。"""
        cursor = await self._db.execute(
            "DELETE FROM saved_quizzes WHERE id = ?",
            (record_id,),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def list_all(self) -> list[SavedQuizListItem]:
        """saved_at DESC 順で全レコードを返す。デシリアライズ失敗レコードはスキップする。"""
        async with self._db.execute(
            """
            SELECT id, generation_result_id, saved_at, topic, question_count, input_params
            FROM saved_quizzes
            ORDER BY saved_at DESC, rowid DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()

        items: list[SavedQuizListItem] = []
        for row in rows:
            id_, gen_result_id, saved_at, topic, question_count, input_params_json = row
            try:
                json.loads(input_params_json)  # デシリアライズ可能か検証
                items.append(
                    SavedQuizListItem(
                        id=id_,
                        generation_result_id=gen_result_id,
                        saved_at=saved_at,
                        topic=topic,
                        question_count=question_count,
                    )
                )
            except Exception as e:
                logger.warning("レコード id=%s のデシリアライズに失敗しました: %s", id_, e)

        return items
