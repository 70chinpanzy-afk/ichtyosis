"""LINE配信ポリシー（週次まとめ + 即時アラート）のテスト"""

import json
from datetime import date
from pathlib import Path

import pytest

from ichthyosis_curator.delivery import policy
from ichthyosis_curator.schemas import DeliveryItem

MONDAY = date(2026, 8, 24)
TUESDAY = date(2026, 8, 25)


def _item(source_id: str, score: float = 0.5, **kwargs) -> DeliveryItem:
    return DeliveryItem(
        source=kwargs.pop("source", "pubmed"),
        source_id=source_id,
        title_ja=kwargs.pop("title_ja", "タイトル"),
        summary_ja=kwargs.pop("summary_ja", "要約"),
        category=kwargs.pop("category", "研究論文"),
        relevance_score=score,
        url="https://example.com",
        **kwargs,
    )


# --- 即時アラートの判定 ---


def test_締切キーワードがあれば即時アラートになる():
    assert policy.is_urgent(_item("a", 0.7, title_ja="治験の参加者募集が始まりました"))


def test_英語キーワードは大文字小文字を問わない():
    assert policy.is_urgent(_item("a", 0.7, summary_ja="FDA APPROVED the drug"))


def test_キーワードがあってもスコアが低ければ即時にしない():
    # 「承認を目指す」程度の言及で通知が飛ぶのを防ぐ
    assert not policy.is_urgent(_item("a", 0.5, title_ja="将来の承認を目指した研究"))


def test_高スコアの新薬ニュースは即時アラートになる():
    assert policy.is_urgent(_item("a", 0.9, category="新薬・治療法"))


def test_締切があれば無条件で即時アラートにする():
    # 週次まとめを待つと締切を過ぎてしまう
    item = _item("a", 0.4, category="制度・支援")
    item.deadline = "2026-09-30"
    assert policy.is_urgent(item)


def test_期限内に動く必要があれば即時アラートにする():
    item = _item("a", 0.4, category="制度・支援")
    item.action_required = True
    assert policy.is_urgent(item)


def test_締切も要対応も無い制度記事は週次にまわす():
    assert not policy.is_urgent(_item("a", 0.6, category="制度・支援"))


def test_高スコアでも研究論文は即時にしない():
    # 論文は締切がないので週次まとめで足りる
    assert not policy.is_urgent(_item("a", 0.95, category="研究論文"))


def test_即時アラートはスコア順で上限まで():
    items = [_item(str(i), 0.9, category="新薬・治療法") for i in range(5)]
    items[3].relevance_score = 1.0
    urgent = policy.select_urgent(items)
    assert len(urgent) == policy.MAX_URGENT_PER_RUN
    assert urgent[0].source_id == "3"


def test_送信済みの記事は即時アラートに再登場しない():
    item = _item("a", 0.9, category="新薬・治療法")
    assert policy.select_urgent([item]) == [item]
    assert policy.select_urgent([item], {policy.item_hash(item)}) == []


# --- 週次まとめ ---


def test_週次まとめは月曜だけ送る():
    assert policy.should_send_weekly(MONDAY)
    assert not policy.should_send_weekly(TUESDAY)


def _write_digest(data_dir: Path, day: str, rows: list[dict]) -> None:
    digests = data_dir / "digests"
    digests.mkdir(parents=True, exist_ok=True)
    (digests / f"{day}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


def test_週次まとめは当日ぶんと過去ぶんを重複なくスコア順に並べる(tmp_path: Path):
    _write_digest(tmp_path, "2026-08-20", [
        {"source": "pubmed", "source_id": "old", "title_ja": "過去", "relevance_score": 0.6},
    ])
    today_items = [_item("new", 0.9), _item("new2", 0.4)]

    weekly = policy.build_weekly_items(str(tmp_path), today_items, today=MONDAY)

    assert [i.source_id for i in weekly] == ["new", "old", "new2"]


def test_即時送信済みは週次まとめの本文から外す(tmp_path: Path):
    sent = _item("sent", 0.95)
    weekly = policy.build_weekly_items(
        str(tmp_path), [sent, _item("other", 0.5)],
        exclude={policy.item_hash(sent)}, today=MONDAY,
    )
    assert [i.source_id for i in weekly] == ["other"]


def test_同じ記事が過去日にもある場合は当日版を使う(tmp_path: Path):
    _write_digest(tmp_path, "2026-08-20", [
        {"source": "pubmed", "source_id": "dup", "title_ja": "古い訳", "relevance_score": 0.6},
    ])
    weekly = policy.build_weekly_items(
        str(tmp_path), [_item("dup", 0.6, title_ja="新しい訳")], today=MONDAY
    )
    assert len(weekly) == 1
    assert weekly[0].title_ja == "新しい訳"


def test_週次まとめの件数には上限がある(tmp_path: Path):
    items = [_item(str(i), 0.5) for i in range(30)]
    weekly = policy.build_weekly_items(str(tmp_path), items, today=MONDAY)
    assert len(weekly) == policy.WEEKLY_LIMIT


# --- 即時送信記録（alerted.json） ---


def test_送信記録を書いて読み戻せる(tmp_path: Path):
    item = _item("a", 0.9)
    policy.record_alerted(str(tmp_path), [item], today=MONDAY)

    assert policy.load_alerted(str(tmp_path), today=MONDAY) == {policy.item_hash(item)}
    assert (tmp_path / policy.ALERTED_FILENAME).exists()


def test_同じ記事を二重に記録しない(tmp_path: Path):
    item = _item("a", 0.9)
    policy.record_alerted(str(tmp_path), [item], today=MONDAY)
    policy.record_alerted(str(tmp_path), [item], today=TUESDAY)

    rows = json.loads((tmp_path / policy.ALERTED_FILENAME).read_text(encoding="utf-8"))
    assert len(rows) == 1


def test_保持期間を過ぎた記録は捨てる(tmp_path: Path):
    old = date(2026, 1, 1).isoformat()
    (tmp_path / policy.ALERTED_FILENAME).write_text(
        json.dumps([{"hash": "stale", "date": old, "title": "古い"}]), encoding="utf-8"
    )
    policy.record_alerted(str(tmp_path), [_item("a", 0.9)], today=MONDAY)

    rows = json.loads((tmp_path / policy.ALERTED_FILENAME).read_text(encoding="utf-8"))
    assert [r["hash"] for r in rows] == [policy.item_hash(_item("a", 0.9))]


def test_読み出しは期間で絞る(tmp_path: Path):
    (tmp_path / policy.ALERTED_FILENAME).write_text(
        json.dumps([
            {"hash": "recent", "date": "2026-08-20"},
            {"hash": "stale", "date": "2026-06-01"},
        ]),
        encoding="utf-8",
    )
    assert policy.load_alerted(str(tmp_path), days=7, today=MONDAY) == {"recent"}


def test_壊れた送信記録は空として扱う(tmp_path: Path):
    (tmp_path / policy.ALERTED_FILENAME).write_text("{ broken", encoding="utf-8")
    assert policy.load_alerted(str(tmp_path), today=MONDAY) == set()
