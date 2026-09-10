"""patient_insight の品質チェックのテスト

患者プロフィールを使わない運用では、行動につながる文は汎用の
patient_insight ひとつだけになる。LLMはこれを一般論に収束させがちなので、
劣化に気づけるようにしておく。
"""

import logging

import pytest

from ichthyosis_curator.curation.quality import (
    has_specifics,
    is_boilerplate,
    report_boilerplate,
)


class _Article:
    def __init__(self, patient_insight: str, title_ja: str = "タイトル"):
        self.patient_insight = patient_insight
        self.title_ja = title_ja


# 実際に配信されていた文（2026-08-21 のダイジェストより）
REAL_BOILERPLATE = "この研究が示すのは新しい可能性です。引き続き、新しい治療法が登場するまで、現在のケアを大切にしつつ情報を追ってみてください。"
REAL_GENERIC = "動画で説明されているように、日々のスキンケアで症状を管理することが大切です。主治医と相談しながら、自分に合った方法を見つけてください。"


@pytest.mark.parametrize("text", [
    REAL_BOILERPLATE,
    REAL_GENERIC,
    "主治医に相談しながらスキンケアを工夫してみてください。",
    "試してみる価値があります。今後の進展に期待しましょう。",
])
def test_一般論だけの文を検出する(text: str):
    assert is_boilerplate(text)


@pytest.mark.parametrize("text", [
    "成人が対象の治験です。同じ仕組みの薬が子どもにも広がる見込みがあるか、次の診察で聞いてみてください。",
    "アンモニウム乳酸を含む市販の保湿剤の報告です。今の保湿剤の成分表示を確認してみてください。",
    "TMB-001という開発中の外用薬についての報告です。",
    "デュピクセントの適応が広がるかもしれません。主治医に相談してみてください。",
])
def test_記事固有の手がかりがあれば一般論とみなさない(text: str):
    assert not is_boilerplate(text)


def test_空文字は一般論として扱う():
    assert is_boilerplate("")
    assert is_boilerplate("   ")


def test_具体性の判定():
    assert has_specifics("8歳から使えます")          # 数字
    assert has_specifics("JAK阻害薬の話です")        # 英字
    assert has_specifics("デュピクセントの報告")      # カタカナの固有名
    assert not has_specifics("スキンケアのポイントです")  # ありふれたカタカナのみ
    assert not has_specifics("保湿が大切です")


def test_一般論の件数をログに出す(caplog):
    articles = [_Article(REAL_BOILERPLATE), _Article("TMB-001の試験結果です。")]

    with caplog.at_level(logging.WARNING):
        count = report_boilerplate(articles)

    assert count == 1
    assert "1/2件" in caplog.text


def test_問題なければ何もログに出さない(caplog):
    with caplog.at_level(logging.WARNING):
        assert report_boilerplate([_Article("TMB-001の試験結果です。")]) == 0

    assert caplog.text == ""
