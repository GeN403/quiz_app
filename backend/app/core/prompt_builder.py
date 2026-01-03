"""
プロンプト生成ロジック
"""

from typing import List


# 制約条件を独立した変数として定義
CONSTRAINT_RULES = """
・必ず「問題文」「正解」「別解/正誤判定基準」「解説」の要素を含めてください。
・出力はJSON形式で、以下のキーを持つオブジェクトとしてください: "question", "answer", "Alternative Solutions/Correctness Judgment Criteria", "explanation"
・sourceについては後述の指示に従ってください。
・問題の後半で問題の答えを一意に絞れるような情報を盛り込んでください。
・日本語での呼び方と外来語としての呼び方の両方が存在する場合、別解として「別解/正誤判定基準」欄にその旨を記載するか、どちらか一方に限定できる問題文に改めてください。
・文末は「～でしょう？」としてください。
・問題文は1文で作成してください。
・「日本で一番高い山は富士山ですが、世界で一番高い山は何でしょう？」のような前半と後半が対照的な問題（パラレル問題）は「～ですが、～」とする。
・パラレル問題では対照的なキーワードを**強調**してください。
・体言止めは避けてください。
・作品名は『』（2重鍵かっこ）で囲んでください。
・問題文は80文字以内にしてください。
・漢字検定2級程度の語彙には後ろから()でルビを追加してください。
・最初は広い情報から入り、徐々に狭い情報に絞ってください。
・前半に知名度が低い情報、後半に知名度が高い情報を配置してください。
"""


def build_prompt_url_mode(category_name: str, url: str, title: str, text_excerpt: str, quotes: List[str], question_count: int) -> str:
    """
    URLモード用のプロンプトを生成

    重要: LLMには「URLとquoteを選ぶ」責任を与えない。
           サーバが決めたURL・quote候補のみを使わせる。
    """
    if question_count == 1:
        output_format = """
# 出力形式
・あなたの応答は、解説や挨拶を一切含んではいけません。
・あなたの応答は、**厳密なJSON形式のオブジェクト**である必要があります。
・JSONのキーは必ずダブルクオート（"）で囲んでください。シングルクオート（'）は使用禁止です。
・JSONの最後の要素の後にカンマ（,）を付けないでください。
・形式: {"question": "...", "answer": "...", "Alternative Solutions/Correctness Judgment Criteria": "...", "explanation": "...", "source": {"title": "...", "url": "...", "quote": "..."}}
"""
    else:
        output_format = f"""
# 出力形式
・あなたの応答は、解説や挨拶を一切含んではいけません。
・あなたの応答は、**{question_count}問のクイズを含むJSON配列**である必要があります。
・JSONのキーは必ずダブルクオート（"）で囲んでください。シングルクオート（'）は使用禁止です。
・JSONの最後の要素の後にカンマ（,）を付けないでください。
・形式: [{{"question": "...", "answer": "...", ...}}, {{"question": "...", "answer": "...", ...}}]
"""

    # quote候補をリスト化
    quote_list = "\n".join([f"  {i+1}. {q[:100]}..." for i, q in enumerate(quotes[:5])])

    prompt = f"""
# 役割
あなたはプロのクイズ作家であり、厳密なJSONの専門家です。

# タスク
以下のURL本文**のみ**を根拠に、競技クイズで使えるような本格的なクイズを作成してください。

# 制約条件
{CONSTRAINT_RULES}

# 参照元（サーバ指定・変更禁止）
・URL: {url}
・タイトル: {title}
・カテゴリ: {category_name}

# ページ本文（抜粋）
```
{text_excerpt[:3000]}
```

# source フィールドの指示（重要）
・"source" は以下の形式で出力してください：
  {{"title": "{title}", "url": "{url}", "quote": "..."}}
・"source"."url" は必ず上記のURL（{url}）をそのままコピーしてください。**絶対に変更・捏造しないでください**。
・"source"."title" は必ず上記のタイトル（{title}）をそのままコピーしてください。
・"source"."quote" には、上記ページ本文から引用した**実際に存在する文章**を30〜150文字程度で設定してください。
・**重要**: "quote"は、上記「ページ本文（抜粋）」に**完全一致する部分文字列**でなければなりません。存在しない文章を作らないでください。
・以下の候補から選ぶか、本文中の別の部分を使用してください：
{quote_list}

{output_format}

# 最重要ルール
・あなたの応答は、**厳密なJSON RFC 8259準拠**である必要があります。
・キーは必ずダブルクオート（"）で囲む。
・文字列値も必ずダブルクオート（"）で囲む。
・末尾カンマ禁止。
・制御文字禁止。
"""
    return prompt


def build_prompt_category_mode(category_name: str, question_count: int) -> str:
    """
    カテゴリモード用のプロンプトを生成

    カテゴリモードでは、LLMに参照元URLを選ばせる（既存の動作を維持）
    """
    if question_count == 1:
        output_format = """
# 出力形式
・あなたの応答は、解説や挨拶を一切含んではいけません。
・あなたの応答は、**厳密なJSON形式のオブジェクト**である必要があります。
・形式: {"question": "...", "answer": "...", "Alternative Solutions/Correctness Judgment Criteria": "...", "explanation": "...", "source": {"title": "...", "url": "...", "quote": ""}}
"""
    else:
        output_format = f"""
# 出力形式
・あなたの応答は、解説や挨拶を一切含んではいけません。
・あなたの応答は、**{question_count}問のクイズを含むJSON配列**である必要があります。
・形式: [{{"question": "...", "answer": "...", ...}}, {{"question": "...", "answer": "...", ...}}]
"""

    prompt = f"""
# 役割
あなたはプロのクイズ作家であり、厳密なJSONの専門家です。

# タスク
「{category_name}」のカテゴリで、競技クイズで使えるような本格的なクイズを作成してください。

# 制約条件
{CONSTRAINT_RULES}

# source フィールドの指示
・"source" は以下の形式で出力してください：
  {{"title": "トピック名", "url": "参照URL", "quote": ""}}
・"source"."url" には、必ずコトバンク（https://kotobank.jp）または公式サイト（*.go.jp、*.ac.jp）のURLを使用してください。
・ブログ、まとめサイト、SNS、Q&Aサイトは使用禁止です。
・適切なURLが見つからない場合は、"url"に「参照URLを提示できません」と記載してください。
・"quote" はカテゴリモードでは空文字列（""）で構いません。

{output_format}

# 最重要ルール
・あなたの応答は、**厳密なJSON RFC 8259準拠**である必要があります。
・キーは必ずダブルクオート（"）で囲む。
・文字列値も必ずダブルクオート（"）で囲む。
・末尾カンマ禁止。
"""
    return prompt
