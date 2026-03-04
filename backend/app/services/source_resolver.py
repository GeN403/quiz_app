"""
SourceResolver: URL→本文テキスト抽出→quote候補生成を行うサービス

サーバ責務でURLを解決し、LLMに「捏造」させない設計にする。
"""
import logging

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import re
from fastapi import HTTPException
logger = logging.getLogger(__name__)


class SourceResolver:
    """
    URLから本文を取得し、quote候補を生成するクラス
    """

    def __init__(self, url: str, timeout: int = 10):
        """
        Args:
            url: 取得するURL
            timeout: タイムアウト秒数（デフォルト10秒）
        """
        self.url = url
        self.timeout = timeout
        self.title: Optional[str] = None
        self.text: Optional[str] = None
        self.quotes: List[str] = []

    def fetch_and_parse(self) -> Dict[str, any]:
        """
        URLを取得し、HTMLをパースして本文とquote候補を抽出する

        Returns:
            {
                "url": str,
                "title": str,
                "text": str (全本文),
                "quotes": List[str] (quote候補リスト)
            }

        Raises:
            HTTPException: 取得・パース失敗時
        """
        logger.info(f"[SourceResolver] Fetching URL: {self.url}")

        try:
            # User-Agentを設定してブロックを回避
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(
                self.url,
                timeout=self.timeout,
                headers=headers,
                allow_redirects=True
            )

            logger.info(f"[SourceResolver] HTTP Status: {response.status_code}")
            logger.info(f"[SourceResolver] Final URL: {response.url}")

            response.raise_for_status()

        except requests.exceptions.Timeout as e:
            logger.info(f"[SourceResolver ERROR] Timeout: {e}")
            raise HTTPException(
                status_code=504,
                detail=f"URL_FETCH_TIMEOUT: URLの取得がタイムアウトしました（{self.timeout}秒以内に応答なし）: {self.url}"
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 500
            logger.info(f"[SourceResolver ERROR] HTTP Error {status_code}: {e}")

            if status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail=f"URL_FETCH_FORBIDDEN: URLへのアクセスが拒否されました（403 Forbidden）: {self.url}"
                )
            elif status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"URL_NOT_FOUND: URLが見つかりませんでした（404 Not Found）: {self.url}"
                )
            elif status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail=f"URL_RATE_LIMIT: レート制限に達しました（429 Too Many Requests）: {self.url}"
                )
            else:
                raise HTTPException(
                    status_code=502,
                    detail=f"URL_FETCH_ERROR: URLの取得に失敗しました（HTTP {status_code}）: {self.url}"
                )
        except requests.RequestException as e:
            logger.info(f"[SourceResolver ERROR] Request failed: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"URL_FETCH_FAILED: URLの取得に失敗しました: {str(e)}"
            )

        # HTMLパース
        try:
            soup = BeautifulSoup(response.content, 'html.parser')

            # タイトル抽出
            self.title = soup.title.string.strip() if soup.title and soup.title.string else "タイトル不明"
            logger.info(f"[SourceResolver] Page title: {self.title}")

            # 不要タグを除去
            for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'iframe']):
                tag.decompose()

            # 本文テキスト抽出
            self.text = soup.get_text(separator='\n', strip=True)

            # 空白・改行の正規化
            self.text = re.sub(r'\n+', '\n', self.text)  # 連続改行を1つに
            self.text = re.sub(r' +', ' ', self.text)    # 連続スペースを1つに

            logger.info(f"[SourceResolver] Extracted text length: {len(self.text)} chars")
            logger.info(f"[SourceResolver] Text preview (first 300 chars): {self.text[:300]}...")

            if not self.text or len(self.text) < 100:
                raise HTTPException(
                    status_code=400,
                    detail=f"URL_CONTENT_TOO_SHORT: 抽出テキストが短すぎます（{len(self.text)}文字）。有効なコンテンツが含まれていない可能性があります。"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.info(f"[SourceResolver ERROR] Parse error: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"URL_PARSE_ERROR: ページ内容の解析に失敗しました: {str(e)}"
            )

        # quote候補を生成
        self.quotes = self._extract_quote_candidates(self.text)
        logger.info(f"[SourceResolver] Generated {len(self.quotes)} quote candidates")

        return {
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "quotes": self.quotes
        }

    def _extract_quote_candidates(self, text: str, min_length: int = 100, max_length: int = 500) -> List[str]:
        """
        本文から quote 候補を抽出する

        Args:
            text: 全本文
            min_length: 最小文字数
            max_length: 最大文字数

        Returns:
            quote候補のリスト
        """
        candidates = []

        # 段落に分割（改行2つ以上で区切る）
        paragraphs = re.split(r'\n{2,}', text)

        for para in paragraphs:
            para = para.strip()

            # 長さが適切な段落を候補に追加
            if min_length <= len(para) <= max_length:
                candidates.append(para)

            # 長すぎる段落は文単位で分割して追加
            elif len(para) > max_length:
                # 句点で分割
                sentences = re.split(r'[。．\n]', para)
                current_chunk = ""

                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue

                    # 現在のchunkに追加
                    if len(current_chunk) + len(sent) <= max_length:
                        current_chunk += sent + "。"
                    else:
                        # chunkが十分な長さなら候補に追加
                        if len(current_chunk) >= min_length:
                            candidates.append(current_chunk.strip())
                        current_chunk = sent + "。"

                # 残りのchunkも追加
                if len(current_chunk) >= min_length:
                    candidates.append(current_chunk.strip())

        # 最大10個まで
        return candidates[:10]

    def verify_quote(self, quote: str) -> bool:
        """
        指定されたquoteが本文に含まれるか検証する

        Args:
            quote: 検証するquote

        Returns:
            True: 本文に含まれる
            False: 含まれない
        """
        if not self.text:
            return False

        # より緩い正規化：空白・改行・句読点を削除して検証
        def normalize(text):
            return (text
                    .replace('\n', '')
                    .replace(' ', '')
                    .replace('　', '')
                    .replace('。', '')  # 句点を削除
                    .replace('、', '')  # 読点を削除
                    .replace('.', '')
                    .replace(',', ''))

        normalized_text = normalize(self.text)
        normalized_quote = normalize(quote)

        is_found = normalized_quote in normalized_text

        if is_found:
            logger.info(f"[SourceResolver] Quote verified: '{quote[:50]}...' found in text")
        else:
            logger.info(f"[SourceResolver] Quote NOT found: '{quote[:50]}...'")

        return is_found
