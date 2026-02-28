"""
LangGraph クイズ生成ワークフローの共有ステート定義
"""

import operator
from typing import Annotated, TypedDict, Optional, Any, Literal, NotRequired
from pydantic import BaseModel, model_validator


# ---- 検証ループ用 型定義 (Task 1.1) ----

class ClaimEntry(TypedDict):
    """原子的主張の単位。claim_id で一意に識別する。"""
    claim_id: str  # 例: "C0001"（ゼロ埋め 4 桁連番）
    text: str      # 「主語＋述語」を含む自然言語の短文


class EvidenceEntry(TypedDict):
    """1 件の根拠エントリ。claim_id で対応する主張と紐付ける。"""
    # 必須フィールド（total=True デフォルト）
    claim_id: str        # 例: "C0001"
    evidence_id: str     # 例: "E0001"（同一 claim_id 内ゼロ埋め連番）
    url: str
    quote: str
    rank: int            # 小さいほど優先（生成時に必ず付与）
    # 任意フィールド
    title: NotRequired[str]
    retrieved_at: NotRequired[str]


class VerificationResult(TypedDict):
    """1 主張の事実確認結果。"""
    # 必須フィールド（total=True デフォルト）
    claim_id: str
    verdict: Literal["pass", "fail"]
    # 条件付き必須: verdict=="fail" のとき非空文字列が必須（ランタイムチェックは verify_claims が担う）
    reason: NotRequired[Optional[str]]
    # 任意フィールド
    used_evidence_ids: NotRequired[list[str]]
    confidence: NotRequired[float]


class VerificationSnapshot(TypedDict):
    """1 試行（ドラフト）のスナップショット。verification_history に蓄積される。"""
    attempt: int                              # 0-origin の書き換え回数
    quiz_text: str                            # QUESTION:\n...\n\n---\n\nEXPLANATION:\n...
    claims: list[ClaimEntry]
    evidence_list: list[EvidenceEntry]
    verification_results: list[VerificationResult]
    failed_claim_ids: list[str]
    retrieval_retry_count: NotRequired[int]
    termination_reason_code: NotRequired[
        Literal[
            "ALL_CLAIMS_PASSED",
            "MAX_VERIFICATION_ATTEMPTS_REACHED",
            "NO_CHANGE_LIMIT_REACHED",
            "RETRIEVAL_RETRY_EXCEEDED",
            "UNKNOWN",
        ]
    ]
    termination_reason_message: NotRequired[str]
    proposal: NotRequired["MinorProposal | MajorProposal"]
    llm_meta: NotRequired[dict[str, str | int | float]]


class DisambiguationParametersModel(BaseModel):
    major_count_threshold: int = 16
    minor_count_threshold: int = 5
    score_threshold: float = 0.70
    max_attempts: int = 3
    no_change_stop_threshold: int = 2
    max_retrieval_retries: int = 0

    @model_validator(mode="after")
    def validate_constraints(self) -> "DisambiguationParametersModel":
        if self.minor_count_threshold < 0:
            raise ValueError("minor_count_threshold must be >= 0")
        if self.minor_count_threshold >= self.major_count_threshold:
            raise ValueError("minor_count_threshold must be less than major_count_threshold")
        if not (0.0 <= self.score_threshold <= 1.0):
            raise ValueError("score_threshold must be between 0.0 and 1.0")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.no_change_stop_threshold < 1:
            raise ValueError("no_change_stop_threshold must be >= 1")
        if self.max_retrieval_retries < 0:
            raise ValueError("max_retrieval_retries must be >= 0")
        return self


class SearchParams(TypedDict):
    source_policy: str
    max_candidates: int
    similarity_metric: str
    score_threshold: float
    normalization_rule: str
    selection_rule: str


class CompetingConcept(TypedDict):
    competing_id: str
    source: str
    original_label: str
    normalized_label: str
    category: Literal["exact", "synonym", "hyper_hypo", "related"]
    similarity: float
    score: float
    selected: bool


class DiscoveryResult(TypedDict):
    snapshot_id: str
    evidence_status: Literal["ok", "partial", "failed"]
    sources_attempted: list[str]
    sources_succeeded: list[str]
    sources_failed: list[str]
    search_params: SearchParams
    candidates: list[CompetingConcept]


