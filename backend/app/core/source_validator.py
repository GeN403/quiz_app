"""
source フィールド検証ロジック
"""
import logging

from typing import Dict, Any, Optional
logger = logging.getLogger(__name__)


def verify_source_fields(quiz_dict: Dict[str, Any], expected_url: str, source_text: Optional[str] = None) -> None:
    """
    単一のクイズオブジェクトのsourceフィールドを検証する

    Args:
        quiz_dict: クイズオブジェクト（dict）
        expected_url: サーバが選定したURL
        source_text: 取得した本文（quote検証用、URLモード時のみ）

    Raises:
        ValueError: 検証失敗時
    """
    # sourceフィールドの存在確認
    if "source" not in quiz_dict:
        raise ValueError("source フィールドが存在しません")

    source = quiz_dict["source"]

    if not isinstance(source, dict):
        raise ValueError(f"source は辞書である必要があります（actual: {type(source)}）")

    # 必須フィールドの確認
    if "url" not in source:
        raise ValueError("source.url が存在しません")
    if "title" not in source:
        raise ValueError("source.title が存在しません")

    # URLの一致確認（URLモード時）
    if expected_url != "参照URLを提示できません":
        actual_url = source["url"]
        if actual_url != expected_url:
            raise ValueError(f"source.url が不一致: expected={expected_url}, actual={actual_url}")
        logger.info(f"[VERIFY] source.url matched: {actual_url}")

    # quote検証（URLモード時）
    if source_text is not None and "quote" in source:
        quote = source["quote"]
        if quote and len(quote) > 0:
            # より緩い正規化：空白・改行・句読点を削除して部分一致を確認
            def normalize(text):
                return (text
                        .replace('\n', '')
                        .replace(' ', '')
                        .replace('　', '')
                        .replace('。', '')  # 句点を削除
                        .replace('、', '')  # 読点を削除
                        .replace('.', '')
                        .replace(',', ''))

            normalized_text = normalize(source_text)
            normalized_quote = normalize(quote)

            if normalized_quote not in normalized_text:
                raise ValueError(f"source.quote が本文に存在しません: '{quote[:50]}...'")
            logger.info(f"[VERIFY] source.quote verified: '{quote[:50]}...'")
        else:
            logger.info(f"[VERIFY] source.quote is empty (allowed in category mode)")

    # 余計なキーがないか確認
    allowed_keys = {"title", "url", "quote"}
    extra_keys = set(source.keys()) - allowed_keys
    if extra_keys:
        raise ValueError(f"source に余計なキーが含まれています: {extra_keys}")

    logger.info("[VERIFY] source fields validation passed")
