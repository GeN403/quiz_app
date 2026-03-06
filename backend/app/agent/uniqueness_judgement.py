"""
一意性判定サービス。

Tasks: 3.1, 3.2, 3.3
"""

from __future__ import annotations

from typing import Any

from app.agent.state import (
    CompetingConcept,
    DisambiguationParametersModel,
    JudgementResult,
)


CATEGORY_WEIGHT = {
    "exact": 1.0,
    "synonym": 0.9,
    "hyper_hypo": 0.75,
    "related": 0.5,
}

CATEGORY_LABEL_JA = {
    "exact": "同名",
    "synonym": "同義語",
    "hyper_hypo": "上位/下位",
    "related": "関連語",
}


class ReasonTemplateFormatter:
    def format(
        self,
        verdict: str,
        top_competitor: CompetingConcept | None,
        effective_competing_count: int,
        params: DisambiguationParametersModel,
    ) -> str:
        if verdict == "unknown":
            return "探索不完全のため確定判定できません。"
        if verdict == "pass":
            return (
                "有効競合がしきい値未満のため一意と判定しました "
                f"(effective={effective_competing_count}, "
                f"minor_count_threshold={params.minor_count_threshold})。"
            )
        category_text = "不明"
        label = "-"
        if top_competitor:
            category_text = CATEGORY_LABEL_JA.get(top_competitor["category"], "不明")
            label = top_competitor["original_label"]
        return (
            f"{category_text}競合（{label}）が検出され、"
            f"{effective_competing_count}件の有効競合を確認しました "
            f"(minor_count_threshold={params.minor_count_threshold}, "
            f"major_count_threshold={params.major_count_threshold})。"
        )


class UniquenessJudgementService:
    def __init__(self) -> None:
        self._formatter = ReasonTemplateFormatter()

    def judge(
        self,
        candidates: list[CompetingConcept],
        evidence_status: str,
        params: DisambiguationParametersModel,
    ) -> JudgementResult:
        for candidate in candidates:
            weight = CATEGORY_WEIGHT.get(candidate["category"], 0.0)
            candidate["score"] = float(candidate["similarity"]) * weight
            candidate["selected"] = candidate["score"] >= params.score_threshold

        selected = [candidate for candidate in candidates if candidate["selected"]]
        effective_competing_count = len(selected)
        top_competitor = selected[0] if selected else None

        if evidence_status != "ok":
            verdict = "unknown"
        elif effective_competing_count >= params.major_count_threshold:
            verdict = "fail_major"
        elif effective_competing_count >= params.minor_count_threshold:
            verdict = "fail_minor"
        else:
            verdict = "pass"

        reason = self._formatter.format(
            verdict=verdict,
            top_competitor=top_competitor,
            effective_competing_count=effective_competing_count,
            params=params,
        )
        return {
            "verdict": verdict,
            "reason": reason,
            "evidence_status": evidence_status,  # type: ignore[typeddict-item]
            "effective_competing_count": effective_competing_count,
        }
