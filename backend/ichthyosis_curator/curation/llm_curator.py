"""OpenAI gpt-4oによるキュレーション・翻訳"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Type, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from ichthyosis_curator.schemas import (
    RawArticle,
    CuratedArticle,
    CurationBatchResult,
)
from ichthyosis_curator.curation.prompts import (
    SYSTEM_PROMPT,
    CURATION_USER_PROMPT,
    DAILY_GREETING_PROMPT,
)

load_dotenv()
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class BatchFailure:
    """LLMキュレーションバッチの失敗記録（1バッチ = 1件）"""

    batch_index: int
    error: str


@dataclass
class CurationRunStats:
    """curate_articles 呼び出し1回分の実行統計。

    呼び出し元が失敗を検知できるよう curate_articles に渡して
    バッチ失敗を蓄積させるための軽量な収集用オブジェクト。
    """

    total_batches: int = 0
    failures: list[BatchFailure] = field(default_factory=list)

    @property
    def failed_batches(self) -> int:
        return len(self.failures)

    @property
    def all_batches_failed(self) -> bool:
        return self.total_batches > 0 and self.failed_batches == self.total_batches


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _parse_llm(
    client: OpenAI,
    schema: Type[T],
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o",
) -> T:
    resp = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text_format=schema,
    )
    return resp.output_parsed


def curate_articles(
    raw_articles: list[RawArticle],
    model: str = "gpt-4o",
    batch_size: int = 10,
    stats: CurationRunStats | None = None,
) -> list[CuratedArticle]:
    """記事をバッチ処理でキュレーション（関連性評価・分類・翻訳）

    stats: 指定するとバッチ数・失敗回数・代表エラーを呼び出し元に伝えるための
    CurationRunStats に結果を蓄積する（既存呼び出しとの後方互換性維持のためオプション）。
    """
    if not raw_articles:
        return []

    client = _get_client()
    all_curated: list[CuratedArticle] = []

    batch_count = (len(raw_articles) + batch_size - 1) // batch_size
    if stats is not None:
        stats.total_batches += batch_count

    for i in range(0, len(raw_articles), batch_size):
        batch = raw_articles[i : i + batch_size]

        # LLMに渡すために記事情報を構造化
        articles_for_llm = []
        for a in batch:
            articles_for_llm.append({
                "source": a.source,
                "source_id": a.source_id,
                "title": a.title,
                "abstract": a.abstract[:1000],  # トークン節約
                "url": a.url,
                "published_date": a.published_date,
                "language": a.language,
            })

        articles_json = json.dumps(articles_for_llm, ensure_ascii=False, indent=2)
        prompt = CURATION_USER_PROMPT.format(articles_json=articles_json)

        try:
            result = _parse_llm(
                client, CurationBatchResult, SYSTEM_PROMPT, prompt, model
            )
            all_curated.extend(result.curated_articles)
            logger.debug(f"Batch {i // batch_size + 1}: {len(result.curated_articles)} curated")
        except Exception as e:
            logger.error(f"Curation batch {i // batch_size + 1} failed: {e}")
            if stats is not None:
                stats.failures.append(
                    BatchFailure(batch_index=i // batch_size + 1, error=str(e))
                )
            continue

    # 関連性スコア0.3以上でフィルタし、スコア降順ソート
    filtered = [a for a in all_curated if a.relevance_score >= 0.3]
    filtered.sort(key=lambda a: a.relevance_score, reverse=True)

    logger.info(
        f"Curation: {len(filtered)} relevant from {len(raw_articles)} raw articles"
    )
    return filtered


def generate_greeting(date_str: str, model: str = "gpt-4o") -> str:
    """日次挨拶メッセージを生成"""
    client = _get_client()
    try:
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": "あなたは温かいメッセージを書くアシスタントです。"},
                {"role": "user", "content": DAILY_GREETING_PROMPT.format(date=date_str)},
            ],
        )
        return resp.output_text
    except Exception as e:
        logger.warning(f"Greeting generation failed: {e}")
        return f"{date_str}の魚鱗癬関連情報をお届けします。"
