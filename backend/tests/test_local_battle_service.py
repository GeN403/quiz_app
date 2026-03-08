"""
Local battle service unit tests (RED first)
"""

from __future__ import annotations

import json

from app.services.local_battle import BattlePreparationService, BattleQuestionClassifier


class _StubRepo:
    def __init__(self, response):
        self._response = response

    async def get_battle_sources(self, set_id: str):
        return self._response


def test_classifier_returns_question_when_minimum_multiple_choice_conditions_are_met():
    classifier = BattleQuestionClassifier()

    question = classifier.classify(
        source_saved_quiz_id="saved-1",
        answer_package={
            "prompt": "首都はどこ？",
            "choices": [
                {"id": "tokyo", "text": "東京"},
                {"id": "osaka", "text": "大阪"},
            ],
            "correctChoiceId": "tokyo",
        },
    )

    assert question is not None
    assert question.prompt == "首都はどこ？"
    assert len(question.choices) == 2
    assert question.correct_choice_id == "tokyo"


def test_classifier_returns_none_when_prompt_is_missing():
    classifier = BattleQuestionClassifier()

    question = classifier.classify(
        source_saved_quiz_id="saved-1",
        answer_package={
            "choices": [
                {"id": "a", "text": "A"},
                {"id": "b", "text": "B"},
            ],
            "correctChoiceId": "a",
        },
    )

    assert question is None


def test_classifier_returns_none_when_choices_are_less_than_two():
    classifier = BattleQuestionClassifier()

    question = classifier.classify(
        source_saved_quiz_id="saved-1",
        answer_package={
            "prompt": "Q",
            "choices": [{"id": "a", "text": "A"}],
            "correctChoiceId": "a",
        },
    )

    assert question is None


def test_classifier_returns_none_when_correct_answer_cannot_be_uniquely_identified():
    classifier = BattleQuestionClassifier()

    question = classifier.classify(
        source_saved_quiz_id="saved-1",
        answer_package={
            "prompt": "Q",
            "choices": [
                {"id": "a", "text": "同じ"},
                {"id": "b", "text": "同じ"},
            ],
            "answer": "同じ",
        },
    )

    assert question is None


async def test_prepare_aggregates_deleted_and_non_multiple_choice_counts():
    classifier = BattleQuestionClassifier()
    repo = _StubRepo(
        (
            "set-1",
            "セットA",
            [
                {
                    "saved_quiz_id": "deleted-quiz",
                    "is_deleted": True,
                    "answer_package_json": None,
                },
                {
                    "saved_quiz_id": "free-text",
                    "is_deleted": False,
                    "answer_package_json": json.dumps({"question": "text-only", "answer": "A"}),
                },
                {
                    "saved_quiz_id": "mc-quiz",
                    "is_deleted": False,
                    "answer_package_json": json.dumps(
                        {
                            "prompt": "Q",
                            "choices": [
                                {"id": "a", "text": "A"},
                                {"id": "b", "text": "B"},
                            ],
                            "correctChoiceId": "a",
                        }
                    ),
                },
            ],
        )
    )

    service = BattlePreparationService(repository=repo, classifier=classifier)

    result = await service.prepare("set-1")

    assert result is not None
    assert result.total_item_count == 3
    assert result.deleted_excluded_count == 1
    assert result.active_item_count == 2
    assert result.non_multiple_choice_excluded_count == 0
    assert result.eligible_question_count == 2
    assert result.startable is True
    assert result.reason_code is None
    assert len(result.questions) == 2


async def test_prepare_sets_reason_code_when_no_eligible_question_remains():
    classifier = BattleQuestionClassifier()
    repo = _StubRepo(
        (
            "set-1",
            "セットA",
            [
                {
                    "saved_quiz_id": "free-text",
                    "is_deleted": False,
                    "answer_package_json": json.dumps({"question": "text-only"}),
                }
            ],
        )
    )

    service = BattlePreparationService(repository=repo, classifier=classifier)

    result = await service.prepare("set-1")

    assert result is not None
    assert result.startable is False
    assert result.eligible_question_count == 0
    assert result.reason_code == "NO_ELIGIBLE_MULTIPLE_CHOICE"
