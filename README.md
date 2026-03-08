# 🤝 Sales Copilot API

営業活動を支援するAIコパイロットAPI。OpenAIのStructured Outputsを使用して、営業メール生成、商談議事録要約、提案書アウトライン生成などの機能を提供します。

## 🎯 主な機能

- **営業メール生成**: 顧客情報と目的から適切な営業メールを自動生成
- **商談議事録要約**: 商談内容を分析し、要点・決定事項・ネクストアクションを抽出
- **提案書アウトライン生成**: 顧客の課題と自社サービスから提案書の構成を生成
- **会話履歴管理**: SQLiteで顧客とのやり取りを保存・検索

## 🚀 セットアップ

### 1. 依存パッケージのインストール

```bash
cd sales-copilot
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成し、OpenAI APIキーを設定します。

```bash
cp .env.example .env
```

`.env`ファイルを編集:
```
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 3. アプリケーションの起動

```bash
uvicorn app.main:app --reload
```

または

```bash
python -m app.main
```

サーバーが起動したら、以下のURLでアクセスできます:
- API: http://localhost:8000
- ドキュメント: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📝 API エンドポイント

### 1. 営業メール生成

**POST** `/api/generate-email`

```json
{
  "customer_name": "田中太郎",
  "customer_company": "株式会社サンプル",
  "email_type": "initial_approach",
  "context": "新規顧客への初回アプローチ。物流システムの提案を行いたい。",
  "key_points": [
    "配送コスト削減",
    "リアルタイム追跡機能",
    "既存システムとの連携"
  ]
}
```

**レスポンス:**
```json
{
  "subject": "【物流効率化のご提案】配送コスト削減とリアルタイム追跡の実現",
  "body": "田中太郎様\n\nお世話になっております...",
  "tone": "フォーマルかつ親しみやすい",
  "next_action": "1週間以内にフォローアップの電話を入れる"
}
```

### 2. 商談議事録要約

**POST** `/api/summarize-meeting`

```json
{
  "customer_name": "佐藤花子",
  "customer_company": "株式会社テスト",
  "meeting_date": "2024-01-24",
  "meeting_content": "本日は物流システムの導入について打ち合わせを実施。現在の課題として、配送状況の可視化ができていない点、繁忙期の人手不足が挙げられた。予算は年間500万円程度。3月までに導入したいとのこと。"
}
```

**レスポンス:**
```json
{
  "summary": "物流システム導入の打ち合わせ。配送状況の可視化と繁忙期の人手不足が主な課題。予算500万円、3月までの導入を希望。",
  "key_points": [
    "配送状況の可視化が課題",
    "繁忙期の人手不足",
    "予算: 年間500万円",
    "導入希望時期: 3月まで"
  ],
  "decisions": [
    "3月までの導入を目指す",
    "予算は年間500万円程度"
  ],
  "concerns": [
    "配送状況の可視化ができていない",
    "繁忙期の人手不足"
  ],
  "next_actions": [
    "詳細な提案書を作成",
    "デモンストレーションの日程調整",
    "導入スケジュールの策定"
  ]
}
```

### 3. 提案書アウトライン生成

**POST** `/api/generate-proposal`

```json
{
  "customer_name": "山田次郎",
  "customer_company": "株式会社物流",
  "customer_industry": "製造業",
  "customer_challenges": "配送コストが高い、配送状況が見えない、ドライバー不足",
  "our_services": "クラウド型配送管理システム、リアルタイム追跡、AI配車最適化",
  "proposal_goal": "3ヶ月以内にシステム導入を決定し、配送コスト15%削減を実現"
}
```

**レスポンス:**
```json
{
  "title": "配送業務効率化・コスト削減提案書",
  "sections": [
    {
      "title": "現状課題の整理",
      "key_points": [
        "配送コストの増加傾向",
        "配送状況の可視化不足",
        "ドライバー不足による業務負荷"
      ]
    },
    {
      "title": "ご提案するソリューション",
      "key_points": [
        "クラウド型配送管理システムの導入",
        "リアルタイム追跡機能による可視化",
        "AI配車最適化によるコスト削減"
      ]
    }
  ],
  "expected_qa": [
    {
      "question": "導入にかかる期間はどのくらいですか？",
      "answer": "通常2-3ヶ月程度で導入可能です。"
    }
  ]
}
```

### 4. 会話履歴取得

**GET** `/api/conversations/{customer_id}`

顧客IDで会話履歴を取得します。

**GET** `/api/conversations`

すべての会話履歴を取得します（最大100件）。

### 5. 会話履歴作成

**POST** `/api/conversations`

手動で会話履歴を作成します。

### 6. 会話履歴削除

**DELETE** `/api/conversations/{conversation_id}`

指定されたIDの会話履歴を削除します。

## 🏗️ プロジェクト構造

```
sales-copilot/
├── app/
│   ├── main.py          # FastAPIアプリケーション
│   ├── llm.py           # OpenAI API呼び出し（Structured Outputs）
│   ├── schemas.py       # Pydanticスキーマ定義
│   ├── prompts.py       # 営業特化プロンプト
│   └── db.py            # SQLiteデータベース操作
├── .env.example         # 環境変数テンプレート
├── requirements.txt     # 依存パッケージ
└── README.md            # このファイル
```

## 🔧 技術スタック

- **FastAPI**: 高速なWeb APIフレームワーク
- **OpenAI API**: GPT-4を使用したAI生成（Structured Outputs）
- **Pydantic**: データバリデーションと型安全性
- **SQLite**: 軽量なデータベース
- **Python 3.9+**: プログラミング言語

## 📊 データベーススキーマ

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_company TEXT NOT NULL,
    conversation_type TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔒 セキュリティ

- APIキーは`.env`ファイルで管理（Gitにコミットしない）
- 会話履歴はローカルのSQLiteに保存
- CORS設定により外部からのアクセスを制御可能

## 💡 使用例

### cURLでの使用例

```bash
# 営業メール生成
curl -X POST "http://localhost:8000/api/generate-email" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "田中太郎",
    "customer_company": "株式会社サンプル",
    "email_type": "initial_approach",
    "context": "新規顧客への初回アプローチ",
    "key_points": ["配送コスト削減", "リアルタイム追跡"]
  }'
```

### Pythonでの使用例

```python
import requests

response = requests.post(
    "http://localhost:8000/api/generate-email",
    json={
        "customer_name": "田中太郎",
        "customer_company": "株式会社サンプル",
        "email_type": "initial_approach",
        "context": "新規顧客への初回アプローチ",
        "key_points": ["配送コスト削減", "リアルタイム追跡"]
    }
)

print(response.json())
```

## 🤝 サポート

問題が発生した場合:

1. OpenAI APIキーが正しく設定されているか確認
2. 依存パッケージが正しくインストールされているか確認
3. ログを確認してエラーメッセージを確認

---

**Sales Copilot API** | Powered by OpenAI GPT-4
