"""
pytest 共通設定

langchain_google_genai の google-generativeai バージョン不整合を
sys.modules パッチで回避する（エンドポイントテスト用）。
"""

import sys
from unittest.mock import MagicMock

# langchain_google_genai とその内部サブモジュールをモック化
# （google-generativeai の Modality 属性欠如によるインポートエラーを回避）
_MOCK_MODULES = [
    "langchain_google_genai",
    "langchain_google_genai._enums",
    "langchain_google_genai.chat_models",
    "langchain_google_genai.llms",
    "langchain_google_genai.embeddings",
]

for _mod in _MOCK_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
