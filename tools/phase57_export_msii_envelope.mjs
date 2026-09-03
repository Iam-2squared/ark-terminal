#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

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
const FALSE_KEYS = Object.freeze([
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
]);
const DEFAULT_VERSIONS = Object.freeze({
  selectorVersion: "PHASE57_DYNAMIC5M_FROZEN_SELECTOR",
  entryVersion: "PHASE57_FROZEN_ENTRY",
  exitV3Version: "PHASE57_EXIT_V3_FROZEN",
  exitV4Version: "PHASE57_EXIT_V4_FROZEN",
  allocationVersion: "PHASE57_CAPITAL_ALLOCATION_FROZEN",
});

function parseArgs(argv) {
  const out = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) throw new Error(`unexpected argument ${token}`);
    const key = token.slice(2);
    const next = argv[index + 1];
    if (next === undefined || next.startsWith("--")) out[key] = true;
    else { out[key] = next; index += 1; }
  }
  return out;
}
function required(args, key) {
  const value = args[key];
  if (value === undefined || value === true || String(value).trim() === "") throw new Error(`--${key} is required`);
  return String(value);
}
function timestamp(value, label) {
  const parsed = Date.parse(String(value ?? ""));
  if (!Number.isFinite(parsed)) throw new Error(`${label} must be a valid absolute timestamp`);
  return new Date(parsed).toISOString();
}
function finiteNumber(value, label, { min = -Infinity, integer = false } = {}) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < min || (integer && !Number.isInteger(number))) throw new Error(`${label} is invalid`);
  return number;
}
function assertSafety(value, label) {
  if (!value || typeof value !== "object") throw new Error(`${label} safety contract is required`);
  for (const key of FALSE_KEYS) if (value[key] !== false) throw new Error(`${label}.${key} must remain false`);
}
function normalizeSymbol(value) {
  const raw = String(value ?? "").trim().toUpperCase();
  if (/^\d+(?:\.0+)?$/.test(raw)) return `${String(Math.trunc(Number(raw)))}.T`;
  return raw;
}
function positionFor(state, strategyId, symbol) {
  const strategy = state?.strategies?.[strategyId];
  return strategy?.positions?.[symbol] ?? strategy?.positions?.[normalizeSymbol(symbol)] ?? null;
}
function laneYEntryDecisions(state, point) {
  return (point?.allocation?.decisions ?? []).filter((row) => row?.status === "ACCEPTED").map((row) => {
    const position = positionFor(state, row.strategyId, row.symbol);
    if (!position) throw new Error(`accepted Lane Y allocation missing position ${row.strategyId}/${row.symbol}`);
    return Object.freeze({
      strategyId: row.strategyId,
      symbol: row.symbol,
      decisionAt: point.at,
      intentKind: "ENTRY",
      referencePrice: finiteNumber(position.entryReferencePrice, `entry reference price ${row.strategyId}/${row.symbol}`, { min: Number.MIN_VALUE }),
    });
  });
}
function laneYExitDecisions(point) {
  return (point?.exitEvaluation?.closed ?? []).map((row) => Object.freeze({
    strategyId: row.strategyId,
    symbol: row.symbol,
    decisionAt: point.at,
    intentKind: "EXIT",
    referencePrice: finiteNumber(row.exitReferencePrice ?? row.lastMarkPrice, `exit reference price ${row.strategyId}/${row.symbol}`, { min: Number.MIN_VALUE }),
  }));
}

