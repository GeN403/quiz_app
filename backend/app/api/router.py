"""
APIルータ統合
"""

from fastapi import APIRouter
from app.api.routes import resolve_source, generate_quiz
from app.schemas.requests import QuizRequest


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

    # /generate-quiz エンドポイントを追加（modelを注入）
    # ※ generate_quiz.routerは直接includeできないため、個別に登録
    @api_router.post("/generate-quiz", tags=["quiz"])
    async def generate_quiz_endpoint(request: QuizRequest):
        return await generate_quiz.generate_quiz(request, gemini_model)

    return api_router
