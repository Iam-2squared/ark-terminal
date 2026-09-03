#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { processMsiiShadowRuntimePoint } from "../predict/realtime/phase57-msii-shadow-runtime.js";

const SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) throw new Error(`unexpected argument: ${token}`);
    const key = token.slice(2);
    const next = argv[index + 1];
    if (next === undefined || next.startsWith("--")) args[key] = true;
    else {
      args[key] = next;
      index += 1;
    }
  }
  return args;
}

function required(args, key) {
  const value = args[key];
  if (value === undefined || value === true || String(value).trim() === "") throw new Error(`--${key} is required`);
  return String(value);
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function readJsonl(file) {
  return fs.readFileSync(file, "utf8").split(/\r?\n/).filter((line) => line.trim()).map((line, index) => {
    try { return JSON.parse(line); }
    catch (error) { throw new Error(`invalid JSONL at ${file}:${index + 1}: ${error.message}`); }
  });
}

function atomicWriteJson(file, value) {
  const directory = path.dirname(file);
  fs.mkdirSync(directory, { recursive: true });
  const temp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(temp, file);
}

function numberOption(args, key, fallback) {
  if (args[key] === undefined) return fallback;
  const value = Number(args[key]);
  if (!Number.isFinite(value)) throw new Error(`--${key} must be numeric`);
  return value;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const envelopeFile = required(args, "envelope");
  const captureFile = required(args, "captures");
  const stateFile = required(args, "state");
  const scoreFile = required(args, "score");
  const pairFile = required(args, "pair");
  const marketSizeUnit = required(args, "market-size-unit");
  const tickSizeUnit = required(args, "tick-size-unit");
  if (marketSizeUnit !== "SHARES" || tickSizeUnit !== "SHARES") {
    throw new Error("Lane M must fail closed unless both size units are explicitly attested as SHARES");
  }

  const envelope = readJson(envelopeFile);
  const prior = fs.existsSync(stateFile) ? readJson(stateFile) : { ledger: [] };
  const captureRows = readJsonl(captureFile);
  const result = processMsiiShadowRuntimePoint({
    sessionDate: envelope.sessionDate,
    predeclaredStartAt: envelope.predeclaredStartAt,
    actualStartAt: envelope.actualStartAt,
    missingCaptureCount: Number(envelope.missingCaptureCount ?? 0),
    backfillUsed: envelope.backfillUsed === true,
    initialCapital: Number(envelope.initialCapital ?? 1_000_000),
    priorLedger: Array.isArray(prior.ledger) ? prior.ledger : [],
    captureRows,
    phase57State: envelope.phase57State,
    pointResult: envelope.pointResult,
    versions: envelope.versions,
    orderStyleResearchLabel: envelope.orderStyleResearchLabel ?? "MARKETABLE_QUOTE",
    ttlMs: numberOption(args, "ttl-ms", Number(envelope.ttlMs ?? 5_000)),
    decisionLatencyMs: numberOption(args, "decision-latency-ms", Number(envelope.decisionLatencyMs ?? 100)),
    marketSizeUnit,
    tickSizeUnit,
    transactionCostJpy: numberOption(args, "transaction-cost-jpy", Number(envelope.transactionCostJpy ?? 0)),
    laneYDecisions: Array.isArray(envelope.laneYDecisions) ? envelope.laneYDecisions : [],
  });

  atomicWriteJson(stateFile, {
    schemaVersion: 1,
    version: result.version ?? "phase57-msii-shadow-runtime-r2",
    sessionDate: envelope.sessionDate,
    ledger: result.ledger,
    safety: SAFETY,
  });
  atomicWriteJson(scoreFile, result.score);
  atomicWriteJson(pairFile, result.pair);
  process.stdout.write(`${JSON.stringify({
    status: result.status,
    complete: result.complete,
    decisionAt: result.decisionAt,
    entryIntentCount: result.entryIntentCount ?? 0,
    exitIntentCount: result.exitIntentCount ?? 0,
    closedTradesCommitted: result.closedTradesCommitted ?? 0,
    ledgerEventCount: result.score?.ledgerEventCount ?? result.ledger?.length ?? 0,
    fillRatePercent: result.score?.fillRatePercent ?? null,
    pairCount: result.pair?.pairCount ?? 0,
    safety: SAFETY,
  })}\n`);
  return result.complete ? 0 : 2;
}

try {
  process.exitCode = main();
} catch (error) {
  process.stderr.write(`${JSON.stringify({ status: "BLOCKED_PHASE57_MSII_RUNTIME", error: String(error?.message ?? error), safety: SAFETY })}\n`);
  process.exitCode = 1;
}
