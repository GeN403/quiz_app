# Quiz App

カテゴリ・URL・キーワードからクイズを生成し、回答判定、保存、クイズセット作成までできるアプリです。

## 主な機能
- クイズ生成（カテゴリ / URL / キーワード）
- 回答判定、解説表示、回答履歴
- 生成結果の保存（Saved Quizzes）
- 保存済みクイズ一覧・詳細・削除
- クイズセット作成・一覧・詳細・削除

## 必要環境
- Docker Desktop（Windows は WSL2 backend 推奨）
- または以下のローカル実行環境
  - Node.js 20+
  - Python 3.11+
- Gemini API キー

## 初期設定
### 1. backend の環境変数
`backend/.env.example` を `backend/.env` にコピーして、`GEMINI_API_KEY` を設定してください。

```powershell
cd backend
Copy-Item .env.example .env
# .env を開いて GEMINI_API_KEY を設定
cd ..
```

---

## 推奨起動方法（Docker）

### 1. Docker 基盤の事前確認（Windows + PowerShell）
```powershell
docker version
docker info
docker context ls
docker context show
docker compose version
Get-Service *docker*
wsl -l -v
```

正常目安:
- `docker version` で `Server` が表示される
- `docker context show` が `desktop-linux`
- `docker-desktop` (WSL) が利用可能

### 2. 起動
```powershell
docker compose up -d --build
```

### 3. 動作確認
- Frontend: http://localhost:3000
- Backend Docs: http://localhost:8000/docs

```powershell
docker compose ps
docker compose logs -f
```

### 4. 停止
```powershell
docker compose down
```

### 5. コンテナ/volume を含めて初期化
```powershell
docker compose down -v
```

---

## Docker トラブルシューティング

### A. `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`
Docker daemon 接続前で失敗しています（compose や Dockerfile の問題ではありません）。

復旧優先順:
1. Docker Desktop 起動確認
2. Linux Containers モード確認
3. `docker context use desktop-linux`
4. `wsl --shutdown` 実行後に Docker Desktop 再起動
5. Windows 再起動

### B. `Module not found: Can't resolve '@radix-ui/react-tabs'`（Docker実行時）
古い `node_modules` volume が残っている可能性があります。

```powershell
docker compose down -v
docker compose build --no-cache frontend
docker compose up -d frontend
```

---

## ローカル起動方法（Dockerを使わない場合）

### 1. Backend
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend
```powershell
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:3000
- Backend Docs: http://localhost:8000/docs

必要に応じて `frontend/.env.local` を作成:
```env
BACKEND_INTERNAL_URL=http://127.0.0.1:8000
```

注意:
- Next.js は `frontend` ディレクトリで実行してください（ルートで `npm run dev` しない）。

---

## Latest UI Updates
- Added top navigation links on Home:
  - `Saved Quizzes`
  - `Quiz Sets`
  - `Local Battle`
- Added `SaveButton` in the quiz display area
- Added local battle navigation in quiz set pages:
  - `/quiz-sets`: `Local Battle` button
  - `/quiz-sets/[id]`: `Battle with this Set` button

### Save to Battle Flow
1. Generate a quiz on Home
2. Save with `SaveButton`
3. Confirm in `Saved Quizzes`
4. Create a set in `Quiz Sets`
5. Start local battle from one of these paths:
   - Home `Local Battle`
   - `Quiz Sets` `Local Battle`
   - `Quiz Set Detail` `Battle with this Set`

Notes:
- Save is enabled only when the generated result has `package_id`
- From quiz set detail, `setId` query is passed and auto-selection runs in `/local-battle`

---

## ディレクトリ（主要）
- `frontend/` : Next.js アプリ
- `backend/` : FastAPI アプリ
- `docker-compose.yml` : 開発用 compose 設定
