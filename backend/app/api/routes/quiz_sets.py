"""
クイズセット CRUD + ローカル対戦準備エンドポイント
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.repository.quiz_set import InvalidSavedQuizIdError, QuizSetRepository
from app.schemas.local_battle import BattleReadyResponse
from app.schemas.quiz_set import CreateQuizSetRequest, QuizSetDetail, QuizSetResponse
from app.services.local_battle import BattlePreparationService, BattleQuestionClassifier

logger = logging.getLogger(__name__)


def create_quiz_sets_router() -> APIRouter:
    router = APIRouter(prefix="/quiz-sets", tags=["quiz-sets"])

    @router.post("", status_code=201, response_model=QuizSetResponse)
    async def create_quiz_set(request: Request, body: CreateQuizSetRequest):
        repo = QuizSetRepository(request.app.state.db)
        try:
            return await repo.create(body)
        except InvalidSavedQuizIdError:
            raise HTTPException(status_code=422, detail="INVALID_SAVED_QUIZ_ID")
        except Exception as e:
            logger.error("DB エラーが発生しました: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="DB_ERROR")

    @router.get("", response_model=dict)
    async def list_quiz_sets(request: Request):
        repo = QuizSetRepository(request.app.state.db)
        try:
            items = await repo.list_all()
            return {"items": [item.model_dump() for item in items]}
        except Exception as e:
            logger.error("DB エラーが発生しました: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="DB_ERROR")

    @router.get("/{set_id}", response_model=QuizSetDetail)
    async def get_quiz_set(set_id: str, request: Request):
        repo = QuizSetRepository(request.app.state.db)
        try:
            detail = await repo.get_by_id(set_id)
        except Exception as e:
            logger.error("DB エラーが発生しました: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="DB_ERROR")

        if detail is None:
            raise HTTPException(status_code=404, detail="QUIZ_SET_NOT_FOUND")
        return detail

    @router.get("/{set_id}/battle-ready", response_model=BattleReadyResponse)
    async def get_quiz_set_battle_ready(set_id: str, request: Request):
        repo = QuizSetRepository(request.app.state.db)
        service = BattlePreparationService(repo, BattleQuestionClassifier())
        try:
            ready = await service.prepare(set_id)
        except Exception as e:
            logger.error("battle-ready 取得でエラーが発生しました: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="DB_ERROR")

        if ready is None:
            raise HTTPException(status_code=404, detail="QUIZ_SET_NOT_FOUND")

        return ready

    @router.delete("/{set_id}", status_code=204)
    async def delete_quiz_set(set_id: str, request: Request):
        repo = QuizSetRepository(request.app.state.db)
        try:
            deleted = await repo.delete_by_id(set_id)
        except Exception as e:
            logger.error("DB エラーが発生しました: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="DB_ERROR")

        if not deleted:
            raise HTTPException(status_code=404, detail="QUIZ_SET_NOT_FOUND")
        return Response(status_code=204)

    return router
