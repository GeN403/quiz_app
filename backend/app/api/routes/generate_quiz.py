"""
/generate-quiz エンドポイント
"""

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from app.schemas.requests import QuizRequest
from app.core.config import CATEGORY_NAMES
from app.core.domain_validator import validate_url_domain
from app.core.prompt_builder import build_prompt_url_mode
from app.core.source_validator import verify_source_fields
from app.clients.gemini_client import call_llm_with_retry, parse_json_with_retry
from services.source_resolver import SourceResolver
from models.quiz import QuizData, QuizListResponse
import google.generativeai as genai


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
    print(f"\n{'='*60}")
    print(f"[REQUEST] category={request.category}, source_type={request.source_type}, question_count={request.question_count}")
    print(f"{'='*60}\n")

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

    category_name = CATEGORY_NAMES[request.category]

    try:
        # --- URLモード（唯一サポートされるモード） ---
        print(f"\n--- [URL MODE] Resolving source URL ---")
        print(f"[INFO] Selected URL (server-side): {request.source_value}")

        resolver = SourceResolver(request.source_value, timeout=10)
        resolved = resolver.fetch_and_parse()

        selected_url = resolved["url"]
        selected_title = resolved["title"]
        source_text = resolved["text"]
        quote_candidates = resolved["quotes"]

        print(f"[INFO] Resolved title: {selected_title}")
        print(f"[INFO] Extracted text length: {len(source_text)} chars")
        print(f"[INFO] Quote candidates: {len(quote_candidates)} items")

        # selected_quoteの検証と確定
        if request.selected_quote:
            # UIで選択されたquoteを使用（本文に存在するか検証）
            print(f"[INFO] selected_quote provided: '{request.selected_quote[:50]}...'")
            if not resolver.verify_quote(request.selected_quote):
                raise HTTPException(
                    status_code=400,
                    detail=f"SELECTED_QUOTE_INVALID: 選択されたquoteが本文に存在しません"
                )
            selected_quote = request.selected_quote
            print(f"[INFO] selected_quote validated")
        else:
            # selected_quoteが渡されていない場合は、候補の最初を使用
            selected_quote = quote_candidates[0] if quote_candidates else ""
            print(f"[INFO] Using first quote candidate as default")

        # プロンプト生成（URLモードのみ）
        prompt = build_prompt_url_mode(
            category_name=category_name,
            url=selected_url,
            title=selected_title,
            text_excerpt=source_text,
            quotes=quote_candidates,
            question_count=request.question_count
        )

        # --- LLM呼び出し + JSONパース（リトライあり） ---
        print(f"\n--- [LLM CALL] Calling Gemini API ---")
        raw_response = call_llm_with_retry(model, prompt, max_retries=2)

        print("--- [RAW RESPONSE] ---")
        print(raw_response[:500])
        print("--- [END RAW RESPONSE] ---\n")

        parsed_json = parse_json_with_retry(raw_response, max_retries=2)

        # --- source完全上書き（最重要: LLMの出力を一切信用しない） ---
        print(f"\n--- [SOURCE OVERRIDE] Replacing all source fields with server-confirmed values ---")
        print(f"[SOURCE OVERRIDE] URL: {selected_url}")
        print(f"[SOURCE OVERRIDE] Title: {selected_title}")
        print(f"[SOURCE OVERRIDE] Quote: '{selected_quote[:50]}...'")

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
            print(f"[SOURCE OVERRIDE] Replaced source for quiz {idx+1}")

        print(f"[SOURCE OVERRIDE] All {len(quiz_list)} quizzes updated with server-confirmed source\n")

        # --- source検証（サーバ確定値の検証） ---
        print(f"--- [VALIDATION] Verifying server-confirmed source fields ---")

        # 各問のsourceを検証（これはサーバ確定値なので必ず通るはず）
        for idx, quiz in enumerate(quiz_list):
            quiz_num = idx + 1
            print(f"[VALIDATION] Validating quiz {quiz_num}/{len(quiz_list)}...")

            try:
                verify_source_fields(quiz, expected_url=selected_url, source_text=source_text)
            except ValueError as e:
                # サーバ確定値の検証が失敗するのは実装バグ
                print(f"[VALIDATION ERROR] Quiz {quiz_num}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"INTERNAL_ERROR: サーバ確定値の検証に失敗しました（実装バグ）: {str(e)}"
                )

        print(f"[VALIDATION] All {len(quiz_list)} quizzes validated successfully\n")

        # --- Pydanticモデルでバリデーション ---
        print(f"--- [PYDANTIC VALIDATION] Validating with Pydantic models ---")

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
            print(f"[PYDANTIC ERROR] {e}")
            raise HTTPException(
                status_code=502,
                detail=f"PYDANTIC_VALIDATION_ERROR: 生成結果がスキーマに適合しません: {str(e)}"
            )

        print(f"[PYDANTIC VALIDATION] Success\n")

        print(f"{'='*60}")
        print(f"[SUCCESS] Quiz generation completed")
        print(f"{'='*60}\n")

        return result

    except HTTPException:
        # HTTPExceptionはそのまま再スロー
        raise
    except Exception as e:
        error_str = str(e)
        print(f"[ERROR] Unexpected error: {error_str[:200]}")
        raise HTTPException(
            status_code=500,
            detail=f"QUIZ_GENERATION_ERROR: クイズ生成中に予期しないエラーが発生しました: {error_str}"
        )
