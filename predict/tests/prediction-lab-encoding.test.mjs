import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { TextDecoder } from "node:util";

const INDEX_URL = new URL("../index.html", import.meta.url);
const MOJIBAKE_MARKERS = Object.freeze([
  "\uFFFD",
  "鬯",
  "郢",
  "驛",
  "髫",
  "鬩",
  "繝",
]);

async function readIndexBytes() {
  return readFile(INDEX_URL);
}

async function readIndexHtml() {
  const bytes = await readIndexBytes();

  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}

function occurrenceCount(html, pattern) {
  return (html.match(pattern) ?? []).length;
}

test("Prediction Lab index is strict UTF-8 without mojibake markers", async () => {
  const html = await readIndexHtml();

  assert.match(html, /<meta charset="UTF-8"\s*\/>/);
  assert.match(html, /<html lang="ja">/);

  for (const marker of MOJIBAKE_MARKERS) {
    assert.equal(
      html.includes(marker),
      false,
      `index.html contains mojibake marker: ${marker}`,
    );
  }
});

test("Prediction Lab keeps its required Japanese interface labels", async () => {
  const html = await readIndexHtml();
  const requiredLabels = [
    "銘柄を探す",
    "AI成績",
    "銘柄コード",
    "分析を実行",
    "リアルタイム株価",
    "現在価格",
    "総合スコア",
    "この評価について",
  ];

  for (const label of requiredLabels) {
    assert.equal(
      html.includes(label),
      true,
      `index.html is missing interface label: ${label}`,
    );
  }
});

test("Prediction Lab structural tags remain balanced", async () => {
  const html = await readIndexHtml();

  for (const tag of [
    "div",
    "section",
    "article",
    "p",
    "span",
    "strong",
    "button",
  ]) {
    const openingCount = occurrenceCount(
      html,
      new RegExp(`<${tag}(?:\\s|>)`, "gi"),
    );
    const closingCount = occurrenceCount(
      html,
      new RegExp(`</${tag}>`, "gi"),
    );

    assert.equal(
      openingCount,
      closingCount,
      `${tag} tags must be balanced`,
    );
  }
});

test("Prediction Lab retains each required module entry exactly once", async () => {
  const html = await readIndexHtml();
  const moduleEntries = [
    "script.js",
    "./analysis/prediction-lab-entry.js",
    "./analysis/ai-analysis-entry.js",
  ];

  for (const source of moduleEntries) {
    assert.equal(
      html.split(`src="${source}"`).length - 1,
      1,
      `${source} must be loaded exactly once`,
    );
  }
});
