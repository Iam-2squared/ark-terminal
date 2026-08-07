#!/usr/bin/env node
import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";
import { downloadHistoricalUniverse, DEFAULT_BENCHMARK_MAP } from "../predict/data/phase50-historical-downloader.js";
import { buildPhase45PersistencePlan } from "../predict/data/phase45-persistence.js";

function parseArgs(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    options[key] = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : "true";
  }
  return options;
}

async function readJsonIfExists(filePath) {
  try { return JSON.parse(await fs.readFile(filePath, "utf8")); }
  catch (error) { if (error?.code === "ENOENT") return null; throw error; }
}

async function atomicWriteJson(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.tmp-${process.pid}`;
  await fs.writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await fs.rename(temporary, filePath);
}

function buildInstruments(args) {
  const symbols = String(args.symbols || "7203.T").split(",").map((item) => item.trim()).filter(Boolean);
  const equities = symbols.map((symbol) => ({ symbol, outputSymbol: symbol, kind: "OHLCV", currency: "JPY" }));
  if (args["include-benchmarks"] !== "true") return equities;
  const benchmarks = Object.entries(DEFAULT_BENCHMARK_MAP).map(([outputSymbol, config]) => ({
    symbol: config.providerSymbol,
    outputSymbol,
    kind: config.kind,
    currency: config.currency,
  }));
  return [...equities, ...benchmarks];
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const end = args.end || new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  const start = args.start || "2020-01-01";
  const outputDir = path.resolve(args["output-dir"] || "data/data-lake");
  const rawPath = path.resolve(args["raw-output"] || "data/historical/downloaded.phase45.json");
  const instruments = buildInstruments(args);

  const downloaded = await downloadHistoricalUniverse({
    instruments,
    start,
    end,
    interval: args.interval || "1d",
    concurrency: Number(args.concurrency || 3),
  });
  await atomicWriteJson(rawPath, {
    status: downloaded.status,
    records: downloaded.records,
    warnings: downloaded.warnings,
    quarantined: downloaded.quarantined,
    safety: downloaded.safety,
  });

  const shardPath = path.join(outputDir, "shards", "latest.json");
  const existingShard = await readJsonIfExists(shardPath);
  const plan = buildPhase45PersistencePlan({ records: downloaded.records, provider: "YAHOO_CHART", existingShard });
  if (plan.status !== "READY_TO_PERSIST") {
    await atomicWriteJson(path.join(outputDir, "rejected.json"), {
      status: plan.status,
      blockers: plan.batch?.inspection?.blockers ?? [],
      warnings: plan.batch?.inspection?.warnings ?? [],
      ingestionRejected: plan.ingestionPlan?.rejected ?? [],
      integrity: plan.ingestionPlan?.integrity ?? null,
      safety: plan.safety,
    });
    throw new Error("PHASE50_DOWNLOADER_PIPELINE_BLOCKED");
  }

  await atomicWriteJson(shardPath, plan.ingestionPlan.merged.shard);
  await atomicWriteJson(path.join(outputDir, "manifest.json"), plan.ingestionPlan.manifest);
  await atomicWriteJson(path.join(outputDir, "checkpoint.json"), plan.checkpoint);
  await atomicWriteJson(path.join(outputDir, "rejected.json"), { rejected: [], safety: plan.safety });

  console.log(JSON.stringify({
    status: "READY_TO_PERSIST",
    downloadedSymbols: downloaded.symbols.length,
    downloadedRecords: downloaded.records.length,
    quarantinedRecords: downloaded.quarantined.length,
    warningCount: downloaded.warnings.length,
    totalRecordCount: plan.ingestionPlan.merged.shard.recordCount,
    insertedCount: plan.ingestionPlan.merged.insertedKeys.length,
    updatedCount: plan.ingestionPlan.merged.updatedKeys.length,
    brokerWrites: 0,
    excelOrderWrites: 0,
    rssOrderCalls: 0,
    liveOrders: 0,
  }, null, 2));
}

main().catch((error) => {
  console.error(error?.failures ? JSON.stringify({ message: error.message, failures: error.failures }, null, 2) : error?.stack || String(error));
  process.exitCode = 1;
});