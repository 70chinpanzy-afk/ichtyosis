"""Pydanticモデル定義"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

from ichthyosis_curator.identifiers import article_slug


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


class DeliveryItem(BaseModel):
    """LINE配信用の正規化モデル。

    配信対象は2系統ある:
      - 当日キュレーションした CuratedArticle（週次まとめの当日分・即時アラート）
      - 過去日の digests/*.json から読み直した行（週次まとめの過去6日分）

    後者には region や旧カテゴリ（sales系プロンプトが混入していた時期のもの）が
    含まれており CuratedArticle では復元できないため、category を素の str にし
    extra="ignore" で余分なキーを捨てる専用モデルを用意する。
    """

    model_config = ConfigDict(extra="ignore")

    source: str = ""
    source_id: str = ""
    original_title: str = ""
    title_ja: str = ""
    summary_ja: str = ""
    patient_insight: str = ""
    category: str = "ニュース"
    relevance_score: float = 0.0
    url: str = ""

    @property
    def slug(self) -> str:
        """公開URL用の安定ID（DBのidはCIで毎日振り直されるため使わない）"""
        return article_slug(self.source, self.source_id)

    @classmethod
    def from_curated(cls, article: "CuratedArticle") -> "DeliveryItem":
        return cls(
            source=article.source,
            source_id=article.source_id,
            original_title=article.original_title,
            title_ja=article.title_ja,
            summary_ja=article.summary_ja,
            patient_insight=article.patient_insight,
            category=article.category,
            relevance_score=article.relevance_score,
            url=article.url,
        )

    @classmethod
    def from_row(cls, row: dict) -> "DeliveryItem":
        """digests/*.json の1行（DBのcurated_articles由来）から復元する"""
        return cls(
            source=row.get("source") or "",
            source_id=row.get("source_id") or "",
            original_title=row.get("original_title") or "",
            title_ja=row.get("title_ja") or "",
            summary_ja=row.get("summary_ja") or "",
            patient_insight=row.get("patient_insight") or "",
            category=row.get("category") or "ニュース",
            relevance_score=row.get("relevance_score") or 0.0,
            url=row.get("url") or "",
        )
