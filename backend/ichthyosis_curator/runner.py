"""キュレーション実行オーケストレーター"""

import logging

from ichthyosis_curator.config import CuratorConfig
from ichthyosis_curator.db import init_db, log_run, save_curated_article
from ichthyosis_curator.sources.pubmed import get_pubmed_articles
from ichthyosis_curator.sources.clinical_trials import search_clinical_trials
from ichthyosis_curator.sources.news_rss import get_news_articles
from ichthyosis_curator.sources.reddit import get_reddit_posts
from ichthyosis_curator.sources.patient_communities import get_patient_community_posts
from ichthyosis_curator.sources.youtube import get_youtube_videos
from ichthyosis_curator.sources.japan_support import get_japan_support_articles
from ichthyosis_curator.curation.llm_curator import (
    curate_articles,
    generate_greeting,
    CurationRunStats,
)
from ichthyosis_curator.curation.dedup import (
    filter_unseen_articles,
    filter_unseen_raw,
    mark_articles_sent,
)
from ichthyosis_curator.curation.history import load_seen_hashes
from ichthyosis_curator.curation.personalize import personalize_insights
from ichthyosis_curator.curation.quality import report_boilerplate
from ichthyosis_curator.curation.visit_brief import build_visit_brief
from ichthyosis_curator.delivery import policy
from ichthyosis_curator.delivery.line_messaging import (
    MODE_URGENT,
    MODE_WEEKLY,
    build_empty_message,
    build_flex_messages,
    send_line_flex,
    send_line_push,
)
from ichthyosis_curator.schemas import DeliveryItem
from ichthyosis_curator.timeutil import now_jst

logger = logging.getLogger(__name__)


def _build_llm_failure_alert(stats: CurationRunStats) -> str:
    """LLMキュレーションが全滅した場合にLINEへ送る警告テキストを組み立てる"""
    representative_error = stats.failures[0].error if stats.failures else "unknown error"
    return (
        "⚠️ キュレーション失敗: LLM呼び出しが全滅"
        f"（{representative_error}）。"
        "OpenAIのクレジット/請求設定を確認してください"
    )


def _should_alert_llm_failure(articles_sent: int, stats: CurationRunStats) -> bool:
    """0件送信 かつ 1回以上のバッチ失敗があるときにアラートを出すべきか判定"""
    return articles_sent == 0 and stats.failed_batches > 0


