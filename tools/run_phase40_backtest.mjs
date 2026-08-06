#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { runPhase40HistoricalDataFoundation } from "../predict/backtest/phase40-historical-data.js";
import {
  buildPhase40ResumeCheckpoint,
  runPhase40BatchBacktest,
} from "../predict/backtest/phase40-batch-runner.js";
import { runPhase40Analysis } from "../predict/backtest/phase40-analysis.js";

const SAFETY = Object.freeze({
  mode: "HISTORICAL_BACKTEST_ONLY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
});

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const value = argv[index + 1]?.startsWith("--") ? true : argv[++index] ?? true;
    args[key] = value;
  }
  return args;
}

function parseList(value, fallback = []) {
  if (!value) return fallback;
  return String(value)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parsePositiveInteger(value, fallback) {
  const number = Math.trunc(Number(value));
  return Number.isFinite(number) && number > 0 ? number : fallback;
}

function parseCsvLine(line) {
  const values = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      if (quoted && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      values.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  values.push(current);
  return values;
}

function parseCsv(text) {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter((line) => line.trim());
  if (!lines.length) return [];
  const headers = parseCsvLine(lines[0]).map((item) => item.trim());
  return lines.slice(1).map((line) => {
    const values = parseCsvLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
}

async function readJsonIfExists(filePath) {
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

async function loadRows(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  const text = await fs.readFile(filePath, "utf8");
  if (extension === ".json") {
    const parsed = JSON.parse(text);
    return Array.isArray(parsed) ? parsed : parsed.rows ?? parsed.candles ?? [];
  }
  if (extension === ".csv") return parseCsv(text);
  throw new Error(`Unsupported historical data format: ${extension}`);
}

async function findDataFiles(dataDir, requestedSymbols) {
  const entries = await fs.readdir(dataDir, { withFileTypes: true });
  const files = entries
    .filter((entry) => entry.isFile() && [".csv", ".json"].includes(path.extname(entry.name).toLowerCase()))
    .map((entry) => path.join(dataDir, entry.name));
  if (!requestedSymbols.length) return files;
  const requested = new Set(requestedSymbols.map((symbol) => symbol.toUpperCase()));
  return files.filter((filePath) => requested.has(path.basename(filePath, path.extname(filePath)).toUpperCase()));
}

function normalizeRows(rows, symbol) {
  return rows.map((row) => ({
    ...row,
    symbol: row.symbol ?? row.Symbol ?? symbol,
    date: row.date ?? row.Date ?? row.datetime ?? row.Datetime,
    time: row.time ?? row.Time,
    open: row.open ?? row.Open,
    high: row.high ?? row.High,
    low: row.low ?? row.Low,
    close: row.close ?? row.Close,
    adjustedClose:
      row.adjustedClose ?? row.AdjustedClose ?? row["Adj Close"] ?? row.adjClose ?? row.close ?? row.Close,
    volume: row.volume ?? row.Volume,
  }));
}

async function writeJson(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function collectAnalysisRecords(rawResults) {
  return rawResults.flatMap((item) => {
    const raw = item.result;
    return [
      ...(raw?.training ?? raw?.partitions?.training ?? []),
      ...(raw?.validation ?? raw?.partitions?.validation ?? []),
      ...(raw?.test ?? raw?.partitions?.test ?? []),
    ].map((record) => ({
      ...record,
      symbol: record.symbol ?? raw?.symbol ?? "UNKNOWN",
      horizonDays: record.horizonDays ?? record.period ?? raw?.period ?? 1,
      netReturn: record.netReturn ?? record.strategyReturn ?? record.actualReturn ?? 0,
      drawdown: record.drawdown ?? 0,
      modelRole: record.modelRole ?? "CHAMPION",
    }));
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const dataDir = path.resolve(String(args["data-dir"] ?? "data/historical/prices"));
  const outputDir = path.resolve(String(args["output-dir"] ?? "data/backtest-runs/latest"));
  const periods = parseList(args.periods, ["1", "3", "5", "10", "20"]).map((value) => parsePositiveInteger(value, 5));
  const requestedSymbols = parseList(args.symbols).map((value) => value.toUpperCase());
  const concurrency = parsePositiveInteger(args.concurrency, 2);
  const maximumSamples = parsePositiveInteger(args["maximum-samples"], 300);
  const retryFailed = args["retry-failed"] === true || args["retry-failed"] === "true";
  const checkpointPath = path.join(outputDir, "checkpoint.json");
  const existingCheckpoint = await readJsonIfExists(checkpointPath);
  const files = await findDataFiles(dataDir, requestedSymbols);

  if (!files.length) throw new Error(`No CSV or JSON files found in ${dataDir}`);

  const tasks = [];
  const datasetAudits = [];
  for (const filePath of files) {
    const symbol = path.basename(filePath, path.extname(filePath)).toUpperCase();
    const rows = normalizeRows(await loadRows(filePath), symbol);
    const prepared = runPhase40HistoricalDataFoundation({
      symbol,
      rows,
      source: filePath,
    });
    datasetAudits.push({
      symbol,
      sourceFile: filePath,
      audit: prepared.audit,
      readyForBacktest: prepared.status === "READY_FOR_BATCH_BACKTEST",
    });
    if (prepared.status !== "READY_FOR_BATCH_BACKTEST") continue;
    for (const period of periods) {
      tasks.push({
        taskId: `${symbol}:${period}`,
        symbol,
        companyName: symbol,
        industry: "UNKNOWN",
        period,
        candles: prepared.candles,
        weights: {},
        maximumSamples,
        historyMetadata: {
          source: filePath,
          datasetId: prepared.dataset.datasetId,
          audit: prepared.audit,
        },
      });
    }
  }

  const config = {
    createdAt: new Date().toISOString(),
    dataDir,
    outputDir,
    symbols: requestedSymbols,
    periods,
    concurrency,
    maximumSamples,
    retryFailed,
    taskCount: tasks.length,
    safety: { ...SAFETY },
  };
  await writeJson(path.join(outputDir, "config.json"), config);
  await writeJson(path.join(outputDir, "dataset-audits.json"), datasetAudits);

  if (!tasks.length) {
    throw new Error("No backtest-ready datasets were produced. Check dataset-audits.json");
  }

  const result = await runPhase40BatchBacktest({
    tasks,
    checkpoint: existingCheckpoint,
    options: {
      concurrency,
      retryFailed,
      planId: args["plan-id"] ?? `phase40-local-${Date.now()}`,
    },
  });

  const checkpoint = buildPhase40ResumeCheckpoint(result);
  const analysis = runPhase40Analysis(collectAnalysisRecords(result.rawResults));

  await Promise.all([
    writeJson(checkpointPath, checkpoint),
    writeJson(path.join(outputDir, "completed.json"), result.completed),
    writeJson(path.join(outputDir, "failed.json"), result.failed),
    writeJson(path.join(outputDir, "summary.json"), {
      status: result.status,
      completedCount: result.completed.length,
      failedCount: result.failed.length,
      groupedBySymbol: result.groupedBySymbol,
      brokerWrites: result.brokerWrites,
      liveOrders: result.liveOrders,
      safety: result.safety,
    }),
    writeJson(path.join(outputDir, "analysis.json"), analysis),
  ]);

  console.log(JSON.stringify({
    status: result.status,
    outputDir,
    files: files.length,
    tasks: tasks.length,
    completed: result.completed.length,
    failed: result.failed.length,
    brokerWrites: result.brokerWrites,
    liveOrders: result.liveOrders,
    safety: result.safety,
  }, null, 2));
}

const directRun = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (directRun) {
  main().catch((error) => {
    console.error(`[Phase40.5] ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  });
}

export { collectAnalysisRecords, findDataFiles, loadRows, parseArgs, parseCsv };
