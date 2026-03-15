"""キュレーション実行オーケストレーター"""

import logging
from datetime import datetime

from ichthyosis_curator.config import CuratorConfig
from ichthyosis_curator.db import init_db, log_run, save_curated_article
from ichthyosis_curator.sources.pubmed import get_pubmed_articles
from ichthyosis_curator.sources.clinical_trials import search_clinical_trials
from ichthyosis_curator.sources.news_rss import get_news_articles
from ichthyosis_curator.curation.llm_curator import curate_articles, generate_greeting
from ichthyosis_curator.curation.dedup import filter_unseen_articles, mark_articles_sent
from ichthyosis_curator.delivery.line_messaging import format_digest_for_line, send_line_push
from ichthyosis_curator.schemas import DailyDigest

logger = logging.getLogger(__name__)


def run_daily_curation(config: CuratorConfig) -> bool:
    """
    メインパイプライン:
    1. DB初期化
    2. 全ソースからデータ取得
    3. LLMでキュレーション
    4. 重複排除
    5. DB保存
    6. LINE通知
    7. ログ記録
    """
    init_db(config.db_path)

    today = datetime.now().strftime("%Y-%m-%d")
    today_display = datetime.now().strftime("%Y年%m月%d日")
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

    logger.info(f"合計: {len(all_raw)} raw articles from {sources_scanned} sources")

    if not all_raw:
        logger.warning("全ソースからの取得が0件です")
        log_run(
            config.db_path, sources_scanned, 0, 0, 0,
            status="warning", error_message="No articles from any source",
        )
        _send_empty_digest(config, today_display, sources_scanned)
        return True

    # --- キュレーション ---
    logger.info("=== LLMキュレーション開始 ===")
    try:
        curated = curate_articles(all_raw, model=config.openai_model)
        logger.info(f"キュレーション結果: {len(curated)} relevant / {len(all_raw)} raw")
    except Exception as e:
        logger.error(f"Curation failed: {e}")
        log_run(
            config.db_path, sources_scanned, len(all_raw), 0, 0,
            status="error", error_message=f"Curation: {e}",
        )
        return False

    # --- 重複排除 ---
    unseen = filter_unseen_articles(curated, config.db_path)
    logger.info(f"重複排除後: {len(unseen)} new / {len(curated) - len(unseen)} duplicates")

    to_send = unseen[: config.max_articles]

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
        )

    # --- 挨拶メッセージ生成 ---
    try:
        greeting = generate_greeting(today_display, model=config.openai_model)
    except Exception:
        greeting = f"{today_display}の魚鱗癬関連情報をお届けします。"

    # --- LINE通知 ---
    digest = DailyDigest(
        date=today_display,
        total_sources_scanned=sources_scanned,
        articles=to_send,
        greeting=greeting,
    )

    line_sent = False
    if config.line_channel_access_token and config.line_user_id:
        message = format_digest_for_line(digest)
        line_sent = send_line_push(
            config.line_channel_access_token, config.line_user_id, message,
        )
    else:
        logger.info("LINE credentials not set, skipping LINE notification")

    if line_sent:
        mark_articles_sent(to_send, config.db_path)

    # --- ログ記録 ---
    log_run(
        config.db_path,
        sources_scanned=sources_scanned,
        articles_found=len(all_raw),
        articles_curated=len(curated),
        articles_sent=len(to_send),
        status="ok",
        error_message="; ".join(errors) if errors else None,
    )

    logger.info(f"=== 完了: {len(to_send)} articles saved, LINE={line_sent} ===")
    return True


def _send_empty_digest(config: CuratorConfig, date: str, sources_scanned: int) -> None:
    digest = DailyDigest(
        date=date,
        total_sources_scanned=sources_scanned,
        articles=[],
        greeting=f"{date}の魚鱗癬関連情報をお届けします。",
    )
    if config.line_channel_access_token and config.line_user_id:
        message = format_digest_for_line(digest)
        send_line_push(config.line_channel_access_token, config.line_user_id, message)
