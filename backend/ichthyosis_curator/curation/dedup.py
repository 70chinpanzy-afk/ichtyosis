"""重複排除モジュール"""

from ichthyosis_curator.identifiers import compute_article_hash
from ichthyosis_curator.schemas import CuratedArticle, RawArticle
from ichthyosis_curator.db import is_article_seen, mark_article_seen

__all__ = [
    "compute_article_hash",
    "filter_unseen_articles",
    "filter_unseen_raw",
    "mark_articles_sent",
]


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


def filter_unseen_raw(
    articles: list[RawArticle],
    seen: set[str],
) -> list[RawArticle]:
    """既出記事をキュレーション前（raw段階）に落とす。

    従来の重複排除は LLM キュレーションの後段にあったため、既出記事にも
    毎日 OpenAI の課金が発生していた。raw 段階で落とすことでコストも減る。

    seen は history.load_seen_hashes() が返すコミット済み digests 由来の集合。
    """
    unseen = []
    for article in articles:
        article_hash = compute_article_hash(article.source, article.source_id)
        if article_hash not in seen:
            unseen.append(article)
    return unseen
