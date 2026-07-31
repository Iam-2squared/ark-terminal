import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pages = new Map([
  ["index.html", "mobile.css"],
  ["tasks/index.html", "../mobile.css"],
  ["stocks/index.html", "../mobile.css"],
  ["stocks/detail/index.html", "../../mobile.css"],
  ["news/index.html", "../mobile.css"],
  ["predict/index.html", "../mobile.css"],
  ["predict/performance.html", "../mobile.css"],
  ["discovery/index.html", "../mobile.css"],
]);

test("主要ページが共通スマホCSSを最後に読み込む", async () => {
  for (const [path, mobilePath] of pages) {
    const html = await readFile(new URL(`../${path}`, import.meta.url), "utf8");
    const mobileIndex = html.indexOf(`href="${mobilePath}"`);
    const stylesheetIndexes = [...html.matchAll(/rel="stylesheet"/g)].map(
      (match) => match.index,
    );

    assert.notEqual(mobileIndex, -1, `${path} に ${mobilePath} が必要です`);
    assert.ok(
      mobileIndex > Math.max(...stylesheetIndexes.slice(0, -1)),
      `${path} は mobile.css を最後に読み込む必要があります`,
    );
  }
});

test("スマホCSSが横はみ出し・タップ領域・表・チャートを補正する", async () => {
  const css = await readFile(new URL("../mobile.css", import.meta.url), "utf8");

  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /overflow-x: hidden/);
  assert.match(css, /min-height: 44px/);
  assert.match(css, /\.tableContainer/);
  assert.match(css, /\.tradingviewChart/);
  assert.doesNotMatch(
    css,
    /content-visibility: auto/,
    "ランキング行を画面外判定で空白にしない",
  );
});

test("Service Workerが新しいスマホCSSをキャッシュする", async () => {
  const worker = await readFile(
    new URL("../service-worker.js", import.meta.url),
    "utf8",
  );

  assert.match(worker, /ark-terminal-v6/);
  assert.match(worker, /"\.\/mobile\.css"/);
});
