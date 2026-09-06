"""設定管理モジュール"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class CuratorConfig:
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("CURATOR_OPENAI_MODEL", "gpt-4o"))
    db_path: str = field(default_factory=lambda: os.getenv("CURATOR_DB_PATH", "ichthyosis_curator.db"))
    pubmed_email: str = field(default_factory=lambda: os.getenv("CURATOR_PUBMED_EMAIL", ""))
    max_articles: int = field(default_factory=lambda: int(os.getenv("CURATOR_MAX_ARTICLES_PER_RUN", "20")))
    log_level: str = field(default_factory=lambda: os.getenv("CURATOR_LOG_LEVEL", "INFO"))

    # 公開データ（frontend/public/data）の場所。
    # 配信履歴・週次まとめ・即時送信記録の読み書きに使う。
    # CIは backend/ を作業ディレクトリにして実行するため相対パスがこの形になる。
    data_dir: str = field(default_factory=lambda: os.getenv("CURATOR_DATA_DIR", "../frontend/public/data"))

    # 患者プロフィール（GitHub Actions Secret から渡す平文）。
    # 公開リポジトリなのでファイルには置かない。未設定なら汎用文で配信する。
    patient_profile: str = field(default_factory=lambda: os.getenv("PATIENT_PROFILE", ""))

    # LINE Messaging API
    line_channel_access_token: str = field(default_factory=lambda: os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
    line_user_id: str = field(default_factory=lambda: os.getenv("LINE_USER_ID", ""))

    # API
    api_host: str = field(default_factory=lambda: os.getenv("CURATOR_API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: int(os.getenv("CURATOR_API_PORT", "8001")))
    api_secret: str = field(default_factory=lambda: os.getenv("CURATOR_API_SECRET", ""))
    frontend_url: str = field(default_factory=lambda: os.getenv("FRONTEND_URL", "http://localhost:3000"))


def load_config() -> CuratorConfig:
    cfg = CuratorConfig()
    missing = []
    if not cfg.openai_api_key:
        missing.append("OPENAI_API_KEY")
    if missing:
        raise EnvironmentError(f"必須環境変数が未設定です: {', '.join(missing)}")
    return cfg
