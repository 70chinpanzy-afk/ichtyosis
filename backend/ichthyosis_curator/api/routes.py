"""APIエンドポイント定義"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from ichthyosis_curator.db import (
    get_digest_dates,
    get_articles_by_date,
    get_article_by_id,
    search_articles,
)

router = APIRouter()


class DigestSummary(BaseModel):
    date: str
    article_count: int


class ArticleResponse(BaseModel):
    id: int
    digest_date: str
    source: str
    source_id: str
    original_title: Optional[str]
    title_ja: Optional[str]
    summary_ja: Optional[str]
    category: Optional[str]
    region: Optional[str] = None
    relevance_score: Optional[float]
    url: Optional[str]
    published_date: Optional[str]
    curation_reasoning: Optional[str]
    created_at: Optional[str]


def _get_db_path(request: Request) -> str:
    return request.app.state.config.db_path


@router.get("/")
def root():
    return {
        "service": "Sales News Copilot - 営業向けニュースキュレーター",
        "version": "0.2.0",
        "endpoints": ["/api/digests", "/api/articles/{id}", "/api/search"],
    }


@router.get("/api/digests", response_model=list[DigestSummary])
def list_digests(request: Request, limit: int = Query(default=30, le=365)):
    db_path = _get_db_path(request)
    dates = get_digest_dates(db_path, limit)
    result = []
    for date in dates:
        articles = get_articles_by_date(db_path, date)
        result.append(DigestSummary(date=date, article_count=len(articles)))
    return result


@router.get("/api/digests/{date}", response_model=list[ArticleResponse])
def get_digest(request: Request, date: str):
    db_path = _get_db_path(request)
    articles = get_articles_by_date(db_path, date)
    if not articles:
        raise HTTPException(status_code=404, detail=f"Digest not found for {date}")
    return articles


@router.get("/api/articles/{article_id}", response_model=ArticleResponse)
def get_article(request: Request, article_id: int):
    db_path = _get_db_path(request)
    article = get_article_by_id(db_path, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("/api/search", response_model=list[ArticleResponse])
def search(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, le=200),
):
    db_path = _get_db_path(request)
    return search_articles(db_path, q, limit)
