"""
LangGraph StateGraph ファクトリ

9 ノード構成のコンパイル済みグラフを生成する。
Requirements: 2.1, 1.4, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 6.4, 6.5
"""

from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes import (
    validate_input,
    fetch_source,
    make_resolve_topic_input_node,
    make_generate_quiz_node,
    parse_output,
    make_decompose_claims_node,
    make_collect_evidence_node,
    make_verify_claims_node,
    make_rewrite_quiz_node,
    MAX_VERIFICATION_RETRIES,
)


def create_quiz_agent_graph(gemini_api_key: str):
    """
    LangGraph StateGraph をコンパイルして返す。

    Args:
        gemini_api_key: Gemini API キー（各ファクトリノードのクロージャへ注入）

    Returns:
        graph.invoke(AgentState) で使用可能なコンパイル済みグラフ
    """
    workflow = StateGraph(AgentState)

    # 既存の 5 ノードを登録
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("fetch_source", fetch_source)
    workflow.add_node("resolve_topic_input", make_resolve_topic_input_node(gemini_api_key))
    workflow.add_node("generate_quiz", make_generate_quiz_node(gemini_api_key))
    workflow.add_node("parse_output", parse_output)

    # 検証ループの 4 ノードを登録 (Task 7.2, Requirements: 6.3)
    workflow.add_node("decompose_claims", make_decompose_claims_node(gemini_api_key))
    workflow.add_node("collect_evidence", make_collect_evidence_node(gemini_api_key))
    workflow.add_node("verify_claims", make_verify_claims_node(gemini_api_key))
    workflow.add_node("rewrite_quiz", make_rewrite_quiz_node(gemini_api_key))

    # エントリポイント
    workflow.set_entry_point("validate_input")

    # 既存の条件付きエッジ
    def route_after_validate(state: AgentState) -> str:
        return END if state.get("error_code") else "fetch_source"

    def route_after_fetch(state: AgentState) -> str:
        return END if state.get("error_code") else "resolve_topic_input"

    def route_after_resolve_topic(state: AgentState) -> str:
        return END if state.get("error_code") else "generate_quiz"

    # Task 7.1: generate_quiz → decompose_claims に変更（Requirements: 6.1）
    def route_after_generate(state: AgentState) -> str:
        return END if state.get("error_code") else "decompose_claims"

    # Task 7.1: 検証ループのルーティング関数 (Requirements: 6.2)
    def route_after_decompose(state: AgentState) -> str:
        return END if state.get("error_code") else "collect_evidence"

    def route_after_collect(state: AgentState) -> str:
        return END if state.get("error_code") else "verify_claims"

    def route_after_verify(state: AgentState) -> str:
        if state.get("error_code"):
            return END
        verification_outcome = state.get("verification_outcome")
        if verification_outcome and verification_outcome.get("verdict") == "unknown":
            return "parse_output"
        results = state.get("verification_results", [])
        if all(r.get("verdict") == "pass" for r in results):
            return "parse_output"
        return "rewrite_quiz"

    def route_after_rewrite(state: AgentState) -> str:
        return END if state.get("error_code") else "decompose_claims"

    workflow.add_conditional_edges("validate_input", route_after_validate)
    workflow.add_conditional_edges("fetch_source", route_after_fetch)
    workflow.add_conditional_edges("resolve_topic_input", route_after_resolve_topic)
    workflow.add_conditional_edges("generate_quiz", route_after_generate)

    # Task 7.2: 検証ループのエッジ (Requirements: 6.4, 6.5)
    workflow.add_conditional_edges("decompose_claims", route_after_decompose)
    workflow.add_conditional_edges("collect_evidence", route_after_collect)
    workflow.add_conditional_edges("verify_claims", route_after_verify)
    workflow.add_conditional_edges("rewrite_quiz", route_after_rewrite)

    # parse_output は常に END
    workflow.add_edge("parse_output", END)

    return workflow.compile()
