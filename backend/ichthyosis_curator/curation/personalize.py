"""患者プロフィールに合わせた「次にできること」の生成

**このモジュールの出力は LINE 送信にのみ使い、DB にも公開JSON にも保存しない。**

リポジトリ (70chinpanzy-afk/ichtyosis) は公開されており、
frontend/public/data/ はそのままコミットされる。プロフィールは
子どもの医療情報なので、キュレーション段階で混ぜてしまうと公開データに
残ってしまう。そのため personalize は「保存が全部終わったあと、
LINEに送る直前」の独立したパスとして実行する。
"""

from __future__ import annotations

import json
import logging
import os

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from ichthyosis_curator.curation.prompts import (
    PERSONALIZE_SYSTEM_PROMPT,
    PERSONALIZE_USER_PROMPT,
)
from ichthyosis_curator.schemas import DeliveryItem

logger = logging.getLogger(__name__)

# 1回の配信で扱う記事数は最大10件程度なので、まとめて1リクエストで処理する
MAX_ITEMS = 12
MAX_SUMMARY_CHARS = 400


class _PersonalizedInsight(BaseModel):
    """LLMの戻り値。永続化しないのでschemas.pyには置かない"""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    text: str


class _PersonalizedInsightBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insights: list[_PersonalizedInsight]


def personalize_insights(
    items: list[DeliveryItem],
    profile: str,
    model: str = "gpt-4o",
) -> dict[str, str]:
    """記事ごとの「次にできること」を生成し、source_id -> テキスト で返す。

    プロフィール未設定・記事0件・LLM失敗のいずれでも空辞書を返し、
    呼び出し側は汎用の patient_insight にフォールバックする。
    """
    if not profile.strip() or not items:
        return {}

    targets = items[:MAX_ITEMS]
    payload = [
        {
            "source_id": item.source_id,
            "title": item.title_ja or item.original_title,
            "summary": (item.summary_ja or "")[:MAX_SUMMARY_CHARS],
            "category": item.category,
        }
        for item in targets
    ]

    prompt = PERSONALIZE_USER_PROMPT.format(
        profile=profile.strip(),
        articles_json=json.dumps(payload, ensure_ascii=False, indent=2),
    )

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": PERSONALIZE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            text_format=_PersonalizedInsightBatch,
        )
        result = resp.output_parsed
    except Exception as e:
        # パーソナライズは失敗しても配信自体は止めない
        logger.warning(f"パーソナライズに失敗したため汎用文で配信します: {e}")
        return {}

    if result is None:
        return {}

    known = {item.source_id for item in targets}
    overrides = {
        insight.source_id: insight.text.strip()
        for insight in result.insights
        if insight.source_id in known and insight.text.strip()
    }
    logger.info(f"パーソナライズ: {len(overrides)}/{len(targets)} 件に個別コメントを生成")
    return overrides
