"""
Sales Copilot UI（完成形）
商談メモを /api/sales-flow に送信し、メール/アジェンダ/上司向け要約を表示。
SQLite に履歴保存・履歴読み込みで入力・結果を完全復元。
"""

from datetime import date, datetime
import json

import streamlit as st

from presenters import (
    format_boss_summary,
    format_summary_card,
    build_template_lite,
    build_template_bank,
)
from history_repo import (
    init_history_db,
    list_history,
    load_history,
    list_history_by_customer,
)

from usecase_generate import execute_sales_flow
from infra_api import api_healthcheck

def normalize_wrapped(obj: dict) -> dict:
    """
    新形式(wrapped)ならそのまま返す。
    旧形式(APIレスポンス直)なら wrapped に変換して返す。
    """
    if not obj:
        return {}

    # 新形式判定
    if isinstance(obj, dict) and "meta" in obj and "data" in obj and "payload" in obj:
        return obj

    # 旧形式を wrapped に昇格
    return {
        "meta": {"status": "ok", "saved_at": None},
        "payload": {},
        "data": obj,
        "error": None,
    }


# =========================
# 設定
# =========================
API_BASE = "http://127.0.0.1:8000"
HISTORY_DB = "ui_history.db"


# =========================
# セッション初期化（1回だけ）
# =========================
def init_session_state():
    defaults = [
        ("running", False),
        ("memo_text", ""),
        ("last_response", None),
        ("last_history_id", None),
        ("last_run_at", None),
        ("last_edit_at", None),
        ("show_timeline", False),        
        ("customer_name", ""),
        ("customer_company", ""),
        ("meeting_date", date.today()),
        ("mode", "lite"),
        ("tone", "sales"),
    ]
    for key, val in defaults:
        if key not in st.session_state:
            st.session_state[key] = val
    # API接続状態は1回だけ評価して再利用（未定義・二重評価を防ぐ）
    if "api_ok" not in st.session_state:
        st.session_state["api_ok"] = api_healthcheck(API_BASE)

# =========================
# 画面構築
# =========================
st.set_page_config(page_title="Sales Copilot UI", layout="wide")
init_history_db(HISTORY_DB)
init_session_state()

api_ok = st.session_state["api_ok"]
st.title("Sales Copilot（日本語UI）")
st.caption("入力 → /api/sales-flow → 結果を3タブで表示")

if api_ok:
    st.success("✅ FastAPI 接続OK（/docs）")
else:
    st.error("❌ FastAPI に接続できません（/docs が開けない）")

