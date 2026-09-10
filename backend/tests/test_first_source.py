"""FIRST（米国患者団体）ソースのテスト

旧ドメイン ichthyosis.org は消滅しており、2026-07 時点の調査ではこれを
「WAFによるTLS遮断で対処不能」と誤って結論づけていた。実際は
firstskinfoundation.org へリブランド移転していただけで、この取り違えのため
FIRSTは全期間で1件も取得できていなかった。
"""

import pytest

pytest.importorskip("bs4")

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

    assert len(articles) == len(pc.FIRST_GUIDE_PAGES)
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
    assert len(first) == len(pc.FIRST_GUIDE_PAGES)


def test_取得できないISGとInspireは撤去されている():
    # 動かないコードが残っていると「取得できているつもり」になる
    assert not hasattr(pc, "get_isg_articles")
    assert not hasattr(pc, "get_inspire_posts")
