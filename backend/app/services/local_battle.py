"""
ローカル対戦向けの準備サービス
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from app.repository.quiz_set import QuizSetRepository
from app.schemas.local_battle import BattleChoice, BattleQuestion, BattleReadyResponse


class BattleQuestionClassifier:
    """answer_package から multiple-choice 問題を抽出・正規化する。"""

    def classify(self, source_saved_quiz_id: str, answer_package: dict[str, object]) -> BattleQuestion | None:
        prompt = self._extract_prompt(answer_package)
        if prompt is None:
            return None

        choices = self._extract_choices(answer_package.get("choices"))
        if len(choices) < 2:
            choices = self._build_fallback_choices(answer_package)
        if len(choices) < 2:
            return None

        correct_choice_id = self._resolve_correct_choice_id(answer_package, choices)
        if correct_choice_id is None:
            return None

        return BattleQuestion(
            question_id=source_saved_quiz_id,
            source_saved_quiz_id=source_saved_quiz_id,
            prompt=prompt,
            choices=choices,
            correct_choice_id=correct_choice_id,
        )

    def _extract_prompt(self, answer_package: Mapping[str, object]) -> str | None:
        for key in ("prompt", "question"):
            value = answer_package.get(key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
            if isinstance(value, Mapping):
                nested = self._pick_string(value, ("text", "value", "label"))
                if nested:
                    return nested
        return None

    def _extract_choices(self, raw_choices: object) -> list[BattleChoice]:
        if not isinstance(raw_choices, list):
            return []

        choices: list[BattleChoice] = []
        used_choice_ids: set[str] = set()

        for index, raw_choice in enumerate(raw_choices, start=1):
            choice = self._normalize_choice(raw_choice, index)
            if choice is None:
                continue

            choice_id = choice.choice_id
            if choice_id in used_choice_ids:
                choice_id = f"{choice_id}-{index}"

            used_choice_ids.add(choice_id)
            choices.append(BattleChoice(choice_id=choice_id, text=choice.text))

        return choices

    def _build_fallback_choices(self, answer_package: Mapping[str, object]) -> list[BattleChoice]:
        """Build fallback choices when `choices` is missing."""
        answer_text = self._extract_answer_text(answer_package)
        if answer_text is None:
            return []

        choices = [BattleChoice(choice_id="correct", text=answer_text)]
        for index, candidate in enumerate(self._build_distractor_candidates(answer_text), start=1):
            if candidate == answer_text:
                continue
            if any(existing.text == candidate for existing in choices):
                continue
            choices.append(BattleChoice(choice_id=f"fallback-{index}", text=candidate))
            if len(choices) >= 4:
                break

        return choices if len(choices) >= 2 else []

    def _extract_answer_text(self, answer_package: Mapping[str, object]) -> str | None:
        raw_answer = answer_package.get("answer")

        if isinstance(raw_answer, str):
            stripped = raw_answer.strip()
            return stripped or None

        if isinstance(raw_answer, Mapping):
            return self._pick_string(raw_answer, ("text", "value", "label"))

        return None

    def _build_distractor_candidates(self, answer_text: str) -> list[str]:
        if answer_text.isdigit():
            value = int(answer_text)
            return [str(value + 1), str(value - 1 if value > 0 else 1), "0"]

        return ["None of the above", "Unknown", "Other"]

    def _normalize_choice(self, raw_choice: object, index: int) -> BattleChoice | None:
        default_choice_id = f"choice-{index}"

        if isinstance(raw_choice, str):
            text = raw_choice.strip()
            if not text:
                return None
            return BattleChoice(choice_id=default_choice_id, text=text)

        if not isinstance(raw_choice, dict):
            return None

        text = self._pick_string(raw_choice, ("text", "label", "choice", "value"))
        if text is None:
            return None

        choice_id = self._pick_string(raw_choice, ("choice_id", "choiceId", "id", "key"))
        return BattleChoice(choice_id=choice_id or default_choice_id, text=text)

    def _resolve_correct_choice_id(
        self,
        answer_package: Mapping[str, object],
        choices: list[BattleChoice],
    ) -> str | None:
        # 1) choice id 系の指定
        for key in ("correct_choice_id", "correctChoiceId"):
            resolved = self._resolve_choice_reference(answer_package.get(key), choices)
            if resolved is not None:
                return resolved

        # 2) answer は id またはテキスト一致として扱う
        resolved = self._resolve_choice_reference(answer_package.get("answer"), choices)
        if resolved is not None:
            return resolved

        # 3) index 指定
        for key in ("correct_index", "correctIndex"):
            raw_index = answer_package.get(key)
            if isinstance(raw_index, int) and 0 <= raw_index < len(choices):
                return choices[raw_index].choice_id

        return None

    def _resolve_choice_reference(self, raw_reference: object, choices: list[BattleChoice]) -> str | None:
        if isinstance(raw_reference, int):
            if 0 <= raw_reference < len(choices):
                return choices[raw_reference].choice_id
            return None

        if isinstance(raw_reference, Mapping):
            reference = self._pick_string(raw_reference, ("text", "value", "label"))
            if reference is None:
                return None
        elif isinstance(raw_reference, str):
            reference = raw_reference.strip()
        else:
            return None

        if not reference:
            return None

        for choice in choices:
            if choice.choice_id == reference:
                return choice.choice_id

        matched_by_text = [choice.choice_id for choice in choices if choice.text == reference]
        if len(matched_by_text) == 1:
            return matched_by_text[0]

        return None

    def _pick_string(self, data: Mapping[str, object], keys: tuple[str, ...]) -> str | None:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
        return None


class BattlePreparationService:
    """対戦開始前の集約判定を返す。"""

    def __init__(
        self,
        repository: QuizSetRepository,
        classifier: BattleQuestionClassifier | None = None,
    ) -> None:
        self._repository = repository
        self._classifier = classifier or BattleQuestionClassifier()

    async def prepare(self, set_id: str) -> BattleReadyResponse | None:
        if not set_id:
            return None

        source = await self._repository.get_battle_sources(set_id)
        if source is None:
            return None

        source_set_id, set_name, rows = source

        total_item_count = len(rows)
        active_rows = [row for row in rows if not row["is_deleted"]]
        deleted_excluded_count = total_item_count - len(active_rows)

        questions: list[BattleQuestion] = []
        for row in active_rows:
            answer_package = self._parse_answer_package(row.get("answer_package_json"))
            if answer_package is None:
                continue

            classified = self._classifier.classify(
                source_saved_quiz_id=row["saved_quiz_id"],
                answer_package=answer_package,
            )
            if classified is not None:
                questions.append(classified)

        active_item_count = len(active_rows)
        eligible_question_count = len(questions)
        non_multiple_choice_excluded_count = active_item_count - eligible_question_count
        startable = eligible_question_count > 0

        return BattleReadyResponse(
            set_id=source_set_id,
            set_name=set_name,
            total_item_count=total_item_count,
            deleted_excluded_count=deleted_excluded_count,
            active_item_count=active_item_count,
            non_multiple_choice_excluded_count=non_multiple_choice_excluded_count,
            eligible_question_count=eligible_question_count,
            startable=startable,
            reason_code=None if startable else "NO_ELIGIBLE_MULTIPLE_CHOICE",
            questions=questions,
        )

    def _parse_answer_package(self, answer_package_json: str | None) -> dict[str, object] | None:
        if not answer_package_json:
            return None

        try:
            loaded = json.loads(answer_package_json)
        except json.JSONDecodeError:
            return None

        if not isinstance(loaded, dict):
            return None

        return loaded