# ---------- サイドバー（入力 + 履歴のみ。履歴UIはここに統一） ----------
with st.sidebar:
    st.header("入力")
    customer_name = st.text_input("顧客名（例：山田 太郎）", key="customer_name")
    customer_company = st.text_input("会社名（例：〇〇銀行）", key="customer_company")
    meeting_date = st.date_input("日付", key="meeting_date")
    mode = st.selectbox("モード", options=["lite", "bank"], key="mode")
    tone = st.selectbox("トーン", options=["sales", "exec"], key="tone")

    st.divider()
    if st.button("この顧客のタイムラインを見る", key="btn_timeline"):
        company = (st.session_state.get("customer_company") or "").strip()
        name = (st.session_state.get("customer_name") or "").strip()

        if not company or not name:
            st.warning("会社名と顧客名を入れてください")
        else:
            st.session_state["show_timeline"] = True
            st.rerun()

    # 閉じるボタン（任意だけど実用的）
    if st.session_state.get("show_timeline"):
        if st.button("タイムラインを閉じる", key="btn_timeline_close"):
            st.session_state["show_timeline"] = False
            st.rerun()

    if st.button("接続再判定"):
        st.session_state["api_ok"] = api_healthcheck(API_BASE)
        st.rerun()

    st.divider()
    st.subheader("履歴")

    # 履歴検索（会社名・担当者で絞り込み）
    q = st.text_input("履歴検索（会社名/担当者）", key="history_query", placeholder="例：〇〇銀行")
    rows_all = list_history(HISTORY_DB, limit=30)
    
    # 検索クエリでフィルタリング
    if q and q.strip():
        filtered = []
        for r in rows_all:
            # response_json がある場合とない場合の両方に対応
            if len(r) >= 8:
                rid, created_at, company, name, mdate, m, t, _ = r[:8]
            else:
                rid, created_at, company, name, mdate, m, t = r[:7]
            text = f"{company or ''} {name or ''}".lower()
            if q.lower() in text:
                filtered.append(r)
        rows = filtered
    else:
        rows = rows_all

    # 履歴ラベル生成（失敗履歴には⚠️を付ける）
    labels = []

    for row in rows:
        if len(row) >= 8:
            rid, created_at, company, name, mdate, m, t, response_json = row[:8]
    
            is_error = False
            try:
                if response_json:
                    loaded = json.loads(response_json)
                    wrapped = normalize_wrapped(loaded)
                    status = wrapped.get("meta", {}).get("status")
                    is_error = status == "error"
            except Exception:
                is_error = False

            prefix = "⚠️ " if is_error else "✅ "
            labels.append(
                f"{prefix}[{rid}] {created_at} | {company or ''} {name or ''} | {mdate} | {m}/{t}"
            )
        else:
            rid, created_at, company, name, mdate, m, t = row[:7]
            labels.append(
                f"✅ [{rid}] {created_at} | {company or ''} {name or ''} | {mdate} | {m}/{t}"
            )
    # 直近保存した履歴IDがあれば、それを selectbox のデフォルトにする
    default_index = 0
    if rows and st.session_state.get("last_history_id") is not None:
        for i, r in enumerate(rows):
            history_id = r[0] if r else None
            if history_id == st.session_state["last_history_id"]:
                default_index = i
                break

    selected_idx = (
        st.selectbox(
            "履歴を選択（読み込み）",
            options=list(range(len(labels))),
            format_func=lambda i: labels[i],
            index=default_index,
        )
        if labels
        else None
    )

    col_h1, col_h2 = st.columns([1, 1])
    with col_h1:
        load_btn = st.button("読み込み", key="btn_history_load", disabled=(selected_idx is None))
    with col_h2:
        clear_btn = st.button("履歴クリア（表示のみ）", key="btn_history_clear", disabled=(selected_idx is None))

    if clear_btn:
        st.session_state["last_response"] = None
        st.session_state["last_history_id"] = None
        st.rerun()

    if load_btn and selected_idx is not None:
        history_id = rows[selected_idx][0] if rows[selected_idx] else None
        if not history_id:
            st.error("履歴の読み込みに失敗しました")
            st.rerun()
        row = load_history(HISTORY_DB, history_id)

        if row:
            # DBの1件分の履歴から、UIの入力・メモ・結果をすべて復元
            st.session_state["memo_text"] = row.memo or ""
            st.session_state["customer_name"] = row.customer_name or ""
            st.session_state["customer_company"] = row.customer_company or ""

            try:
                st.session_state["meeting_date"] = datetime.strptime(row.meeting_date, "%Y-%m-%d").date()
            except Exception:
                st.session_state["meeting_date"] = date.today()

            st.session_state["mode"] = row.mode or "lite"
            st.session_state["tone"] = row.tone or "sales"

            try:
                loaded = json.loads(row.response_json) if row.response_json else None
                st.session_state["last_response"] = normalize_wrapped(loaded) if loaded else None
                st.session_state["last_history_id"] = history_id
            except Exception:
                st.session_state["last_response"] = None
                st.session_state["last_history_id"] = None

        # state を更新し終えてから rerun することで、ウィジェットに反映させる
        st.rerun()

    

# ---------- 本文：テンプレ・メモ・実行 ----------
# サイドバーの値はすべて session_state に入っているので、
# メイン側では session_state から読む設計に統一しておく。
customer_name = st.session_state["customer_name"]
customer_company = st.session_state["customer_company"]
meeting_date = st.session_state["meeting_date"]
mode = st.session_state["mode"]
tone = st.session_state["tone"]

meeting_date_str = str(meeting_date)
name_for_template = (customer_name or "").strip() or "（ご担当者名未入力）"
company_for_template = (customer_company or "").strip() or "（会社名未入力）"


def build_current_template() -> str:
    if mode == "bank":
        return build_template_bank(name_for_template, company_for_template, meeting_date_str)
    return build_template_lite(name_for_template, company_for_template, meeting_date_str)


colT1, colT2, colT3 = st.columns([1, 1, 3])
with colT1:
    if st.button("テンプレを入れる", key="btn_insert_template"):
        st.session_state["memo_text"] = build_current_template()
with colT2:
    if st.button("クリア", key="btn_clear_memo"):
        st.session_state["memo_text"] = ""
