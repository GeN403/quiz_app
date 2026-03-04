"""
ドメイン検証ロジック
"""
import logging

import json
from pathlib import Path
from urllib.parse import urlparse
from fastapi import HTTPException
logger = logging.getLogger(__name__)


def load_allowed_domains():
    """allowed_domains.json から追加許可ドメインを読み込む"""
    config_path = Path(__file__).parent.parent.parent / "config" / "allowed_domains.json"
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("additional_domains", [])
        else:
            logger.info(f"[WARNING] {config_path} が見つかりません。追加ドメインなしで動作します。")
            return []
    except Exception as e:
        logger.info(f"[ERROR] allowed_domains.json の読み込みに失敗: {e}")
        return []


def is_domain_allowed(domain: str, additional_domains: list) -> bool:
    """ドメインが許可リストに含まれるかチェック"""
    domain_lower = domain.lower()

    # 基本許可ドメイン
    if domain_lower == "kotobank.jp" or domain_lower.endswith(".kotobank.jp"):
        return True
    if domain_lower.endswith(".go.jp"):
        return True
    if domain_lower.endswith(".ac.jp"):
        return True

    # 追加許可ドメイン
    for allowed in additional_domains:
        allowed_lower = allowed.lower()
        if domain_lower == allowed_lower or domain_lower.endswith("." + allowed_lower):
            return True

    return False


def validate_url_domain(url: str) -> None:
    """
    URLのドメインが許可リストに含まれるか検証する

    Raises:
        HTTPException: ドメインが許可されていない場合
    """
    additional_domains = load_allowed_domains()

    if url == "参照URLを提示できません":
        # 特殊ケース: URLなしを許可
        return

    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail=f"INVALID_URL_FORMAT: 無効なURL形式です: {url}"
        )

    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if not is_domain_allowed(domain, additional_domains):
            raise HTTPException(
                status_code=400,
                detail=f"SOURCE_URL_DOMAIN_NOT_ALLOWED: ドメイン（{domain}）は許可リストに含まれていません"
            )
        logger.info(f"[OK] URL domain validated: {domain}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"URL_PARSE_ERROR: URLの解析に失敗しました: {str(e)}"
        )
