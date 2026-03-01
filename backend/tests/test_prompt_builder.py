"""
プロンプトビルダー拡張のユニットテスト (Task 7.2)

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8, 3.9, 3.10
"""

import pytest
from app.core.prompt_builder import build_prompt_url_mode, build_prompt_category_mode


# --- テスト共通パラメータ ---
BASE_KWARGS = dict(
    category_name="科学",
    url="https://example.com",
    title="テスト記事",
    text_excerpt="テスト本文テキスト",
    quotes=["引用文1"],
    question_count=1,
)


class TestBuildConstraintRules:
    """build_constraint_rules 関数化の検証（Req 3.4〜3.6）"""

    def test_default_args_produce_80_char_limit(self):
        """デフォルト引数で 80 文字制限が含まれる（Req 3.5）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS)
        assert "80文字以内" in prompt

    def test_short_produces_40_char_limit(self):
        """length_option='short' で 40 文字制限（Req 3.4）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS, length_option="short")
        assert "40文字以内" in prompt
        assert "80文字以内" not in prompt

    def test_long_produces_150_char_limit(self):
        """length_option='long' で 150 文字制限（Req 3.6）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS, length_option="long")
        assert "150文字以内" in prompt
        assert "80文字以内" not in prompt

    def test_medium_produces_80_char_limit(self):
        """length_option='medium' で 80 文字制限（Req 3.5）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS, length_option="medium")
        assert "80文字以内" in prompt


class TestDifficultySection:
    """difficulty 別指示文の検証（Req 3.1〜3.3）"""

    def test_easy_difficulty_instruction_included(self):
        """difficulty='easy' で一般向け指示が含まれる（Req 3.1）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS, difficulty="easy")
        # 「一般」「広く知られた」等のキーワードが入っていること
        assert "一般" in prompt or "広く知られた" in prompt or "かんたん" in prompt

    def test_normal_difficulty_instruction_included(self):
        """difficulty='normal' で競技クイズレベル指示が含まれる（Req 3.2）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS, difficulty="normal")
        assert "競技クイズ" in prompt or "ふつう" in prompt

    def test_hard_difficulty_instruction_included(self):
        """difficulty='hard' で専門家向け指示が含まれる（Req 3.3）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS, difficulty="hard")
        assert "専門" in prompt or "ニッチ" in prompt or "むずかしい" in prompt

    def test_default_difficulty_is_normal(self):
        """デフォルト（difficulty 未指定）で normal 相当の指示が含まれる"""
        prompt_default = build_prompt_url_mode(**BASE_KWARGS)
        prompt_normal = build_prompt_url_mode(**BASE_KWARGS, difficulty="normal")
        assert prompt_default == prompt_normal


class TestTopicSection:
    """topic 指示セクションの検証（Req 3.8〜3.10）"""

    def test_topic_section_included_when_specified(self):
        """topic 指定時にトピック指示が含まれる（Req 3.8）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS, topic="富士山")
        assert "富士山" in prompt

    def test_topic_safety_constraint_included(self):
        """topic 指定時に本文外知識禁止の安全制約が含まれる（Req 3.10）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS, topic="富士山")
        # 「本文」または「裏付け」等の制約キーワードが入っていること
        assert "本文" in prompt or "裏付け" in prompt

    def test_topic_section_omitted_when_none(self):
        """topic=None 時にトピック指示セクションが含まれない（Req 3.9）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS, topic=None)
        assert "トピック指示" not in prompt

    def test_topic_section_omitted_by_default(self):
        """デフォルト（topic 未指定）でトピック指示が省かれる（Req 3.9）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS)
        assert "トピック指示" not in prompt


class TestBackwardCompatibility:
    """既存動作の後方互換性検証（Req 6.1〜6.3）"""

    def test_existing_category_name_still_in_prompt(self):
        """category_name がプロンプトに反映される（既存動作）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS)
        assert "科学" in prompt

    def test_url_still_in_prompt(self):
        """URL がプロンプトに反映される（既存動作）"""
        prompt = build_prompt_url_mode(**BASE_KWARGS)
        assert "https://example.com" in prompt

    def test_category_mode_still_uses_constraint_rules(self):
        """build_prompt_category_mode が 80 文字制限を含む（既存動作維持）"""
        prompt = build_prompt_category_mode("科学", 1)
        assert "80文字以内" in prompt
