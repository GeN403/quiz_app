"""
Gemini API クライアント
"""
import logging

import json
import re
from typing import Any
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from fastapi import HTTPException
logger = logging.getLogger(__name__)


def call_llm_with_retry(model, prompt: str, max_retries: int = 2) -> str:
    """
    LLMを呼び出し、エラー時はリトライする

    Args:
        model: Gemini model instance
        prompt: LLMに送るプロンプト
        max_retries: 最大リトライ回数

    Returns:
        LLMの応答テキスト

    Raises:
        HTTPException: LLM呼び出し失敗時
    """
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"[LLM] Calling Gemini API (attempt {attempt + 1}/{max_retries + 1})...")
            response = model.generate_content(prompt)
            return response.text.strip()

        except google_exceptions.Unauthenticated as e:
            logger.info(f"[ERROR] Gemini API認証エラー: {e}")
            raise HTTPException(
                status_code=401,
                detail="GEMINI_API_KEY_INVALID: APIキーが無効です。backend/.envファイルのGEMINI_API_KEYを確認してください。"
            )
        except google_exceptions.PermissionDenied as e:
            logger.info(f"[ERROR] Gemini API権限エラー: {e}")
            raise HTTPException(
                status_code=403,
                detail="GEMINI_API_KEY_PERMISSION_DENIED: APIキーに必要な権限がありません。"
            )
        except (google_exceptions.ResourceExhausted, google_exceptions.TooManyRequests) as e:
            logger.info(f"[ERROR] Gemini APIレート制限: {e}")
            raise HTTPException(
                status_code=429,
                detail="GEMINI_RATE_LIMIT: Gemini APIのレート制限に達しました。しばらく待ってから再度お試しください。"
            )
        except (google_exceptions.ServiceUnavailable, google_exceptions.InternalServerError) as e:
            logger.info(f"[ERROR] Gemini APIサービスエラー: {e}")
            raise HTTPException(
                status_code=503,
                detail="GEMINI_SERVICE_UNAVAILABLE: Gemini APIが一時的に利用できません。"
            )
        except google_exceptions.DeadlineExceeded as e:
            logger.info(f"[ERROR] Gemini APIタイムアウト: {e}")
            raise HTTPException(
                status_code=504,
                detail="GEMINI_TIMEOUT: Gemini APIへのリクエストがタイムアウトしました。"
            )
        except ValueError as e:
            error_str = str(e).lower()
            if "api" in error_str and "key" in error_str:
                logger.info(f"[ERROR] APIキー関連のValueError: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="GEMINI_API_KEY_NOT_SET: GEMINI_API_KEYが設定されていません。"
                )
            else:
                logger.info(f"[ERROR] ValueError: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"GEMINI_VALUE_ERROR: {str(e)}"
                )
        except Exception as e:
            logger.info(f"[ERROR] Gemini API予期しないエラー (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                logger.info(f"[RETRY] Retrying...")
                continue
            else:
                raise HTTPException(
                    status_code=502,
                    detail=f"GEMINI_UNKNOWN_ERROR: Gemini API呼び出し中に予期しないエラーが発生しました: {str(e)}"
                )


def parse_json_with_retry(raw_text: str, max_retries: int = 2) -> Any:
    """
    LLM応答からJSONをパースし、失敗時はリトライする
    重複キーも検出する

    Args:
        raw_text: LLMの生応答
        max_retries: 最大リトライ回数

    Returns:
        パースされたJSON（dict or list）

    Raises:
        HTTPException: パース失敗時 or 重複キー検出時
    """
    logger.info("--- [JSON PARSE] Attempting to parse LLM response ---")

    # クリーンアップ
    cleaned = raw_text.strip()

    # ```json ... ``` ブロックを抽出
    if "```json" in cleaned:
        match = re.search(r'```json\s*(.*?)\s*```', cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
            logger.info("[JSON PARSE] Extracted JSON from code block")
    elif cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
        logger.info("[JSON PARSE] Removed code block markers")

    # 重複キー検出用のフック
    def detect_duplicate_keys(pairs):
        """object_pairs_hook: 重複キーを検出"""
        keys_seen = {}
        result = {}
        for key, value in pairs:
            if key in keys_seen:
                # 重複キー検出
                raise ValueError(f"DUPLICATE_KEY: '{key}' が重複しています")
            keys_seen[key] = True
            result[key] = value
        return result

    # JSONパース試行
    for attempt in range(max_retries + 1):
        try:
            # 重複キー検出を有効にしてパース
            parsed = json.loads(cleaned, object_pairs_hook=detect_duplicate_keys)
            logger.info(f"[JSON PARSE] Success on attempt {attempt + 1}")
            return parsed

        except ValueError as e:
            # 重複キーエラーは即座に502で返す（リトライ不可）
            if "DUPLICATE_KEY" in str(e):
                logger.info(f"[JSON PARSE ERROR] Duplicate key detected: {e}")
                raise HTTPException(
                    status_code=502,
                    detail=f"JSON_DUPLICATE_KEY_ERROR: {str(e)}"
                )
            else:
                # その他のValueErrorは再スロー
                raise

        except json.JSONDecodeError as e:
            logger.info(f"[JSON PARSE ERROR] Attempt {attempt + 1} failed: {e}")
            logger.info(f"[JSON PARSE ERROR] Error at position {e.pos}: {e.msg}")

            if attempt < max_retries:
                # リトライ戦略: よくあるエラーを自動修正
                logger.info("[JSON PARSE] Attempting auto-fix...")

                # 1. 末尾カンマを削除
                cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)

                # 2. 単一引用符をダブルクオートに変換（注意: 値内の単一引用符も変換される）
                # cleaned = cleaned.replace("'", '"')

                # 3. 制御文字を削除
                cleaned = re.sub(r'[\x00-\x1f\x7f]', '', cleaned)

                logger.info(f"[JSON PARSE] Retrying with auto-fixed JSON...")
                continue
            else:
                # 最終的に失敗
                logger.info("--- [FAILED JSON] ---")
                logger.info(cleaned[:500])
                logger.info("--- [END FAILED JSON] ---")
                raise HTTPException(
                    status_code=502,
                    detail=f"JSON_PARSE_ERROR: LLMが有効なJSONを返しませんでした。Error: {e.msg} at position {e.pos}"
                )
