import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../../", import.meta.url);

async function read(relativePath) {
  return readFile(new URL(relativePath, root), "utf8");
}

test("Discovery画面にスクリプトが利用する要素が揃っている", async () => {
  const html = await read("discovery/index.html");
  const requiredIds = [
    "queryFilter",
    "priceFilter",
    "budgetFilter",
    "marketFilter",
    "themeFilter",
    "marketCapFilter",
    "volumeFilter",
    "scoreFilter",
    "confidenceFilter",
    "riskFilter",
    "sortFilter",
    "watchlistOnly",
    "resetFilters",
    "refreshButton",
    "coverageCount",
    "resultCount",
    "blockedCount",
    "coverageBar",
    "coverageDescription",
    "refreshCycleCount",
    "refreshCycleBar",
    "refreshCycleDescription",
    "updatedAt",
    "rankingBody",
    "dataStatus",
    "scanStatus",
    "alertEnabled",
    "alertScore",
    "alertConfidence",
    "alertWatchlistOnly",
    "saveAlertButton",
    "notificationButton",
    "alertStatus",
  ];

  requiredIds.forEach((id) => {
    assert.match(html, new RegExp(`id="${id}"`), `${id} がありません。`);
  });
});

test("スターター銘柄一覧は重複せず必要なメタデータを持つ", async () => {
  const payload = JSON.parse(await read("data/screener-universe.json"));
  const symbols = payload.entries.map((entry) => entry.symbol);

  assert.ok(payload.entries.length >= 20);
  assert.equal(new Set(symbols).size, symbols.length);

  payload.entries.forEach((entry) => {
    assert.match(entry.symbol, /^(?:\d{4}|\d{3}[A-Z])\.T$/);
    assert.ok(entry.name);
    assert.ok(["プライム", "スタンダード", "グロース"].includes(entry.market));
    assert.ok(entry.sector);
    assert.ok(Array.isArray(entry.themes));
    assert.ok(Number(entry.lotSize) > 0);
  });
});

test("HomeとPrediction LabからDiscoveryへ移動できる", async () => {
  const [home, prediction] = await Promise.all([
    read("index.html"),
    read("predict/index.html"),
  ]);

  assert.match(home, /discovery\/index\.html/);
  assert.match(prediction, /\.\.\/discovery\/index\.html/);
});

test("定期更新はデータ専用ブランチへ公開しmainへ直接pushしない", async () => {
  const workflow = await read(".github/workflows/update-screener.yml");

  assert.match(workflow, /automation\/screener-data/);
  assert.match(workflow, /screener-progress\.json/);
  assert.match(workflow, /SCREENER_BATCH_SIZE/);
  assert.match(workflow, /git push --force-with-lease origin/);
  assert.doesNotMatch(workflow, /gh pr create/);
  assert.doesNotMatch(workflow, /git push origin main/);
});

test("Discoveryは最新データを統合Vercel API経由で自動取得する", async () => {
  const [config, router, implementation] = await Promise.all([
    read("discovery/config.js"),
    read("api/screener.js"),
    read("server/screener-data.js"),
  ]);

  assert.match(config, /api\/screener\?mode=data&type=universe/);
  assert.match(config, /api\/screener\?mode=data&type=snapshot/);
  assert.match(router, /ScreenerDataApiInternals/);
  assert.match(router, /screenerDataHandler/);
  assert.match(implementation, /automation\/screener-data/);
  assert.match(implementation, /stale-while-revalidate/);
});

test("ローカル開発ではService Workerが古いJSを返さない", async () => {
  const serviceWorker = await read("service-worker.js");

  assert.match(serviceWorker, /ark-terminal-v\d+/);
  assert.match(serviceWorker, /isLocalDevelopment/);
  assert.match(serviceWorker, /event\.respondWith\(fetch\(request\)\)/);
});