# main.py
import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv
import json

# .envファイルから環境変数を読み込む
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# APIキーを設定
genai.configure(api_key=api_key)

# ----------------------------------------------------
# ↓↓↓ プロンプトとルールの定義 ↓↓↓
# ----------------------------------------------------

# 使用するモデルを選択（実際に利用可能なモデル名にしてください）
model = genai.GenerativeModel('gemini-2.0-flash')

# クイズの生成元となるページのURL
target_url = "https://kotobank.jp/word/%E9%A2%A8%E7%AB%8B%E3%81%A1%E3%81%AC-44764"

# 制約条件を独立した変数として定義（再利用するため）
CONSTRAINT_RULES = """
・必ず「問題文」「正解」「別解/正誤判定基準」「解説」「出典」の要素を含めてください。
・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "answer", "Alternative Solutions/Correctness Judgment Criteria", "explanation","source"
・"source"にはウェブページタイトルとURLを含めてください。
・問題の後半で問題の答えを一意に絞れるような情報を盛り込んでください。
・日本語での呼び方と外来語としての呼び方の両方が存在する場合、別解として「別解/正誤判定基準」欄にその旨を記載するか、どちらか一方に限定できる問題文に改めてください。
・文末は「～でしょう？」としてください。
・「日本で一番高い山は富士山ですが、世界で一番高い山は何でしょう？」のような前半と後半が対照的な問題（パラレル問題）は「～ですが、～」とする。
・パラレル問題では対照的なキーワードを**強調**してください。
・体言止めは避けてください。
・作品名は『』（2重鍵かっこ）で囲んでください。
・問題文は80文字以内にしてください。
・漢字検定2級程度の語彙には後ろから()でルビを追加してください。
・最初は広い情報から入り、徐々に狭い情報に絞ってください。
・前半に知名度が低い情報、後半に知名度が高い情報を配置してください。
"""

# --- ① 生成フェーズ用のプロンプト ---
prompt_template_generate = f"""
# 役割
あなたはプロのクイズ作家です。

# タスク
以下の文章を基にして、競技クイズで使えるような本格的なクイズを1問作成してください。

# 制約条件
{CONSTRAINT_RULES}

# 文章
{{source_text}}
"""

# --- ② 自己評価・修正フェーズ用のプロンプト ---
prompt_template_refine = f"""
# 役割
あなたは、AIが生成したクイズを評価し、修正する品質保証の専門家です。

# タスク
AIが生成した以下の「生成物」が、「制約条件」を完全に満たしているか厳密にチェックしてください。
もし一つでも違反があれば、すべての違反箇所を修正し、制約条件を完全に満たした最終的なJSONオブジェクトのみを出力してください。
もし違反がなければ、元の「生成物」をそのまま出力してください。

# 制約条件
{CONSTRAINT_RULES}

# AIによる生成物
{{draft_quiz}}
"""

# ----------------------------------------------------
# ↑↑↑ プロンプトとルールの定義ここまで ↑↑↑
# ----------------------------------------------------

def get_web_info(url):
    """URLから本文テキストとタイトルを抽出する関数"""
    try:
        print(f"📄 '{url}' から情報を取得中...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # タイトルを取得
        title = soup.title.string if soup.title else "タイトル不明"
        
        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()
        
        body_text = soup.get_text(separator='\n', strip=True)
        print("✅ 情報の取得完了！")
        return body_text, title
    except requests.RequestException as e:
        print(f"❌ URLの取得に失敗しました: {e}")
        return None, None

# --- メインの処理 ---
# 1. URLから本文とタイトルを取得
source_text, source_title = get_web_info(target_url)

if source_text:
    # --- ① 生成フェーズ ---
    print("\n--- ① 生成フェーズ ---")
    prompt_generate = prompt_template_generate.format(source_text=source_text)
    print("🤖 AIにクイズの初稿を生成させています...")
    response_generate = model.generate_content(prompt_generate)
    first_draft_text = response_generate.text
    print("✅ 初稿が完成しました！")
    print(first_draft_text)

    # --- ② 自己評価・修正フェーズ ---
    print("\n--- ② 自己評価・修正フェーズ ---")
    prompt_refine = prompt_template_refine.format(draft_quiz=first_draft_text)
    print("🧐 AIが生成結果を自己評価し、必要なら修正します...")
    response_refine = model.generate_content(prompt_refine)
    
    # 最終的な出力を整形
    final_text = response_refine.text.strip().replace("```json\n", "").replace("\n```", "")
    
    print("✅ 最終版が完成しました！")
    print("\n--- 最終出力結果 ---")
    
    # JSONとしてきれいに整形して表示
    try:
        final_json = json.loads(final_text)
        print(json.dumps(final_json, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print("エラー: 最終出力が有効なJSONではありません。")
        print(final_text)