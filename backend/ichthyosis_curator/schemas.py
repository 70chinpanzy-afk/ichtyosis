"""Pydanticモデル定義"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


Category = Literal[
    "新薬・治療法",
    "研究論文",
    "ケア・対処法",
    "体験談・対処法",
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


class DrugInfo(BaseModel):
    """記事に登場する薬品情報"""
    model_config = ConfigDict(extra="forbid")

    drug_name: str = Field(description="薬品名（日本語表記、括弧で英語名も記載）")
    ingredients: str = Field(default="", description="有効成分・薬剤名（一般名）")
    description: str = Field(default="", description="この薬が何をするか、一般向けの簡単な説明")


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
    patient_insight: str = Field(default="", description="患者さんへのポイント: この記事が患者さんやご家族にとって何を意味するか")
    drugs: list[DrugInfo] = Field(default_factory=list, description="記事に含まれる薬品リスト")


class CurationBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    curated_articles: list[CuratedArticle]


class DailyDigest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str
    total_sources_scanned: int
    articles: list[CuratedArticle]
    greeting: str = ""
