"""記事の識別子

DBの autoincrement な id は使えない。GitHub Actions では SQLite が毎回
空から作られるため id が毎日 1 から振り直され、`articles/1.json` が
日々上書きされて過去記事のページが別記事の内容になってしまう。
（実際に直近6日ぶんの id がすべて 1..N で衝突していた）

そこで公開URLには (source, source_id) から決まる安定した slug を使う。
"""

import hashlib

SLUG_LENGTH = 16


def compute_article_hash(source: str, source_id: str) -> str:
    return hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()


def article_slug(source: str, source_id: str) -> str:
    """公開URL・エクスポートファイル名に使う安定ID"""
    if not source or not source_id:
        return ""
    return compute_article_hash(source, source_id)[:SLUG_LENGTH]
