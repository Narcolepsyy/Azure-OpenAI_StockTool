# Azure-OpenAI_StockTool

## 概要

Azure-OpenAI_StockToolは、FastAPIとAzure/OpenAI（GPTモデル）を活用し、株価情報の取得・対話型AIアシスタント機能を提供するWebアプリケーションです。yfinance APIを用いて、リアルタイムの株価や企業情報、関連ニュース、リスク指標などを取得できます。フロントエンドはReact (Vite) を採用しています。

## 📁 Project Structure

This project is organized into clear, modular directories:

```
Azure-OpenAI_StockTool/
├── app/                    # Backend application code
│   ├── auth/              # Authentication & JWT
│   ├── core/              # Configuration & settings
│   ├── models/            # Database models & schemas
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic
│   │   └── aws/          # AWS service integrations
│   └── utils/             # Utilities & helpers
├── frontend/              # React frontend (Vite + TypeScript)
├── docs/                  # 📚 All documentation files
├── tests/                 # 🧪 All test files
├── scripts/               # 🔧 Setup & utility scripts
├── demos/                 # 🎬 Demo & debug scripts
├── html_demos/            # 🌐 HTML demonstration files
├── knowledge/             # RAG knowledge base files
├── lambda_functions/      # AWS Lambda functions
├── localstack/            # LocalStack initialization scripts
├── static/                # Static assets
├── main.py               # FastAPI application entry point
├── docker-compose.yml    # Docker orchestration
└── Dockerfile            # Application container
```

