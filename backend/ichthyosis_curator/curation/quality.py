"""patient_insight の品質チェック

患者プロフィールを使わない方針なので、行動につながる文を作る役目は
汎用の patient_insight ひとつが担う。ところがLLMは放っておくと
「主治医に相談しましょう」「保湿が大切です」といった、どの記事にも
書ける一般論に収束する（実データでは7件中7件がそうだった）。

プロンプトで禁止しただけでは守られたか分からないので、生成結果を
機械的に検査してCIログに出す。判定は完璧である必要はなく、
劣化に気づける程度の粗い指標でよい。
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# どの記事にも書ける締め文句。語幹で持ち、活用形の違いを拾う。
# 具体性の判定と AND を取るので、多少広めに取っても誤検知は増えにくい。
GENERIC_PHRASES = (
    "相談",
    "期待",
    "注視",
    "試してみ",
    "取り入れ",
    "工夫してみ",
    "参考にし",
    "参考程度",
    "大切",
    "見守",
    "情報を追",
    "見直す良い機会",
    "有益です",
    "役立つかもしれません",
)

# 具体性ありと判定しない、ありふれたカタカナ語
GENERIC_KATAKANA = {
    "スキンケア", "ケア", "アドバイス", "ポイント", "バリア", "コメント",
    "ルーチン", "ルーティン", "クリーム", "タイプ", "シリーズ", "サイト",
    "ステップ", "ローション",
}

_DIGIT_RE = re.compile(r"[0-9０-９]")
_KATAKANA_RE = re.compile(r"[ァ-ヴー]{3,}")
_LATIN_RE = re.compile(r"[A-Za-z]{2,}")


def has_specifics(text: str) -> bool:
    """記事固有の手がかり（数字・薬品名・成分名・略語など）を含むか"""
    if _DIGIT_RE.search(text):
        return True
    if _LATIN_RE.search(text):
        return True
    for word in _KATAKANA_RE.findall(text):
        if word not in GENERIC_KATAKANA:
            return True
    return False


def is_boilerplate(insight: str) -> bool:
    """一般論だけで、記事固有の手がかりが無い文か"""
    if not insight or not insight.strip():
        return True
    if not any(phrase in insight for phrase in GENERIC_PHRASES):
        return False
    return not has_specifics(insight)


def report_boilerplate(articles) -> int:
    """一般論に終始した patient_insight を数え、CIログに残す。

    Returns: 一般論と判定された件数
    """
    flagged = [a for a in articles if is_boilerplate(getattr(a, "patient_insight", ""))]
    if not flagged:
        return 0

    logger.warning(
        f"patient_insightが一般論のみの記事: {len(flagged)}/{len(articles)}件"
        "（プロンプトの見直しを検討してください）"
    )
    for article in flagged[:3]:
        title = getattr(article, "title_ja", "") or getattr(article, "original_title", "")
        logger.warning(f"  - {title[:40]}: {getattr(article, 'patient_insight', '')[:60]}")
    return len(flagged)
