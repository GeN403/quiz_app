"""
/generate-quiz-agent エンドポイント

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.1, 5.1
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError, field_validator
from app.api.answer_package import build_answer_package
from uuid import uuid4
import os


class QuizAgentRequest(BaseModel):
    """リクエストスキーマ"""
    category: str
    question_count: int = 1
    source_type: str
    source_value: str
    selected_quote: Optional[str] = None
    topic: Optional[str] = None

    @field_validator("topic", mode="before")
    @classmethod
    def normalize_topic(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = str(v).strip()
        if not stripped:
            return None
        if len(stripped) > 100:
            raise ValueError("topic must be 100 characters or fewer after stripping")
        return stripped


def create_generate_quiz_agent_router(gemini_api_key: Optional[str]) -> APIRouter:
    """
    エージェントルーターを生成するファクトリ。
    グラフは起動時に一度コンパイルし、クロージャとして保持する。

    Args:
        gemini_api_key: Gemini API キー（None の場合は全リクエストで 500 を返す）

    Returns:
        /generate-quiz-agent と /health を登録した APIRouter
    """
    # グラフをコンパイル（api_key がある場合のみ）
    graph = None
    if gemini_api_key:
        from app.agent.graph import create_quiz_agent_graph
        graph = create_quiz_agent_graph(gemini_api_key)

    router = APIRouter()

    # -----------------------------------------------------------------------
    # GET /health (Requirements: 1.4)
    # -----------------------------------------------------------------------
    @router.get("/health")
    async def health():
        return {"status": "ok"}

    # -----------------------------------------------------------------------
    # POST /generate-quiz-agent (Requirements: 1.1, 1.2, 1.3, 1.5, 4.1)
    # -----------------------------------------------------------------------
    @router.post("/generate-quiz-agent")
    async def generate_quiz_agent_endpoint(request: Request):
        # GEMINI_API_KEY 未設定チェック (Requirements: 1.5)
        if not gemini_api_key or graph is None:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY_NOT_SET")

        # 手動 JSON パース（FastAPI の自動バリデーションを使わない）(Requirements: 4.1)
        # → 型エラーや必須フィールド欠落を 400 INVALID_INPUT で統一的に返す
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="INVALID_INPUT")

        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="INVALID_INPUT")

        try:
            req_data = QuizAgentRequest(**body)
        except ValidationError:
            raise HTTPException(status_code=400, detail="INVALID_INPUT")

        # 初期ステートを構築してグラフを実行
        initial_state = {
            "category": req_data.category,
            "question_count": req_data.question_count,
            "source_type": req_data.source_type,
            "source_value": req_data.source_value,
            "selected_quote": req_data.selected_quote or "",
            "source_text": "",
            "source_title": "",
            "source_url": "",
            "selected_quote_final": "",
            "llm_raw_response": "",
            "result": None,
            "error_code": None,
            "error_status": None,
            "topic": req_data.topic,
            "resolved_topic": None,
            "verification_attempts": 0,
            "retrieval_retry_count": 0,
            "verification_no_change_count": 0,
            "disambiguation_parameters": {},
            "verification_history": [],
        }

        final_state = graph.invoke(initial_state)

        # エラーを HTTPException に変換 (Requirements: 4.1)
        if final_state.get("error_code"):
            raise HTTPException(
                status_code=final_state["error_status"],
                detail=final_state["error_code"],
            )

        correlation_id = request.headers.get("x-correlation-id", "").strip() or f"corr_{uuid4().hex[:12]}"
        try:
            retention_limit = int(os.getenv("ANSWER_PACKAGE_LOG_RETENTION_LIMIT", "500"))
        except ValueError:
            retention_limit = 500
        response_body = build_answer_package(
            final_state,
            correlation_id,
            retention_limit=retention_limit,
        )
        # 成功: 既存互換フィールドを含む回答パッケージを返す
        return JSONResponse(content=response_body, status_code=200)

    return router
