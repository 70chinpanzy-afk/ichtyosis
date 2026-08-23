"""LINE Messaging API通知（Flex Message対応）"""

import json as _json
import logging
import os

import requests

from ichthyosis_curator.schemas import DeliveryItem

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

# LINEの制限: カルーセルは最大12バブル、Flexメッセージ1件のJSONは50KBまで。
# 「患者さんへのポイント」を載せるとバブルが膨らむので余裕を持って抑える。
MAX_BUBBLES = 12
MAX_FLEX_BYTES = 45000
MAX_INSIGHT_CHARS = 200

MODE_WEEKLY = "weekly"
MODE_URGENT = "urgent"

CATEGORY_COLORS = {
    "新薬・治療法": "#E74C3C",
    "研究論文": "#3498DB",
    "ケア・対処法": "#2ECC71",
    "体験談・対処法": "#F1C40F",
    "関連疾患からの知見": "#9B59B6",
    "ニュース": "#F39C12",
    "制度・支援": "#16A085",
}

CATEGORY_EMOJI = {
    "新薬・治療法": "\U0001f48a",
    "研究論文": "\U0001f4c4",
    "ケア・対処法": "\U0001f9f4",
    "体験談・対処法": "\U0001f4ac",
    "関連疾患からの知見": "\U0001f517",
    "ニュース": "\U0001f4f0",
    "制度・支援": "\U0001f3e5",
}

SOURCE_LABELS = {
    "pubmed": "PubMed",
    "clinical_trials": "臨床試験",
    "google_news": "ニュース",
    "reddit": "Reddit",
    "youtube": "YouTube",
    "patient_blog": "患者ブログ",
    "first": "FIRST",
    "isg": "ISG",
    "inspire": "Inspire",
}

CATEGORY_ORDER = [
    "新薬・治療法",
    "制度・支援",
    "研究論文",
    "ケア・対処法",
    "体験談・対処法",
    "関連疾患からの知見",
    "ニュース",
]


def _get_source_label(source: str) -> str:
    for key, label in SOURCE_LABELS.items():
        if key in source:
            return label
    return "その他"


def _truncate(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _article_link(item: DeliveryItem, frontend_url: str) -> str:
    if frontend_url and item.slug:
        return f"{frontend_url.rstrip('/')}/article/{item.slug}"
    return item.url or ""


def _build_article_bubble(
    item: DeliveryItem, frontend_url: str, insight_override: str = ""
) -> dict:
    """1記事分のFlex Bubble

    insight_override があればそれを「次にできること」として表示する
    （患者プロフィールに合わせて生成した文）。無ければキュレーション時の
    汎用 patient_insight を「患者さんへのポイント」として表示する。
    """
    category = item.category or "ニュース"
    cat_color = CATEGORY_COLORS.get(category, "#95A5A6")
    source_label = _get_source_label(item.source)
    link_url = _article_link(item, frontend_url)

    body_contents = [
        {
            "type": "text",
            "text": item.title_ja or item.original_title or "無題",
            "weight": "bold",
            "size": "xxl",
            "wrap": True,
            "maxLines": 3,
            "color": "#333333",
        },
        {
            "type": "text",
            "text": item.summary_ja or "（要約なし）",
            "size": "xl",
            "color": "#555555",
            "wrap": True,
            "margin": "lg",
        },
    ]

    # 生成済みなのに従来LINEに出ていなかった部分
    insight_text = insight_override or item.patient_insight
    insight_label = "次にできること" if insight_override else "患者さんへのポイント"
    if insight_text:
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#F4F6F8",
            "cornerRadius": "md",
            "paddingAll": "12px",
            "margin": "lg",
            "contents": [
                {
                    "type": "text",
                    "text": insight_label,
                    "size": "md",
                    "weight": "bold",
                    "color": cat_color,
                },
                {
                    "type": "text",
                    "text": _truncate(insight_text, MAX_INSIGHT_CHARS),
                    "size": "lg",
                    "color": "#555555",
                    "wrap": True,
                    "margin": "sm",
                },
            ],
        })

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
                            "text": category,
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
            "contents": body_contents,
            "spacing": "none",
            "paddingTop": "4px",
        },
    }

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


