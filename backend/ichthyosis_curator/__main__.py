"""エントリーポイント: python -m ichthyosis_curator"""

import sys
import logging
import argparse

from ichthyosis_curator.config import load_config
from ichthyosis_curator.runner import run_daily_curation


def main():
    parser = argparse.ArgumentParser(
        description="魚鱗癬紅皮症 デイリーニュースキュレーター"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="デバッグログを有効にする"
    )
    parser.add_argument(
        "--serve", action="store_true", help="APIサーバーを起動する"
    )
    parser.add_argument(
        "--port", type=int, default=8001, help="APIサーバーのポート（デフォルト: 8001）"
    )
    parser.add_argument(
        "--export", type=str, metavar="OUTPUT_DIR",
        help="静的JSONをエクスポートする（例: ../frontend/public/data）"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="LINEに送らず、送るはずだったFlex JSONを標準出力に出す"
    )
    parser.add_argument(
        "--force-weekly", action="store_true",
        help="曜日に関係なく週次まとめを生成する（動作確認用）"
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.export:
        from ichthyosis_curator.exporter import export_static_json
        try:
            config = load_config()
        except EnvironmentError as e:
            logging.error(f"設定エラー: {e}")
            sys.exit(1)
        count = export_static_json(config.db_path, args.export)
        logging.info(f"エクスポート完了: {count} articles")
        sys.exit(0)
    elif args.serve:
        import uvicorn
        from ichthyosis_curator.api.app import app

        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        try:
            config = load_config()
        except EnvironmentError as e:
            logging.error(f"設定エラー: {e}")
            sys.exit(1)

        success = run_daily_curation(
            config, dry_run=args.dry_run, force_weekly=args.force_weekly
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
