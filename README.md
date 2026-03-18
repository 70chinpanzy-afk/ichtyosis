# Sales Copilot

営業メモを構造化して返す `FastAPI` バックエンドと、ローカル運用の `Streamlit` UI を持つプロジェクトです。  
本番運用は以下の2パターンに対応しています。

- APIのみ Railway にデプロイ（推奨）
- API + UI（Streamlit）を Railway にデプロイ（外出先スマホ利用向け）

## 構成

- `app/`: RailwayへデプロイするFastAPIアプリ
- `ui_streamlit.py`: ローカル実行用UI（任意）
- `history_repo.py`: Postgresに履歴を保存

## 主要エンドポイント（FastAPI）

- `GET /` : API情報
- `GET /healthz` : ヘルスチェック（DB接続確認込み）
- `POST /api/sales-flow` : 営業フロー生成

## 環境変数

`.env.example` をコピーして `.env` を作成してください。

必須（API）:

- `OPENAI_API_KEY`
- `DATABASE_URL`  
  例: `postgresql://postgres:postgres@localhost:5432/sales_copilot`

任意（API）:

- `OPENAI_MODEL`（デフォルト: `gpt-4o-mini`）
- `HOST`（デフォルト: `0.0.0.0`）
- `PORT`（デフォルト: `8000`）
- `CORS_ALLOW_ORIGINS`（カンマ区切り）
- `CORS_ALLOW_CREDENTIALS`（`true`/`false`、デフォルト `false`）

任意（UI）:

- `SALES_COPILOT_API_BASE`（デフォルト: `http://127.0.0.1:8000`）
- `HISTORY_DATABASE_URL`（未指定時は `DATABASE_URL` を利用）

## ローカル開発手順

### 1. API（FastAPI）

```bash
cd sales-copilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Postgresを用意して `DATABASE_URL` を設定してから起動:

```bash
python -m app.main
```

`PORT` が設定されていればその値で起動します。  
例: `PORT=8080 python -m app.main`

動作確認:

```bash
curl http://127.0.0.1:8000/healthz
```

### 2. UI（Streamlit, 任意）

```bash
pip install -r requirements-ui.txt
streamlit run ui_streamlit.py
```

UIは `SALES_COPILOT_API_BASE` で指定したFastAPIを呼び出します。

## Railwayデプロイ（FastAPIのみ）

このリポジトリには以下を同梱しています。

- `Dockerfile`: FastAPI用コンテナビルド
- `railway.json`: 起動コマンドとヘルスチェック設定

Railway側で設定する主な変数:

- `OPENAI_API_KEY`
- `DATABASE_URL`（Railway Postgres の接続文字列）
- `OPENAI_MODEL`（任意）
- `CORS_ALLOW_ORIGINS`（任意）

デプロイ後、Railwayは `/healthz` で疎通確認します。

## Railwayデプロイ（外出先で使う: API + UI）

外出先でスマホから使う場合は、Railway に UI サービスを追加します。

### 1. APIサービス（既存）

- 既存の `sales-copilot` サービスを利用
- `https://<api-domain>/healthz` が `{"status":"ok","database":"up"}` であることを確認

### 2. UIサービス（新規）

Railwayで同じリポジトリから2つ目のサービスを作成し、以下を設定します。

- Builder: Dockerfile
- Dockerfile Path: `Dockerfile.streamlit`
- Start Command: 空でOK（DockerfileのCMDを使用）

UIサービスの Variables:

- `SALES_COPILOT_API_BASE=https://<api-domain>`
- `HISTORY_DATABASE_URL`（任意。履歴を使う場合のみ）

### 3. UIの公開URLでアクセス

- `https://<ui-domain>.up.railway.app` をスマホで開く
- サイドバーの「接続再判定」を押して接続状態を確認

### 注意（重要）

- APIに認証がないため、URLを知っている第三者も利用できる状態です。
- 本番運用時は将来的にAPIトークン認証を追加することを推奨します。

## 補足

- SQLite依存は削除し、DBアクセスはPostgres（`psycopg`）へ統一済みです。
- Streamlit UIは本番デプロイ対象外です（ローカル利用専用）。
