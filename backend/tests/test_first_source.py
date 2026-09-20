"""FIRST（米国患者団体）ソースのテスト

旧ドメイン ichthyosis.org は消滅しており、2026-07 時点の調査ではこれを
「WAFによるTLS遮断で対処不能」と誤って結論づけていた。実際は
firstskinfoundation.org へリブランド移転していただけで、この取り違えのため
FIRSTは全期間で1件も取得できていなかった。
"""

import pytest

pytest.importorskip("bs4")

from datetime import date  # noqa: E402

from ichthyosis_curator.sources import patient_communities as pc  # noqa: E402

GUIDE_HTML = """
<html><body>
  <nav>ナビゲーション</nav>
  <main>
    <h1>Overheating</h1>
    <p>Many individuals with ichthyosis do not sweat normally. Limit outdoor
    activities to before 10:00 a.m. and after 2:00 p.m. Use cooling vests,
    misters and cool packs. Watch for dizziness, fatigue and confusion.</p>
  </main>
  <footer>フッター</footer>
  <script>console.log('x')</script>
</body></html>
"""


def _stub_get(monkeypatch, html: str, status_ok: bool = True):
    class _Resp:
        text = html

        def raise_for_status(self):
            if not status_ok:
                raise RuntimeError("404")

    monkeypatch.setattr(pc.requests, "get", lambda *a, **k: _Resp())
    monkeypatch.setattr(pc.time, "sleep", lambda *_: None)


def test_新ドメインを見ている():
    assert "firstskinfoundation.org" in pc.FIRST_BASE
    assert all("firstskinfoundation.org" in u for u in pc.FIRST_RSS_FEEDS)
    # 消滅した旧ドメインを参照していないこと
    assert "www.ichthyosis.org/" not in " ".join(pc.FIRST_RSS_FEEDS)


def test_実用ガイドを本文つきで取り込む(monkeypatch):
    _stub_get(monkeypatch, GUIDE_HTML)

    articles = pc.fetch_first_guides()

    # 静的ページなので全部を毎日叩かず、日替わりで少しずつ回す
    assert len(articles) == pc.GUIDE_PAGES_PER_RUN
    a = articles[0]
    assert a.source == "patient_org:FIRST_guide"
    assert "10:00 a.m." in a.abstract
    # ナビ・フッタ・スクリプトは落とす
    assert "ナビゲーション" not in a.abstract
    assert "console.log" not in a.abstract


def test_ガイドは収集が空白だったテーマに当たる(monkeypatch):
    from ichthyosis_curator.curation.themes import detect_themes

    _stub_get(monkeypatch, GUIDE_HTML)
    article = pc.fetch_first_guides()[0]

    assert "heat" in detect_themes(f"{article.title} {article.abstract}")


def test_本文が短すぎるページは捨てる(monkeypatch):
    _stub_get(monkeypatch, "<html><body><main><p>短い</p></main></body></html>")

    assert pc.fetch_first_guides() == []


def test_取得に失敗しても落ちない(monkeypatch):
    _stub_get(monkeypatch, GUIDE_HTML, status_ok=False)

    assert pc.fetch_first_guides() == []


def test_ガイドのURLは安定している(monkeypatch):
    _stub_get(monkeypatch, GUIDE_HTML)

    first = {a.source_id for a in pc.fetch_first_guides()}
    second = {a.source_id for a in pc.fetch_first_guides()}

    # 静的ページなので毎回同じIDになり、重複排除で一度だけ配信される
    assert first == second
    assert len(first) == pc.GUIDE_PAGES_PER_RUN


def test_取得できないISGとInspireは撤去されている():
    # 動かないコードが残っていると「取得できているつもり」になる
    assert not hasattr(pc, "get_isg_articles")
    assert not hasattr(pc, "get_inspire_posts")


# --- 日替わりローテーション ---


def test_数日で全ガイドを一巡する():
    """静的ページを毎日全部叩く意味はないが、取りこぼしも困る"""
    seen: set[str] = set()
    base = date(2026, 9, 20).toordinal()
    days_needed = -(-len(pc.FIRST_GUIDE_PAGES) // pc.GUIDE_PAGES_PER_RUN)

    for offset in range(days_needed + 2):
        for path, _ in pc._guides_for_today(date.fromordinal(base + offset)):
            seen.add(path)

    assert seen == {path for path, _ in pc.FIRST_GUIDE_PAGES}


def test_同じ日なら同じガイドを返す():
    day = date(2026, 9, 20)

    assert pc._guides_for_today(day) == pc._guides_for_today(day)


def test_収集が空白だった領域のガイドが入っている():
    paths = {path for path, _ in pc.FIRST_GUIDE_PAGES}

    # 学校・耳・夏の汗は、当初の収集でそれぞれ1件・1件・3件しかなかった
    assert any("school-survival-guide" in p for p in paths)
    assert any("ear-care-for-children" in p for p in paths)
    assert any("is-my-child-overheating" in p for p in paths)
    assert any("bullying" in p for p in paths)


def test_目次ページは含めない():
    # セクションの目次は中身が薄く、記事として配信する価値がない
    index_pages = {
        "/living-with-ichthyosis/life-stages",
        "/living-with-ichthyosis/daily-skin-care",
        "/living-with-ichthyosis/mental-health",
    }
    paths = {path for path, _ in pc.FIRST_GUIDE_PAGES}

    assert not (paths & index_pages)


def test_ガイドのタイトルは英語のまま():
    """original_title になるため。日本語を入れると地域判定を狂わせる原因になる"""
    for _, label in pc.FIRST_GUIDE_PAGES:
        assert not any("\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9faf" for ch in label), label