def run_daily_curation(
    config: CuratorConfig,
    dry_run: bool = False,
    force_weekly: bool = False,
) -> bool:
    """
    メインパイプライン:
    1. DB初期化
    2. 全ソースからデータ取得
    3. 既出記事をraw段階で除外（LLMコスト削減も兼ねる）
    4. LLMでキュレーション
    5. DB保存（サイトは毎日更新される）
    6. LINE配信判定 — 週次まとめ（月曜）と即時アラート（締切・募集）のみ
    7. ログ記録

    dry_run: LINEに送らず、送るはずだったFlex JSONを標準出力に書き出す
    force_weekly: 曜日に関係なく週次まとめを生成する（動作確認用）
    """
    init_db(config.db_path)

    # 配信先は日本なので日付・曜日はJST基準（CIランナーはUTCで動く）
    now = now_jst()
    today = now.strftime("%Y-%m-%d")
    today_display = now.strftime("%Y年%m月%d日")
    sources_scanned = 0
    all_raw = []
    errors = []

    # --- データ取得 ---
    logger.info("=== データソースからの取得開始 ===")

    try:
        pubmed = get_pubmed_articles(config.pubmed_email or "curator@example.com", days_back=7)
        all_raw.extend(pubmed)
        sources_scanned += 1
        logger.info(f"PubMed: {len(pubmed)} articles")
    except Exception as e:
        logger.error(f"PubMed fetch failed: {e}")
        errors.append(f"PubMed: {e}")

    try:
        ct = search_clinical_trials(days_back=30)
        all_raw.extend(ct)
        sources_scanned += 1
        logger.info(f"ClinicalTrials.gov: {len(ct)} studies")
    except Exception as e:
        logger.error(f"ClinicalTrials.gov fetch failed: {e}")
        errors.append(f"ClinicalTrials: {e}")

    try:
        news = get_news_articles(days_back=3)
        all_raw.extend(news)
        sources_scanned += 1
        logger.info(f"News RSS: {len(news)} articles")
    except Exception as e:
        logger.error(f"News fetch failed: {e}")
        errors.append(f"News: {e}")

    try:
        reddit = get_reddit_posts(days_back=14)
        all_raw.extend(reddit)
        sources_scanned += 1
        logger.info(f"Reddit: {len(reddit)} posts")
    except Exception as e:
        logger.error(f"Reddit fetch failed: {e}")
        errors.append(f"Reddit: {e}")

    try:
        community_posts = get_patient_community_posts(days_back=14)
        all_raw.extend(community_posts)
        sources_scanned += 1
        logger.info(f"Patient communities: {len(community_posts)} posts")
    except Exception as e:
        logger.error(f"Patient communities fetch failed: {e}")
        errors.append(f"PatientCommunities: {e}")

    try:
        youtube_videos = get_youtube_videos(days_back=30)
        all_raw.extend(youtube_videos)
        sources_scanned += 1
        logger.info(f"YouTube: {len(youtube_videos)} videos")
    except Exception as e:
        logger.error(f"YouTube fetch failed: {e}")
        errors.append(f"YouTube: {e}")

    # 日本の制度・助成。更新は年に数回だが、締切があって動けば結果が変わる情報。
    try:
        support = get_japan_support_articles()
        all_raw.extend(support)
        sources_scanned += 1
        logger.info(f"日本の制度・支援: {len(support)} 件")
    except Exception as e:
        logger.error(f"Japan support fetch failed: {e}")
        errors.append(f"JapanSupport: {e}")

    logger.info(f"合計: {len(all_raw)} raw articles from {sources_scanned} sources")

    # --- 既出記事をキュレーション前に除外 ---
    # CIではSQLiteが毎回空から作られるため、コミット済みの digests/*.json を
    # 履歴として使う。LLMに投げる前に落とすのでAPIコストも下がる。
    seen_hashes = load_seen_hashes(config.data_dir, days=60)
    before_dedup = len(all_raw)
    all_raw = filter_unseen_raw(all_raw, seen_hashes)
    logger.info(
        f"raw重複排除: {len(all_raw)} new / {before_dedup - len(all_raw)} 既出をスキップ"
    )

    if not all_raw:
        # 「ソースが0件」と「取れたが全部既出」は別物。
        # 重複排除を入れると後者が普通に起きるので、警告にしない。
        if before_dedup == 0:
            logger.warning("全ソースからの取得が0件です")
            status, note = "warning", "No articles from any source"
        else:
            logger.info(f"取得した{before_dedup}件はすべて既出のため新着なし")
            status, note = "ok", None

        log_run(
            config.db_path, sources_scanned, before_dedup, 0, 0,
            status=status, error_message=note,
        )
        _send_empty_digest(config, today_display, dry_run, force_weekly)
        return True

    # --- キュレーション ---
    logger.info("=== LLMキュレーション開始 ===")
    curation_stats = CurationRunStats()
    try:
        curated = curate_articles(
            all_raw, model=config.openai_model, stats=curation_stats
        )
        logger.info(f"キュレーション結果: {len(curated)} relevant / {len(all_raw)} raw")
    except Exception as e:
        logger.error(f"Curation failed: {e}")
        log_run(
            config.db_path, sources_scanned, len(all_raw), 0, 0,
            status="error", error_message=f"Curation: {e}",
        )
        return False

    if curation_stats.failed_batches > 0:
        if curation_stats.all_batches_failed:
            logger.error(
                f"LLMキュレーションが全バッチ失敗: "
                f"{curation_stats.failed_batches}/{curation_stats.total_batches} batches"
            )
        else:
            logger.info(
                f"LLMキュレーションの一部バッチが失敗: "
                f"{curation_stats.failed_batches}/{curation_stats.total_batches} batches"
            )

    # --- 重複排除 ---
    unseen = filter_unseen_articles(curated, config.db_path)
    logger.info(f"重複排除後: {len(unseen)} new / {len(curated) - len(unseen)} duplicates")

    to_send = unseen[: config.max_articles]

    # patient_insight が一般論に収束していないかCIログに残す。
    # 患者プロフィールを使わない運用では、行動につながる文はこれ一本なので
    # 劣化に気づけるようにしておく。
    report_boilerplate(to_send)

    # --- DB保存 ---
    import json as _json
    for article in to_send:
        drugs_data = [d.model_dump() for d in article.drugs] if article.drugs else []
        save_curated_article(
            db_path=config.db_path,
            digest_date=today,
            source=article.source,
            source_id=article.source_id,
            original_title=article.original_title,
            title_ja=article.title_ja,
            summary_ja=article.summary_ja,
            category=article.category,
            relevance_score=article.relevance_score,
            url=article.url,
            published_date=article.published_date,
            curation_reasoning=article.curation_reasoning,
            drugs_json=_json.dumps(drugs_data, ensure_ascii=False),
            patient_insight=article.patient_insight,
            deadline=article.deadline,
            action_required=article.action_required,
        )

    # --- LINE配信判定 ---
    # サイト（frontend/public/data）は毎日更新するが、LINEは
    # 週次まとめ（月曜）と即時アラート（締切・募集）だけに絞る。
    today_items = [DeliveryItem.from_curated(article) for article in to_send]

    alert_llm_failure = _should_alert_llm_failure(len(to_send), curation_stats)
    line_sent = False

    if alert_llm_failure:
        # 運用アラートは曜日に関係なく即時に出す
        alert_text = _build_llm_failure_alert(curation_stats)
        logger.error(f"LLM全滅アラートをLINE送信: {alert_text}")
        line_sent = _push_text(config, alert_text, dry_run)
    else:
        line_sent = _deliver(config, today_items, today_display, dry_run, force_weekly)

    if line_sent:
        mark_articles_sent(to_send, config.db_path)

    # --- ログ記録 ---
    llm_failure_note = None
    if curation_stats.failed_batches > 0:
        representative_error = (
            curation_stats.failures[0].error if curation_stats.failures else ""
        )
        llm_failure_note = (
            f"LLM batches failed: {curation_stats.failed_batches}/"
            f"{curation_stats.total_batches} ({representative_error})"
        )

    combined_errors = errors + ([llm_failure_note] if llm_failure_note else [])
    log_run(
        config.db_path,
        sources_scanned=sources_scanned,
        articles_found=before_dedup,
        articles_curated=len(curated),
        articles_sent=len(to_send),
        status="error" if alert_llm_failure else "ok",
        error_message="; ".join(combined_errors) if combined_errors else None,
    )

    logger.info(
        f"=== 完了: {len(to_send)} articles saved, LINE={line_sent}, "
        f"llm_alert={alert_llm_failure} ==="
    )
    return True


