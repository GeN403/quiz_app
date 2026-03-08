"""
APIルータ統合
"""

from typing import Optional

from fastapi import APIRouter
from app.api.routes import resolve_source, generate_quiz, suggest_source
from app.schemas.requests import QuizRequest


def create_agent_router(gemini_api_key: Optional[str] = None) -> APIRouter:
    """
    LangGraph エージェントルーターを生成する。
    既存の create_api_router とは独立した新規関数。

    Args:
        gemini_api_key: Gemini API キー

    Returns:
        /generate-quiz-agent と /health を登録した APIRouter
    """
    from app.api.routes.generate_quiz_agent import create_generate_quiz_agent_router
    return create_generate_quiz_agent_router(gemini_api_key)


def create_api_router(gemini_model) -> APIRouter:
    """
    全てのルートを統合したAPIRouterを作成

    Args:
        gemini_model: Gemini APIモデルインスタンス

    Returns:
        統合されたAPIRouter
    """
    api_router = APIRouter()

    # /resolve-source エンドポイントを追加
    api_router.include_router(resolve_source.router, tags=["source"])

    # /suggest-source エンドポイントを追加
    api_router.include_router(suggest_source.router, tags=["source"])

    # /generate-quiz エンドポイントを追加（modelを注入）
    # ※ generate_quiz.routerは直接includeできないため、個別に登録
    @api_router.post("/generate-quiz", tags=["quiz"])
    async def generate_quiz_endpoint(request: QuizRequest):
        return await generate_quiz.generate_quiz(request, gemini_model)

    # /saved-quizzes エンドポイントを追加
    from app.api.routes.saved_quizzes import create_saved_quizzes_router
    api_router.include_router(create_saved_quizzes_router())

    return api_router
