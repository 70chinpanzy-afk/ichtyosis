"""重複排除モジュール"""

import hashlib

from ichthyosis_curator.schemas import CuratedArticle
from ichthyosis_curator.db import is_article_seen, mark_article_seen


def compute_article_hash(source: str, source_id: str) -> str:
    return hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()


def filter_unseen_articles(
    articles: list[CuratedArticle],
    db_path: str,
) -> list[CuratedArticle]:
    unseen = []
    for article in articles:
        article_hash = compute_article_hash(article.source, article.source_id)
        if not is_article_seen(db_path, article_hash):
            unseen.append(article)
    return unseen


def mark_articles_sent(
    articles: list[CuratedArticle],
    db_path: str,
) -> None:
    for article in articles:
        article_hash = compute_article_hash(article.source, article.source_id)
        mark_article_seen(
            db_path,
            article_hash=article_hash,
            source=article.source,
            source_id=article.source_id,
            title=article.original_title,
            url=article.url,
        )
