import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  findDataFiles,
  loadRows,
  parseArgs,
  parseCsv,
} from "../../tools/run_phase40_backtest.mjs";

test("parseArgs reads named options", () => {
  assert.deepEqual(
    parseArgs(["--data-dir", "data/prices", "--concurrency", "4", "--retry-failed"]),
    {
      "data-dir": "data/prices",
      concurrency: "4",
      "retry-failed": true,
    },
  );
});

test("parseCsv supports quoted commas", () => {
  const rows = parseCsv('Date,Open,Note\n2026-01-05,100,"hello, world"\n');
  assert.equal(rows.length, 1);
  assert.equal(rows[0].Date, "2026-01-05");
  assert.equal(rows[0].Note, "hello, world");
});

test("findDataFiles filters csv/json by requested symbols", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ark-phase40-cli-"));
  await Promise.all([
    fs.writeFile(path.join(directory, "7203.T.csv"), "Date,Open\n2026-01-05,100\n"),
    fs.writeFile(path.join(directory, "6758.T.json"), "[]"),
    fs.writeFile(path.join(directory, "ignore.txt"), "ignore"),
  ]);
  const files = await findDataFiles(directory, ["7203.T"]);
  assert.deepEqual(files.map((filePath) => path.basename(filePath)), ["7203.T.csv"]);
});

test("loadRows reads json arrays and csv rows", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ark-phase40-loader-"));
  const csvPath = path.join(directory, "7203.T.csv");
  const jsonPath = path.join(directory, "6758.T.json");
  await fs.writeFile(csvPath, "Date,Open\n2026-01-05,100\n");
  await fs.writeFile(jsonPath, JSON.stringify([{ date: "2026-01-05", open: 200 }]));
  assert.equal((await loadRows(csvPath))[0].Open, "100");
  assert.equal((await loadRows(jsonPath))[0].open, 200);
});

test("CLI source is locked to historical-only safety", async () => {
  const source = await fs.readFile(new URL("../../tools/run_phase40_backtest.mjs", import.meta.url), "utf8");
  for (const flag of [
    "brokerWriteAllowed: false",
    "liveTradingAllowed: false",
    "orderCreationAllowed: false",
    "orderTransmissionAllowed: false",
    "orderCancellationAllowed: false",
    "orderModificationAllowed: false",
    "excelOrderWriteAllowed: false",
    "orderTriggerWriteAllowed: false",
    "automaticPromotionAllowed: false",
    "productionUpdateAllowed: false",
  ]) {
    assert.match(source, new RegExp(flag.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});