def _deliver(
    config: CuratorConfig,
    today_items: list[DeliveryItem],
    today_display: str,
    dry_run: bool,
    force_weekly: bool,
) -> bool:
    """即時アラートと週次まとめの送信を判定して実行する"""
    already_alerted = policy.load_alerted(config.data_dir)
    urgent = policy.select_urgent(today_items, already_alerted)
    send_weekly = force_weekly or policy.should_send_weekly()

    logger.info(
        f"配信判定: urgent={len(urgent)}件, weekly={send_weekly} "
        f"(force_weekly={force_weekly})"
    )

    sent = False

    # --- 即時アラート ---
    if urgent:
        messages = build_flex_messages(
            urgent,
            date_label=today_display,
            frontend_url=config.frontend_url,
            mode=MODE_URGENT,
            insight_overrides=_personalize(config, urgent),
        )
        if _push_flex(config, messages, dry_run, label="urgent"):
            sent = True
            if not dry_run:
                policy.record_alerted(config.data_dir, urgent)

    if not send_weekly:
        logger.info("本日は週次まとめの送信日ではないためスキップ")
        return sent

    # --- 週次まとめ ---
    # 即時送信済みは本文から外し、ヘッダーで件数だけ知らせる
    weekly_exclude = policy.load_alerted(config.data_dir, days=7)
    if dry_run:
        # dry-runでは record_alerted していないので、今回ぶんを手で足す
        weekly_exclude = weekly_exclude | {policy.item_hash(i) for i in urgent}

    weekly_items = policy.build_weekly_items(
        config.data_dir, today_items, exclude=weekly_exclude
    )

    try:
        greeting = generate_greeting(today_display, model=config.openai_model)
    except Exception:
        greeting = f"{today_display}の魚鱗癬関連情報をお届けします。"

    # 「次の診察で聞くとよいこと」を過去1か月ぶんから作る。
    # 失敗しても空リストが返るだけで、まとめ自体は送られる。
    brief = build_visit_brief(
        config.data_dir, model=config.openai_model, extra_items=today_items
    )

    messages = build_flex_messages(
        weekly_items,
        date_label=today_display,
        greeting=greeting,
        frontend_url=config.frontend_url,
        mode=MODE_WEEKLY,
        urgent_count=len(weekly_exclude),
        insight_overrides=_personalize(config, weekly_items),
        brief_entries=brief,
    )
    if _push_flex(config, messages, dry_run, label="weekly"):
        sent = True

    return sent