export function buildMsiiEnvelopeFromRealtimeState(state, {
  predeclaredStartAt,
  actualStartAt,
  missingCaptureCount = 0,
  initialCapital = 1_000_000,
  versions = DEFAULT_VERSIONS,
  referenceMaxAgeMs = 5_000,
  ttlMs = 5_000,
  decisionLatencyMs = 100,
} = {}) {
  if (!state || typeof state !== "object" || Array.isArray(state)) throw new Error("Phase57 realtime state object required");
  assertSafety(state.safety, "phase57State");
  if (!state.sessionDate) throw new Error("Phase57 state.sessionDate required");
  if (!state?.pipeline?.history?.length) throw new Error("Phase57 state.pipeline.history must contain a committed realtime point");
  const point = state.pipeline.history.at(-1);
  const decisionAt = timestamp(point?.at, "point.at");
  if (state.pipeline.lastPointTime && timestamp(state.pipeline.lastPointTime, "pipeline.lastPointTime") !== decisionAt) {
    throw new Error("Phase57 pipeline last point does not match latest history point");
  }
  assertSafety(point.safety, "pointResult");
  const declared = timestamp(predeclaredStartAt, "predeclaredStartAt");
  const actual = timestamp(actualStartAt, "actualStartAt");
  const missing = finiteNumber(missingCaptureCount, "missingCaptureCount", { min: 0, integer: true });
  const capital = finiteNumber(initialCapital, "initialCapital", { min: Number.MIN_VALUE });
  const referenceAge = finiteNumber(referenceMaxAgeMs, "referenceMaxAgeMs", { min: 0 });
  const ttl = finiteNumber(ttlMs, "ttlMs", { min: 0 });
  const latency = finiteNumber(decisionLatencyMs, "decisionLatencyMs", { min: 0 });
  const requiredVersions = ["selectorVersion", "entryVersion", "exitV3Version", "exitV4Version", "allocationVersion"];
  for (const key of requiredVersions) if (!String(versions?.[key] ?? "").trim()) throw new Error(`versions.${key} required`);
  const laneYDecisions = Object.freeze([
    ...laneYEntryDecisions(state, point),
    ...laneYExitDecisions(point),
  ].sort((left, right) => left.strategyId.localeCompare(right.strategyId) || normalizeSymbol(left.symbol).localeCompare(normalizeSymbol(right.symbol)) || left.intentKind.localeCompare(right.intentKind)));
  return Object.freeze({
    schemaVersion: 1,
    phase: "57.msii.runtime-envelope.r1",
    status: "PHASE57_MSII_RUNTIME_ENVELOPE_READY",
    sessionDate: state.sessionDate,
    predeclaredStartAt: declared,
    actualStartAt: actual,
    missingCaptureCount: missing,
    backfillUsed: false,
    initialCapital: capital,
    phase57State: state,
    pointResult: point,
    versions: Object.freeze({ ...versions }),
    laneYDecisions,
    orderStyleResearchLabel: "MARKETABLE_QUOTE",
    referenceMaxAgeMs: referenceAge,
    ttlMs: ttl,
    decisionLatencyMs: latency,
    methodology: Object.freeze({
      sourceDecisionAlreadyFrozen: true,
      selectorRetunedForLaneM: false,
      entryRetunedForLaneM: false,
      exitRetunedForLaneM: false,
      allocationRetunedForLaneM: false,
      futureOutcomeUsed: false,
      backfillUsed: false,
      exactLaneYDecisionTimestampPreserved: true,
    }),
    safety: SAFETY,
  });
}

function atomicWrite(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(temp, file);
}
function main() {
  const args = parseArgs(process.argv.slice(2));
  const stateFile = required(args, "state");
  const output = required(args, "output");
  const state = JSON.parse(fs.readFileSync(stateFile, "utf8"));
  const envelope = buildMsiiEnvelopeFromRealtimeState(state, {
    predeclaredStartAt: required(args, "predeclared-start-at"),
    actualStartAt: required(args, "actual-start-at"),
    missingCaptureCount: args["missing-capture-count"] ?? 0,
    initialCapital: args["initial-capital"] ?? 1_000_000,
    referenceMaxAgeMs: args["reference-max-age-ms"] ?? 5_000,
    ttlMs: args["ttl-ms"] ?? 5_000,
    decisionLatencyMs: args["decision-latency-ms"] ?? 100,
  });
  atomicWrite(output, envelope);
  process.stdout.write(`${JSON.stringify({ status: envelope.status, sessionDate: envelope.sessionDate, decisionAt: envelope.pointResult.at, laneYDecisionCount: envelope.laneYDecisions.length, output, safety: SAFETY })}\n`);
  return 0;
}

const isDirectRun = process.argv[1] ? import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href : false;
if (isDirectRun) {
  try { process.exitCode = main(); }
  catch (error) {
    process.stderr.write(`${JSON.stringify({ status: "BLOCKED_PHASE57_MSII_ENVELOPE_EXPORT", error: String(error?.message ?? error), safety: SAFETY })}\n`);
    process.exitCode = 1;
  }
}

export { DEFAULT_VERSIONS as PHASE57_MSII_DEFAULT_VERSIONS, SAFETY as PHASE57_MSII_ENVELOPE_SAFETY };