**Key Directories:**
- 📚 **docs/** - Complete documentation (40+ guides covering architecture, AWS, performance, etc.)
- 🧪 **tests/** - Comprehensive test suite (60+ test files)
- 🔧 **scripts/** - Setup scripts (`setup_localstack.sh`, `setup_dashboard.sh`, `verify_aws_resources.py`)
- 🎬 **demos/** - Demo and debugging scripts
- 🌐 **html_demos/** - Standalone HTML demonstrations

See individual README files in each directory for detailed information.

---

## 🚀 AWS Integration with LocalStack

This project includes **enterprise-grade AWS integrations** that you can run locally using LocalStack:

- **S3** - Document storage for RAG knowledge base
- **DynamoDB** - Distributed conversation storage with TTL
- **SQS** - Asynchronous task queue
- **SNS** - Notification system
- **Lambda** - Scheduled stock updates
- **CloudWatch** - Metrics and monitoring

### Quick Start with LocalStack

1. **Get LocalStack Auth Token** (Free):
   - Sign up at: https://app.localstack.cloud/
   - Get token from: https://app.localstack.cloud/workspace/auth-token
   - Add to `.env`: `LOCALSTACK_AUTH_TOKEN="ls-your-token-here"`

2. **Run Setup Script**:
   ```bash
   ./scripts/setup_localstack.sh
   ```

3. **Verify Resources**:
   ```bash
   python scripts/verify_aws_resources.py
   ```

4. **Run Tests**:
   ```bash
   python tests/test_aws_integration.py
   ```

**📖 Complete Guide**: See `docs/LOCALSTACK_SETUP_GUIDE.md` for detailed setup instructions.

**🏗️ Architecture Details**: See `docs/AWS_INTEGRATION.md` for comprehensive AWS integration documentation.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for frontend development)

### 1. Clone and Setup Environment
```bash
# Clone repository
git clone https://github.com/Narcolepsyy/Azure-OpenAI_StockTool.git
cd Azure-OpenAI_StockTool

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
# Copy and edit .env file with your API keys
# Required: At least one of OPENAI_API_KEY or AZURE_OPENAI_* keys
# Optional: LOCALSTACK_AUTH_TOKEN (free from https://app.localstack.cloud/)

# Example minimal .env:
OPENAI_API_KEY=sk-your-key-here
LOCALSTACK_AUTH_TOKEN=ls-your-token-here  # Optional but recommended
```

### 3. Start Services
```bash
# Start LocalStack (for AWS features)
docker compose up -d localstack

# Start backend
python main.py
```

### 4. Access the Application
- **Web Interface**: http://localhost:8000/app
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/healthz

### 5. Test Everything
```bash
# Run comprehensive test
./scripts/test_quick_start.sh
```

### 6. Deploy Lambda Functions (Optional)
```bash
# Deploy automated stock data updater
./scripts/deploy_lambda.sh

# Create CloudWatch monitoring dashboard
./scripts/create_cloudwatch_dashboard.sh

# Test Lambda functions
python scripts/test_lambda.py
```

**📖 Detailed Guides**: 
- Complete walkthrough: `docs/GETTING_STARTED.md`
- Lambda & CloudWatch: `docs/LAMBDA_AND_CLOUDWATCH_GUIDE.md`

---

## 追加: 対応モデル / デプロイエイリアス

バックエンド `/models` エンドポイントは現在利用可能なモデル（エイリアスと実デプロイメント名）を返します。既定では以下をサポート:

| Alias / Choice | 説明 | Azure 環境変数 (任意) |
|----------------|------|------------------------|
| gpt-4.1 | 高精度モデル | `AZURE_OPENAI_DEPLOYMENT_4_1` |
| gpt-4.1-mini | 軽量高速 | `AZURE_OPENAI_DEPLOYMENT_4_1_MINI` |
| o3 | 高推論/最適化 (例) | `AZURE_OPENAI_DEPLOYMENT_O3` |
| gpt-5 | 次世代モデル (占位) | `AZURE_OPENAI_DEPLOYMENT_GPT5` |
| gpt-oss-120b | OSS大型 (占位/カスタム) | `AZURE_OPENAI_DEPLOYMENT_OSS_120B` |

フロントエンドのフォールバックセレクタにも `gpt-oss-120b` を追加済みです。Azureを使わず標準OpenAIキーのみ設定した場合、エイリアスはそのままモデル名として送信されます。

---

## 主な機能

- **AIチャットアシスタント (ツールコール)** – 株価、企業情報、ニュース、リスク評価を自動でツール経由取得
- **履歴付きマルチターン会話** – `conversation_id` によりコンテキスト維持
- **ニュース拡張 (全文抽出 + RAG オプション)**
- **RAG (任意)** – `knowledge/` ディレクトリをChromaへインデックス
- **リスク指標計算** – 年率ボラティリティ、Sharpe、最大ドローダウン、VaR、β(ベンチマーク)
- **管理ログ/監査** – Adminユーザーでチャットログ閲覧
- **リアルタイム株価ダッシュボード** – Finnhub WebSocketで2秒ごとに株価自動更新、ウォッチリスト管理

---

## 画面構成

- **チャットセクション**  
  - 質問プロンプト入力欄
  - システムプロンプト（任意）
  - Azure OpenAIのデプロイメント名指定（任意）
  - 回答＆ツールコールの結果表示

- **サイドバー (チャット一覧)**  
  - セッションタイトルは Markdown の一部記法 (太字/斜体/コード) をインライン表示します。
  - セキュリティのため HTML は無効化し、単一行に省略表示します（リンク等はプレーンテキスト）。

- **株価クイック取得セクション**  
  - 銘柄入力欄（例：AAPL）
  - 取得した株価・日時・通貨・データソース表示

---

## 環境変数 (抜粋)

| 変数 | 用途 |
|------|------|
| AZURE_OPENAI_API_KEY | Azure OpenAI キー |
| AZURE_OPENAI_ENDPOINT | エンドポイント URL |
| AZURE_OPENAI_API_VERSION | API バージョン |
| AZURE_OPENAI_DEPLOYMENT | 既定デプロイメント (フォールバック) |
| AZURE_OPENAI_DEPLOYMENT_4_1 | gpt-4.1 用エイリアス |
| AZURE_OPENAI_DEPLOYMENT_4_1_MINI | gpt-4.1-mini 用 |
| AZURE_OPENAI_DEPLOYMENT_O3 | o3 用 |
| AZURE_OPENAI_DEPLOYMENT_GPT5 | gpt-5 用 |
| AZURE_OPENAI_DEPLOYMENT_OSS_120B | gpt-oss-120b 用 |
| OPENAI_API_KEY | 標準 OpenAI 使用時のキー |
| OPENAI_MODEL | 標準OpenAI利用時の既定モデル |
| RAG_ENABLED | RAG有効可否 (true/false) |
| AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT | RAG埋め込みモデル (Azure) |
| FINNHUB_API_KEY | Finnhub API キー (リアルタイム株価ダッシュボード用) |

---

## モデル解決ロジック概要

1. 標準 OpenAI キーが設定されていれば OpenAI プロバイダ優先
2. 無ければ Azure OpenAI を利用
3. Azure 利用時はエイリアス → デプロイメント名にマップ
4. 指定が無ければ `AZURE_OPENAI_DEPLOYMENT` or `OPENAI_MODEL` を利用

---

## システムプロンプト標準

デフォルトの system_prompt はフロント/バックエンド双方に同一文面が設定され、株価・ニュース等の取得時に必ず内部ツールを利用するよう誘導します (理由→ツール精度/最新性確保)。

---

## セットアップ / 既存手順

1. **環境変数の設定**
   - `.env` ファイルにAzure OpenAI APIキーなど必要な設定を記載
   - 例: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `APP_API_KEY` 等

2. **バックエンドの起動**
   ```bash
   uvicorn main:app --reload
   ```
   デフォルトで `http://127.0.0.1:8000` で起動します。

3. **フロントエンドの起動（開発時）**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   デフォルトで `http://localhost:5173` でアクセス可能です。

4. **本番ビルド**
   ```
   npm run build
   ```
   `/app` でReactアプリが提供されます。

---

## API エンドポイント（抜粋）

- `/chat`  
  OpenAIベースの対話型チャットAPI。APIキー必須。
- `/stock/{symbol}`  
  株価クイック取得API
- `/news/{symbol}`  
  関連ニュース取得API

---

## 使用例

- チャット欄に「AAPLの最新株価は？」と質問
- 直接「AAPL」と入力し株価を取得

---

## 注意事項

- APIキーの漏洩に注意してください。
- yfinanceの仕様変更等による情報の遅延や取得失敗が発生する場合があります。
- Azure OpenAIの利用にはAzureサブスクリプション・権限が必要です。

---

## ライセンス

MIT License

---

## 開発・運用者向けメモ

- FastAPIは `127.0.0.1:8000` で起動
- ViteのReact開発サーバは `5173` ポート
- 本番運用時はReactをビルドし、`/app` 経由でアクセス

---

## お問い合わせ

バグ報告・機能要望などはGitHub Issuesをご利用ください。

---

## New: Multi-turn chat and chat history management

- The server now maintains per-conversation history (TTL-based). The chat API returns a `conversation_id` you can reuse on subsequent requests to keep context.
- To start a new chat from the UI, click “New chat” — the next message creates a fresh conversation.
- To delete a chat’s history, click “Delete chat history” (or POST `/chat/clear` with `{ conversation_id }`).

### API details
- POST `/chat`
  - Request: `{ prompt, system_prompt?, deployment?, conversation_id?, reset? }`
  - Response: `{ content, tool_calls?, conversation_id }`
- POST `/chat/clear`
  - Request: `{ conversation_id: string }`
  - Response: `{ conversation_id: string, cleared: boolean }`

---

## Improved: News fetching with fallback and caching

- The news tool first tries yfinance and falls back to Yahoo Finance RSS when needed.
- Results are cached per symbol+limit for a short TTL to reduce flakiness and latency.
- Env vars:
  - `NEWS_CACHE_SIZE` (default 1024)
  - `NEWS_TTL_SECONDS` (default 300)

