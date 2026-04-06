"""Bluesky 自動投稿モジュール（AT Protocol）"""

import logging
import os
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def post_to_bluesky(
    articles: list[dict],
    site_url: str = "https://ichtyosis.vercel.app",
) -> bool:
    """
    キュレーション結果をBlueskyに投稿する。
    BLUESKY_HANDLE / BLUESKY_APP_PASSWORD が未設定の場合はスキップ。
    """
    handle = os.environ.get("BLUESKY_HANDLE")
    app_password = os.environ.get("BLUESKY_APP_PASSWORD")

    if not handle or not app_password:
        logger.info("Bluesky credentials not set, skipping Bluesky post")
        return False

    try:
        from atproto import Client
    except ImportError:
        logger.warning("atproto not installed, skipping Bluesky post")
        return False

    try:
        client = Client()
        client.login(handle, app_password)

        post_text = _compose_post(articles, site_url)
        if not post_text:
            logger.info("No articles to post about")
            return False

        # リンクカード（OGP embed）を作成
        facets = _extract_link_facets(post_text)

        client.send_post(
            text=post_text,
            facets=facets if facets else None,
        )
        logger.info(f"Bluesky post successful ({len(post_text)} chars)")
        return True

    except Exception as e:
        logger.error(f"Bluesky post failed: {e}")
        return False


def _compose_post(articles: list[dict], site_url: str) -> Optional[str]:
    """Bluesky投稿を組み立てる（300文字制限 = 300 grapheme clusters）"""
    if not articles:
        return None

    today = datetime.now().strftime("%m/%d")

    tags = "#魚鱗癬 #ichthyosis #希少疾患"
    footer = f"\n\n{site_url}\n{tags}"

    header = f"【{today} 魚鱗癬ニュース】{len(articles)}件の最新情報\n"

    # Blueskyは300 grapheme clusters（日本語1文字=1）
    remaining = 300 - len(header) - len(footer)
    body_lines = []

    for article in articles[:3]:
        title = article.get("title_ja") or article.get("original_title", "")
        if not title:
            continue
        line = f"・{title}"
        if len(line) + 1 > remaining:  # +1 for newline
            # タイトルを短縮
            max_len = remaining - 2  # "…" + "\n"
            if max_len > 5:
                line = line[:max_len] + "…"
                body_lines.append(line)
            break
        body_lines.append(line)
        remaining -= len(line) + 1

    if not body_lines:
        return f"{header.strip()}{footer}"

    body = "\n".join(body_lines)
    return f"{header}{body}{footer}"


def _extract_link_facets(text: str) -> list:
    """テキスト内のURLをBlueskyのfacet（リッチテキスト）に変換"""
    try:
        from atproto import models
    except ImportError:
        return []

    facets = []
    url_pattern = re.compile(r"https?://[^\s]+")

    # UTF-8バイト位置で計算（AT Protocolの仕様）
    text_bytes = text.encode("utf-8")

    for match in url_pattern.finditer(text):
        url = match.group()
        # バイト位置を計算
        start_byte = len(text[: match.start()].encode("utf-8"))
        end_byte = start_byte + len(url.encode("utf-8"))

        facets.append(
            models.AppBskyRichtextFacet.Main(
                index=models.AppBskyRichtextFacet.ByteSlice(
                    byteStart=start_byte,
                    byteEnd=end_byte,
                ),
                features=[
                    models.AppBskyRichtextFacet.Link(uri=url),
                ],
            )
        )

    # ハッシュタグも facet に
    tag_pattern = re.compile(r"#(\S+)")
    for match in tag_pattern.finditer(text):
        tag = match.group(1)
        start_byte = len(text[: match.start()].encode("utf-8"))
        end_byte = start_byte + len(match.group().encode("utf-8"))

        facets.append(
            models.AppBskyRichtextFacet.Main(
                index=models.AppBskyRichtextFacet.ByteSlice(
                    byteStart=start_byte,
                    byteEnd=end_byte,
                ),
                features=[
                    models.AppBskyRichtextFacet.Tag(tag=tag),
                ],
            )
        )

    return facets
