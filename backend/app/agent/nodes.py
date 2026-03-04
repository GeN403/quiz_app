"""
LangGraph クイズ生成ワークフロー: 5 ノード実装
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

from fastapi import HTTPException
from pydantic import ValidationError
from google.api_core import exceptions as google_exceptions
from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.source_resolver import SourceResolver
from app.core.prompt_builder import (
    build_prompt_url_mode,
    build_prompt_decompose_claims,
    build_prompt_verify_claim,
    build_prompt_rewrite_quiz,
)
from app.clients.gemini_client import parse_json_with_retry
from app.models.quiz import QuizData
from app.agent.state import (
    AgentState,
    ClaimEntry,
    EvidenceEntry,
    VerificationResult,
    VerificationSnapshot,
    DisambiguationParametersModel,
    JudgementResult,
)
from app.agent.loop_control import LoopControlService
from app.agent.disambiguation_services import (
    MinorDisambiguationService,
    MajorDisambiguationService,
)


# ---------------------------------------------------------------------------
# Task 2.1: validate_input ノード
# ---------------------------------------------------------------------------

def validate_input(state: AgentState) -> dict[str, Any]:
    """
    入力検証ノード。

    エラー時: {"error_code": str, "error_status": int}
    正常時:   {}
    Requirements: 2.2, 3.5
    """
    print("[validate_input] Starting validation")

    if state.get("question_count") != 1:
        print(f"[validate_input] Invalid question_count: {state.get('question_count')}")
        return {"error_code": "INVALID_QUESTION_COUNT", "error_status": 400}

    if state.get("source_type") != "url":
        print(f"[validate_input] Invalid source_type: {state.get('source_type')!r}")
        return {"error_code": "INVALID_INPUT", "error_status": 400}

    source_value = state.get("source_value", "")
    if not source_value or not source_value.startswith(("http://", "https://")):
        print(f"[validate_input] Invalid source_value: {source_value!r}")
        return {"error_code": "INVALID_INPUT", "error_status": 400}

    print("[validate_input] Validation passed")
    return {}


# ---------------------------------------------------------------------------
# Task 2.2: fetch_source ノード
# ---------------------------------------------------------------------------

def fetch_source(state: AgentState) -> dict[str, Any]:
    """
    URL 取得ノード。

    正常時: {
        "source_text": str,           # 8,000 文字以内
        "source_title": str,
        "source_url": str,
        "selected_quote_final": str,
    }
    エラー時: {"error_code": "SOURCE_FETCH_FAILED", "error_status": 502}
    Requirements: 2.3, 2.4
    """
    source_value = state.get("source_value", "")
    selected_quote = state.get("selected_quote", "")
    print(f"[fetch_source] Fetching URL: {source_value}")

    try:
        resolver = SourceResolver(source_value, timeout=10)
        resolved = resolver.fetch_and_parse()
    except Exception as e:
        print(f"[fetch_source] Error fetching source: {e}")
        return {"error_code": "SOURCE_FETCH_FAILED", "error_status": 502}

    text = resolved.get("text", "")

    # 先頭 8,000 文字に切り詰め (Requirements: 2.3)
    if len(text) > 8000:
        print(f"[fetch_source] Text truncated from {len(text)} to 8000 chars")
        text = text[:8000]

    # タイトル取得（取得できなければ URL をフォールバック）
    title = resolved.get("title") or source_value

    # selected_quote_final を決定
    quotes = resolved.get("quotes", [])
    if selected_quote:
        is_found = resolver.verify_quote(selected_quote)
        if is_found:
            selected_quote_final = selected_quote
        else:
            print("[fetch_source] Selected quote not found, using first candidate")
            selected_quote_final = quotes[0] if quotes else ""
    else:
        selected_quote_final = quotes[0] if quotes else ""

    print(f"[fetch_source] Success: title={title!r}, text_len={len(text)}")
    return {
        "source_text": text,
        "source_title": title,
        "source_url": resolved.get("url", source_value),
        "selected_quote_final": selected_quote_final,
    }


# ---------------------------------------------------------------------------
# Task 3.1: generate_quiz ノードファクトリ
# ---------------------------------------------------------------------------

def make_generate_quiz_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """
    ファクトリ関数。gemini_api_key をクロージャに閉じ込めたノード関数を返す。

    返すノード関数:
      正常時: {"llm_raw_response": str}
      エラー時: {"error_code": str, "error_status": int}
    Requirements: 2.5, 4.2, 4.3, 4.4, 4.5, 4.6
    """

    def generate_quiz(state: AgentState) -> dict[str, Any]:
        print("[generate_quiz] Building prompt and calling Gemini API")

        quote_final = state.get("selected_quote_final", "")
        prompt = build_prompt_url_mode(
            category_name=state.get("category", ""),
            url=state.get("source_url", ""),
            title=state.get("source_title", ""),
            text_excerpt=state.get("source_text", ""),
            quotes=[quote_final] if quote_final else [],
            question_count=1,
            topic=state.get("resolved_topic"),
        )

        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-lite",
                google_api_key=gemini_api_key,
            )
            response = llm.invoke(prompt)
            raw_text = response.content
            print(f"[generate_quiz] LLM response received ({len(raw_text)} chars)")
            return {"llm_raw_response": raw_text}

        except google_exceptions.Unauthenticated:
            print("[generate_quiz] Unauthenticated error")
            return {"error_code": "GEMINI_API_KEY_INVALID", "error_status": 401}
        except google_exceptions.PermissionDenied:
            print("[generate_quiz] PermissionDenied error")
            return {"error_code": "GEMINI_API_KEY_PERMISSION_DENIED", "error_status": 403}
        except google_exceptions.ResourceExhausted:
            print("[generate_quiz] ResourceExhausted error")
            return {"error_code": "GEMINI_RATE_LIMIT", "error_status": 429}
        except (google_exceptions.ServiceUnavailable, google_exceptions.InternalServerError):
            print("[generate_quiz] Service unavailable error")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}
        except google_exceptions.DeadlineExceeded:
            print("[generate_quiz] DeadlineExceeded error")
            return {"error_code": "GEMINI_TIMEOUT", "error_status": 504}
        except Exception as e:
            print(f"[generate_quiz] Unexpected error: {e}")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}

    return generate_quiz


# ---------------------------------------------------------------------------
# Task 3.2: parse_output ノード
# ---------------------------------------------------------------------------

def parse_output(state: AgentState) -> dict[str, Any]:
    """
    JSON パース・source 上書き・Pydantic 検証ノード。

    正常時: {"result": dict}   # QuizData.model_dump(by_alias=True)
    エラー時: {"error_code": "AI_INVALID_JSON", "error_status": 500}
    Requirements: 2.6, 2.7, 3.1, 3.2, 3.3, 3.6, 4.7
    """
    print("[parse_output] Parsing LLM response")
    raw_response = state.get("llm_raw_response", "")

    try:
        parsed = parse_json_with_retry(raw_response)
    except Exception as e:
        print(f"[parse_output] JSON parse error: {e}")
        return {"error_code": "AI_INVALID_JSON", "error_status": 500}

    if not isinstance(parsed, dict):
        print(f"[parse_output] Parsed result is not a dict: {type(parsed)}")
        return {"error_code": "AI_INVALID_JSON", "error_status": 500}

    # source 強制上書き（LLM の出力を信用しない）(Requirements: 3.6)
    parsed["source"] = {
        "url": state.get("source_url", ""),
        "title": state.get("source_title", ""),
        "quote": state.get("selected_quote_final", ""),
    }
    print("[parse_output] Source overwritten with server-confirmed values")

    # Pydantic 検証 (Requirements: 3.1, 3.2)
    try:
        quiz_data = QuizData(**parsed)
        result = quiz_data.model_dump(by_alias=True)
    except ValidationError as e:
        print(f"[parse_output] Pydantic validation error: {e}")
        return {"error_code": "AI_INVALID_JSON", "error_status": 500}

    print("[parse_output] Success")
    return {"result": result}


# ---------------------------------------------------------------------------
# Task 3.1 / 3.2: resolve_topic_input ノードファクトリ
# ---------------------------------------------------------------------------

def make_resolve_topic_input_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """
    ファクトリ関数。topic の有無を評価してトピックを解決するノード関数を返す。

    topic が指定済みの場合:
      → LLM 呼び出しなしで {"resolved_topic": topic} を返す

    topic が未指定（None）の場合:
      → 探索専用 LLM（temperature=0.2, max_tokens=32）でソーステキストから探索
      → 後処理パイプライン適用後に {"resolved_topic": resolved_topic} を返す

    エラー時: {"error_code": "TOPIC_RESOLVE_FAILED", "error_status": 500}
    Requirements: 1.1, 1.2, 1.4, 1.5, 2.1, 2.2, 2.3, 3.1–3.8
    """
    # 探索専用 LLM インスタンスをファクトリ呼び出し時に 1 度だけ生成（クロージャで保持）
    explore_llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=gemini_api_key,
        temperature=0.2,
        max_tokens=32,
    )

    def resolve_topic_input(state: AgentState) -> dict[str, Any]:
        topic = state.get("topic")

        # topic が指定済みの場合はスキップ（Requirements: 2.1, 2.2, 2.3）
        if topic is not None:
            logger.info(
                "[resolve_topic_input] topic provided, skipping exploration: %s", topic
            )
            return {"resolved_topic": topic}

        # topic が未指定の場合は LLM で探索（Requirements: 3.1–3.8）
        source_text = state.get("source_text", "")
        source_title = state.get("source_title", "")
        prompt = (
            f"タイトル: {source_title}\n\n"
            f"本文:\n{source_text[:2000]}\n\n"
            "以下のタイトルと本文を読み、クイズ問題として具体的で興味深いトピックを"
            "1つ選んでください。"
            "トピック名だけを1行・20文字以内で返し、説明や装飾は一切付けないでください。"
        )

        try:
            ai_msg = explore_llm.invoke(prompt)
            raw = ai_msg.text

            # 後処理パイプライン（Requirements: 3.4）
            # ①改行で分割して 1 行目のみ採用 → ②strip → ③空文字チェック → ④20文字切り詰め
            resolved_topic = raw.split("\n")[0].strip()
            if not resolved_topic:
                return {"error_code": "TOPIC_RESOLVE_FAILED", "error_status": 500}
            if len(resolved_topic) > 20:
                resolved_topic = resolved_topic[:20]

            logger.info(
                "[resolve_topic_input] topic not provided, exploring... resolved: %s",
                resolved_topic,
            )
            return {"resolved_topic": resolved_topic}

        except Exception:
            return {"error_code": "TOPIC_RESOLVE_FAILED", "error_status": 500}

    return resolve_topic_input


# ---------------------------------------------------------------------------
# Task 3 (検証ループ): decompose_claims ノードファクトリ
# ---------------------------------------------------------------------------

def make_decompose_claims_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """
    ファクトリ関数。llm_raw_response を解析して quiz_text を構築し、
    LLM に原子的主張リストの分解を要求するノード関数を返す。

    返すノード関数:
      正常時: {
          "claims": list[ClaimEntry],  # claim_id C0001〜・最大 5 件
          "quiz_text": str,
          "evidence_list": [],         # リセット
          "verification_results": [],  # リセット
      }
      エラー時: {"error_code": str, "error_status": int}
    Requirements: 1.1, 1.2, 1.3, 1.4, 4.6
    """

    def decompose_claims(state: AgentState) -> dict[str, Any]:
        print("[decompose_claims] Starting")

        # 1. llm_raw_response をパースして QuizData を取り出す (Task 3.1)
        raw_response = state.get("llm_raw_response", "")
        try:
            parsed = parse_json_with_retry(raw_response)
        except Exception as e:
            print(f"[decompose_claims] Failed to parse llm_raw_response: {e}")
            return {"error_code": "AI_INVALID_JSON", "error_status": 500}

        if not isinstance(parsed, dict):
            print("[decompose_claims] llm_raw_response is not a dict")
            return {"error_code": "AI_INVALID_JSON", "error_status": 500}

        # 2. quiz_text を構築する (Task 3.1)
        question = parsed.get("question", "")
        explanation = parsed.get("explanation", "")
        alternative = parsed.get(
            "Alternative Solutions/Correctness Judgment Criteria", ""
        )
        quiz_text = (
            f"QUESTION:\n{question}\n\n"
            f"---\n\nEXPLANATION:\n{explanation}\n\n"
            f"---\n\nALTERNATIVE:\n{alternative}"
        )
        print(f"[decompose_claims] Built quiz_text ({len(quiz_text)} chars)")

        # 3. build_prompt_decompose_claims を呼び出して LLM に主張リストを要求する (Task 3.1)
        prompt = build_prompt_decompose_claims(quiz_text)
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-lite",
                google_api_key=gemini_api_key,
            )
            response = llm.invoke(prompt)
            claims_raw = response.content
            print(f"[decompose_claims] LLM response received ({len(claims_raw)} chars)")

        except google_exceptions.Unauthenticated:
            print("[decompose_claims] Unauthenticated error")
            return {"error_code": "GEMINI_API_KEY_INVALID", "error_status": 401}
        except google_exceptions.PermissionDenied:
            print("[decompose_claims] PermissionDenied error")
            return {"error_code": "GEMINI_API_KEY_PERMISSION_DENIED", "error_status": 403}
        except google_exceptions.ResourceExhausted:
            print("[decompose_claims] ResourceExhausted error")
            return {"error_code": "GEMINI_RATE_LIMIT", "error_status": 429}
        except (google_exceptions.ServiceUnavailable, google_exceptions.InternalServerError):
            print("[decompose_claims] Service unavailable error")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}
        except google_exceptions.DeadlineExceeded:
            print("[decompose_claims] DeadlineExceeded error")
            return {"error_code": "GEMINI_TIMEOUT", "error_status": 504}
        except Exception as e:
            print(f"[decompose_claims] Unexpected error: {e}")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}

        # 4. LLM レスポンスをパースして主張リストを取り出す (Task 3.2)
        try:
            claims_parsed = parse_json_with_retry(claims_raw)
        except Exception as e:
            print(f"[decompose_claims] Failed to parse claims response: {e}")
            return {"error_code": "CLAIM_DECOMPOSE_FAILED", "error_status": 500}

        if not isinstance(claims_parsed, list):
            print("[decompose_claims] Claims response is not a list")
            return {"error_code": "CLAIM_DECOMPOSE_FAILED", "error_status": 500}

        # 5. claim_id を付与して最大 5 件に切り詰める (Task 3.2)
        claims: list[ClaimEntry] = []
        for i, item in enumerate(claims_parsed[:5], 1):
            if isinstance(item, dict) and "text" in item:
                claims.append({
                    "claim_id": f"C{i:04d}",
                    "text": str(item["text"]),
                })

        # 6. 主張が 0 件の場合はエラー (Task 3.2, Requirements: 1.4)
        if not claims:
            print("[decompose_claims] No valid claims extracted")
            return {"error_code": "CLAIM_DECOMPOSE_FAILED", "error_status": 500}

        print(f"[decompose_claims] Extracted {len(claims)} claims")
        # 7. claims / quiz_text を返し、evidence_list / verification_results をリセット
        return {
            "claims": claims,
            "quiz_text": quiz_text,
            "evidence_list": [],
            "verification_results": [],
        }

    return decompose_claims


# ---------------------------------------------------------------------------
# Task 4 (検証ループ): collect_evidence ノードファクトリ
# ---------------------------------------------------------------------------

def make_collect_evidence_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """
    ファクトリ関数。各主張に対してソーステキストから根拠 quote を抽出し、
    不十分な場合は補足 URL からも取得するノード関数を返す。

    返すノード関数:
      常に正常終了: {"evidence_list": list[EvidenceEntry]}
      （取得失敗は 0 件扱い。エラー終了しない）
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.7
    """

    def _extract_quote(llm: Any, text: str, claim_text: str) -> str:
        """テキストから主張に関連する根拠 quote を LLM で抽出する"""
        prompt = (
            f"以下のテキストから、主張を検証するための根拠となる引用文を抽出してください。\n\n"
            f"【主張】\n{claim_text}\n\n"
            f"【テキスト】\n{text[:3000]}\n\n"
            f"JSONオブジェクトのみを出力してください（説明文・コードブロック不要）:\n"
            f'{{"quote": "引用文（50〜300文字）。根拠が見つからない場合は空文字列"}}'
        )
        response = llm.invoke(prompt)
        parsed = parse_json_with_retry(response.content)
        if isinstance(parsed, dict):
            return str(parsed.get("quote", "")).strip()
        return ""

    def _suggest_url(llm: Any, claim_text: str) -> str:
        """主張の根拠となる補足 URL を LLM に提案させる"""
        prompt = (
            f"以下の主張について、事実確認に使える信頼性の高い日本語 URL を 1 つ提案してください。\n\n"
            f"【主張】\n{claim_text}\n\n"
            f"JSONオブジェクトのみを出力してください（説明文・コードブロック不要）:\n"
            f'{{"url": "URL。適切な URL がない場合は空文字列"}}'
        )
        response = llm.invoke(prompt)
        parsed = parse_json_with_retry(response.content)
        if isinstance(parsed, dict):
            url = str(parsed.get("url", "")).strip()
            if url.startswith(("http://", "https://")):
                return url
        return ""

    def collect_evidence(state: AgentState) -> dict[str, Any]:
        print("[collect_evidence] Starting")

        claims: list[ClaimEntry] = state.get("claims", [])
        source_text = state.get("source_text", "")
        source_url = state.get("source_url", "")

        evidence_list: list[EvidenceEntry] = []

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            google_api_key=gemini_api_key,
        )

        for claim in claims:
            claim_id = claim["claim_id"]
            claim_text = claim["text"]
            ev_idx = 0  # evidence_id 連番（同一 claim_id 内）

            # Task 4.1: source_text から quote を抽出 (Requirements: 2.1, 2.2)
            quote = ""
            try:
                quote = _extract_quote(llm, source_text, claim_text)
            except Exception as e:
                print(f"[collect_evidence] Quote extraction failed for {claim_id}: {e}")
                quote = ""

            if quote:
                ev_idx += 1
                entry: EvidenceEntry = {
                    "claim_id": claim_id,
                    "evidence_id": f"E{ev_idx:04d}",
                    "url": source_url,
                    "quote": quote,
                    "rank": 1,
                }
                evidence_list.append(entry)
                print(f"[collect_evidence] Added source evidence for {claim_id}")
            else:
                # Task 4.2: 不十分な場合は補足 URL を取得 (Requirements: 2.3)
                try:
                    supp_url = _suggest_url(llm, claim_text)
                    if supp_url:
                        resolver = SourceResolver(supp_url, timeout=10)
                        resolved = resolver.fetch_and_parse()
                        supp_text = resolved.get("text", "")

                        supp_quote = ""
                        try:
                            supp_quote = _extract_quote(llm, supp_text, claim_text)
                        except Exception:
                            supp_quote = ""

                        if supp_quote:
                            ev_idx += 1
                            supp_entry: EvidenceEntry = {
                                "claim_id": claim_id,
                                "evidence_id": f"E{ev_idx:04d}",
                                "url": supp_url,
                                "quote": supp_quote,
                                "rank": 2,
                            }
                            evidence_list.append(supp_entry)
                            print(
                                f"[collect_evidence] Added supplementary evidence for {claim_id}"
                            )
                except Exception as e:
                    # SourceResolver 等の例外はすべて捕捉して 0 件扱いで続行
                    print(
                        f"[collect_evidence] Supplementary fetch failed for {claim_id}: {e}"
                    )

        print(f"[collect_evidence] Total evidence entries: {len(evidence_list)}")
        return {"evidence_list": evidence_list}

    return collect_evidence


# ---------------------------------------------------------------------------
# Task 5 (検証ループ): verify_claims ノードファクトリ
# ---------------------------------------------------------------------------

# MAX_VERIFICATION_RETRIES は graph.py からも参照する
MAX_VERIFICATION_RETRIES = 3


def make_verify_claims_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """
    ファクトリ関数。各主張を根拠エントリと照合して pass/fail 判定し、
    結果に応じてスナップショットを蓄積してループ遷移先を決定するノード関数を返す。

    返すノード関数:
      全 pass:    {"verification_results": list[VerificationResult]}
      fail(上限内): {"verification_results": ..., "verification_history": [snapshot]}
      fail(上限超過): {"verification_results": ..., "verification_history": [snapshot],
                       "error_code": "VERIFICATION_MAX_RETRIES_EXCEEDED", "error_status": 500}
      スキーマエラー: {"error_code": "INTERNAL_SCHEMA_ERROR", "error_status": 500}
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.2, 4.4, 4.5
    """

    def _resolve_disambiguation_parameters(
        state: AgentState,
    ) -> tuple[DisambiguationParametersModel | None, dict[str, Any] | None]:
        raw_params = state.get("disambiguation_parameters")
        try:
            if isinstance(raw_params, DisambiguationParametersModel):
                return raw_params, None
            if isinstance(raw_params, dict):
                return DisambiguationParametersModel(**raw_params), None
            return DisambiguationParametersModel(), None
        except ValidationError:
            return None, {
                "error_code": "PARAMETER_CONSTRAINT_VIOLATION",
                "error_status": 400,
                "termination_reason_code": "UNKNOWN",
                "termination_reason_message": "判定パラメータの制約違反",
            }

    def verify_claims(state: AgentState) -> dict[str, Any]:
        print("[verify_claims] Starting")
        params, param_error = _resolve_disambiguation_parameters(state)
        if param_error:
            return param_error

        claims: list[ClaimEntry] = state.get("claims", [])
        evidence_list: list[EvidenceEntry] = state.get("evidence_list", [])
        quiz_text: str = state.get("quiz_text", "")
        verification_attempts: int = state.get("verification_attempts", 0)
        retrieval_retry_count: int = state.get("retrieval_retry_count", 0)
        no_change_count: int = state.get("verification_no_change_count", 0)

        # claim_id → EvidenceEntry リストのインデックスを構築
        evidence_by_claim: dict[str, list[EvidenceEntry]] = {}
        for ev in evidence_list:
            cid = ev["claim_id"]
            if cid not in evidence_by_claim:
                evidence_by_claim[cid] = []
            evidence_by_claim[cid].append(ev)

        # LLM インスタンス（根拠あり主張の判定に使用）
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            google_api_key=gemini_api_key,
        )

        verification_results: list[VerificationResult] = []

        # Task 5.1: 各主張を判定する
        for claim in claims:
            claim_id = claim["claim_id"]
            evidences = evidence_by_claim.get(claim_id, [])

            if not evidences:
                # Task 5.1: 根拠 0 件 → 自動 fail（LLM 呼び出しなし）(Requirements: 3.6)
                auto_fail: VerificationResult = {
                    "claim_id": claim_id,
                    "verdict": "fail",
                    "reason": "根拠が取得できないため検証不能",
                }
                verification_results.append(auto_fail)
                print(f"[verify_claims] Auto-fail for {claim_id} (no evidence)")
                continue

            # Task 5.1: 根拠あり → LLM 判定 (Requirements: 3.1)
            prompt = build_prompt_verify_claim(claim, evidences)
            try:
                response = llm.invoke(prompt)
                parsed = parse_json_with_retry(response.content)

                if not isinstance(parsed, dict):
                    verdict = "fail"
                    reason = "LLM 応答のパースに失敗"
                else:
                    verdict = str(parsed.get("verdict", "fail"))
                    # None を "" に変換してから strip
                    reason = str(parsed.get("reason", "") or "").strip()

                # Task 5.1: verdict=="fail" かつ reason が空/None → INTERNAL_SCHEMA_ERROR
                if verdict == "fail" and not reason:
                    print(f"[verify_claims] INTERNAL_SCHEMA_ERROR: fail with empty reason for {claim_id}")
                    return {"error_code": "INTERNAL_SCHEMA_ERROR", "error_status": 500}

                vr: VerificationResult = {
                    "claim_id": claim_id,
                    "verdict": verdict,  # type: ignore[typeddict-item]
                }
                if reason:
                    vr["reason"] = reason
                verification_results.append(vr)
                print(f"[verify_claims] {claim_id}: {verdict}")

            except Exception as e:
                # LLM 呼び出し例外 → fail として処理
                reason = f"LLM 呼び出しに失敗: {str(e)[:100]}"
                vr_err: VerificationResult = {
                    "claim_id": claim_id,
                    "verdict": "fail",
                    "reason": reason,
                }
                verification_results.append(vr_err)
                print(f"[verify_claims] LLM error for {claim_id}: {e}")

        # Task 5.2: 全 pass チェック
        failed_results = [r for r in verification_results if r.get("verdict") == "fail"]

        if not failed_results:
            # 全 pass: verification_results のみ返す（スナップショット追記なし）
            print("[verify_claims] All claims passed")
            verification_outcome: JudgementResult = {
                "verdict": "pass",
                "reason": "全主張が根拠と整合したため通過",
                "evidence_status": "ok",
                "effective_competing_count": 0,
            }
            return {
                "verification_results": verification_results,
                "disambiguation_parameters": params,
                "verification_outcome": verification_outcome,
                "verification_no_change_count": 0,
            }

        # fail あり: スナップショットを先に構築して verification_history に差分追記
        failed_claim_ids = [r["claim_id"] for r in failed_results]
        snapshot: VerificationSnapshot = {
            "attempt": verification_attempts,
            "quiz_text": quiz_text,
            "claims": claims,
            "evidence_list": evidence_list,
            "verification_results": verification_results,
            "failed_claim_ids": failed_claim_ids,
            "retrieval_retry_count": retrieval_retry_count,
            "llm_meta": {
                "model": "gemini-2.0-flash-lite",
                "temperature": 0.0,
            },
        }
        print(
            f"[verify_claims] Fail detected: {failed_claim_ids}, "
            f"attempts={verification_attempts}"
        )

        loop_control = LoopControlService()
        previous_history = state.get("verification_history", [])
        if previous_history and previous_history[-1].get("failed_claim_ids") == failed_claim_ids:
            no_change_count += 1
        else:
            no_change_count = 0

        effective_failed_count = len(failed_claim_ids)
        if effective_failed_count >= params.major_count_threshold:
            loop_verdict = "fail_major"
        else:
            loop_verdict = "fail_minor"

        loop_decision = loop_control.should_continue(
            verdict=loop_verdict,
            attempts=verification_attempts,
            no_change_count=no_change_count,
            retrieval_retry_count=retrieval_retry_count,
            params=params,
        )

        if not loop_decision["continue_loop"]:
            snapshot["termination_reason_code"] = loop_decision["termination_reason_code"]
            snapshot["termination_reason_message"] = loop_decision["termination_reason_message"]
            verification_outcome: JudgementResult = {
                "verdict": "unknown",
                "reason": loop_decision["termination_reason_message"],
                "evidence_status": "partial",
                "effective_competing_count": effective_failed_count,
                "termination_reason": loop_decision["termination_reason_code"],
            }
            return {
                "verification_results": verification_results,
                "verification_history": [snapshot],
                "disambiguation_parameters": params,
                "verification_outcome": verification_outcome,
                "verification_no_change_count": no_change_count,
                "termination_reason_code": loop_decision["termination_reason_code"],
                "termination_reason_message": loop_decision["termination_reason_message"],
            }

        if loop_verdict == "fail_major":
            proposal = MajorDisambiguationService().propose(
                concept_text=quiz_text[:50],
                candidates=[
                    {
                        "competing_id": failed["claim_id"],
                        "source": "verification",
                        "original_label": failed.get("reason", "") or failed["claim_id"],
                        "normalized_label": (failed.get("reason", "") or failed["claim_id"]).lower(),
                        "category": "related",
                        "similarity": 1.0,
                        "score": 1.0,
                        "selected": True,
                    }
                    for failed in failed_results
                ],
            )
        else:
            proposal = MinorDisambiguationService().propose(
                concept_text=quiz_text[:50],
                reason=failed_results[0].get("reason", "") or "限定語を追加",
            )
        snapshot["proposal"] = proposal
        verification_outcome = {
            "verdict": loop_verdict,
            "reason": failed_results[0].get("reason", "") or "検証に失敗",
            "evidence_status": "ok",
            "effective_competing_count": effective_failed_count,
        }

        return {
            "verification_results": verification_results,
            "verification_history": [snapshot],
            "disambiguation_parameters": params,
            "verification_outcome": verification_outcome,
            "verification_no_change_count": no_change_count,
        }

    return verify_claims


# ---------------------------------------------------------------------------
# Task 6 (検証ループ): rewrite_quiz ノードファクトリ
# ---------------------------------------------------------------------------

def make_rewrite_quiz_node(
    gemini_api_key: str,
) -> Callable[[AgentState], dict[str, Any]]:
    """
    ファクトリ関数。fail した主張情報をもとに LLM に問題を書き換えさせ、
    llm_raw_response を更新して verification_attempts をインクリメントするノード関数を返す。

    返すノード関数:
      正常時: {"llm_raw_response": str, "verification_attempts": int}
      エラー時: {"error_code": str, "error_status": int}
    Requirements: 4.1, 4.3
    """

    def rewrite_quiz(state: AgentState) -> dict[str, Any]:
        print("[rewrite_quiz] Starting")

        quiz_text: str = state.get("quiz_text", "")
        verification_results = state.get("verification_results", [])
        current_attempts: int = state.get("verification_attempts", 0)

        # fail した主張の claim_id と reason を抽出
        failed_claims = [
            {
                "claim_id": r["claim_id"],
                "text": "",  # verification_results には text は含まれないため空文字
                "reason": str(r.get("reason", "") or ""),
            }
            for r in verification_results
            if r.get("verdict") == "fail"
        ]

        # claims から text を補完（state["claims"] がある場合）
        claims_map = {c["claim_id"]: c["text"] for c in state.get("claims", [])}
        for fc in failed_claims:
            fc["text"] = claims_map.get(fc["claim_id"], "")

        prompt = build_prompt_rewrite_quiz(quiz_text, failed_claims)
        print(f"[rewrite_quiz] Rewriting quiz with {len(failed_claims)} failed claims")

        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-lite",
                google_api_key=gemini_api_key,
            )
            response = llm.invoke(prompt)
            raw_text = response.content
            print(f"[rewrite_quiz] LLM response received ({len(raw_text)} chars)")

        except google_exceptions.Unauthenticated:
            print("[rewrite_quiz] Unauthenticated error")
            return {"error_code": "GEMINI_API_KEY_INVALID", "error_status": 401}
        except google_exceptions.PermissionDenied:
            print("[rewrite_quiz] PermissionDenied error")
            return {"error_code": "GEMINI_API_KEY_PERMISSION_DENIED", "error_status": 403}
        except google_exceptions.ResourceExhausted:
            print("[rewrite_quiz] ResourceExhausted error")
            return {"error_code": "GEMINI_RATE_LIMIT", "error_status": 429}
        except (google_exceptions.ServiceUnavailable, google_exceptions.InternalServerError):
            print("[rewrite_quiz] Service unavailable error")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}
        except google_exceptions.DeadlineExceeded:
            print("[rewrite_quiz] DeadlineExceeded error")
            return {"error_code": "GEMINI_TIMEOUT", "error_status": 504}
        except Exception as e:
            print(f"[rewrite_quiz] Unexpected error: {e}")
            return {"error_code": "GEMINI_SERVICE_UNAVAILABLE", "error_status": 503}

        # verification_attempts を +1 インクリメント
        new_attempts = current_attempts + 1
        print(f"[rewrite_quiz] Incremented verification_attempts: {current_attempts} → {new_attempts}")

        return {
            "llm_raw_response": raw_text,
            "verification_attempts": new_attempts,
        }

    return rewrite_quiz
