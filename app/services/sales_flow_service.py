# app/services/sales_flow_service.py
from app.schemas import (
    SalesFlowRequest, SalesFlowResponse,
    CorePack, BankAddon, EnterpriseAddon
)
from app.services.openai_service import parse_llm
from app.prompts import (
    CORE_SYSTEM, BANK_ADDON_SYSTEM, ENTERPRISE_ADDON_SYSTEM, tone_instruction
)

def run_sales_flow(req: SalesFlowRequest) -> SalesFlowResponse:
    # Core
    core = parse_llm(
        CorePack,
        system_prompt=CORE_SYSTEM + "\n" + tone_instruction(req.tone),
        user_prompt=(
            f"商談メモ/議事録:\n{req.memo}\n\n"
            f"補足: company={req.company}, customer_name={req.customer_name}, product={req.product}\n"
            "出力はCorePackに厳密準拠。推測で断定しない。"
        ),
    )

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
