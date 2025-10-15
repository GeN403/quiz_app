# Gemini APIを用いたクイズ問題作成
(1) プロンプトやモデルを変えることで、LLMから返ってくる出力が意図するものになるよう工夫することができる。今回、作成に厳しい制約がある競技クイズの問題を作成させるタスクを題材に様々な方法で推論に工夫を行った。  
(2) 本検証はローカル環境で実験を行うため、まず、デスクトップで実験のためのフォルダー(prompt-lab)を作成した。さらに、venvという名前の仮想環境を作り、仮想環境を有効にした。さらにGemini APIをたたくためのライブラリとAPIキーを安全に管理するためのライブラリ、のちに使うWebスクレイピングを行うライブラリをインストールしました。Geminiにテンプレートを作らせ、各ファイルを以下のように編集した。

```
pip install google-generativeai python-dotenv
pip install requests beautifulsoup4
```
さらに、prompt-lab直下に.envとmain.pyを作成した。

```
# .env
GEMINI_API_KEY=ここにコピーしたGeminiのAPIキーを貼り付ける
```

```Python
# main.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# APIキーを設定
genai.configure(api_key=api_key)

# ----------------------------------------------------
# ↓↓↓ ここから下を書き換えて実験する ↓↓↓
# ----------------------------------------------------

# 使用するモデルを選択
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# クイズの生成元となる文章
source_text = """
日本で最も高い山は富士山であり、その標高は3,776メートルである。
静岡県と山梨県にまたがる活火山であり、美しい円錐状の形から日本の象徴として広く知られている。
2013年には、関連する文化財群とともに「富士山-信仰の対象と芸術の源泉」として世界文化遺産に登録された。
"""

# AIへの指示（プロンプト）
# ここを色々書き換えて、出力がどう変わるか試してみましょう！
prompt = f"""
あなたはプロのクイズ作家です。
以下の文章を基にして、競技クイズで使えるような本格的な4択クイズを1問作成してください。

【制約条件】
・必ず「問題文」「正解の選択肢」「不正解の選択肢3つ」「解説」の要素を含めてください。
・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "options", "answer", "explanation"
・optionsは4つの選択肢を含む配列にしてください。

【文章】
{source_text}
"""

# ----------------------------------------------------
# ↑↑↑ ここまでを書き換えて実験する ↑↑↑
# ----------------------------------------------------


# Gemini APIを呼び出し
print("🤖 AIにクイズを生成させています...")
response = model.generate_content(prompt)
print("✅ 生成が完了しました！")
print("--- 出力結果 ---")
print(response.text)
```
Gemini API Keyの取得が必要だったので、Google AI Studioにクレジットカードを紐づけ済みのGoogleアカウントでログインし、Create API key in new projectからAPI Keyを取得しました。  
まず、素直に`gemini-flash-1.5-latest`は現在利用できなくなっているので`model = genai.get_generative_model('gemini-1.5-flash-latest')`を`model = genai.get_generative_model('gemini-2.0-flash')`にモデルを変更し、そのまま実行しました。

```
(venv) PS C:\Users\PC_User\Desktop\prompt-lab> python main.py
🤖 AIにクイズを生成させています...
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
E0000 00:00:1760403570.495688   32908 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
✅ 生成が完了しました！
--- 出力結果 ---
{
  "question": "2013年に世界文化遺産に登録された富士山ですが、文化遺産として の登録名は何でしょう？",
  "options": [
    "富士山-自然の驚異",
    "富士山-信仰の対象と芸術の源泉",
    "富士山-日本の魂",
    "富士山-活火山の象徴"
  ],
  "answer": "富士山-信仰の対象と芸術の源泉",
  "explanation": "富士山は2013年に「富士山-信仰の対象と芸術の源泉」として世 界文化遺産に登録されました。これは、富士山が古来より信仰の対象であり、また多くの芸術作品の源泉となってきた文化的価値を評価されたものです。"
}
```



