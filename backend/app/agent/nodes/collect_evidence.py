"""Collect evidence node factory."""
import logging

from typing import Any, Callable

from app.agent.state import AgentState, ClaimEntry, EvidenceEntry
from app.clients.gemini_client import parse_json_with_retry
logger = logging.getLogger(__name__)


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
        logger.info("[collect_evidence] Starting")

        claims: list[ClaimEntry] = state.get("claims", [])
        source_text = state.get("source_text", "")
        source_url = state.get("source_url", "")

        evidence_list: list[EvidenceEntry] = []

        from app.agent import nodes as nodes_pkg
        llm = nodes_pkg.ChatGoogleGenerativeAI(
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
                logger.info(f"[collect_evidence] Quote extraction failed for {claim_id}: {e}")
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
                logger.info(f"[collect_evidence] Added source evidence for {claim_id}")
            else:
                # Task 4.2: 不十分な場合は補足 URL を取得 (Requirements: 2.3)
                try:
                    supp_url = _suggest_url(llm, claim_text)
                    if supp_url:
                        resolver = nodes_pkg.SourceResolver(supp_url, timeout=10)
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
                            logger.info(
                                f"[collect_evidence] Added supplementary evidence for {claim_id}"
                            )
                except Exception as e:
                    # SourceResolver 等の例外はすべて捕捉して 0 件扱いで続行
                    logger.info(
                        f"[collect_evidence] Supplementary fetch failed for {claim_id}: {e}"
                    )

        logger.info(f"[collect_evidence] Total evidence entries: {len(evidence_list)}")
        return {"evidence_list": evidence_list}

    return collect_evidence
