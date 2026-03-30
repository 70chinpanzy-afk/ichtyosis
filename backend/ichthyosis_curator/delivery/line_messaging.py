"""LINE Messaging API通知（Flex Message対応）"""

import logging
import os

import requests

from ichthyosis_curator.schemas import CuratedArticle, DailyDigest

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

CATEGORY_COLORS = {
    "経済・ビジネス": "#2ECC71",
    "政治・社会": "#3498DB",
    "テクノロジー": "#9B59B6",
    "国際": "#F39C12",
    "スポーツ・文化": "#E74C3C",
}

CATEGORY_EMOJI = {
    "経済・ビジネス": "\U0001f4b9",
    "政治・社会": "\U0001f3db\ufe0f",
    "テクノロジー": "\U0001f4bb",
    "国際": "\U0001f30d",
    "スポーツ・文化": "\u26bd",
}

REGION_EMOJI = {
    "japan": "\U0001f1ef\U0001f1f5",
    "international": "\U0001f30d",
}

SOURCE_LABELS = {
    "google_news": "ニュース",
}


def _get_source_label(source: str) -> str:
    for key, label in SOURCE_LABELS.items():
        if key in source:
            return label
    return "その他"


def _build_article_bubble(
    article: CuratedArticle,
    frontend_url: str,
    db_id: int | None,
) -> dict:
    """1記事分のFlex Bubble"""
    category = article.category or "ニュース"
    cat_color = CATEGORY_COLORS.get(category, "#95A5A6")
    source_label = _get_source_label(article.source)
    region_emoji = REGION_EMOJI.get(article.region, "")

    # リンクURL
    if frontend_url and db_id:
        link_url = f"{frontend_url}/article/{db_id}"
    else:
        link_url = article.url or ""

    summary = article.summary_ja or "（要約なし）"

    bubble: dict = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"{region_emoji} {category}",
                            "size": "lg",
                            "color": "#FFFFFF",
                        }
                    ],
                    "backgroundColor": cat_color,
                    "cornerRadius": "md",
                    "paddingAll": "6px",
                    "paddingStart": "12px",
                    "paddingEnd": "12px",
                },
                {
                    "type": "text",
                    "text": source_label,
                    "size": "lg",
                    "color": "#999999",
                    "align": "end",
                    "gravity": "center",
                    "flex": 0,
                },
            ],
            "paddingBottom": "10px",
            "paddingTop": "14px",
            "paddingStart": "20px",
            "paddingEnd": "20px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": article.title_ja or article.original_title or "無題",
                    "weight": "bold",
                    "size": "xxl",
                    "wrap": True,
                    "maxLines": 3,
                    "color": "#333333",
                },
                {
                    "type": "text",
                    "text": summary,
                    "size": "xl",
                    "color": "#555555",
                    "wrap": True,
                    "margin": "lg",
                },
            ],
            "spacing": "none",
            "paddingTop": "4px",
        },
    }

    # リンクがある場合はフッターにボタン追加
    if link_url:
        bubble["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "詳しく読む",
                        "uri": link_url,
                    },
                    "style": "primary",
                    "color": cat_color,
                    "height": "sm",
                },
            ],
            "paddingTop": "8px",
        }

    return bubble


def _build_header_bubble(digest: DailyDigest) -> dict:
    """ヘッダー用Bubble（挨拶 + 日付）"""
    contents = [
        {
            "type": "text",
            "text": "Sales News Copilot",
            "size": "sm",
            "color": "#AAAAAA",
        },
        {
            "type": "text",
            "text": "デイリーニュース",
            "weight": "bold",
            "size": "xxl",
            "color": "#333333",
            "margin": "sm",
        },
        {
            "type": "text",
            "text": digest.date,
            "size": "md",
            "color": "#999999",
            "margin": "md",
        },
        {
            "type": "separator",
            "margin": "lg",
        },
    ]

    if digest.greeting:
        contents.append({
            "type": "text",
            "text": digest.greeting,
            "size": "lg",
            "color": "#555555",
            "wrap": True,
            "margin": "lg",
        })

    contents.append({
        "type": "text",
        "text": f"本日の注目記事: {len(digest.articles)}件",
        "size": "xl",
        "color": "#333333",
        "weight": "bold",
        "margin": "lg",
    })

    # カテゴリ別件数
    by_cat: dict[str, int] = {}
    for a in digest.articles:
        by_cat[a.category] = by_cat.get(a.category, 0) + 1

    for cat, count in by_cat.items():
        emoji = CATEGORY_EMOJI.get(cat, "")
        contents.append({
            "type": "text",
            "text": f"{emoji} {cat}: {count}件",
            "size": "lg",
            "color": "#888888",
            "margin": "sm",
        })

    return {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": contents,
        },
    }


def _build_footer_bubble(frontend_url: str, total: int) -> dict:
    """フッター用Bubble（全件リンク）"""
    bubble: dict = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"他にも{total}件の記事があります",
                    "size": "xl",
                    "color": "#555555",
                    "align": "center",
                    "wrap": True,
                },
            ],
            "justifyContent": "center",
            "alignItems": "center",
        },
    }

    if frontend_url:
        bubble["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "すべての記事を見る",
                        "uri": frontend_url,
                    },
                    "style": "primary",
                    "color": "#4A90D9",
                    "height": "sm",
                },
            ],
        }

    return bubble


