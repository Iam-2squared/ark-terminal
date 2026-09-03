#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  appendPhase57MsiiDashboardHistory,
  buildPhase57MsiiDashboardSnapshot,
  PHASE57_MSII_DASHBOARD_SAFETY,
} from "../predict/realtime/phase57-msii-dashboard.js";

const SAFETY = Object.freeze({ ...PHASE57_MSII_DASHBOARD_SAFETY, mode: "LANE_M_DASHBOARD_WATCH_READ_ONLY" });
const FALSE_KEYS = Object.freeze([
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
]);

function assertSafety(value, label) {
  if (!value || typeof value !== "object") throw new Error(`${label} safety required`);
  for (const key of FALSE_KEYS) if (value[key] !== false) throw new Error(`${label}.${key} must remain false`);
}
function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) throw new Error(`unexpected argument ${token}`);
    const key = token.slice(2), next = argv[i + 1];
    if (next === undefined || next.startsWith("--")) out[key] = true;
    else { out[key] = next; i += 1; }
  }
  return out;
}
function required(args, key) {
  const value = args[key];
  if (value === undefined || value === true || String(value).trim() === "") throw new Error(`--${key} is required`);
  return String(value);
}
function numeric(args, key, fallback) {
  if (args[key] === undefined) return fallback;
  const value = Number(args[key]);
  if (!Number.isFinite(value)) throw new Error(`--${key} must be numeric`);
  return value;
}
function iso(value, label = "timestamp") {
  const parsed = Date.parse(String(value ?? ""));
  if (!Number.isFinite(parsed)) throw new Error(`${label} invalid`);
  return new Date(parsed).toISOString();
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function atomicWrite(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(temp, file);
}
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

export function rebuildPhase57MsiiDashboardArtifacts(outputDir) {
  assertSafety(SAFETY, "dashboard watcher");
  const scoreFile = path.join(outputDir, "latest-score.json");
  const pairFile = path.join(outputDir, "latest-pair.json");
  const historyFile = path.join(outputDir, "dashboard-history.json");
  const latestFile = path.join(outputDir, "dashboard-latest.json");
  if (!fs.existsSync(scoreFile) || !fs.existsSync(pairFile)) {
    return Object.freeze({ status: "WAITING_FOR_LANE_M_SCORE_PAIR", updated: false, safety: SAFETY });
  }
  const score = readJson(scoreFile), pair = readJson(pairFile);
  assertSafety(score.safety, "score");
  assertSafety(pair.safety, "pair");
  const coverage = score.coverage ?? null;
  const snapshot = buildPhase57MsiiDashboardSnapshot({ score, pair, coverage });
  const history = fs.existsSync(historyFile) ? readJson(historyFile) : [];
  const nextHistory = appendPhase57MsiiDashboardHistory(history, snapshot);
  const unchanged = history.length === nextHistory.length;
  atomicWrite(latestFile, snapshot);
  if (!unchanged) atomicWrite(historyFile, nextHistory);
  return Object.freeze({
    status: unchanged ? "PHASE57_MSII_DASHBOARD_CURRENT" : "PHASE57_MSII_DASHBOARD_UPDATED",
    updated: !unchanged,
    at: snapshot.at,
    strategyCount: snapshot.aggregate.strategyCount,
    fillRatePercent: snapshot.aggregate.fillRatePercent,
    netPnlJpy: snapshot.aggregate.netPnlJpy,
    pairCount: snapshot.aggregate.pairCount,
    coveragePercent: snapshot.aggregate.coveragePercent,
    historyPointCount: nextHistory.length,
    safety: SAFETY,
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const outputDir = required(args, "output-dir");
  const pollMs = numeric(args, "poll-ms", 1_000);
  const stopAt = args["stop-at"] ? Date.parse(iso(args["stop-at"], "stop-at")) : null;
  if (pollMs < 200) throw new Error("--poll-ms must be >= 200");
  process.stdout.write(`${JSON.stringify({ status: "PHASE57_MSII_DASHBOARD_WATCH_START", outputDir, pollMs, safety: SAFETY })}\n`);
  let lastStatus = null, lastAt = null;
  while (true) {
    const now = Date.now();
    if (stopAt !== null && now >= stopAt) break;
    const result = rebuildPhase57MsiiDashboardArtifacts(outputDir);
    if (result.status !== lastStatus || result.at !== lastAt || result.updated) {
      process.stdout.write(`${JSON.stringify(result)}\n`);
      lastStatus = result.status;
      lastAt = result.at ?? null;
    }
    await sleep(pollMs);
  }
  const finalResult = rebuildPhase57MsiiDashboardArtifacts(outputDir);
  process.stdout.write(`${JSON.stringify({ status: "PHASE57_MSII_DASHBOARD_WATCH_STOPPED", final: finalResult, safety: SAFETY })}\n`);
  return 0;
}

const direct = process.argv[1] ? import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href : false;
if (direct) {
  main().then((code) => { process.exitCode = code; }).catch((error) => {
    process.stderr.write(`${JSON.stringify({ status: "BLOCKED_PHASE57_MSII_DASHBOARD_WATCH", error: String(error?.message ?? error), safety: SAFETY })}\n`);
    process.exitCode = 1;
  });
}

export const PHASE57_MSII_DASHBOARD_WATCH_SAFETY = SAFETY;
