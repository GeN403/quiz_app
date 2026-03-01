"""
ResolveConfig ドメインサービスのユニットテスト (Task 5.1)

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 5.4
"""

import pytest
from app.core.resolve_config import ResolveConfig
from app.core.config import CATEGORY_NAMES


# ---------------------------------------------------------------------------
# 候補リスト定数のテスト（Requirements: 1.5, 2.3, 3.3, 4.2, 4.4）
# ---------------------------------------------------------------------------

class TestCandidateConstants:
    """クラス定数が正しく定義されていることを確認"""

    def test_difficulty_candidates_values(self):
        """DIFFICULTY_CANDIDATES が easy/normal/hard の 3 値であること"""
        assert set(ResolveConfig.DIFFICULTY_CANDIDATES) == {"easy", "normal", "hard"}

    def test_difficulty_candidates_is_tuple(self):
        """DIFFICULTY_CANDIDATES が tuple であること（accidental mutation 防止）"""
        assert isinstance(ResolveConfig.DIFFICULTY_CANDIDATES, tuple)

    def test_length_candidates_values(self):
        """LENGTH_CANDIDATES が short/medium/long の 3 値であること"""
        assert set(ResolveConfig.LENGTH_CANDIDATES) == {"short", "medium", "long"}

    def test_length_candidates_is_tuple(self):
        """LENGTH_CANDIDATES が tuple であること"""
        assert isinstance(ResolveConfig.LENGTH_CANDIDATES, tuple)

    def test_genre_candidates_count(self):
        """GENRE_CANDIDATES が 13 要素であること（CATEGORY_NAMES に対応）
        CATEGORY_NAMES が将来変更された場合はこのテストも更新対象。
        """
        assert len(ResolveConfig.GENRE_CANDIDATES) == 13

    def test_genre_candidates_no_duplicates(self):
        """GENRE_CANDIDATES に重複がないこと"""
        candidates = ResolveConfig.GENRE_CANDIDATES
        assert len(candidates) == len(set(candidates))

    def test_genre_candidates_is_tuple(self):
        """GENRE_CANDIDATES が tuple であること"""
        assert isinstance(ResolveConfig.GENRE_CANDIDATES, tuple)

    def test_genre_candidates_all_in_category_names(self):
        """GENRE_CANDIDATES の全値が CATEGORY_NAMES.values() に含まれること"""
        category_values = set(CATEGORY_NAMES.values())
        for genre in ResolveConfig.GENRE_CANDIDATES:
            assert genre in category_values

    def test_genre_candidates_order_deterministic(self):
        """GENRE_CANDIDATES の順序が CATEGORY_NAMES の挿入順と一致すること
        （set を使っていないこと = プロセス間で順序が安定すること）
        """
        expected = tuple(dict.fromkeys(CATEGORY_NAMES.values()))
        assert ResolveConfig.GENRE_CANDIDATES == expected


# ---------------------------------------------------------------------------
# resolve_difficulty のテスト（Requirements: 2.1, 2.2, 2.3）
# ---------------------------------------------------------------------------

class TestResolveDifficulty:
    """resolve_difficulty メソッドのテスト"""

    def test_none_returns_valid_value(self):
        """None を渡すと DIFFICULTY_CANDIDATES のいずれかを返すこと"""
        rc = ResolveConfig(seed=42)
        result = rc.resolve_difficulty(None)
        assert result in ResolveConfig.DIFFICULTY_CANDIDATES

    def test_explicit_easy(self):
        """'easy' を渡すと 'easy' をそのまま返すこと（明示指定値の最優先）"""
        rc = ResolveConfig(seed=42)
        assert rc.resolve_difficulty("easy") == "easy"

    def test_explicit_normal(self):
        """'normal' を渡すと 'normal' をそのまま返すこと"""
        rc = ResolveConfig(seed=42)
        assert rc.resolve_difficulty("normal") == "normal"

    def test_explicit_hard(self):
        """'hard' を渡すと 'hard' をそのまま返すこと"""
        rc = ResolveConfig(seed=42)
        assert rc.resolve_difficulty("hard") == "hard"

    def test_none_result_in_candidates(self):
        """None 時のランダム選択結果が有効値のみであること"""
        for seed in range(20):
            rc = ResolveConfig(seed=seed)
            assert rc.resolve_difficulty(None) in ("easy", "normal", "hard")


# ---------------------------------------------------------------------------
# resolve_length のテスト（Requirements: 3.1, 3.2, 3.3）
# ---------------------------------------------------------------------------

