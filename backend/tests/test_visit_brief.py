"""受診前ブリーフ（次の診察で聞くとよいこと）のテスト

出力は「質問」に限定する。指示文や治療提案が混ざると、医療判断を
こちらが下すことになってしまう。
"""

import json
from pathlib import Path

import pytest

from ichthyosis_curator.curation import visit_brief
from ichthyosis_curator.curation.visit_brief import (
    BriefEntry,
    build_visit_brief,
    is_question,
)
from ichthyosis_curator.delivery import line_messaging as lm
from ichthyosis_curator.schemas import DeliveryItem


def _item(source_id: str = "aaa", score: float = 0.8) -> DeliveryItem:
    return DeliveryItem(
        source="pubmed",
        source_id=source_id,
        title_ja="TMB-001の試験結果",
        summary_ja="要約",
        category="新薬・治療法",
        relevance_score=score,
        url="https://example.com",
    )


def _stub_llm(monkeypatch, questions: list[dict]):
    class _Resp:
        output_parsed = visit_brief._BriefResult(
            questions=[visit_brief._BriefQuestion(**q) for q in questions]
        )

    class _Client:
        def __init__(self, **kwargs):
            self.responses = self

        def parse(self, **kwargs):
            return _Resp()

    monkeypatch.setattr(visit_brief, "OpenAI", _Client)


# --- 疑問形の判定 ---


@pytest.mark.parametrize("text", [
    "この薬は子どもでも使える見込みはありますか？",
    "今の処方に加える意味はありますか。",
    "うちの子は対象になるでしょうか？",
])
def test_疑問形を通す(text: str):
    assert is_question(text)


@pytest.mark.parametrize("text", [
    "成人向けの薬について確認しましょう。",
    "保湿剤を切り替えてください。",
    "",
])
def test_疑問形でないものは弾く(text: str):
    assert not is_question(text)


# --- 生成 ---


def test_質問と根拠記事を組にして返す(monkeypatch, tmp_path: Path):
    _stub_llm(monkeypatch, [
        {"question": "TMB-001は子どもでも使えますか？", "source_id": "aaa"},
    ])

    entries = build_visit_brief(str(tmp_path), extra_items=[_item()])

    assert len(entries) == 1
    assert entries[0].question == "TMB-001は子どもでも使えますか？"
    assert entries[0].article is not None
    assert entries[0].article.title_ja == "TMB-001の試験結果"


def test_疑問形でない項目は落とす(monkeypatch, tmp_path: Path):
    _stub_llm(monkeypatch, [
        {"question": "保湿剤を切り替えてください。", "source_id": "aaa"},
        {"question": "TMB-001は子どもでも使えますか？", "source_id": "aaa"},
    ])

    entries = build_visit_brief(str(tmp_path), extra_items=[_item()])

    assert [e.question for e in entries] == ["TMB-001は子どもでも使えますか？"]


def test_重複した質問はまとめる(monkeypatch, tmp_path: Path):
    _stub_llm(monkeypatch, [
        {"question": "使えますか？", "source_id": "aaa"},
        {"question": "使えますか？", "source_id": "aaa"},
    ])

    assert len(build_visit_brief(str(tmp_path), extra_items=[_item()])) == 1


def test_上限を超えない(monkeypatch, tmp_path: Path):
    _stub_llm(monkeypatch, [
        {"question": f"質問{i}ですか？", "source_id": "aaa"} for i in range(10)
    ])

    entries = build_visit_brief(str(tmp_path), extra_items=[_item()])

    assert len(entries) == visit_brief.MAX_QUESTIONS


def test_根拠記事が見つからなくても質問は残す(monkeypatch, tmp_path: Path):
    _stub_llm(monkeypatch, [{"question": "使えますか？", "source_id": "存在しない"}])

    entries = build_visit_brief(str(tmp_path), extra_items=[_item()])

    assert entries[0].article is None


def test_記事が無ければLLMを呼ばない(monkeypatch, tmp_path: Path):
    def boom(*args, **kwargs):
        raise AssertionError("呼ばれてはいけない")

    monkeypatch.setattr(visit_brief, "OpenAI", boom)
    assert build_visit_brief(str(tmp_path), extra_items=[]) == []


def test_LLMが失敗しても配信は止めない(monkeypatch, tmp_path: Path):
    def boom(*args, **kwargs):
        raise RuntimeError("API down")

    monkeypatch.setattr(visit_brief, "OpenAI", boom)
    assert build_visit_brief(str(tmp_path), extra_items=[_item()]) == []


# --- 表示 ---


def test_ブリーフは週次まとめのヘッダー直後に入る():
    entries = [BriefEntry(question="使えますか？", article=_item())]

    bubbles = lm.build_flex_messages(
        [_item()], date_label="D", brief_entries=entries
    )[0]["contents"]["contents"]

    assert "次の診察で聞いてみるとよいこと" in json.dumps(bubbles[1], ensure_ascii=False)


def test_ブリーフが無ければバブルを足さない():
    bubbles = lm.build_flex_messages([_item()], date_label="D")[0]["contents"]["contents"]

    assert "次の診察で聞いてみるとよいこと" not in json.dumps(bubbles, ensure_ascii=False)


def test_質問は番号付きで根拠タイトルを添えて出す():
    entries = [
        BriefEntry(question="使えますか？", article=_item()),
        BriefEntry(question="対象になりますか？", article=None),
    ]

    body = json.dumps(lm.build_brief_bubble(entries), ensure_ascii=False)

    assert "1. 使えますか？" in body
    assert "2. 対象になりますか？" in body
    assert "TMB-001の試験結果" in body
    assert "答えは主治医の判断によります" in body
