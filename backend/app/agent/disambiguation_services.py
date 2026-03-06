"""
fail_minor / fail_major の解消提案サービス。
"""

from __future__ import annotations

from app.agent.state import CompetingConcept, MajorProposal, MinorProposal


class MinorDisambiguationService:
    def propose(self, concept_text: str, reason: str) -> MinorProposal:
        if "前置き" in reason:
            mode = "preface"
            preface = "入門"
            after = f"{preface} {concept_text}"
            return {
                "mode": mode,
                "before_concept": concept_text,
                "after_concept": after,
                "added_preface": preface,
                "edit_ops": [
                    {
                        "op": "insert",
                        "path": "text",
                        "before": concept_text,
                        "after": after,
                    }
                ],
            }

        mode = "qualifier"
        qualifier = "（基礎）"
        after = f"{concept_text}{qualifier}"
        return {
            "mode": mode,
            "before_concept": concept_text,
            "after_concept": after,
            "added_qualifier": qualifier,
            "edit_ops": [
                {
                    "op": "replace",
                    "path": "text",
                    "before": concept_text,
                    "after": after,
                }
            ],
        }


class MajorDisambiguationService:
    def propose(self, concept_text: str, candidates: list[CompetingConcept]) -> MajorProposal:
        alternatives = sorted(
            [
                {
                    "concept": candidate["original_label"],
                    "rank": index + 1,
                    "score": float(candidate["score"]),
                }
                for index, candidate in enumerate(
                    sorted(candidates, key=lambda item: float(item["score"]), reverse=True)
                )
            ],
            key=lambda item: item["rank"],
        )
        if not alternatives:
            alternatives = [{"concept": f"{concept_text}（別題材）", "rank": 1, "score": 0.0}]
        return {
            "replaced_concept": concept_text,
            "alternatives": alternatives,
            "selected_alternative": alternatives[0],
        }
