"""
FastAPI アプリケーション エントリポイント（互換性レイヤー）

既存の起動方法（uvicorn main:app）との互換性を保つため、
backend.app.main の app を再export する。
"""

from app.main import app

__all__ = ["app"]
