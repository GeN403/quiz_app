"""
保存済みクイズ CRUD エンドポイント
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.repository.saved_quiz import DuplicateGenerationResultError, SavedQuizRepository
from app.schemas.saved_quiz import (
    SavedQuizDetail,
    SavedQuizListItem,
    SavedQuizResponse,
    SaveQuizRequest,
)

logger = logging.getLogger(__name__)


def create_saved_quizzes_router() -> APIRouter:
    router = APIRouter(prefix="/saved-quizzes", tags=["saved-quizzes"])

    @router.post("", status_code=201, response_model=SavedQuizResponse)
    async def save_quiz(request: Request, body: SaveQuizRequest):
        repo = SavedQuizRepository(request.app.state.db)
        try:
            return await repo.save(body)
        except DuplicateGenerationResultError:
            raise HTTPException(status_code=409, detail="DUPLICATE_GENERATION_RESULT")

    @router.get("", response_model=dict)
    async def list_quizzes(request: Request):
        repo = SavedQuizRepository(request.app.state.db)
        items = await repo.list_all()
        return {"items": [item.model_dump() for item in items]}

    @router.get("/{record_id}", response_model=SavedQuizDetail)
    async def get_quiz(record_id: str, request: Request):
        repo = SavedQuizRepository(request.app.state.db)
        detail = await repo.get_by_id(record_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="SAVED_QUIZ_NOT_FOUND")
        return detail

    @router.delete("/{record_id}", status_code=204)
    async def delete_quiz(record_id: str, request: Request):
        repo = SavedQuizRepository(request.app.state.db)
        try:
            deleted = await repo.delete_by_id(record_id)
        except Exception as e:
            logger.error("DB エラーが発生しました: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="DB_ERROR")
        if not deleted:
            raise HTTPException(status_code=404, detail="SAVED_QUIZ_NOT_FOUND")
        return Response(status_code=204)

    return router