def build_flex_messages(
    digest: DailyDigest,
    frontend_url: str = "",
    article_db_ids: list[int] | None = None,
) -> list[dict]:
    """Flex Messageオブジェクトのリストを生成"""
    if not frontend_url:
        frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")

    # 記事→DB IDのマッピング
    id_map: dict[str, int] = {}
    if article_db_ids:
        for i, article in enumerate(digest.articles):
            if i < len(article_db_ids):
                id_map[article.source_id] = article_db_ids[i]

    if not digest.articles:
        # 記事なしの場合はテキストメッセージ
        return [{
            "type": "text",
            "text": f"\U0001f4f0 Sales News Copilot\n"
                    f"\U0001f4c5 {digest.date}\n\n"
                    f"{digest.greeting}\n\n"
                    f"本日は新しいニュースはありませんでした。\n"
                    f"明日もチェックを続けます。",
        }]

    messages: list[dict] = []

    # --- Carousel 1: ヘッダー + 上位記事（最大12 bubbles） ---
    bubbles: list[dict] = []
    bubbles.append(_build_header_bubble(digest))

    # 重要度スコアの高い順に最大10記事
    sorted_articles = sorted(digest.articles, key=lambda a: a.relevance_score, reverse=True)
    for article in sorted_articles[:10]:
        db_id = id_map.get(article.source_id)
        bubbles.append(_build_article_bubble(article, frontend_url, db_id))

    # フッター
    bubbles.append(_build_footer_bubble(frontend_url, len(digest.articles)))

    alt_text = f"Sales News Copilot {digest.date}（{len(digest.articles)}件）"
    messages.append({
        "type": "flex",
        "altText": alt_text[:400],
        "contents": {
            "type": "carousel",
            "contents": bubbles,
        },
    })

    return messages


def format_digest_for_line(
    digest: DailyDigest,
    frontend_url: str = "",
    article_db_ids: list[int] | None = None,
) -> str:
    """テキスト形式のフォールバック（後方互換性）"""
    if not frontend_url:
        frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")

    id_map: dict[str, int] = {}
    if article_db_ids:
        for i, article in enumerate(digest.articles):
            if i < len(article_db_ids):
                id_map[article.source_id] = article_db_ids[i]

    lines = []
    lines.append(f"\U0001f4f0 Sales News Copilot")
    lines.append(f"\U0001f4c5 {digest.date}")
    lines.append("")

    if digest.greeting:
        lines.append(digest.greeting)
        lines.append("")

    if not digest.articles:
        lines.append("本日は新しいニュースはありませんでした。")
        return "\n".join(lines)

    by_category: dict[str, list[CuratedArticle]] = {}
    for article in digest.articles:
        by_category.setdefault(article.category, []).append(article)

    order = ["経済・ビジネス", "政治・社会", "テクノロジー", "国際", "スポーツ・文化"]

    for cat in order:
        articles = by_category.get(cat, [])
        if not articles:
            continue
        emoji = CATEGORY_EMOJI.get(cat, "\U0001f4cc")
        lines.append(f"{emoji} {cat}")
        for a in articles[:3]:
            lines.append(f"  {a.title_ja}")
            db_id = id_map.get(a.source_id)
            if frontend_url and db_id:
                lines.append(f"  {frontend_url}/article/{db_id}")
            elif a.url:
                lines.append(f"  {a.url}")
            lines.append("")

    if frontend_url:
        lines.append(f"全{len(digest.articles)}件の記事はこちら")
        lines.append(frontend_url)
    else:
        lines.append(f"計{len(digest.articles)}件")
    return "\n".join(lines)


def send_line_flex(token: str, user_id: str, messages: list[dict]) -> bool:
    """Flex Messageを送信"""
    if not token or not user_id:
        logger.warning("LINE credentials not configured, skipping notification")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    body = {
        "to": user_id,
        "messages": messages[:5],  # LINE APIは最大5メッセージ
    }

    import json as _json
    body_size = len(_json.dumps(body, ensure_ascii=False))
    logger.info(f"LINE Flex push: {len(messages)} messages, body size={body_size} bytes")

    try:
        resp = requests.post(LINE_PUSH_URL, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            logger.info("LINE Flex Message sent")
            return True
        else:
            logger.error(f"LINE Flex push failed: {resp.status_code} {resp.text} (body_size={body_size})")
            # Flex失敗時はテキストにフォールバック
            logger.info("Falling back to text message")
            alt_texts = []
            for msg in messages:
                if msg.get("type") == "flex":
                    alt_texts.append(msg.get("altText", ""))
            if alt_texts:
                text_body = {
                    "to": user_id,
                    "messages": [{"type": "text", "text": t} for t in alt_texts[:5] if t],
                }
                try:
                    resp2 = requests.post(LINE_PUSH_URL, headers=headers, json=text_body, timeout=30)
                    if resp2.status_code == 200:
                        logger.info("LINE text fallback sent")
                        return True
                    else:
                        logger.error(f"LINE text fallback also failed: {resp2.status_code} {resp2.text}")
                except requests.RequestException as e2:
                    logger.error(f"LINE text fallback request failed: {e2}")
            return False
    except requests.RequestException as e:
        logger.error(f"LINE Flex push request failed: {e}")
        return False


def send_line_push(token: str, user_id: str, message: str) -> bool:
    """テキストメッセージを送信（後方互換性）"""
    if not token or not user_id:
        logger.warning("LINE credentials not configured, skipping notification")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    chunks = _split_message(message, max_len=5000)
    messages = [{"type": "text", "text": chunk} for chunk in chunks[:5]]

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
