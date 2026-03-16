"""LINE Messaging API通知"""

import logging
import os

import requests

from ichthyosis_curator.schemas import CuratedArticle, DailyDigest

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

CATEGORY_EMOJI = {
    "新薬・治療法": "\U0001f48a",
    "研究論文": "\U0001f4c4",
    "ケア・対処法": "\U0001f9f4",
    "関連疾患からの知見": "\U0001f517",
    "ニュース": "\U0001f4f0",
}



def format_digest_for_line(
    digest: DailyDigest,
    frontend_url: str = "",
    article_db_ids: list[int] | None = None,
) -> str:
    if not frontend_url:
        frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")

    # 記事→DB IDのマッピング
    id_map: dict[str, int] = {}
    if article_db_ids:
        for i, article in enumerate(digest.articles):
            if i < len(article_db_ids):
                id_map[article.source_id] = article_db_ids[i]

    lines = []
    lines.append(f"\U0001f52c 魚鱗癬紅皮症 デイリーニュース")
    lines.append(f"\U0001f4c5 {digest.date}")
    lines.append("")

    if digest.greeting:
        lines.append(digest.greeting)
        lines.append("")

    if not digest.articles:
        lines.append("本日は新しい関連ニュースはありませんでした。")
        lines.append("明日もチェックを続けます。")
        return "\n".join(lines)

    by_category: dict[str, list[CuratedArticle]] = {}
    for article in digest.articles:
        by_category.setdefault(article.category, []).append(article)

    order = ["新薬・治療法", "研究論文", "ケア・対処法", "関連疾患からの知見", "ニュース"]

    for cat in order:
        articles = by_category.get(cat, [])
        if not articles:
            continue
        emoji = CATEGORY_EMOJI.get(cat, "\U0001f4cc")
        lines.append(f"{emoji} {cat}")
        for a in articles[:3]:  # カテゴリ毎に最大3件
            lines.append(f"  {a.title_ja}")
            # フロントエンドURLがあればサイトの記事ページへリンク
            db_id = id_map.get(a.source_id)
            if frontend_url and db_id:
                lines.append(f"  {frontend_url}/article/{db_id}")
            elif a.url:
                lines.append(f"  {a.url}")
            lines.append("")

    # サイトへの全件リンク
    if frontend_url:
        lines.append(f"全{len(digest.articles)}件の記事はこちら")
        lines.append(frontend_url)
    else:
        lines.append(f"計{len(digest.articles)}件")
    return "\n".join(lines)


def send_line_push(token: str, user_id: str, message: str) -> bool:
    """LINE Messaging APIでpushメッセージを送信"""
    if not token or not user_id:
        logger.warning("LINE credentials not configured, skipping notification")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # LINE Messaging APIは1メッセージ最大5000文字
    chunks = _split_message(message, max_len=5000)

    messages = [{"type": "text", "text": chunk} for chunk in chunks[:5]]  # 最大5メッセージ

    body = {
        "to": user_id,
        "messages": messages,
    }

    try:
        resp = requests.post(LINE_PUSH_URL, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            logger.info("LINE push notification sent")
            return True
        else:
            logger.error(f"LINE push failed: {resp.status_code} {resp.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"LINE push request failed: {e}")
        return False


def _split_message(message: str, max_len: int = 5000) -> list[str]:
    if len(message) <= max_len:
        return [message]

    chunks = []
    current = ""
    for line in message.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line[:max_len]
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks
