# 📈 Azure-OpenAI StockTool DEMO – Chat with the Market
[DEMO VIDEO](https://drive.google.com/file/d/1B1sNUfY5oYQSipheqQFa8lbwyCilUDv1/view?usp=sharing)

## 概要

Azure-OpenAI_StockToolは、FastAPIとAzure/OpenAI（GPTモデル）を活用し、株価情報の取得・対話型AIアシスタント機能を提供するWebアプリケーションです。yfinance APIを用いて、リアルタイムの株価や企業情報、関連ニュース、リスク指標などを取得できます。フロントエンドはReact (Vite) を採用しています。

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

---

## 画面構成

- **チャットセクション**  
  - 質問プロンプト入力欄
  - システムプロンプト（任意）
  - Azure OpenAIのデプロイメント名指定（任意）
  - 回答＆ツールコールの結果表示

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