def _personalize(
    config: CuratorConfig, items: list[DeliveryItem]
) -> dict[str, str]:
    """LINE送信直前にプロフィールを当てて「次にできること」を作る。

    ここで作った文は公開データ(frontend/public/data)には一切書かない。
    DB保存とエクスポートはこの時点で既に終わっており、対象は
    LINEに送るメッセージだけ。
    """
    if not config.patient_profile:
        return {}
    return personalize_insights(
        items, config.patient_profile, model=config.openai_model
    )


def _push_flex(
    config: CuratorConfig, messages: list[dict], dry_run: bool, label: str
) -> bool:
    if dry_run:
        import json as _json

        print(f"=== DRY RUN ({label}) ===")
        print(_json.dumps(messages, ensure_ascii=False, indent=2))
        return False
    if not (config.line_channel_access_token and config.line_user_id):
        logger.info("LINE credentials not set, skipping LINE notification")
        return False
    return send_line_flex(
        config.line_channel_access_token, config.line_user_id, messages
    )


def _push_text(config: CuratorConfig, text: str, dry_run: bool) -> bool:
    if dry_run:
        print("=== DRY RUN (text) ===")
        print(text)
        return False
    if not (config.line_channel_access_token and config.line_user_id):
        logger.info("LINE credentials not set, skipping LINE notification")
        return False
    return send_line_push(
        config.line_channel_access_token, config.line_user_id, text
    )


def _send_empty_digest(
    config: CuratorConfig, date_display: str, dry_run: bool, force_weekly: bool
) -> None:
    """新着ゼロの日。週次まとめの日だけ「新着なし」を知らせ、平日は黙る"""
    if not (force_weekly or policy.should_send_weekly()):
        logger.info("新着なし・週次まとめの日でもないため何も送らない")
        return

    message = build_empty_message(
        date_display, f"{date_display}の魚鱗癬関連情報をお届けします。"
    )
    if dry_run:
        import json as _json

        print("=== DRY RUN (empty) ===")
        print(_json.dumps([message], ensure_ascii=False, indent=2))
        return
    if not (config.line_channel_access_token and config.line_user_id):
        logger.info("LINE credentials not set, skipping LINE notification")
        return
    send_line_flex(
        config.line_channel_access_token, config.line_user_id, [message]
    )