class JudgementResult(TypedDict):
    verdict: Literal["pass", "fail_minor", "fail_major", "unknown"]
    reason: str
    evidence_status: Literal["ok", "partial", "failed"]
    effective_competing_count: int
    termination_reason: NotRequired[str]


class MinorProposal(TypedDict):
    mode: Literal["qualifier", "preface"]
    before_concept: str
    after_concept: str
    added_qualifier: NotRequired[str]
    added_preface: NotRequired[str]
    edit_ops: list[dict[str, str]]


class AlternativeConcept(TypedDict):
    concept: str
    rank: int
    score: float


class MajorProposal(TypedDict):
    replaced_concept: str
    alternatives: list[AlternativeConcept]
    selected_alternative: AlternativeConcept


class LoopDecision(TypedDict):
    continue_loop: bool
    termination_reason_code: Literal[
        "ALL_CLAIMS_PASSED",
        "MAX_VERIFICATION_ATTEMPTS_REACHED",
        "NO_CHANGE_LIMIT_REACHED",
        "RETRIEVAL_RETRY_EXCEEDED",
        "UNKNOWN",
    ]
    termination_reason_message: str
    next_attempt: int
    retrieval_retry_count: int


class DisambiguationSnapshot(TypedDict):
    attempt: int
    input_concept: str
    normalized_concept: str
    verdict: Literal["pass", "fail_minor", "fail_major", "unknown"]
    reason: str
    evidence_status: Literal["ok", "partial", "failed"]
    snapshot_id: str
    effective_competing_count: int
    proposal: NotRequired[MinorProposal | MajorProposal]
    llm_meta: NotRequired[dict[str, str | int | float]]


class AgentState(TypedDict, total=False):
    """
    ノード間で受け渡す共有ステートコンテナ。

    不変条件: `result` と `error_code` は排他。
    - 成功終了: result が dict, error_code が None
    - エラー終了: result が None, error_code が str
    """
    # ルートハンドラが設定（入力）
    category: str
    question_count: int
    source_type: str
    source_value: str
    selected_quote: str

    # fetch_source ノードが設定
    source_text: str             # 先頭 8,000 文字に切り詰め済み
    source_title: str            # HTML <title> または URL フォールバック
    source_url: str              # 確定 URL
    selected_quote_final: str    # 検証済み quote（空文字列可）

    # generate_quiz ノードが設定
    llm_raw_response: str

    # parse_output ノードが設定
    result: Optional[dict[str, Any]]  # QuizData.model_dump(by_alias=True)

    # ルートハンドラが設定（ResolveTopicInput 入力）
    topic: Optional[str]           # None または strip 済み非空文字列（API 層で正規化済み）

    # resolve_topic_input ノードが設定
    resolved_topic: Optional[str]  # 解決済みトピック（正常時は非空文字列・20文字以内）

    # エラー伝播（いずれかのノードが設定）
    error_code: Optional[str]
    error_status: Optional[int]

    # 検証ループ用フィールド (Task 1.2)
    # decompose_claims が設定
    claims: list[ClaimEntry]
    quiz_text: str  # QUESTION:\n...\n\n---\n\nEXPLANATION:\n...\n\n---\n\nALTERNATIVE:\n...

    # collect_evidence が設定
    evidence_list: list[EvidenceEntry]

    # verify_claims が設定
    verification_results: list[VerificationResult]

    # rewrite_quiz が +1 インクリメント（初期値 0; 初回生成はカウントしない）
    verification_attempts: int
    retrieval_retry_count: int
    verification_no_change_count: int
    verification_outcome: JudgementResult
    termination_reason_code: str
    termination_reason_message: str
    disambiguation_parameters: DisambiguationParametersModel | dict[str, Any]

    # reducer方式: verify_claims は差分 [snapshot] のみ返す
    # !! 非 reducer 方式（全体返却）との混在禁止 !!
    verification_history: Annotated[list[VerificationSnapshot], operator.add]


def calculate_verification_attempts(
    verification_history: list[VerificationSnapshot],
) -> int:
    """
    verification ブロック出力用 attempts を計算する。
    - attempt は「判定ループ 1 周」を表す
    - retrieval_retry は Discovery 内再試行であり attempts に含めない
    """
    if not verification_history:
        return 0
    return max(snapshot["attempt"] for snapshot in verification_history) + 1
