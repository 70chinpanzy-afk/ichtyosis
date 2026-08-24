"""受診前ブリーフ: 次の診察で聞くとよいことを組み立てる

読んで終わりにしないための中核。診察は月に1回程度しかなく、時間も短いので
「聞き忘れ」が起きやすい。過去1か月に集まった情報から質問を作っておけば、
短い診察時間を有効に使える。

安全のため出力は「質問」に限定する。判断は医師に委ね、こちらからは
治療方針を提案しない。疑問形になっていない項目は機械的に落とす。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from ichthyosis_curator.curation.history import load_recent_items
from ichthyosis_curator.curation.prompts import (
    VISIT_BRIEF_SYSTEM_PROMPT,
    VISIT_BRIEF_USER_PROMPT,
)
from ichthyosis_curator.schemas import DeliveryItem

logger = logging.getLogger(__name__)

BRIEF_DAYS = 30
MAX_QUESTIONS = 5
# LLMに渡す記事数。多すぎても質問の質は上がらず、トークンだけ増える
MAX_SOURCE_ITEMS = 20
MAX_SUMMARY_CHARS = 300

# 質問として成立している語尾
_QUESTION_ENDINGS = ("？", "?", "か。", " か", "ますか", "ですか", "でしょうか")


class _BriefQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    source_id: str


class _BriefResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[_BriefQuestion]


class BriefEntry(BaseModel):
    """質問と、その根拠になった記事"""

    model_config = ConfigDict(extra="forbid")

    question: str
    article: DeliveryItem | None = None


def is_question(text: str) -> bool:
    """疑問形になっているか（指示文が混ざるのを防ぐ）"""
    stripped = (text or "").strip().rstrip("。 ")
    if not stripped:
        return False
    return any(stripped.endswith(ending.rstrip("。 ")) for ending in _QUESTION_ENDINGS)


def build_visit_brief(
    data_dir: str,
    model: str = "gpt-4o",
    days: int = BRIEF_DAYS,
    today: date | None = None,
    extra_items: list[DeliveryItem] | None = None,
) -> list[BriefEntry]:
    """過去 days 日ぶんの記事から、次の診察で聞くとよいことを作る。

    extra_items は当日ぶん（まだ digests/*.json に書き出されていない記事）。
    失敗時は空リストを返し、呼び出し側は「ブリーフなし」で配信を続ける。
    """
    items = list(extra_items or []) + load_recent_items(data_dir, days=days, today=today)
    if not items:
        return []

    by_source_id: dict[str, DeliveryItem] = {}
    for item in items:
        by_source_id.setdefault(item.source_id, item)

    targets = sorted(
        by_source_id.values(), key=lambda i: i.relevance_score, reverse=True
    )[:MAX_SOURCE_ITEMS]

    payload = [
        {
            "source_id": item.source_id,
            "title": item.title_ja or item.original_title,
            "summary": (item.summary_ja or "")[:MAX_SUMMARY_CHARS],
            "category": item.category,
        }
        for item in targets
    ]

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": VISIT_BRIEF_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": VISIT_BRIEF_USER_PROMPT.format(
                        articles_json=json.dumps(payload, ensure_ascii=False, indent=2)
                    ),
                },
            ],
            text_format=_BriefResult,
        )
        result = resp.output_parsed
    except Exception as e:
        logger.warning(f"受診前ブリーフの生成に失敗したためスキップします: {e}")
        return []

    if result is None:
        return []

    entries: list[BriefEntry] = []
    seen: set[str] = set()
    for q in result.questions:
        question = q.question.strip()
        if not is_question(question):
            logger.info(f"疑問形でないため除外: {question[:40]}")
            continue
        if question in seen:
            continue
        seen.add(question)
        entries.append(
            BriefEntry(question=question, article=by_source_id.get(q.source_id))
        )
        if len(entries) >= MAX_QUESTIONS:
            break

    logger.info(f"受診前ブリーフ: {len(entries)}件の質問を生成")
    return entries