class TestResolveLength:
    """resolve_length メソッドのテスト"""

    def test_none_returns_valid_value(self):
        """None を渡すと LENGTH_CANDIDATES のいずれかを返すこと"""
        rc = ResolveConfig(seed=42)
        result = rc.resolve_length(None)
        assert result in ResolveConfig.LENGTH_CANDIDATES

    def test_explicit_short(self):
        """'short' を渡すと 'short' をそのまま返すこと"""
        rc = ResolveConfig(seed=42)
        assert rc.resolve_length("short") == "short"

    def test_explicit_medium(self):
        """'medium' を渡すと 'medium' をそのまま返すこと"""
        rc = ResolveConfig(seed=42)
        assert rc.resolve_length("medium") == "medium"

    def test_explicit_long(self):
        """'long' を渡すと 'long' をそのまま返すこと"""
        rc = ResolveConfig(seed=42)
        assert rc.resolve_length("long") == "long"

    def test_none_result_in_candidates(self):
        """None 時のランダム選択結果が有効値のみであること"""
        for seed in range(20):
            rc = ResolveConfig(seed=seed)
            assert rc.resolve_length(None) in ("short", "medium", "long")


# ---------------------------------------------------------------------------
# resolve_genre のテスト（Requirements: 4.1, 4.2, 4.3, 4.4）
# ---------------------------------------------------------------------------

class TestResolveGenre:
    """resolve_genre メソッドのテスト"""

    def test_none_returns_value_in_candidates(self):
        """None を渡すと GENRE_CANDIDATES のいずれかを返すこと"""
        rc = ResolveConfig(seed=42)
        result = rc.resolve_genre(None)
        assert result in ResolveConfig.GENRE_CANDIDATES

    def test_none_result_not_empty(self):
        """None 時の結果が空文字・None にならないこと"""
        rc = ResolveConfig(seed=42)
        result = rc.resolve_genre(None)
        assert result is not None
        assert result != ""

    def test_explicit_value_returned_as_is(self):
        """明示的なジャンル値を渡すとそのまま返すこと"""
        rc = ResolveConfig(seed=42)
        assert rc.resolve_genre("スポーツ") == "スポーツ"

    def test_explicit_custom_genre(self):
        """GENRE_CANDIDATES にない自由記述ジャンルもそのまま返すこと"""
        rc = ResolveConfig(seed=42)
        assert rc.resolve_genre("プログラミング") == "プログラミング"

    def test_none_result_in_candidates_multiple_seeds(self):
        """複数 seed で None 時の結果が常に GENRE_CANDIDATES 内であること"""
        for seed in range(20):
            rc = ResolveConfig(seed=seed)
            assert rc.resolve_genre(None) in ResolveConfig.GENRE_CANDIDATES


# ---------------------------------------------------------------------------
# 決定論的再現性のテスト（Requirements: 5.4）
# ---------------------------------------------------------------------------

class TestDeterministicReproducibility:
    """同一 seed + 同一呼び出し順で常に同一結果が得られることを確認"""

    def test_same_seed_same_results(self):
        """同一 seed の 2 インスタンスが同じ呼び出し順で同一結果を返すこと"""
        rc1 = ResolveConfig(seed=12345)
        rc2 = ResolveConfig(seed=12345)

        assert rc1.resolve_difficulty(None) == rc2.resolve_difficulty(None)
        assert rc1.resolve_length(None) == rc2.resolve_length(None)
        assert rc1.resolve_genre(None) == rc2.resolve_genre(None)

    def test_same_seed_repeated_calls_same_result(self):
        """同一 seed で複数回インスタンス生成しても常に同一結果であること"""
        results = []
        for _ in range(5):
            rc = ResolveConfig(seed=99)
            d = rc.resolve_difficulty(None)
            le = rc.resolve_length(None)
            g = rc.resolve_genre(None)
            results.append((d, le, g))

        assert len(set(results)) == 1, "全実行で同一結果が得られるべき"

    def test_different_seeds_may_differ(self):
        """異なる seed では結果が異なる可能性があること（統計的確認）"""
        # 100 種の seed のうち少なくとも 2 種が異なる結果を返すことを確認
        results = set()
        for seed in range(100):
            rc = ResolveConfig(seed=seed)
            results.add(rc.resolve_difficulty(None))
        # easy/normal/hard の 3 値があれば diversity がある
        assert len(results) > 1

    def test_no_global_state_pollution(self):
        """異なる seed の 2 インスタンスが互いに干渉しないこと"""
        rc_a = ResolveConfig(seed=1)
        rc_b = ResolveConfig(seed=2)

        # rc_b を先に呼び出しても rc_a の結果は seed=1 のまま
        _ = rc_b.resolve_difficulty(None)
        _ = rc_b.resolve_length(None)

        rc_a_fresh = ResolveConfig(seed=1)
        assert rc_a.resolve_difficulty(None) == rc_a_fresh.resolve_difficulty(None)
        assert rc_a.resolve_length(None) == rc_a_fresh.resolve_length(None)
        assert rc_a.resolve_genre(None) == rc_a_fresh.resolve_genre(None)
