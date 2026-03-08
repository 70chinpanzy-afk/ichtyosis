# presenters.py
def format_boss_summary(customer_name: str, meeting_date: str, payload: dict) -> str:
    core = (payload or {}).get("core", {}) or {}
    summary_200 = (core.get("summary_200") or "").strip()
    key_points = core.get("key_points") or []
    decisions = core.get("decisions") or []
    missing_info = core.get("missing_info") or []
    action_items = core.get("action_items") or []
    next_steps = core.get("next_steps") or []

    def bullets(items, prefix="・", limit=5):
        items = [str(x).strip() for x in items if str(x).strip()]
        items = items[:limit]
        if not items:
            return "（なし）"
        return "\n".join([f"{prefix}{x}" for x in items])

    next_actions = list(action_items) + list(next_steps)
    title = f"【商談要約】{customer_name}／現金管理・精査業務（仮）"
    lines = [
        title,
        "",
        f"・日時：{meeting_date}",
        f"・先方：{customer_name}",
        "",
        "【概要】",
        summary_200 or "（概要が空です。入力メモを増やすか、要約生成の指示を見直してください）",
        "",
        "【主な論点・課題】",
        bullets(key_points, limit=5),
        "",
        "【決定事項】",
        bullets(decisions, limit=5),
        "",
        "【未決・確認事項】",
        bullets(missing_info, limit=5),
        "",
        "【次アクション】",
        bullets(next_actions, limit=7),
        "",
        "【補足】",
        "・次回は概算費用レンジと導入スケジュール案を提示予定（仮）",
    ]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)

def build_template_lite(customer_name: str, customer_company: str, meeting_date_str: str) -> str:
    return f"""・先方：{customer_company} {customer_name}
・目的：（例：現金管理・精査業務の効率化の情報交換／初回）
・日付：{meeting_date_str}

【現状（事実）】
・
・

【困りごと／課題（先方の発言）】
・
・

【先方の関心・質問（そのまま）】
・
・

【当社回答（言ったこと／次回回答予定）】
・
・

【決定事項（確定したこと）】
・

【次回に向けて】
・当社：
・先方：
"""

def format_summary_card(wrapped: dict) -> dict:
    """
    送信前チェック用の要約カード情報を返す。
    入力: wrapped 形式（{"meta": {...}, "payload": {...}, "data": {...}, "error": ...}）
    戻り値: {"title": str, "subtitle": str, "next_actions": list, "open_questions": list}
    """
    meta = (wrapped or {}).get("meta", {})
    status = meta.get("status", "ok")
    payload = (wrapped or {}).get("payload", {})
    data = (wrapped or {}).get("data", {}) or {}
    
    # 失敗時は薄く表示
    if status == "error":
        return {
            "title": "⚠️ エラーが発生しました",
            "subtitle": wrapped.get("error", "不明なエラー"),
            "next_actions": [],
            "open_questions": [],
        }
    
    # 成功時: data から core を取得
    core = data.get("core", {}) or {}
    action_items = core.get("action_items", []) or []
    next_steps = core.get("next_steps", []) or []
    missing_info = core.get("missing_info", []) or []
    
    # 次アクション上位3（action_items + next_steps を統合）
    next_actions = list(action_items) + list(next_steps)
    next_actions = [str(x).strip() for x in next_actions if str(x).strip()][:3]
    
    # 未確認事項上位3
    open_questions = [str(x).strip() for x in missing_info if str(x).strip()][:3]
    
    # payload から顧客情報を取得
    customer_name = payload.get("customer_name", "")
    customer_company = payload.get("customer_company", "")
    meeting_date = payload.get("meeting_date", "")
    
    return {
        "title": f"📋 {customer_company or ''} {customer_name or ''}".strip() or "📋 送信前チェック",
        "subtitle": f"日付: {meeting_date}" if meeting_date else "",
        "next_actions": next_actions,
        "open_questions": open_questions,
    }


def build_template_bank(customer_name: str, customer_company: str, meeting_date_str: str) -> str:
    return f"""・先方：{customer_company}（部店：現金センター）／ご担当：{customer_name}
・目的：（例：現金管理・精査業務の効率化／内部統制・監査対応の改善）
・日付：{meeting_date_str}

【現状（事実）】
・精査：手作業中心／紙＋Excel
・繁忙期：残業増／ダブルチェック必須
・監査：証跡整理に時間

【論点（先方の関心・質問）】
・導入コスト感（概算レンジ）
・導入期間（いつ稼働できるか）
・運用変更の範囲（現場負担）
・監査／内部統制メリット（証跡・権限・ログ）

【当社回答（言ったこと／次回提示）】
・次回：費用レンジ＋導入スケジュール案を提示
・運用変更：最小化の方針（要ヒアリング）
・監査：ログ・証跡の自動保存／検索性向上

【稟議・決裁（分かれば）】
・決裁者：
・関係部署：
・稟議の論点（価格/リスク/監査）：

【確認したい情報（次回まで）】
・対象拠点数：
・現金量：
・導入希望時期：
・現行フロー（回収→精査→保管→記録）：
・監査で求められる帳票／証跡：

【決定事項】
・今回：導入判断は行わない

【次回に向けて】
・当社：概算費用レンジ／導入スケジュール案／監査・内部統制メリット整理
・先方：拠点数／現金量／希望時期／決裁プロセスの整理
"""
