"""
FastAPI アプリケーション本体
"""

import os
import sys
import io
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from app.api.router import create_api_router, create_agent_router


# Windows環境でのUTF-8出力を強制（cp932エンコーディングエラー対策）
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# .envファイルから環境変数を読み込む
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# APIキーの存在チェックと設定
if not api_key:
    print("[WARNING] GEMINI_API_KEY が設定されていません。")
    print("[WARNING] バックエンドは起動しますが、クイズ生成は失敗します。")
    print("[WARNING] backend/.env ファイルに GEMINI_API_KEY を設定してください。")
else:
    print("[OK] GEMINI_API_KEY が正しく設定されています。")

# APIキーを設定（Noneでも設定して、実際のAPI呼び出し時にエラーを捕捉）
genai.configure(api_key=api_key)

# 使用するモデルを選択
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# 新フィールド名（RequestValidationError ハンドラが選択的に処理する対象）
_NEW_FIELDS = frozenset({"difficulty", "length", "genre", "topic"})
_SEED_FIELD = "resolve_seed"


# FastAPIアプリケーションの初期化
app = FastAPI()


@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    2-pass バリデーションエラーハンドラ。

    Pass 1: resolve_seed フィールドのエラーを順序非依存で先行検出し
            {"detail": "INVALID_SEED"} (HTTP 422) を返す。
            loc は list/tuple どちらで来ても tuple() で正規化してから in 判定する。
    Pass 2: 新フィールド（difficulty/length/genre/topic）の value_error のみを
            {"detail": "ERROR_CODE"} 形式（HTTP 422）で返す。
    それ以外は FastAPI デフォルトハンドラに委譲する（Req 1.10, 1.11）。
    """
    errors = exc.errors()
    # Pass 1: resolve_seed のエラーはエラー種別を問わず INVALID_SEED を返す
    if any(_SEED_FIELD in tuple(err.get("loc", ())) for err in errors):
        return JSONResponse(status_code=422, content={"detail": "INVALID_SEED"})
    # Pass 2: 既存フィールドのバリデーションエラー処理（変更なし）
    for err in errors:
        field = err.get("loc", (None,))[-1]
        if field in _NEW_FIELDS and err.get("type") == "value_error":
            raw = (err.get("ctx") or {}).get("error")
            code = str(raw) if raw is not None else "VALIDATION_ERROR"
            return JSONResponse(status_code=422, content={"detail": code})
    # 既存フィールドのエラーは FastAPI デフォルト形式を維持
    return await request_validation_exception_handler(request, exc)


# CORSミドルウェアの設定（Next.jsのlocalhost:3000からのアクセスを許可する）
origins = [
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルータを統合
api_router = create_api_router(model)
app.include_router(api_router)

# LangGraph エージェントルーターを追加（既存ルートへの影響ゼロ）
app.include_router(create_agent_router(api_key))
