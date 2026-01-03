"""
FastAPI アプリケーション本体
"""

import os
import sys
import io
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import create_api_router


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

# FastAPIアプリケーションの初期化
app = FastAPI()

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
