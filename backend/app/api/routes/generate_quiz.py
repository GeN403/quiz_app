"""
/generate-quiz エンドポイント
"""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from app.schemas.requests import QuizRequest
from app.core.config import CATEGORY_NAMES
from app.core.resolve_config import ResolveConfig
from app.core.domain_validator import validate_url_domain
from app.core.prompt_builder import build_prompt_url_mode
from app.core.source_validator import verify_source_fields
from app.clients.gemini_client import call_llm_with_retry, parse_json_with_retry
from app.services.source_resolver import SourceResolver
from app.models.quiz import QuizData, QuizListResponse, ResolvedConfigData
import google.generativeai as genai
logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/generate-quiz")
async def generate_quiz(request: QuizRequest, model):
    """
    URLを受け取り、Gemini API呼び出しを行ってクイズを生成する

    改善点:
    - sourceの真実性を完全保証（URL/title/quoteをサーバが決定し、LLMの出力を完全に上書き）
    - カテゴリモードを廃止（URLモードのみサポート）
    - JSONパース失敗時のリトライ（最大2回）
    - 重複キー検出
    - エラーは500ではなく502/400で返す
    """
    # --- 新フィールドのデフォルト適用と genre 解決（Req 2.1〜2.5）---
    if request.resolve_seed is not None:
        # resolve_seed 指定時: ResolveConfig でランダム解決（未指定フィールドのみ）
        rc = ResolveConfig(request.resolve_seed)
        resolved_difficulty = rc.resolve_difficulty(request.difficulty)
        resolved_length = rc.resolve_length(request.length)
        resolved_genre = rc.resolve_genre(request.genre)

        randomly_resolved = []
        if request.difficulty is None:
            randomly_resolved.append(f"difficulty={resolved_difficulty}")
        if request.length is None:
            randomly_resolved.append(f"length={resolved_length}")
        if request.genre is None:
            randomly_resolved.append(f"genre={resolved_genre}")
        explicitly_set = []
        if request.difficulty is not None:
            explicitly_set.append("difficulty")
        if request.length is not None:
            explicitly_set.append("length")
        if request.genre is not None:
            explicitly_set.append("genre")
        logger.info(f"[RESOLVE_CONFIG] seed={request.resolve_seed}")
        logger.info(f"[RESOLVE_CONFIG] randomly resolved: {', '.join(randomly_resolved) or 'none'}")
        logger.info(f"[RESOLVE_CONFIG] explicitly set by user: {', '.join(explicitly_set) or 'none'}")
    else:
        # resolve_seed 未指定時: 既存の固定デフォルト（後方互換）
        resolved_difficulty = request.difficulty or "normal"
        resolved_length = request.length or "medium"
        resolved_genre = request.genre if request.genre is not None else CATEGORY_NAMES.get(request.category, request.category)

    resolved_topic = request.topic

    logger.info(f"\n{'='*60}")
    logger.info(f"[REQUEST] category={request.category}, source_type={request.source_type}, question_count={request.question_count}")
    logger.info(f"[REQUEST] difficulty={resolved_difficulty}, length={resolved_length}, genre={resolved_genre}, topic={resolved_topic}")
    logger.info(f"{'='*60}\n")

    # 1. リクエストパラメータの検証
    if request.category not in CATEGORY_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"無効なカテゴリです。有効なカテゴリ: {', '.join(CATEGORY_NAMES.keys())}"
        )

    if request.question_count < 1 or request.question_count > 5:
        raise HTTPException(
            status_code=400,
            detail="question_countは1〜5の範囲で指定してください。"
        )

    # カテゴリモード廃止: URLモードのみサポート
    if request.source_type == "category":
        raise HTTPException(
            status_code=400,
            detail="CATEGORY_MODE_DEPRECATED: カテゴリモードは廃止されました。URL を指定してください。先に /resolve-source エンドポイントで URL を解決し、その URL を source_type='url', source_value=<URL> として送信してください。"
        )

    if request.source_type == "url":
        if not request.source_value:
            raise HTTPException(
                status_code=400,
                detail="source_type が 'url' の場合、source_value（URL）を指定してください。"
            )
        if not request.source_value.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail="source_value には http:// または https:// で始まる有効なURLを指定してください。"
            )

        # URLのドメイン検証
        validate_url_domain(request.source_value)
    else:
        # source_type が url でも category でもない場合
        raise HTTPException(
            status_code=400,
            detail="source_type は 'url' である必要があります。"
        )

    category_name = resolved_genre

    try:
        # --- URLモード（唯一サポートされるモード） ---
        logger.info(f"\n--- [URL MODE] Resolving source URL ---")
        logger.info(f"[INFO] Selected URL (server-side): {request.source_value}")

        resolver = SourceResolver(request.source_value, timeout=10)
        resolved = resolver.fetch_and_parse()

        selected_url = resolved["url"]
        selected_title = resolved["title"]
        source_text = resolved["text"]
        quote_candidates = resolved["quotes"]

        logger.info(f"[INFO] Resolved title: {selected_title}")
        logger.info(f"[INFO] Extracted text length: {len(source_text)} chars")
        logger.info(f"[INFO] Quote candidates: {len(quote_candidates)} items")

        # selected_quoteの検証と確定
        if request.selected_quote:
            # UIで選択されたquoteを使用（本文に存在するか検証）
            logger.info(f"[INFO] selected_quote provided: '{request.selected_quote[:50]}...'")
            if not resolver.verify_quote(request.selected_quote):
                raise HTTPException(
                    status_code=400,
                    detail=f"SELECTED_QUOTE_INVALID: 選択されたquoteが本文に存在しません"
                )
            selected_quote = request.selected_quote
            logger.info(f"[INFO] selected_quote validated")
        else:
            # selected_quoteが渡されていない場合は、候補の最初を使用
            selected_quote = quote_candidates[0] if quote_candidates else ""
            logger.info(f"[INFO] Using first quote candidate as default")

        # プロンプト生成（URLモードのみ）
        prompt = build_prompt_url_mode(
            category_name=category_name,
            url=selected_url,
            title=selected_title,
            text_excerpt=source_text,
            quotes=quote_candidates,
            question_count=request.question_count,
            difficulty=resolved_difficulty,
            length_option=resolved_length,
            topic=resolved_topic,
        )

        # --- LLM呼び出し + JSONパース（リトライあり） ---
        logger.info(f"\n--- [LLM CALL] Calling Gemini API ---")
        raw_response = call_llm_with_retry(model, prompt, max_retries=2)

        logger.info("--- [RAW RESPONSE] ---")
        logger.info(raw_response[:500])
        logger.info("--- [END RAW RESPONSE] ---\n")

        parsed_json = parse_json_with_retry(raw_response, max_retries=2)

        # --- source完全上書き（最重要: LLMの出力を一切信用しない） ---
        logger.info(f"\n--- [SOURCE OVERRIDE] Replacing all source fields with server-confirmed values ---")
        logger.info(f"[SOURCE OVERRIDE] URL: {selected_url}")
        logger.info(f"[SOURCE OVERRIDE] Title: {selected_title}")
        logger.info(f"[SOURCE OVERRIDE] Quote: '{selected_quote[:50]}...'")

        # サーバが確定したsourceオブジェクト
        enforced_source = {
            "title": selected_title,
            "url": selected_url,
            "quote": selected_quote
        }

        # 単問/複数問の正規化
        if isinstance(parsed_json, list):
            quiz_list = parsed_json
        elif isinstance(parsed_json, dict):
            quiz_list = [parsed_json]
        else:
            raise HTTPException(
                status_code=502,
                detail="INVALID_JSON_STRUCTURE: 生成結果がオブジェクトまたは配列ではありません"
            )

        # 全てのクイズの source を強制上書き
        for idx, quiz in enumerate(quiz_list):
            if not isinstance(quiz, dict):
                raise HTTPException(
                    status_code=502,
                    detail=f"INVALID_QUIZ_STRUCTURE: 問題{idx+1}がオブジェクトではありません"
                )
            # LLMが返した source を完全に無視し、サーバ確定値で置換
            quiz["source"] = enforced_source
            logger.info(f"[SOURCE OVERRIDE] Replaced source for quiz {idx+1}")

        logger.info(f"[SOURCE OVERRIDE] All {len(quiz_list)} quizzes updated with server-confirmed source\n")

        # --- source検証（サーバ確定値の検証） ---
        logger.info(f"--- [VALIDATION] Verifying server-confirmed source fields ---")

        # 各問のsourceを検証（これはサーバ確定値なので必ず通るはず）
        for idx, quiz in enumerate(quiz_list):
            quiz_num = idx + 1
            logger.info(f"[VALIDATION] Validating quiz {quiz_num}/{len(quiz_list)}...")

            try:
                verify_source_fields(quiz, expected_url=selected_url, source_text=source_text)
            except ValueError as e:
                # サーバ確定値の検証が失敗するのは実装バグ
                logger.info(f"[VALIDATION ERROR] Quiz {quiz_num}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"INTERNAL_ERROR: サーバ確定値の検証に失敗しました（実装バグ）: {str(e)}"
                )

        logger.info(f"[VALIDATION] All {len(quiz_list)} quizzes validated successfully\n")

        # --- Pydanticモデルでバリデーション ---
        logger.info(f"--- [PYDANTIC VALIDATION] Validating with Pydantic models ---")

        try:
            if request.question_count == 1:
                # 単問の場合
                if isinstance(parsed_json, list) and len(parsed_json) > 0:
                    validated = QuizData(**quiz_list[0])
                    result = validated.model_dump(by_alias=True)
                else:
                    validated = QuizData(**quiz_list[0])
                    result = validated.model_dump(by_alias=True)
            else:
                # 複数問の場合
                validated_list = QuizListResponse(questions=[QuizData(**q) for q in quiz_list])
                result = validated_list.model_dump(by_alias=True)

        except ValidationError as e:
            logger.info(f"[PYDANTIC ERROR] {e}")
            raise HTTPException(
                status_code=502,
                detail=f"PYDANTIC_VALIDATION_ERROR: 生成結果がスキーマに適合しません: {str(e)}"
            )

        logger.info(f"[PYDANTIC VALIDATION] Success\n")

        # --- resolve_seed 指定時: resolved_config を result に付与（Req 6.1〜6.3）---
        if request.resolve_seed is not None:
            result["resolved_config"] = ResolvedConfigData(
                seed=request.resolve_seed,
                difficulty=resolved_difficulty,
                length=resolved_length,
                genre=resolved_genre,
            ).model_dump()

        logger.info(f"{'='*60}")
        logger.info(f"[SUCCESS] Quiz generation completed")
        logger.info(f"{'='*60}\n")

        return result

    except HTTPException:
        # HTTPExceptionはそのまま再スロー
        raise
    except Exception as e:
        error_str = str(e)
        logger.info(f"[ERROR] Unexpected error: {error_str[:200]}")
        raise HTTPException(
            status_code=500,
            detail=f"QUIZ_GENERATION_ERROR: クイズ生成中に予期しないエラーが発生しました: {error_str}"
        )
