"""Pydanticモデル定義"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


Category = Literal[
    "新薬・治療法",
    "研究論文",
    "ケア・対処法",
    "関連疾患からの知見",
    "ニュース",
]


class RawArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    source_id: str
    title: str
    abstract: str = ""
    authors: list[str] = Field(default_factory=list)
    url: str
    published_date: Optional[str] = None
    language: str = "en"


class CuratedArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    source_id: str
    original_title: str
    title_ja: str
    summary_ja: str
    category: Category
    relevance_score: float = Field(ge=0.0, le=1.0)
    url: str
    published_date: Optional[str] = None
    curation_reasoning: str = ""


class CurationBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    curated_articles: list[CuratedArticle]


class DailyDigest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str
    total_sources_scanned: int
    articles: list[CuratedArticle]
    greeting: str = ""
