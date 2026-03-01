import assert from "node:assert/strict";
import test from "node:test";
import { buildGeneratePayload } from "./api";
import { validateGenerateOptionalFields } from "./generateOptions";

test("空値はpayloadからomitされる", () => {
  const payload = buildGeneratePayload({
    difficulty: "",
    length: "   ",
    genre: undefined,
    topic: null as unknown as string,
  });

  assert.deepEqual(payload, {});
});

test("有効値のみpayloadに含まれる", () => {
  const payload = buildGeneratePayload({
    difficulty: "easy",
    length: "medium",
    genre: "歴史",
    topic: "  富士山  ",
  });

  assert.deepEqual(payload, {
    difficulty: "easy",
    length: "medium",
    genre: "歴史",
    topic: "富士山",
  });
});

test("空白topicはomitされる", () => {
  const payload = buildGeneratePayload({
    topic: "   ",
  });

  assert.deepEqual(payload, {});
});

test("topicが長すぎるとエラーになる", () => {
  const tooLongTopic = "a".repeat(61);
  const result = validateGenerateOptionalFields({ topic: tooLongTopic });

  assert.equal(
    result.errors.topic,
    "トピックは60文字以内で入力してください。"
  );
});

test("topicに改行が含まれるとエラーになる", () => {
  const result = validateGenerateOptionalFields({ topic: "富士山\n高さ" });

  assert.equal(
    result.errors.topic,
    "トピックは改行せず1行で入力してください。"
  );
});