次に、問題の形式を競技クイズに寄せるため、ABC（有名なクイズ大会）の「abc/EQIDEN クイズ問題作成の手引き」を参考に制約条件を変更しました。

```Python
# 使用するモデルを選択
model = genai.GenerativeModel('gemini-2.0-flash')

# クイズの生成元となる文章
source_text = """
日本で最も高い山は富士山であり、その標高は3,776メートルである。
静岡県と山梨県にまたがる活火山であり、美しい円錐状の形から日本の象徴として広く知られている。
2013年には、関連する文化財群とともに「富士山-信仰の対象と芸術の源泉」として世界文化遺産に登録された。
"""

# AIへの指示（プロンプト）
# ここを色々書き換えて、出力がどう変わるか試してみましょう！
prompt = f"""
# 役割
あなたはプロのクイズ作家です。

# タスク
以下の文章を基にして、競技クイズで使えるような本格的なクイズを1問作成してください。

# 制約条件
・必ず「問題文」「正解」「別解/正誤判定基準」「解説」「出典」の要素を含めてください。
・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "answer", "Alternative Solutions/Correctness Judgment Criteria", "explanation","source"
・"source"にはウェブページタイトルとURLを含めてください。
・問題の答えを一意に絞れるような情報を盛り込んでください。
・日本語での呼び方と外来語としての呼び方の両方が存在する場合、別解として「別解/正誤判定基準」欄にその旨を記載するか、どちらか一方に限定できる問題文に改めてください。
・文末は「～でしょう？」としてください。
・「日本で一番高い山は富士山ですが、世界で一番高い山は何でしょう？」のような前半と後半が対照的な問題（パラレル問題）は「～ですが、～」とする。
・体言止めは避けてください。
・作品名は『』（2重鍵かっこ）で囲んでください。
・問題文は60文字以内にしてください。

【文章】
{source_text}
"""
```

```
(venv) PS C:\Users\PC_User\Desktop\prompt-lab> python main.py
🤖 AIにクイズを生成させています...
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
E0000 00:00:1760407171.227077   30684 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
✅ 生成が完了しました！
--- 出力結果 ---
```json
{
  "question": "『霊峰の象徴』日本最高峰であり、静岡県と山梨県に跨る活火山は何でしょう？",
  "answer": "富士山",
  "Alternative Solutions/Correctness Judgment Criteria": "不採用",
  "explanation": "富士山は標高3,776mを誇る日本最高峰の山であり、美しい円錐形の形状から日本の象徴として広く知られています。2013年には世界文化遺産に登録されました。",
  "source": {
    "title": "富士山 - Wikipedia",
    "url": "https://ja.wikipedia.org/wiki/%E5%AF%8C%E5%A3%AB%E5%B1%B1"
  }
}
```
『霊峰の象徴』というように作品名でないものを『』で囲ってしまっている。Wikipediaではだれでも編集することができてしまい情報の信憑性が担保できない。後半については、対策として、利用するウェブページを指定した。
```Python
# main.py
import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# APIキーを設定
genai.configure(api_key=api_key)

# ----------------------------------------------------
# ↓↓↓ ここから下を書き換えて実験する ↓↓↓
# ----------------------------------------------------

# 使用するモデルを選択
model = genai.GenerativeModel('gemini-2.0-flash') # もしくは 'gemini-pro'

# クイズの生成元となるページのURL
target_url = "https://kotobank.jp/word/%E9%A2%A8%E7%AB%8B%E3%81%A1%E3%81%AC-44764#:~:text=%E3%81%8B%E3%81%9C%E3%81%9F%E3%81%A1%E3%81%AC%E3%80%90%E9%A2%A8%E7%AB%8B%E3%81%A1%E3%81%AC%E3%80%91,-%E5%B0%8F%E8%AA%AC%E3%80%82&text=%E5%A0%80%E8%BE%B0%E9%9B%84%E4%BD%9C%E3%80%82,%E8%A9%A9%E5%8F%A5%E3%81%8B%E3%82%89%E3%81%A8%E3%81%A3%E3%81%9F%E3%82%82%E3%81%AE%E3%80%82" # ← ここを好きなURLに変えて試す

