"""
ResolveConfig ドメインサービス

difficulty / length / genre フィールドの未指定時に seed ベースで
決定論的にランダム選択を行う。
"""

import random
from typing import Optional

from app.core.config import CATEGORY_NAMES


class ResolveConfig:
    """seed 付き RNG を保持し、各設定フィールドを解決するドメインサービス。

    クラス定数はすべて tuple で定義し、accidental mutation を防止する。
    GENRE_CANDIDATES は dict.fromkeys() で生成することで挿入順を保証する
    （set を使うとプロセス間でハッシュ順が変わり seed 再現性が失われる）。
    """

    DIFFICULTY_CANDIDATES: tuple = ("easy", "normal", "hard")
    LENGTH_CANDIDATES: tuple = ("short", "medium", "long")
    GENRE_CANDIDATES: tuple = tuple(dict.fromkeys(CATEGORY_NAMES.values()))

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def resolve_difficulty(self, value: Optional[str]) -> str:
        """difficulty を解決する。value が非 None の場合はそのまま返す。"""
        if value is not None:
            return value
        return self._rng.choice(self.DIFFICULTY_CANDIDATES)

    def resolve_length(self, value: Optional[str]) -> str:
        """length を解決する。value が非 None の場合はそのまま返す。"""
        if value is not None:
            return value
        return self._rng.choice(self.LENGTH_CANDIDATES)

    def resolve_genre(self, value: Optional[str]) -> str:
        """genre を解決する。value が非 None の場合はそのまま返す。"""
        if value is not None:
            return value
        return self._rng.choice(self.GENRE_CANDIDATES)
