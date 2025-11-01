## プロジェクト概要
AI（Gemini API）を活用し、クイズ問題を自動生成・出題するWebアプリ。  
将来的に **Web / iOS / Android** で動作し、リアルタイム対戦や学習最適化を行う統合型クイズプラットフォームを目指しています。

---

## 使用技術一覧

| Layer | Technology | Purpose |
|-------|-------------|----------|
| **Frontend** | Next.js / TypeScript / Material UI | Web UI構築、SSR対応 |
| **Backend** | FastAPI (Python) | AI連携・クイズ生成APIサーバー |
| **Database** | (予定) Firebase / Supabase | ユーザー・スコア・リアルタイム同期 |
| **Future Infra** | (予定) Docker / React Native | コンテナ化・モバイル化対応 |

---

## 現在の機能
- クイズカテゴリ選択による問題自動生成（Gemini API）
- 回答入力・正誤判定
- 問題・回答履歴の表示
- Pythonスクリプトによるプロンプト最適化実験

---

## 企画中の機能
| 機能 | 内容 | 関連技術 |
|------|------|----------|
| **リアルタイム対戦** | Socket通信またはFirebase Realtime DBで複数ユーザー対戦 | Supabase / Socket.IO |
| **問題推薦AI** | ユーザー履歴・正答率を学習し難易度を最適化 | scikit-learn / Prophet |
| **問題類似度検索** | embedding検索でLLM生成問題の重複回避 | LangChain / Faiss |
| **ネイティブ展開** | Web + iOS + Androidの統合開発 | Expo + React Native for Web |
| **成績分析ダッシュボード** | ユーザーごとの傾向分析・可視化 | Plotly / Streamlit |

---

## アーキテクチャ (Planned)
```plaintext
User
 ↓
[ Next.js (Web) / Expo (Mobile) ]
 ↓
[ API Gateway (TypeScript) ]
 ↓
[ FastAPI (Python, Gemini Integration) ]
 ↓
[ Firebase / Supabase (Realtime DB, Auth) ]
 ↓
[ Analytics (Python, scikit-learn, Prophet) ]
````


## リポジトリ構造

```plaintext
quiz_app/
├── frontend/ # Next.jsのプロジェクト本体
│ ├── app/
│ ├── public/
│ └── ... (Next.jsのその他設定ファイル)
│
├── backend/ # FastAPIのバックエンド
│ ├── Scripts/ (Python仮想環境)
│ ├── Lib/ (Python仮想環境)
│ ├── main.py (APIサーバー本体)
│ ├── requirements.txt
│ └── .env
│
├── node_modules/ # フロントエンドのライブラリ
├── .gitignore
├── package.json # Next.jsのパッケージ管理ファイル
├── README.md
└── tsconfig.json
```

---

## 準備

```bash
# 1. リポジトリをクローン
git clone https://github.com/GeN403/quiz_app.git
cd quiz_app

# 2. バックエンド (FastAPI) のセットアップ
# (ターミナル1 🤖)
cd backend
python -m venv venv
.\Scripts\Activate
pip install -r requirements.txt

# 3. フロントエンド (Next.js) のセットアップ
# (ターミナル2 💻)
# ※ quiz_appのルートフォルダで実行
npm install

# 4. サーバーの起動
# (ターミナル1 🤖)
cd backend
uvicorn main:app --reload

# (ターミナル2 💻)
# ※ quiz_appのルートフォルダで実行
npx next dev frontend --turbopack
```

---

## 📈 Example Screenshot

（例：アプリのUIキャプチャやGIFを挿入）

```markdown
![demo](./public/demo.gif)
```

---

## 🧰 Skills Demonstrated

* LLM統合アプリケーション開発（Gemini API）
* TypeScript / Next.jsを用いたWebフロント開発
* Pythonによるプロンプト設計・API統合
* クラウドサービスを意識した構成設計
* 今後の拡張性を意識したシステムアーキテクチャ設計

---

## リファレンス

* [Google Gemini API Docs](https://ai.google.dev/docs)
* [Next.js Documentation](https://nextjs.org/docs)
* [Firebase Realtime Database](https://firebase.google.com/docs/database)
* [LangChain.js](https://js.langchain.com)

---

## 📩 Author

**GeN403**
GitHub: [https://github.com/GeN403](https://github.com/GeN403)

---
This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).


## 更新履歴
- 2025-10: プロジェクト構成をリファクタリングし、フロントエンドとバックエンドを明確に分離。
  - `frontend/` : Next.js + TypeScript
  - `backend/` : Python + Gemini API
  - `docs/` : 開発ドキュメント・仕様書
