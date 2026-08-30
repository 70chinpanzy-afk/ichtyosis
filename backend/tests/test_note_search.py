"""note.com 検索のテスト

以前は特定ユーザーのRSS1本だけを見ており、5か月で13件しか集まらなかった。
検索APIに切り替えて108件・54人になったが、note の検索は語のAND一致ではないため
テーマ別クエリではノイズが混ざる（実測で「魚鱗癬 夏 体温」に対し29件中27件が無関係）。
"""

import pytest

from ichthyosis_curator.sources import patient_communities as pc


def _payload(*notes: dict) -> dict:
    return {"data": {"notes": {"contents": list(notes)}}}


def _note(name: str, description: str = "", key: str = "nabc", urlname: str = "u1") -> dict:
    return {
        "name": name,
        "description": description,
        "key": key,
        "urlname": urlname,
        "user": {"urlname": urlname},
        "publish_at": "2026-08-01T10:00:00.000+09:00",
        "like_count": 12,
        "comment_count": 3,
    }


@pytest.fixture
def stub_api(monkeypatch):
    def _install(payload: dict):
        class _Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return payload

        monkeypatch.setattr(pc.requests, "get", lambda *a, **k: _Resp())

    return _install


def test_検索結果をRawArticleに変換する(stub_api):
    stub_api(_payload(_note("魚鱗癬と歩んだ家族の物語", "娘の話です", "nx1", "papa")))

    articles = pc._fetch_note_search("魚鱗癬", days_back=1000)

    assert len(articles) == 1
    a = articles[0]
    assert a.url == "https://note.com/papa/n/nx1"
    assert a.source == "patient_blog:note_papa"
    assert a.language == "ja"
    assert a.published_date == "2026-08-01"
    # 反応の多さは「多くの人に刺さったか」の手がかりとして残す
    assert "スキ 12" in a.abstract


def test_テーマ別クエリでは病名を含むものだけ残す(stub_api):
    stub_api(_payload(
        _note("魚鱗癬と歩んだ家族の物語⑥〜隠し続けた手〜", "", "n1", "papa"),
        _note("【企画】note版ペイ・フォワード プロジェクト", "優しさのバトン", "n2", "other"),
    ))

    articles = pc._fetch_note_search("魚鱗癬 保育園", days_back=1000, require_disease=True)

    assert [a.title for a in articles] == ["[note] 魚鱗癬と歩んだ家族の物語⑥〜隠し続けた手〜"]


def test_病名クエリでは絞り込まない(stub_api):
    stub_api(_payload(_note("うちの子の話", "", "n1", "papa")))

    assert len(pc._fetch_note_search("魚鱗癬", days_back=1000)) == 1


def test_概要に病名があれば残す(stub_api):
    stub_api(_payload(_note("娘の足の裏を笑われた日", "魚鱗癬の娘が保育園で", "n1", "mama")))

    assert len(pc._fetch_note_search("魚鱗癬 保育園", 1000, require_disease=True)) == 1


def test_期間より古い記事は落とす(stub_api):
    stub_api(_payload(_note("古い記事", "魚鱗癬", "n1", "papa")))

    assert pc._fetch_note_search("魚鱗癬", days_back=1) == []


def test_APIが落ちても空リストで返る(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("API down")

    monkeypatch.setattr(pc.requests, "get", boom)

    assert pc._fetch_note_search("魚鱗癬", days_back=1000) == []


def test_ユーザー情報が欠けた結果は捨てる(stub_api):
    stub_api({"data": {"notes": {"contents": [{"name": "タイトル", "key": "n1"}]}}})

    assert pc._fetch_note_search("魚鱗癬", days_back=1000) == []