with colT3:
    st.caption(f"※ 現在のモード：{mode}（テンプレが切り替わります）")

# メモ編集時刻の追跡（on_change で確実に更新）
def _on_memo_change():
    st.session_state["last_edit_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

memo = st.text_area(
    "ここに議事録/メモを貼り付け（箇条書きOK）",
    height=320,
    value=st.session_state["memo_text"],
    key="memo_text",
    on_change=_on_memo_change,
)

# 最後の編集時刻を表示（下書き保存の安心感）
if st.session_state.get("last_edit_at"):
    st.caption(f"📝 最終編集：{st.session_state['last_edit_at']}")

# メモの不足項目チェック（入力品質向上）
if memo and memo.strip():
    checks = {
        "課題": ["課題", "困", "問題", "ボトルネック"],
        "現状": ["現状", "今は", "運用", "フロー"],
        "次回": ["次回", "宿題", "アクション", "TODO"],
        "決裁": ["決裁", "稟議", "承認", "上長"],
    }
    memo_lower = memo.lower()
    missing = [k for k, kws in checks.items() if not any(w in memo_lower for w in kws)]
    if missing:
        st.warning(f"💡 不足しがちな項目: {', '.join(missing)}（入れると精度が上がります）")

colA, colB = st.columns([1, 2])
with colA:
    btn_label = "再解析（/api/sales-flow）" if st.session_state.get("last_response") else "実行（/api/sales-flow）"
    run = st.button(
        btn_label,
        type="primary",
        key="run_sales_flow",
        disabled=(not api_ok or st.session_state["running"]),
    )
with colB:
    if st.session_state.get("last_run_at"):
        st.caption(f"最終解析：{st.session_state['last_run_at']}")
    else:
        st.write("※ 500や接続エラーなら、FastAPI（uvicorn）が起動しているか確認")

# 多重実行防止
if st.session_state["running"]:
    st.info("⏳ 処理中です。しばらくお待ちください…")
    st.stop()

# ---------- 実行処理（成功時のみ save_history を1回） ----------
data = st.session_state.get("last_response")

if run:
    st.session_state["running"] = True
    try:
        with st.spinner("API呼び出し中..."):
            result = execute_sales_flow(
                api_base=API_BASE,
                db_path=HISTORY_DB,
                customer_name=customer_name,
                customer_company=customer_company,
                meeting_date=str(meeting_date),
                memo=memo,
                mode=mode,
                tone=tone,
            )

        # 結果を保持（成功・失敗どちらでも wrapped 形式で保存）
        st.session_state["last_response"] = result.data
        st.session_state["last_run_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if result.history_id:
            st.session_state["last_history_id"] = result.history_id

        if not result.ok:
            # API失敗時も履歴は保存済み（wrapped形式）
            st.error(result.error or "処理に失敗しました")
            st.session_state["running"] = False
            st.rerun()  # 失敗履歴も表示できるように rerun
            st.stop()

        if result.error:
            # 保存失敗など「成功だが警告あり」
            st.warning(result.error)
        else:
            st.success("✅ 解析が完了しました")

        # 成功後は履歴リストなども最新にした状態で再描画
        st.session_state["running"] = False
        st.rerun()

    except Exception as e:
        st.session_state["running"] = False
        st.error(f"❌ 想定外エラー: {e}")

    finally:
        st.session_state["running"] = False

if st.session_state.get("show_timeline"):
    company = (st.session_state.get("customer_company") or "").strip()
    name = (st.session_state.get("customer_name") or "").strip()

    if not company or not name:
        st.info("会社名と顧客名を入れるとタイムラインが表示されます。")
    else:
        st.subheader(f"顧客タイムライン：{company} {name}")

        timeline_rows = list_history_by_customer(HISTORY_DB, company, name)

        if not timeline_rows:
            st.info("この顧客の履歴はまだありません。")
        else:
            for r in timeline_rows:
                loaded = json.loads(r["response_json"]) if r["response_json"] else None
                w = normalize_wrapped(loaded) if loaded else {}
                status = (w.get("meta") or {}).get("status")
                icon = "⚠️" if status == "error" else "✅"

                st.markdown(
                    f"{icon} **{r['created_at']}** | {r['mode']}/{r['tone']}"
                )
# ---------- 結果表示（last_response があればタブを常に描画） ----------
wrapped = st.session_state.get("last_response")
wrapped = normalize_wrapped(wrapped) if wrapped else None

if not wrapped:
    st.info("左の履歴から読み込むか、メモを入れて「実行」してください。")
    st.stop()

meta = (wrapped.get("meta") or {})
status = meta.get("status")

if status == "error":
    st.error(wrapped.get("error") or "APIエラー")
    with st.expander("入力（再現用）"):
        st.code(json.dumps(wrapped.get("payload", {}), ensure_ascii=False, indent=2))
    st.stop()

data = wrapped.get("data") or {}
core = data.get("core", {}) or {}
addons = data.get("addons", {}) or {}

# ---------- 送信前チェック要約カード（UX-C） ----------
summary_card = format_summary_card(wrapped)

with st.container():
    st.markdown(f"### {summary_card['title']}")
    if summary_card['subtitle']:
        st.caption(summary_card['subtitle'])
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if summary_card['open_questions']:
            st.markdown("**⚠️ 未確認事項（上位3）**")
            for i, question in enumerate(summary_card['open_questions'], 1):
                st.markdown(f"{i}. {question}")
        else:
            st.markdown("**未確認事項**: （なし）")
    with col2:
        if summary_card['next_actions']:
            st.markdown("**次アクション（上位3）**")
            for i, action in enumerate(summary_card['next_actions'], 1):
                st.markdown(f"{i}. {action}")
        else:
            st.markdown("**次アクション**: （なし）")
    
    st.divider()

tab_mail, tab_agenda, tab_boss = st.tabs(["メール", "次回アジェンダ", "上司向け要約"])

with tab_mail:
    st.subheader("フォローアップメール（送信用）")
    subject = core.get("followup_email_subject", "【フォローアップ】商談御礼と次回確認事項")
    body = core.get("followup_email_body", "")
    st.text_input("件名（このまま送信）", value=subject, key="mail_subject")
    
    # コピペ形式切り替え（件名+本文 / 本文のみ）
    fmt = st.radio("コピー形式", ["件名+本文", "本文のみ"], horizontal=True, key="mail_format")
    copy_text = f"件名：{subject}\n\n{body}\n" if fmt == "件名+本文" else body
    st.text_area("コピー用", value=copy_text, height=280, key="mail_body_copy")
    
    st.download_button(
        "メールをTXTで保存",
        data=f"件名：{subject}\n\n{body}\n",
        file_name="followup_email.txt",
        key="dl_mail",
    )

with tab_agenda:
    st.subheader("次回アジェンダ（会議用）")

    def agenda_block(title_no, title, items):
        st.markdown(f"### {title_no}. {title}")
        text = "\n".join([f"・{x}" for x in items]) if items else "（なし）"
        st.write(text)

    agenda_block(1, "要点", core.get("key_points", []))
    agenda_block(2, "決定事項", core.get("decisions", []))
    agenda_block(3, "次のステップ", core.get("next_steps", []))
    agenda_block(4, "当社アクション", core.get("action_items", []))
    st.markdown("### 5. 想定反論Q&A")
    objections = core.get("objections_qa", [])
    if objections:
        for i, item in enumerate(objections, 1):
            st.markdown(f"**Q{i}.** {item.get('objection', '')}")
            st.markdown(f"**A{i}.** {item.get('answer', '')}")
    else:
        st.write("（なし）")

with tab_boss:
    st.subheader("上司向け要約（コピペ用）")
    boss_text = format_boss_summary(
        customer_name=customer_name,
        meeting_date=str(meeting_date),
        payload=data,
    )
    st.text_area("コピペ用（編集可）", value=boss_text, height=260, key="boss_text")
    st.download_button(
        "TXT保存（コピペ用）",
        data=boss_text,
        file_name="boss_summary.txt",
        key="dl_boss",
    )
    bank = addons.get("bank")
    if bank:
        internal = bank.get("internal_control_points", []) or []
        audit = bank.get("audit_ready_points", []) or []
        with st.expander("銀行向け補助（任意で貼る）"):
            st.markdown("**内部統制ポイント**")
            internal_txt = "\n".join([f"- {x}" for x in internal]) if internal else "（なし）"
            st.write(internal_txt)
            st.markdown("**監査対応ポイント**")
            audit_txt = "\n".join([f"- {x}" for x in audit]) if audit else "（なし）"
            st.write(audit_txt)


with st.expander("（デバッグ）生JSONを表示"):
    st.code(json.dumps(data, ensure_ascii=False, indent=2))

