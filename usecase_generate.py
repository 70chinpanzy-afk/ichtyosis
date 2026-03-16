# usecase_generate.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

from infra_api import call_sales_flow_api
from history_repo import save_history


@dataclass
class GenerateResult:
    ok: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    history_id: Optional[int] = None


def execute_sales_flow(
    *,
    api_base: str,
    db_path: Optional[str],
    customer_name: str,
    customer_company: str,
    meeting_date: str,
    memo: str,
    mode: str,
    tone: str,
) -> GenerateResult:
    history_enabled = bool((db_path or "").strip())

    # 1) payload構築（メモ空でも再現用に保存する）
    payload = {
        "customer_name": customer_name,
        "customer_company": customer_company,
        "company": customer_company,
        "meeting_date": meeting_date,
        "memo": memo or "",
        "mode": mode,
        "tone": tone,
    }

    # 2) 入力バリデーション失敗も履歴に残す（「空で送ってしまった」を再現可能に）
    if not (memo or "").strip():
        err_msg = "商談メモが空です。貼り付けてください。"
        wrapped = {
            "meta": {"status": "error", "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            "payload": payload,
            "data": None,
            "error": err_msg,
        }
        if history_enabled:
            try:
                history_id = save_history(
                    db_path,
                    customer_name=customer_name,
                    customer_company=customer_company,
                    meeting_date=meeting_date,
                    mode=mode,
                    tone=tone,
                    memo=memo or "",
                    response_obj=wrapped,
                )
            except Exception:
                history_id = None
        else:
            history_id = None
        return GenerateResult(ok=False, data=wrapped, error=err_msg, history_id=history_id)

    # 3) API呼び出し
    data, err = call_sales_flow_api(api_base, payload)
    
    # 4) 共通ラッパー形式で履歴保存（成功・失敗どちらでも保存）
    wrapped = {
        "meta": {
            "status": "ok" if not err else "error",
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "payload": payload,
        "data": data if not err else None,
        "error": err if err else None,
    }
    
    history_id = None
    if history_enabled:
        try:
            history_id = save_history(
                db_path,
                customer_name=customer_name,
                customer_company=customer_company,
                meeting_date=meeting_date,
                mode=mode,
                tone=tone,
                memo=memo,
                response_obj=wrapped,
            )
        except Exception as e:
            # 保存失敗は警告として扱う（API成功時のみ）
            if not err:
                return GenerateResult(ok=True, data=wrapped, error=f"履歴保存に失敗: {e!r}", history_id=None)
            # API失敗＋保存失敗の場合は、API失敗を優先
            return GenerateResult(ok=False, data=wrapped, error=err, history_id=None)
    
    if err:
        # API失敗だが履歴は保存できた
        return GenerateResult(ok=False, data=wrapped, error=err, history_id=history_id)
    
    return GenerateResult(ok=True, data=wrapped, error=None, history_id=history_id)
