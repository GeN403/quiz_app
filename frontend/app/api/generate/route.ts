// app/api/generate/route.ts

import { NextResponse } from "next/server";
// Google AI SDKをインポート
import { GoogleGenerativeAI } from "@google/generative-ai";
import * as cheerio from "cheerio";

// APIキーを使ってGoogle AIクライアントを初期化
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || "");

export async function POST(req: Request) {
  try {
    const { url } = await req.json(); // フロントからURLを受け取る

    // 1. URLからHTMLを取得（以前と同じ）
    const response = await fetch(url);
    const html = await response.text();

    // 2. Cheerioでテキストを抽出（以前と同じ）
    const $ = cheerio.load(html);
    $("script, style, nav, footer, header").remove();
    const mainText = $("body").text().replace(/\s\s+/g, " ").trim();
    const shortText = mainText.slice(0, 8000); // Geminiはより多くのテキストを扱えます

    // 3. Gemini APIを呼び出す
    const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash-lite" });

    const prompt = `以下の文章を基に、面白いクイズを1つだけ生成してください。:\n\n${shortText}`;

    const result = await model.generateContent(prompt);
    const geminiResponse = await result.response;
    const quiz = geminiResponse.text();

    // 生成されたクイズをフロントに返す
    return NextResponse.json({ result: quiz });

  } catch (error) {
    console.error(error); // サーバー側で実際のエラーを記録
    return NextResponse.json(
      { error: "クイズの生成に失敗しました。" },
      { status: 500 }
    );
  }
}