def _build_header_bubble(
    date_label: str,
    greeting: str,
    items: list[DeliveryItem],
    mode: str = MODE_WEEKLY,
    urgent_count: int = 0,
) -> dict:
    """ヘッダー用Bubble（週次まとめ / 速報で出し分け）"""
    if mode == MODE_URGENT:
        title = "速報"
        lead = "期限や募集があるお知らせです"
    else:
        title = "今週のまとめ"
        lead = ""

    contents = [
        {
            "type": "text",
            "text": "魚鱗癬紅皮症",
            "size": "sm",
            "color": "#AAAAAA",
        },
        {
            "type": "text",
            "text": title,
            "weight": "bold",
            "size": "xxl",
            "color": "#333333",
            "margin": "sm",
        },
        {
            "type": "text",
            "text": date_label,
            "size": "md",
            "color": "#999999",
            "margin": "md",
        },
        {
            "type": "separator",
            "margin": "lg",
        },
    ]

    if lead:
        contents.append({
            "type": "text",
            "text": lead,
            "size": "lg",
            "color": "#555555",
            "wrap": True,
            "margin": "lg",
        })

    if greeting:
        contents.append({
            "type": "text",
            "text": greeting,
            "size": "lg",
            "color": "#555555",
            "wrap": True,
            "margin": "lg",
        })

    label = "お知らせ" if mode == MODE_URGENT else "注目の記事"
    contents.append({
        "type": "text",
        "text": f"{label}: {len(items)}件",
        "size": "xl",
        "color": "#333333",
        "weight": "bold",
        "margin": "lg",
    })

    # 速報は数件しか出さないのでカテゴリ内訳は冗長になる
    if mode != MODE_URGENT:
        by_cat: dict[str, int] = {}
        for item in items:
            by_cat[item.category] = by_cat.get(item.category, 0) + 1

        ordered = [c for c in CATEGORY_ORDER if c in by_cat]
        ordered += [c for c in by_cat if c not in CATEGORY_ORDER]
        for cat in ordered:
            emoji = CATEGORY_EMOJI.get(cat, "\U0001f4cc")
            contents.append({
                "type": "text",
                "text": f"{emoji} {cat}: {by_cat[cat]}件",
                "size": "lg",
                "color": "#888888",
                "margin": "sm",
            })

    # 即時送信済みは本文から外しているので、件数だけ知らせる
    if mode == MODE_WEEKLY and urgent_count > 0:
        contents.append({
            "type": "text",
            "text": f"※ 今週の速報{urgent_count}件は送信済みのため除いています",
            "size": "md",
            "color": "#AAAAAA",
            "wrap": True,
            "margin": "lg",
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


def _flex_size(bubbles: list[dict]) -> int:
    return len(
        _json.dumps(
            {"type": "carousel", "contents": bubbles}, ensure_ascii=False
        ).encode("utf-8")
    )


def _trim_bubbles(bubbles: list[dict], has_footer: bool) -> list[dict]:
    """バブル数とJSONサイズをLINEの制限内に収める（末尾の記事から削る）"""
    footer = bubbles.pop() if has_footer else None

    if footer is not None:
        max_articles = MAX_BUBBLES - 2  # ヘッダー + フッター
    else:
        max_articles = MAX_BUBBLES - 1
    if len(bubbles) - 1 > max_articles:
        bubbles = bubbles[: max_articles + 1]

    def assembled(bs: list[dict]) -> list[dict]:
        return bs + [footer] if footer is not None else bs

    while len(bubbles) > 1 and _flex_size(assembled(bubbles)) > MAX_FLEX_BYTES:
        bubbles.pop()

    return assembled(bubbles)


def build_flex_messages(
    items: list[DeliveryItem],
    date_label: str,
    greeting: str = "",
    frontend_url: str = "",
    mode: str = MODE_WEEKLY,
    urgent_count: int = 0,
    insight_overrides: dict[str, str] | None = None,
) -> list[dict]:
    """Flex Messageオブジェクトのリストを生成

    insight_overrides: source_id -> パーソナライズ済みテキスト。
    永続化しない前提でここに直接渡す（DeliveryItem には載せない）。
    """
    if not frontend_url:
        frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")

    if not items:
        return [build_empty_message(date_label, greeting)]

    bubbles: list[dict] = [
        _build_header_bubble(date_label, greeting, items, mode, urgent_count)
    ]
    insight_overrides = insight_overrides or {}
    for item in items:
        bubbles.append(
            _build_article_bubble(
                item, frontend_url, insight_overrides.get(item.source_id, "")
            )
        )

    has_footer = bool(frontend_url) and mode == MODE_WEEKLY
    if has_footer:
        bubbles.append(_build_footer_bubble(frontend_url, len(items)))

    bubbles = _trim_bubbles(bubbles, has_footer)

    if mode == MODE_URGENT:
        alt_text = f"魚鱗癬紅皮症 速報 {date_label}（{len(items)}件）"
    else:
        alt_text = f"魚鱗癬紅皮症 今週のまとめ {date_label}（{len(items)}件）"

    return [{
        "type": "flex",
        "altText": alt_text[:400],
        "contents": {
            "type": "carousel",
            "contents": bubbles,
        },
    }]


def build_empty_message(date_label: str, greeting: str = "") -> dict:
    """新着なしのときのテキストメッセージ"""
    body = f"\U0001f52c 魚鱗癬紅皮症 今週のまとめ\n\U0001f4c5 {date_label}\n\n"
    if greeting:
        body += f"{greeting}\n\n"
    body += "今週は新しい関連情報はありませんでした。\n引き続きチェックを続けます。"
    return {"type": "text", "text": body}


def format_items_for_line(
    items: list[DeliveryItem],
    date_label: str,
    greeting: str = "",
    frontend_url: str = "",
) -> str:
    """テキスト形式のフォールバック"""
    if not frontend_url:
        frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")

    lines = ["\U0001f52c 魚鱗癬紅皮症 今週のまとめ", f"\U0001f4c5 {date_label}", ""]

    if greeting:
        lines.extend([greeting, ""])

    if not items:
        lines.append("今週は新しい関連情報はありませんでした。")
        return "\n".join(lines)

    by_category: dict[str, list[DeliveryItem]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)

    ordered = [c for c in CATEGORY_ORDER if c in by_category]
    ordered += [c for c in by_category if c not in CATEGORY_ORDER]

    for cat in ordered:
        emoji = CATEGORY_EMOJI.get(cat, "\U0001f4cc")
        lines.append(f"{emoji} {cat}")
        for item in by_category[cat][:3]:
            lines.append(f"  {item.title_ja or item.original_title}")
            link = _article_link(item, frontend_url)
            if link:
                lines.append(f"  {link}")
            lines.append("")

    if frontend_url:
        lines.append(f"全{len(items)}件の記事はこちら")
        lines.append(frontend_url)
    else:
        lines.append(f"計{len(items)}件")
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

    body_size = len(_json.dumps(body, ensure_ascii=False).encode("utf-8"))
    logger.info(f"LINE Flex push: {len(messages)} messages, body size={body_size} bytes")

    try:
        resp = requests.post(LINE_PUSH_URL, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            logger.info("LINE Flex Message sent")
            return True

        logger.error(
            f"LINE Flex push failed: {resp.status_code} {resp.text} (body_size={body_size})"
        )
        # Flex失敗時はテキストにフォールバック
        logger.info("Falling back to text message")
        alt_texts = [
            msg.get("altText", "")
            for msg in messages
            if msg.get("type") == "flex"
        ]
        if alt_texts:
            text_body = {
                "to": user_id,
                "messages": [{"type": "text", "text": t} for t in alt_texts[:5] if t],
            }
            try:
                resp2 = requests.post(
                    LINE_PUSH_URL, headers=headers, json=text_body, timeout=30
                )
                if resp2.status_code == 200:
                    logger.info("LINE text fallback sent")
                    return True
                logger.error(
                    f"LINE text fallback also failed: {resp2.status_code} {resp2.text}"
                )
            except requests.RequestException as e2:
                logger.error(f"LINE text fallback request failed: {e2}")
        return False
    except requests.RequestException as e:
        logger.error(f"LINE Flex push request failed: {e}")
        return False


def send_line_push(token: str, user_id: str, message: str) -> bool:
    """テキストメッセージを送信"""
    if not token or not user_id:
        logger.warning("LINE credentials not configured, skipping notification")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    chunks = _split_message(message, max_len=5000)
    body = {
        "to": user_id,
        "messages": [{"type": "text", "text": chunk} for chunk in chunks[:5]],
    }

    try:
        resp = requests.post(LINE_PUSH_URL, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            logger.info("LINE push notification sent")
            return True
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
