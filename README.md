## プロジェクト概要
AI（Gemini API）を活用し、クイズ問題を自動生成・出題するWebアプリ。  
将来的に **Web / iOS / Android** で動作し、リアルタイム対戦や学習最適化を行う統合型クイズプラットフォームを目指しています。

---

## 使用技術一覧

| Layer | Technology | Purpose |
|-------|-------------|----------|
| **Frontend** | Next.js / TypeScript / Chakra UI | Web UI構築、SSR対応 |
| **Backend** | Next.js API Routes (TypeScript) | LLM呼び出し・レスポンス処理 |
| **AI Layer** | Python + Gemini API | 問題生成・LLMプロンプト実験 |
| **Database** | (予定) Firebase / Supabase | ユーザー・スコア・リアルタイム同期 |
| **Future Infra** | (予定) FastAPI / Docker / React Native | 拡張・モバイル化対応 |

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
├── frontend/ # Next.js + TypeScript
│ ├── app/
│ ├── public/
│ ├── types/
│ ├── package.json
│ └── tsconfig.json
│
├── backend/ # Python + Gemini API連携
│ ├── main.py
│ ├── requirements.txt
│ ├── .env
│ └── notebooks/ # LLM検証用ノート
│ ├── prompt_test.ipynb
│ └── report.md
│
├── docs/ # メモ・仕様書
│ ├── memo.txt
│ └── architecture.md
│
├── .gitignore
├── LICENSE
├── README.md
└── docker-compose.yml
```

---

## 準備

```bash
# フロントエンドセットアップ
npm install
npm run dev

# AI Layer setup
cd ai
pip install -r requirements.txt
python prompt_test.py
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

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## 更新履歴
- 2025-10: プロジェクト構成をリファクタリングし、フロントエンドとバックエンドを明確に分離。
  - `frontend/` : Next.js + TypeScript
  - `backend/` : Python + Gemini API
  - `docs/` : 開発ドキュメント・仕様書
