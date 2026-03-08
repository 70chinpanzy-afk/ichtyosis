# infra_api.py
import json
import requests

class ApiError(Exception):
    pass

def api_healthcheck(api_base: str) -> bool:
    try:
        r = requests.get(f"{api_base}/docs", timeout=3)
        return r.status_code == 200
    except Exception:
        return False

def call_sales_flow_api(api_base: str, payload: dict):
    """
    成功: (data, None)
    失敗: (None, error_message)
    """
    try:
        r = requests.post(f"{api_base}/api/sales-flow", json=payload, timeout=120)
    except requests.exceptions.ConnectionError:
        return None, "❌ APIに接続できません。FastAPI（uvicorn）が起動しているか確認してください。"
    except requests.exceptions.Timeout:
        return None, "❌ APIがタイムアウトしました。"
    except Exception as e:
        return None, f"❌ リクエストエラー: {e!r}"

    if r.status_code != 200:
        return None, f"APIエラー: {r.status_code}\n{r.text[:500] if r.text else ''}"

    try:
        data = r.json()
    except (json.JSONDecodeError, ValueError) as e:
        return None, f"❌ レスポンスのJSON解析に失敗しました: {e!r}"

    return data, None