# AIへの指示（プロンプト）
# ここを色々書き換えて、出力がどう変わるか試してみましょう！
prompt_template = """
# 役割
あなたはプロのクイズ作家です。

# タスク
以下の文章を基にして、競技クイズで使えるような本格的なクイズを1問作成してください。

# 制約条件
・必ず「問題文」「正解」「別解/正誤判定基準」「解説」「出典」の要素を含めてください。
・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "answer", "Alternative Solutions/Correctness Judgment Criteria", "explanation","source"
・"source"にはウェブページタイトルとURLを含めてください。
・問題の公判で問題の答えを一意に絞れるような情報を盛り込んでください。
・日本語での呼び方と外来語としての呼び方の両方が存在する場合、別解として「別解/正誤判定基準」欄にその旨を記載するか、どちらか一方に限定できる問題文に改めてください。
・文末は「～でしょう？」としてください。
・「日本で一番高い山は富士山ですが、世界で一番高い山は何でしょう？」のような前半と後半が対照的な問題（パラレル問題）は「～ですが、～」とする。
・パラレル問題では対照的なキーワードを**強調**してください。
・体言止めは避けてください。
・作品名は『』（2重鍵かっこ）で囲んでください。
・問題文は80文字以内にしてください。
・漢字検定2級以上の語彙には後ろから()でルビを追加してください。
・最初は広い情報から入り、徐々に狭い情報に絞ってください。
・前半に知名度が低い情報、後半に知名度が高い情報を配置してください。

【文章】
{source_text}
"""

# ----------------------------------------------------
# ↑↑↑ ここまでを書き換えて実験する ↑↑↑
# ----------------------------------------------------

def get_text_from_url(url):
    """URLから本文テキストを抽出する関数"""
    try:
        print(f"📄 '{url}' から本文を取得中...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # エラーがあれば例外を発生させる
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 不要なタグ（スクリプト、スタイルシート、ヘッダー、フッターなど）を削除
        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()
        
        # 本文テキストを取得し、余分な空白を整理
        body_text = soup.get_text(separator='\n', strip=True)
        print("✅ 本文の取得完了！")
        return body_text
    except requests.RequestException as e:
        print(f"❌ URLの取得に失敗しました: {e}")
        return None

# --- メインの処理 ---
# 1. URLから本文を取得
source_text = get_text_from_url(target_url)

if source_text:
    # 2. プロンプトを組み立て
    full_prompt = prompt_template.format(source_text=source_text)

    # 3. Gemini APIを呼び出し
    print("🤖 AIにクイズを生成させています...")
    response = model.generate_content(full_prompt)
    print("✅ 生成が完了しました！")
    print("--- 出力結果 ---")
    print(response.text)
```
```
{
  "question": "堀辰雄(ホリタツオ)の小説で、**婚約者**との生活を通して生の**意味**と幸福感を確立する過程を描き、フランスの詩人バレリーの詩句 から書名をとった作品は何でしょう？",
  "answer": "風立ちぬ",
  "Alternative Solutions/Correctness Judgment Criteria": "カゼタチヌ",
  "explanation": "『風立ちぬ』は堀辰雄の小説で、作者自身の体験を基に、死に直面した状況下での生の意味を追求した作品です。タイトルの由来は、フランスの詩人ポール・ヴァレリーの詩の一節「Le vent se lève!…Il faut tenter de vivre!（風立ちぬ、いざ生きめやも）」から取られています。",
  "source": {
    "ウェブページタイトル": "風立ちぬ(カゼタチヌ)とは？ 意味や使い方 - コトバンク",
    "URL": "https://kotobank.jp/word/%E9%A2%A8%E7%AB%8B%E3%81%A1%E3%81%AC-487863"
  }
}
```
太字の部分が適切ではありません。制約条件が適切に守られていないというところが課題になりました。Self-Refineの仕組みを取り込み、制約条件が適用できているか評価とともに評価させます。
```python

```