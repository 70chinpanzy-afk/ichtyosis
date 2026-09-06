"""患者プロフィールによるパーソナライズのテスト

最重要なのは「プロフィール由来の文が公開データに漏れないこと」。
リポジトリが公開なので、ここが破れると子どもの医療情報が公開される。
"""

import json
from pathlib import Path

import pytest

from ichthyosis_curator import runner
from ichthyosis_curator.config import CuratorConfig
from ichthyosis_curator.curation import personalize
from ichthyosis_curator.curation.personalize import personalize_insights
from ichthyosis_curator.db import init_db, save_curated_article
from ichthyosis_curator.delivery import line_messaging as lm
from ichthyosis_curator.delivery import policy
from ichthyosis_curator.exporter import export_static_json
from ichthyosis_curator.schemas import DeliveryItem

PROFILE = "対象: 子ども（8歳）\n現在の治療: ヒルドイドソフト（朝晩）"
MARKER = "8歳のお子さんのヒルドイドについて次の診察で聞いてみてください"


def _item(source_id: str = "aaa", **kwargs) -> DeliveryItem:
    return DeliveryItem(
        source="pubmed",
        source_id=source_id,
        title_ja=kwargs.pop("title_ja", "タイトル"),
        summary_ja="要約",
        patient_insight=kwargs.pop("patient_insight", "汎用のポイント"),
        category="研究論文",
        relevance_score=0.8,
        url="https://example.com",
        **kwargs,
    )


# --- personalize_insights 単体 ---


def test_プロフィール未設定なら何も生成しない():
    assert personalize_insights([_item()], "") == {}
    assert personalize_insights([_item()], "   ") == {}


def test_記事が無ければ何も生成しない():
    assert personalize_insights([], PROFILE) == {}


def test_LLMが失敗しても配信は止めない(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("API down")

    monkeypatch.setattr(personalize, "OpenAI", boom)
    assert personalize_insights([_item()], PROFILE) == {}


def _stub_llm(monkeypatch, insights: list[dict]):
    class _Resp:
        output_parsed = personalize._PersonalizedInsightBatch(
            insights=[personalize._PersonalizedInsight(**i) for i in insights]
        )

    class _Client:
        def __init__(self, **kwargs):
            self.responses = self

        def parse(self, **kwargs):
            return _Resp()

    monkeypatch.setattr(personalize, "OpenAI", _Client)


def test_知らないsource_idと空文字は捨てる(monkeypatch):
    _stub_llm(monkeypatch, [
        {"source_id": "aaa", "text": MARKER},
        {"source_id": "知らないID", "text": "混入"},
        {"source_id": "bbb", "text": "   "},
    ])

    result = personalize_insights([_item("aaa"), _item("bbb")], PROFILE)

    assert result == {"aaa": MARKER}


# --- 表示 ---


def test_パーソナライズ文があれば次にできることとして出す():
    bubbles = lm.build_flex_messages(
        [_item()], date_label="D", insight_overrides={"aaa": MARKER}
    )[0]["contents"]["contents"]
    body = json.dumps(bubbles[1], ensure_ascii=False)

    assert "次にできること" in body
    assert MARKER in body
    assert "汎用のポイント" not in body


def test_パーソナライズ文が無ければ汎用のポイントを出す():
    body = json.dumps(
        lm.build_flex_messages([_item()], date_label="D")[0]["contents"]["contents"][1],
        ensure_ascii=False,
    )

    assert "患者さんへのポイント" in body
    assert "汎用のポイント" in body


# --- 公開データとの境界（最重要） ---


def test_パーソナライズ文は公開データに一切書かれない(tmp_path: Path, monkeypatch):
    db_path = str(tmp_path / "curator.db")
    data_dir = tmp_path / "data"

    init_db(db_path)
    save_curated_article(
        db_path=db_path,
        digest_date="2026-08-24",
        source="pubmed",
        source_id="aaa",
        original_title="Title",
        title_ja="タイトル",
        summary_ja="要約",
        category="研究論文",
        relevance_score=0.8,
        url="https://example.com",
        published_date=None,
        curation_reasoning="",
        drugs_json="[]",
        patient_insight="汎用のポイント",
    )
    export_static_json(db_path, str(data_dir))

    monkeypatch.setattr(runner, "personalize_insights", lambda *a, **k: {"aaa": MARKER})
    monkeypatch.setattr(policy, "should_send_weekly", lambda today=None: True)
    monkeypatch.setattr(runner, "generate_greeting", lambda *a, **k: "おはようございます。")
    captured: list[list[dict]] = []
    monkeypatch.setattr(
        runner, "_push_flex",
        lambda config, messages, dry_run, label: (captured.append(messages), True)[1],
    )

    config = CuratorConfig(
        openai_api_key="dummy",
        db_path=db_path,
        data_dir=str(data_dir),
        patient_profile=PROFILE,
        line_channel_access_token="token",
        line_user_id="user",
        frontend_url="https://example.com",
    )
    item = _item()

    runner._deliver(config, [item], "2026年08月24日", False, False)

    # LINEには届いている
    assert MARKER in json.dumps(captured, ensure_ascii=False)

    # 公開データにもDBにも書かれていない
    for path in data_dir.rglob("*.json"):
        assert MARKER not in path.read_text(encoding="utf-8"), f"漏洩: {path}"
        assert "8歳" not in path.read_text(encoding="utf-8"), f"漏洩: {path}"
    assert MARKER not in Path(db_path).read_bytes().decode("utf-8", errors="ignore")

    # 元のオブジェクトも書き換わっていない
    assert item.patient_insight == "汎用のポイント"


def test_プロフィール未設定ならLLMを呼ばない(monkeypatch):
    called = []
    monkeypatch.setattr(
        runner, "personalize_insights", lambda *a, **k: called.append(1) or {}
    )
    config = CuratorConfig(openai_api_key="dummy", patient_profile="")

    assert runner._personalize(config, [_item()]) == {}
    assert called == []
