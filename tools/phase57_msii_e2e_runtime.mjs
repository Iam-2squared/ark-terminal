#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  PHASE57_MSII_RUNTIME_VERSION,
  processMsiiShadowRuntimePoint,
} from "../predict/realtime/phase57-msii-shadow-runtime.js";

const SAFETY = Object.freeze({
  mode: "LANE_M_FILE_COORDINATOR_READ_ONLY",
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
const FALSE_KEYS = Object.freeze([
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
]);

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) throw new Error(`unexpected argument ${token}`);
    const key = token.slice(2);
    const next = argv[index + 1];
    if (next === undefined || next.startsWith("--")) args[key] = true;
    else { args[key] = next; index += 1; }
  }
  return args;
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
function iso(value, label) {
  const parsed = Date.parse(String(value ?? ""));
  if (!Number.isFinite(parsed)) throw new Error(`${label} must be a valid absolute timestamp`);
  return new Date(parsed).toISOString();
}
function jstSessionDate(value) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(iso(value, "timestamp")));
  const fields = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${fields.year}-${fields.month}-${fields.day}`;
}
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  return value;
}
function sha256(value) {
  return crypto.createHash("sha256").update(typeof value === "string" || Buffer.isBuffer(value) ? value : JSON.stringify(canonical(value))).digest("hex");
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function readJsonl(file) {
  return fs.readFileSync(file, "utf8").split(/\r?\n/).filter((line) => line.trim()).map((line, index) => {
    try { return JSON.parse(line); }
    catch (error) { throw new Error(`invalid JSONL ${file}:${index + 1}: ${error.message}`); }
  });
}
function atomicWrite(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(temp, file);
}
function assertSafety(value, label) {
  if (!value || typeof value !== "object") throw new Error(`${label} contract is required`);
  for (const key of FALSE_KEYS) if (value[key] !== false) throw new Error(`${label}.${key} must remain false`);
  if (value.transmitted !== undefined && value.transmitted !== false) throw new Error(`${label}.transmitted must remain false`);
}
function safeStamp(value) { return iso(value, "decisionAt").replace(/[-:.]/g, ""); }
function eventSymbol(row) { return String(row?.symbol ?? "").trim().toUpperCase().replace(/\.0+$/, "").replace(/^(\d+)$/, "$1.T"); }
function decisionSymbols(envelope) {
  const accepted = envelope?.pointResult?.allocation?.decisions ?? [];
  const closed = envelope?.pointResult?.exitEvaluation?.closed ?? [];
  return [...new Set([
    ...accepted.filter((row) => row?.status === "ACCEPTED").map((row) => eventSymbol(row)),
    ...closed.map((row) => eventSymbol(row)),
  ].filter(Boolean))].sort();
}

export function validateLaneMEnvelope(envelope, { priorDecisionAt = null } = {}) {
  if (!envelope || typeof envelope !== "object" || Array.isArray(envelope)) throw new Error("Lane M envelope must be an object");
  assertSafety(envelope.safety, "envelope.safety");
  if (envelope.backfillUsed === true) throw new Error("Lane M prospective coordinator forbids backfillUsed=true");
  if (!String(envelope.sessionDate ?? "").match(/^\d{4}-\d{2}-\d{2}$/)) throw new Error("envelope.sessionDate must be YYYY-MM-DD");
  const decisionAt = iso(envelope?.pointResult?.at, "pointResult.at");
  if (jstSessionDate(decisionAt) !== envelope.sessionDate) throw new Error("envelope.sessionDate must match pointResult.at in Asia/Tokyo");
  if (priorDecisionAt && Date.parse(decisionAt) <= Date.parse(priorDecisionAt)) throw new Error("Lane M decisionAt must move strictly forward");
  if (!envelope.phase57State?.strategies) throw new Error("envelope.phase57State.strategies required");
  if (envelope.phase57State.sessionDate !== envelope.sessionDate) throw new Error("phase57State.sessionDate mismatch");
  if (!envelope.pointResult?.allocation || !envelope.pointResult?.exitEvaluation) throw new Error("pointResult allocation/exitEvaluation required");
  iso(envelope.predeclaredStartAt, "predeclaredStartAt");
  iso(envelope.actualStartAt, "actualStartAt");
  const requiredVersions = ["selectorVersion", "entryVersion", "exitV3Version", "exitV4Version", "allocationVersion"];
  for (const key of requiredVersions) if (!String(envelope?.versions?.[key] ?? "").trim()) throw new Error(`envelope.versions.${key} required`);
  return Object.freeze({ decisionAt, requiredSymbols: Object.freeze(decisionSymbols(envelope)) });
}

export function validateCaptureBundle(captureRows, { decisionAt, requiredSymbols, referenceMaxAgeMs = 5_000 } = {}) {
  if (!Array.isArray(captureRows) || !captureRows.length) throw new Error("Lane M capture bundle must contain rows");
  if (!(Number(referenceMaxAgeMs) >= 0)) throw new Error("referenceMaxAgeMs must be >= 0");
  const decisionMs = Date.parse(iso(decisionAt, "decisionAt"));
  const bySymbol = new Map();
  let hasPostDecision = false;
  for (const row of captureRows) {
    assertSafety(row?.safety, "capture.safety");
    if (row?.sourceMode !== "MARKETSPEED_II_RSS_READ_ONLY") throw new Error("capture sourceMode must be MARKETSPEED_II_RSS_READ_ONLY");
    const capturedMs = Date.parse(iso(row?.capturedAt, "capture.capturedAt"));
    const symbol = eventSymbol(row);
    if (!symbol) throw new Error("capture symbol required");
    if (capturedMs > decisionMs) hasPostDecision = true;
    if (capturedMs <= decisionMs) {
      const prior = bySymbol.get(symbol);
      if (!prior || capturedMs > prior.capturedMs) bySymbol.set(symbol, { capturedMs, row });
    }
  }
  const missing = [];
  const stale = [];
  for (const symbol of requiredSymbols ?? []) {
    const ref = bySymbol.get(symbol);
    if (!ref) missing.push(symbol);
    else if (decisionMs - ref.capturedMs > referenceMaxAgeMs) stale.push(symbol);
  }
  if (missing.length) throw new Error(`Lane M pre-decision reference missing: ${missing.join(",")}`);
  if (stale.length) throw new Error(`Lane M pre-decision reference stale: ${stale.join(",")}`);
  return Object.freeze({ rowCount: captureRows.length, hasPostDecision, referenceSymbols: Object.freeze([...bySymbol.keys()].sort()) });
}

export function processLaneMEnvelope({ envelope, captureRows, priorState = {}, marketSizeUnit = "SHARES", tickSizeUnit = "SHARES", referenceMaxAgeMs = 5_000, ttlMs = 5_000, decisionLatencyMs = 100, transactionCostJpy = 0 } = {}) {
  assertSafety(SAFETY, "coordinator.safety");
  if (marketSizeUnit !== "SHARES" || tickSizeUnit !== "SHARES") throw new Error("Lane M size units must be explicitly attested as SHARES");
  const validated = validateLaneMEnvelope(envelope, { priorDecisionAt: priorState.lastDecisionAt ?? null });
  if (priorState.sessionDate && priorState.sessionDate !== envelope.sessionDate) throw new Error("Lane M prior state sessionDate mismatch");
  validateCaptureBundle(captureRows, { decisionAt: validated.decisionAt, requiredSymbols: validated.requiredSymbols, referenceMaxAgeMs });
  const envelopeHash = sha256(envelope);
  const captureHash = sha256(captureRows);
  const seen = new Set(priorState.processedEvidenceHashes ?? []);
  const evidenceHash = sha256({ envelopeHash, captureHash });
  if (seen.has(evidenceHash)) throw new Error("Lane M evidence bundle already processed");

  const result = processMsiiShadowRuntimePoint({
    sessionDate: envelope.sessionDate,
    predeclaredStartAt: envelope.predeclaredStartAt,
    actualStartAt: envelope.actualStartAt,
    missingCaptureCount: Number(envelope.missingCaptureCount ?? 0),
    backfillUsed: false,
    initialCapital: Number(envelope.initialCapital ?? 1_000_000),
    priorLedger: Array.isArray(priorState.ledger) ? priorState.ledger : [],
    captureRows,
    phase57State: envelope.phase57State,
    pointResult: envelope.pointResult,
    versions: envelope.versions,
    orderStyleResearchLabel: envelope.orderStyleResearchLabel ?? "MARKETABLE_QUOTE",
    ttlMs,
    decisionLatencyMs,
    referenceMaxAgeMs,
    marketSizeUnit,
    tickSizeUnit,
    transactionCostJpy,
    laneYDecisions: Array.isArray(envelope.laneYDecisions) ? envelope.laneYDecisions : [],
  });
  if (result.complete !== true) throw new Error(`Lane M runtime blocked: ${result.status}`);
  const nextState = Object.freeze({
    schemaVersion: 1,
    version: PHASE57_MSII_RUNTIME_VERSION,
    sessionDate: envelope.sessionDate,
    lastDecisionAt: validated.decisionAt,
    processedEvidenceHashes: Object.freeze([...(priorState.processedEvidenceHashes ?? []), evidenceHash]),
    ledger: result.ledger,
    safety: SAFETY,
  });
  return Object.freeze({ result, nextState, envelopeHash, captureHash, evidenceHash });
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const envelopeFile = required(args, "envelope");
  const captureFile = required(args, "captures");
  const outputDir = required(args, "output-dir");
  const stateFile = String(args.state ?? path.join(outputDir, "state.json"));
  const envelope = readJson(envelopeFile);
  const captureRows = readJsonl(captureFile);
  const priorState = fs.existsSync(stateFile) ? readJson(stateFile) : {};
  const processed = processLaneMEnvelope({
    envelope,
    captureRows,
    priorState,
    marketSizeUnit: String(args["market-size-unit"] ?? "SHARES"),
    tickSizeUnit: String(args["tick-size-unit"] ?? "SHARES"),
    referenceMaxAgeMs: numeric(args, "reference-max-age-ms", Number(envelope.referenceMaxAgeMs ?? 5_000)),
    ttlMs: numeric(args, "ttl-ms", Number(envelope.ttlMs ?? 5_000)),
    decisionLatencyMs: numeric(args, "decision-latency-ms", Number(envelope.decisionLatencyMs ?? 100)),
    transactionCostJpy: numeric(args, "transaction-cost-jpy", Number(envelope.transactionCostJpy ?? 0)),
  });
  const stamp = safeStamp(processed.nextState.lastDecisionAt);
  atomicWrite(stateFile, processed.nextState);
  atomicWrite(path.join(outputDir, "latest-score.json"), processed.result.score);
  atomicWrite(path.join(outputDir, "latest-pair.json"), processed.result.pair);
  atomicWrite(path.join(outputDir, "points", `${stamp}.json`), {
    schemaVersion: 1,
    status: "PHASE57_MSII_E2E_POINT_COMMITTED",
    sessionDate: envelope.sessionDate,
    decisionAt: processed.nextState.lastDecisionAt,
    envelopeHash: processed.envelopeHash,
    captureHash: processed.captureHash,
    evidenceHash: processed.evidenceHash,
    runtimeStatus: processed.result.status,
    score: processed.result.score,
    pair: processed.result.pair,
    safety: SAFETY,
  });
  process.stdout.write(`${JSON.stringify({ status: "PHASE57_MSII_E2E_POINT_COMMITTED", decisionAt: processed.nextState.lastDecisionAt, ledgerEventCount: processed.nextState.ledger.length, fillRatePercent: processed.result.score?.fillRatePercent ?? null, pairCount: processed.result.pair?.pairCount ?? 0, safety: SAFETY })}\n`);
  return 0;
}

const isDirectRun = process.argv[1] ? import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href : false;
if (isDirectRun) {
  try { process.exitCode = main(); }
  catch (error) {
    process.stderr.write(`${JSON.stringify({ status: "BLOCKED_PHASE57_MSII_E2E_RUNTIME", error: String(error?.message ?? error), safety: SAFETY })}\n`);
    process.exitCode = 1;
  }
}

export const PHASE57_MSII_E2E_SAFETY = SAFETY;
