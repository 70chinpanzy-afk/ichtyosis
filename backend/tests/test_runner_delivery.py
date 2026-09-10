"""runner の配信判定（何を送り、何を送らないか）のテスト"""

import json
from pathlib import Path

import pytest

from ichthyosis_curator import runner
from ichthyosis_curator.config import CuratorConfig
from ichthyosis_curator.delivery import policy
from ichthyosis_curator.schemas import DeliveryItem


@pytest.fixture
def config(tmp_path: Path) -> CuratorConfig:
    return CuratorConfig(
        openai_api_key="dummy",
        data_dir=str(tmp_path),
        line_channel_access_token="token",
        line_user_id="user",
        frontend_url="https://example.com",
    )


@pytest.fixture
def sent(monkeypatch) -> list[tuple[str, list]]:
    """送信を横取りして (ラベル, メッセージ) を記録する"""
    calls: list[tuple[str, list]] = []

    def fake_push_flex(config, messages, dry_run, label):
        calls.append((label, messages))
        return True

    monkeypatch.setattr(runner, "_push_flex", fake_push_flex)
    monkeypatch.setattr(runner, "generate_greeting", lambda *a, **k: "おはようございます。")
    return calls


def _item(source_id: str, score: float = 0.5, **kwargs) -> DeliveryItem:
    return DeliveryItem(
        source="pubmed",
        source_id=source_id,
        title_ja=kwargs.pop("title_ja", "ふつうの記事"),
        summary_ja="要約",
        category=kwargs.pop("category", "研究論文"),
        relevance_score=score,
        url="https://example.com",
        **kwargs,
    )


URGENT = dict(score=0.95, category="新薬・治療法", title_ja="治験の参加者募集が開始")


def _no_weekly(monkeypatch):
    monkeypatch.setattr(policy, "should_send_weekly", lambda today=None: False)


def _weekly(monkeypatch):
    monkeypatch.setattr(policy, "should_send_weekly", lambda today=None: True)


def test_平日にふつうの記事だけなら何も送らない(config, sent, monkeypatch):
    _no_weekly(monkeypatch)
    result = runner._deliver(config, [_item("a")], "2026年08月25日", False, False)
    assert sent == []
    assert result is False


def test_平日でも締切のある記事は即時に送る(config, sent, monkeypatch):
    _no_weekly(monkeypatch)
    runner._deliver(config, [_item("a"), _item("b", **URGENT)], "2026年08月25日", False, False)

    assert [label for label, _ in sent] == ["urgent"]
    bubbles = sent[0][1][0]["contents"]["contents"]
    # 速報にはふつうの記事を混ぜない
    assert len(bubbles) == 2


def test_即時送信した記事は記録され翌日は再送しない(config, sent, monkeypatch):
    _no_weekly(monkeypatch)
    item = _item("b", **URGENT)

    runner._deliver(config, [item], "2026年08月25日", False, False)
    assert (Path(config.data_dir) / policy.ALERTED_FILENAME).exists()

    sent.clear()
    runner._deliver(config, [item], "2026年08月26日", False, False)
    assert sent == []


def test_月曜は週次まとめを送る(config, sent, monkeypatch):
    _weekly(monkeypatch)
    runner._deliver(config, [_item("a"), _item("b", 0.8)], "2026年08月24日", False, False)

    assert [label for label, _ in sent] == ["weekly"]
    bubbles = sent[0][1][0]["contents"]["contents"]
    assert len(bubbles) == 4  # ヘッダー + 記事2 + フッター


def test_月曜に締切記事があれば速報と週次の両方を送り週次からは外す(config, sent, monkeypatch):
    _weekly(monkeypatch)
    runner._deliver(
        config, [_item("a"), _item("b", **URGENT)], "2026年08月24日", False, False
    )

    assert [label for label, _ in sent] == ["urgent", "weekly"]
    weekly_json = json.dumps(sent[1][1], ensure_ascii=False)
    assert "治験の参加者募集が開始" not in weekly_json
    assert "送信済みのため除いています" in weekly_json


def test_force_weeklyは曜日を無視して週次を送る(config, sent, monkeypatch):
    _no_weekly(monkeypatch)
    runner._deliver(config, [_item("a")], "2026年08月25日", False, True)
    assert [label for label, _ in sent] == ["weekly"]


def test_dry_runでは送信も記録もしない(config, monkeypatch, capsys):
    _weekly(monkeypatch)
    monkeypatch.setattr(runner, "generate_greeting", lambda *a, **k: "おはよう。")

    result = runner._deliver(config, [_item("b", **URGENT)], "2026年08月24日", True, False)

    assert result is False
    assert not (Path(config.data_dir) / policy.ALERTED_FILENAME).exists()
    out = capsys.readouterr().out
    assert "DRY RUN (urgent)" in out and "DRY RUN (weekly)" in out


def test_新着ゼロの平日は沈黙する(config, monkeypatch, capsys):
    _no_weekly(monkeypatch)
    runner._send_empty_digest(config, "2026年08月25日", True, False)
    assert "DRY RUN" not in capsys.readouterr().out


def test_新着ゼロでも月曜は新着なしを知らせる(config, monkeypatch, capsys):
    _weekly(monkeypatch)
    runner._send_empty_digest(config, "2026年08月24日", True, False)
    assert "今週は新しい関連情報はありませんでした" in capsys.readouterr().out
