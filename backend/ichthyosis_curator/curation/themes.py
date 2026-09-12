"""困りごとテーマの定義

蓄積済み269件を生活場面ごとに数えたところ、収集が研究の世界に偏っていて、
読者が実際に困る場面がほとんど入っていないことが分かった:

    冬・乾燥 55 / 保湿剤 40 / 新薬・治験 32 / かゆみ 21
    入浴 6 / 感染 6 / 目・耳・爪 5 / 医療費・制度 2 / 夏・汗 1 / 学校・保育園 0

魚鱗癬紅皮症は発汗障害が大きな論点で、夏の体温調節は生活に直結する。
それが1件、学校への説明は0件では、いくらプロンプトを直しても
「保湿が大切」以上の内容は出てこない。素材が無いのだから当然だった。

そこで「記事を集めてからアクションを考える」のをやめ、先に困りごとを
定義し、それを軸に検索する。このモジュールが検索クエリとテーマ判定の
両方の元になる。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ichthyosis_curator.timeutil import today_jst


@dataclass(frozen=True)
class Theme:
    """患者・家族が実際に困る場面のひとつ"""

    key: str
    label: str
    # 記事がこのテーマに当たるかの判定語（日本語・英語。小文字で比較する）
    #
    # 部分一致なので、短い語は別テーマの語に飲み込まれる。
    # 実際に「垢」が「耳垢」に、「寝」が「寝具」に、「服」が「服用」に、
    # 「遺伝」が遺伝子研究の記事すべてに誤爆した。2文字以下の語は避ける。
    keywords: tuple[str, ...]
    # 患者コミュニティ検索用（note / Reddit / YouTube）
    queries_ja: tuple[str, ...] = field(default_factory=tuple)
    queries_en: tuple[str, ...] = field(default_factory=tuple)
    # 医学文献が存在するテーマのみ
    pubmed: tuple[str, ...] = field(default_factory=tuple)


THEMES: tuple[Theme, ...] = (
    Theme(
        key="heat",
        label="夏の汗・体温調節",
        keywords=("発汗", "汗", "熱中症", "体温", "暑", "夏",
                  "sweat", "hypohidrosis", "heat intolerance", "overheat"),
        queries_ja=("魚鱗癬 汗 かけない", "魚鱗癬 夏 体温", "魚鱗癬 熱中症"),
        queries_en=("ichthyosis sweating heat", "ichthyosis overheating summer",
                    "ichthyosis heat intolerance cooling"),
        pubmed=('"ichthyosis" AND ("hypohidrosis" OR "heat intolerance" OR "thermoregulation" OR "sweating")',),
    ),
    Theme(
        key="school",
        label="学校・保育園",
        keywords=("学校", "保育園", "幼稚園", "先生", "クラス", "体育", "プール", "水泳",
                  "school", "teacher", "classmate", "daycare", "swimming", "gym class"),
        queries_ja=("魚鱗癬 保育園", "魚鱗癬 学校 説明", "魚鱗癬 プール 体育"),
        queries_en=("ichthyosis school teacher", "ichthyosis swimming pool",
                    "ichthyosis kids school explain"),
    ),
    Theme(
        key="bathing",
        label="入浴・角質ケア",
        keywords=("入浴", "お風呂", "シャワー", "角質", "皮むけ", "あかすり", "重曹", "入浴剤",
                  "bath", "soak", "descal", "exfoliat", "keratolytic"),
        queries_ja=("魚鱗癬 入浴 方法", "魚鱗癬 皮むけ お風呂", "魚鱗癬 入浴剤"),
        queries_en=("ichthyosis bath routine", "ichthyosis descaling bath",
                    "ichthyosis exfoliation soak"),
        pubmed=('"ichthyosis" AND ("bathing" OR "keratolytic" OR "urea" OR "salicylic acid")',),
    ),
    Theme(
        key="eye",
        label="目（眼瞼外反・ドライアイ）",
        keywords=("眼瞼", "外反", "まぶた", "ドライアイ", "目やに", "角膜", "視力",
                  "ectropion", "eyelid", "dry eye", "cornea", "ophthalm"),
        queries_ja=("魚鱗癬 眼瞼外反", "魚鱗癬 目 乾燥"),
        queries_en=("ichthyosis ectropion eye care", "ichthyosis dry eyes eyelid"),
        pubmed=('"ichthyosis" AND ("ectropion" OR "ophthalmic" OR "eyelid" OR "cornea")',),
    ),
    Theme(
        key="ear",
        label="耳（耳垢・聞こえ）",
        keywords=("耳垢", "耳あか", "難聴", "聞こえ", "外耳",
                  "cerumen", "ear wax", "hearing", "otolog"),
        queries_ja=("魚鱗癬 耳垢", "魚鱗癬 難聴"),
        queries_en=("ichthyosis ear wax buildup", "ichthyosis hearing loss ear"),
        pubmed=('"ichthyosis" AND ("cerumen" OR "hearing" OR "ear canal" OR "otologic")',),
    ),
    Theme(
        key="infection",
        label="感染・とびひ",
        keywords=("感染", "とびひ", "黄色ブドウ球菌", "膿", "抗菌", "抗生",
                  "infection", "staph", "impetigo", "sepsis", "antibiotic"),
        queries_ja=("魚鱗癬 感染 とびひ", "魚鱗癬 皮膚 においケア"),
        queries_en=("ichthyosis skin infection", "ichthyosis staph odor"),
        pubmed=('"ichthyosis" AND ("infection" OR "Staphylococcus" OR "colonization" OR "sepsis")',),
    ),
    Theme(
        key="itch",
        label="かゆみ・睡眠",
        keywords=("かゆみ", "痒", "掻き", "掻破", "睡眠", "就寝", "寝つ", "寝れ",
                  "itch", "pruritus", "scratch", "sleep"),
        queries_ja=("魚鱗癬 かゆみ 対策", "魚鱗癬 夜 眠れない"),
        queries_en=("ichthyosis itching relief", "ichthyosis sleep scratching night"),
        pubmed=('"ichthyosis" AND ("pruritus" OR "itch" OR "sleep")',),
    ),
    Theme(
        key="moisturizer",
        label="保湿剤の選び方と量",
        keywords=("保湿", "ワセリン", "尿素", "セラミド", "ヒルドイド", "乳酸", "軟膏", "処方量",
                  "moistur", "emollient", "vaseline", "petrolatum", "ceramide", "urea"),
        queries_ja=("魚鱗癬 保湿剤 おすすめ", "魚鱗癬 保湿 量 処方"),
        queries_en=("ichthyosis best moisturizer routine", "ichthyosis emollient amount"),
    ),
    Theme(
        key="clothing",
        label="衣類・寝具",
        keywords=("衣類", "衣服", "洋服", "寝具", "シーツ", "洗濯", "布団", "肌着",
                  "clothing", "fabric", "bedding", "sheets", "laundry"),
        queries_ja=("魚鱗癬 衣類 選び方", "魚鱗癬 寝具 シーツ 皮膚"),
        queries_en=("ichthyosis clothing fabric", "ichthyosis bedding sheets skin flakes"),
    ),
    Theme(
        key="newborn",
        label="新生児・乳児期",
        keywords=("新生児", "乳児", "赤ちゃん", "コロジオン", "保育器", "授乳",
                  "newborn", "infant", "collodion", "neonat", "nicu"),
        queries_ja=("魚鱗癬 新生児 ケア", "コロジオンベビー 育児"),
        queries_en=("collodion baby care", "ichthyosis newborn nicu parents"),
        pubmed=('"collodion baby" OR ("ichthyosis" AND ("neonate" OR "newborn"))',),
    ),
    Theme(
        key="growth",
        label="成長・栄養",
        keywords=("成長", "身長", "体重", "栄養", "カロリー", "食欲",
                  "growth", "nutrition", "weight", "calorie", "failure to thrive"),
        queries_ja=("魚鱗癬 成長 体重", "魚鱗癬 栄養"),
        queries_en=("ichthyosis growth nutrition children",),
        pubmed=('"ichthyosis" AND ("growth" OR "nutrition" OR "failure to thrive" OR "caloric")',),
    ),
    Theme(
        key="mental",
        label="見た目・気持ち・まわりの目",
        keywords=("見た目", "視線", "いじめ", "からかい", "自己肯定", "気持ち", "不安", "きょうだい",
                  "stigma", "bullying", "appearance", "psychosocial", "quality of life", "stare"),
        queries_ja=("魚鱗癬 見た目 視線", "魚鱗癬 いじめ", "魚鱗癬 気持ち 家族"),
        queries_en=("ichthyosis bullying stares", "ichthyosis mental health confidence"),
        pubmed=('"ichthyosis" AND ("quality of life" OR "psychosocial" OR "stigma" OR "depression")',),
    ),
    Theme(
        key="support",
        label="医療費・制度・手続き",
        keywords=("助成", "医療費", "申請", "難病", "小児慢性", "受給者証", "補助", "制度",
                  "手帳", "subsidy", "insurance", "reimbursement"),
        queries_ja=("魚鱗癬 医療費 助成", "先天性魚鱗癬様紅皮症 指定難病 申請",
                    "小児慢性特定疾病 皮膚 申請"),
    ),
    Theme(
        key="travel",
        label="外出・旅行・災害時",
        keywords=("旅行", "修学旅行", "外出", "災害", "避難", "備蓄", "温泉",
                  "travel", "disaster", "evacuation", "emergency"),
        queries_ja=("魚鱗癬 旅行 保湿", "魚鱗癬 災害 備え", "難病 災害 備え 薬"),
        queries_en=("ichthyosis travel packing skincare",),
    ),
    Theme(
        key="adult",
        label="おとな・仕事・妊娠",
        keywords=("就職", "仕事", "職場", "妊娠", "出産", "遺伝カウンセリング", "遺伝相談", "結婚",
                  "employment", "workplace", "pregnancy", "genetic counseling"),
        queries_ja=("魚鱗癬 仕事 職場", "魚鱗癬 遺伝 妊娠"),
        queries_en=("ichthyosis adult work life", "ichthyosis genetic counseling pregnancy"),
        pubmed=('"ichthyosis" AND ("genetic counseling" OR "pregnancy" OR "adult")',),
    ),
)

THEMES_BY_KEY = {theme.key: theme for theme in THEMES}


def detect_themes(text: str) -> list[str]:
    """本文からテーマを判定する（LLMを使わないので追加コストなし）"""
    if not text:
        return []
    lowered = text.lower()
    return [
        theme.key
        for theme in THEMES
        if any(kw.lower() in lowered for kw in theme.keywords)
    ]


def rotating_themes(count: int, today: date | None = None) -> list[Theme]:
    """日替わりでテーマを選ぶ。

    全テーマを毎日検索すると、YouTube APIのクォータやRedditのレート制限に
    引っかかる。日付で位置をずらして回せば、数日で全テーマを一巡できる。
    """
    if count >= len(THEMES):
        return list(THEMES)
    today = today or today_jst()
    start = (today.toordinal() * count) % len(THEMES)
    return [THEMES[(start + i) % len(THEMES)] for i in range(count)]


def all_queries_ja() -> list[str]:
    return [q for theme in THEMES for q in theme.queries_ja]


def all_queries_en() -> list[str]:
    return [q for theme in THEMES for q in theme.queries_en]


def all_pubmed_queries() -> list[str]:
    return [q for theme in THEMES for q in theme.pubmed]
