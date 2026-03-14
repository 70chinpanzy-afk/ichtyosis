# app/services/sales_flow_service.py
from app.schemas import (
    SalesFlowRequest, SalesFlowResponse,
    CorePack, BankAddon, EnterpriseAddon
)
from app.services.openai_service import parse_llm
from app.prompts import (
    CORE_SYSTEM, BANK_ADDON_SYSTEM, ENTERPRISE_ADDON_SYSTEM, tone_instruction
)

# ── 固定5項目（LLMに生成させず、コードで確定する） ──
_FIXED_ITEMS = [
    "導入希望時期",
    "想定している予算感",
    "対象となる拠点数・現金量",
    "現在の現金管理・回収の運用方法",
    "稟議・決裁のプロセスと関係者",
]

# 固定項目に該当するLLM出力を判別するキーワード
_FIXED_KEYWORDS = [
    ["導入", "稼働", "希望時期", "時期"],
    ["予算", "コスト", "費用", "レンジ", "価格"],
    ["拠点", "現金量"],
    ["現金管理", "回収", "運用", "現行フロー", "精査"],
    ["稟議", "決裁", "承認"],
]


def _build_missing_info(llm_items: list[str]) -> list[str]:
    """固定5項目＋LLM独自項目を結合する。
    LLM出力のうち固定項目と重複するものは除外し、
    固定項目はコード側の正確なテキストを使う。"""
    # LLM出力から固定項目に該当するものを除外
    extras = []
    for item in llm_items:
        is_fixed = False
        for kws in _FIXED_KEYWORDS:
            if any(kw in item for kw in kws):
                is_fixed = True
                break
        if not is_fixed:
            extras.append(item)

    return list(_FIXED_ITEMS) + extras


def run_sales_flow(req: SalesFlowRequest) -> SalesFlowResponse:
    # Core
    core = parse_llm(
        CorePack,
        system_prompt=CORE_SYSTEM + "\n" + tone_instruction(req.tone),
        user_prompt=(
            f"商談メモ/議事録:\n{req.memo}\n\n"
            f"【既知情報（missing_infoに含めないこと）】\n"
            f"- 会社名: {req.company or '未入力'}\n"
            f"- 担当者名: {req.customer_name or '未入力'}\n"
            f"- 製品: {req.product or '未入力'}\n\n"
            "出力はCorePackに厳密準拠。推測で断定しない。"
        ),
    )

    # 固定5項目はコードで確定し、LLM独自の追加項目だけ残す
    core.missing_info = _build_missing_info(core.missing_info)

    addons = {}

    # まず空で作る
    meta = {
        "mode": req.mode,
        "tone": req.tone,
        "questions_to_confirm": [],
        "assumptions": [],
    }

    # 後から埋める
    questions = []
    if not core.decisions:
        questions.append("本件で顧客側・当社側で確定した事項（例：次回面談日、提供資料、検討範囲）はありますか？")
    if not core.action_items:
        questions.append("次回までに当社が用意すべき資料（費用概算、運用影響、監査観点など）は何を求められていますか？")
    meta["questions_to_confirm"] = questions

    if req.mode == "bank":
        bank = parse_llm(
            BankAddon,
            system_prompt=BANK_ADDON_SYSTEM + "\n" + tone_instruction(req.tone),
        user_prompt=f"メモ:\n{req.memo}\n\nCore:\n{core.model_dump_json(ensure_ascii=False)}",
        )
        addons["bank"] = bank.model_dump()


    elif req.mode == "enterprise":
        ent = parse_llm(
            EnterpriseAddon,
            system_prompt=ENTERPRISE_ADDON_SYSTEM + "\n" + tone_instruction(req.tone),
            user_prompt=f"メモ:\n{req.memo}\n\nCore(JSON):\n{core.model_dump_json(ensure_ascii=False)}",
        )
        addons["enterprise"] = ent.model_dump()

    return SalesFlowResponse(core=core, addons=addons, meta=meta)
