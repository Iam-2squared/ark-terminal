import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import {
  aggregateJquantsMinutesToFiveMinuteBars,
  normalizeJquantsMinuteRows,
  Phase57SelectorJquantsMinuteInternals,
} from "./lib/phase57-selector-jquants-minute.mjs";

const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const PRECOMMIT_PATH = process.env.FULL_PARITY_PRECOMMIT_PATH ?? "predict/research/phase57-entry-reserve87-full-source-parity-precommit.json";
const ADMISSION_PATH = process.env.ADMISSION_V21_PATH ?? "artifacts/input/admission-v21/admission.json";
const OUT_DIR = process.env.OUTPUT_DIR ?? "artifacts/phase57-entry-reserve87-full-source-parity";
const API_KEY = process.env.JQUANTS_API_KEY ?? "";
const SHARD_INDEX = Number(process.env.SHARD_INDEX ?? "0");
const SHARD_COUNT = Number(process.env.SHARD_COUNT ?? "1");
const API_BASE = "https://api.jquants.com/";
const MINUTE_PATH = "v2/equities/bars/minute";
const MASTER_PATH = "v2/equities/master";
const TIMESTAMP_CONTRACT = "BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES";
const ALLOWED_MARKETS = new Set(["0111", "0112", "0113"]);
const DOMESTIC_STOCK_PRODUCT = "011";
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function assert(condition, message) { if (!condition) throw new Error(message); }
function safeError(error) { return String(error?.message ?? error).replace(/[A-Za-z0-9_-]{24,}/g, "[REDACTED]"); }
function writeJson(name, value) {
  fs.mkdirSync(OUT_DIR, { recursive: true, mode: 0o700 });
  const text = JSON.stringify(value, null, 2) + "\n";
  fs.writeFileSync(path.join(OUT_DIR, name), text, { mode: 0o600 });
  fs.writeFileSync(path.join(OUT_DIR, `${name}.sha256`), `${sha256(text)}  ${name}\n`, { mode: 0o600 });
}
function canonicalMinute(row) {
  return JSON.stringify([row.date, row.time, row.code, row.open, row.high, row.low, row.close, row.volume, row.turnover]);
}
function canonicalBar(bar) {
  return JSON.stringify([bar.sessionDate, bar.sourceCode, bar.timestamp, bar.availableAt, bar.open, bar.high, bar.low, bar.close, bar.volume, bar.turnover, bar.observedMinuteCount]);
}
async function requestJson(pathname, query) {
  const url = new URL(pathname, API_BASE);
  for (const [name, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && String(value) !== "") url.searchParams.set(name, String(value));
  }
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const response = await fetch(url, {
      headers: { Accept: "application/json", "x-api-key": API_KEY },
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(90_000),
    });
    if (response.status === 200) return JSON.parse(await response.text());
    if ((response.status === 429 || response.status >= 500) && attempt < 4) {
      await sleep((attempt + 1) * 7000);
      continue;
    }
    if (response.status === 401) throw new Error("AUTH_REJECTED");
    if (response.status === 403) throw new Error("BLOCKED_ENTITLEMENT");
    if (response.status === 429) throw new Error("RATE_LIMITED");
    throw new Error(`JQUANTS_HTTP_${response.status}`);
  }
  throw new Error("JQUANTS_REQUEST_EXHAUSTED");
}
async function fetchMinuteDate(date) {
  const raw = [];
  const seen = new Set();
  let paginationKey = "";
  let pageCount = 0;
  for (let page = 0; page < 2500; page += 1) {
    if (page) await sleep(1500);
    const payload = await requestJson(MINUTE_PATH, { date, pagination_key: paginationKey });
    assert(Array.isArray(payload?.data), "JQUANTS_MINUTE_SCHEMA_INVALID");
    raw.push(...payload.data);
    pageCount += 1;
    const next = String(payload.pagination_key ?? payload.paginationKey ?? "");
    if (!next) break;
    if (seen.has(next) || page === 2499) throw new Error("JQUANTS_MINUTE_PAGINATION_INVALID");
    seen.add(next);
    paginationKey = next;
  }
  return { raw, pageCount };
}
async function fetchMasterDate(date) {
  const payload = await requestJson(MASTER_PATH, { date });
  assert(Array.isArray(payload?.data), "JQUANTS_MASTER_SCHEMA_INVALID");
  return payload.data;
}
function normalizeMaster(rows, date) {
  const byCode = new Map();
  let invalidRows = 0;
  let duplicateCodes = 0;
  for (const row of rows) {
    const code = String(row?.Code ?? "").trim().toUpperCase();
    const rowDate = String(row?.Date ?? "");
    if (rowDate !== date || !Phase57SelectorJquantsMinuteInternals.ISSUE_CODE.test(code)) { invalidRows += 1; continue; }
    if (byCode.has(code)) { duplicateCodes += 1; continue; }
    byCode.set(code, {
      sourceCode: code,
      symbol: Phase57SelectorJquantsMinuteInternals.sourceCodeToSymbol(code),
      marketCode: String(row?.Mkt ?? ""),
      productCategory: String(row?.ProdCat ?? ""),
    });
  }
  return { byCode, invalidRows, duplicateCodes };
}
function groupBars(bars, master) {
  const bySymbol = new Map();
  for (const bar of bars) {
    const meta = master.byCode.get(bar.sourceCode);
    const commonIssue = bar.sourceCode.length === 4 || bar.sourceCode.endsWith("0");
    if (!meta || !ALLOWED_MARKETS.has(meta.marketCode) || meta.productCategory !== DOMESTIC_STOCK_PRODUCT || !commonIssue) continue;
    if (!bySymbol.has(bar.symbol)) bySymbol.set(bar.symbol, true);
  }
  return bySymbol;
}
async function structuralRefetch(sessionDate) {
  const [{ raw, pageCount }, masterRows] = await Promise.all([fetchMinuteDate(sessionDate), fetchMasterDate(sessionDate)]);
  const normalized = normalizeJquantsMinuteRows(raw);
  assert(raw.length === normalized.length, "EXACT_DUPLICATE_MINUTES_PRESENT");
  const master = normalizeMaster(masterRows, sessionDate);
  assert(master.invalidRows === 0 && master.duplicateCodes === 0, "PIT_MASTER_INVALID");
  const bars = aggregateJquantsMinutesToFiveMinuteBars(raw, { sourceMinuteTimestampMeaning: TIMESTAMP_CONTRACT });
  const bySymbol = groupBars(bars, master);
  assert(bySymbol.size > 0, "NO_ELIGIBLE_JPX_SYMBOLS");
  return {
    sessionDate,
    fold: "PURGE",
    pageCount,
    normalizedMinuteRows: normalized.length,
    fiveMinuteBars: bars.length,
    eligibleJpxSymbolCount: bySymbol.size,
    minuteSha256: sha256(normalized.map(canonicalMinute).join("\n")),
    fiveMinuteSha256: sha256(bars.map(canonicalBar).join("\n")),
    memberSetSha256: sha256([...bySymbol.keys()].sort().join("\n")),
  };
}

const precommit = readJson(PRECOMMIT_PATH);
assert(precommit?.status === "FULL_SOURCE_PARITY_PRECOMMITTED_AFTER_PILOT_PASS", "full parity precommit not frozen");
assert(precommit?.pilotEvidence?.status === "SOURCE_PARITY_PILOT_PASS", "pilot evidence not PASS");
assert(precommit?.purpose === "ENTRY_DEV_SOURCE_PARITY_ONLY_NO_FEATURES_NO_LABELS_NO_OUTCOMES", "scope mismatch");
assert(precommit?.developmentUnlocked === false, "precommit cannot unlock development");
assert(Array.isArray(precommit?.sessions) && precommit.sessions.length === 58 && precommit.count === 58, "expected exactly 58 sessions");
assert(precommit?.sharding?.shardCount === SHARD_COUNT, "shard count mismatch");
assert(Number.isInteger(SHARD_INDEX) && SHARD_INDEX >= 0 && SHARD_INDEX < SHARD_COUNT, "invalid shard index");
assert(String(API_KEY).trim(), "JQUANTS_API_KEY_REQUIRED");

const admission = readJson(ADMISSION_PATH);
const expectedByDate = new Map((admission.auditBySession ?? []).map((row) => [row.sessionDate, row]));
const shardSessions = precommit.sessions.filter((_, index) => index % SHARD_COUNT === SHARD_INDEX);
assert(shardSessions.length > 0, "empty shard");

const results = [];
let pass = true;
for (const sessionDate of shardSessions) {
  const expected = expectedByDate.get(sessionDate);
  if (!expected) {
    pass = false;
    results.push({ sessionDate, status: "SOURCE_PARITY_ERROR", error: "MISSING_ADMISSION_REFERENCE" });
    continue;
  }
  try {
    const actual = await structuralRefetch(sessionDate);
    const parity = {};
    for (const key of precommit.requiredParity) {
      parity[key] = { expected: expected[key], actual: actual[key], match: expected[key] === actual[key] };
    }
    const countChecks = {
      eligibleJpxSymbolCount: expected.eligibleJpxSymbolCount === actual.eligibleJpxSymbolCount,
      normalizedMinuteRows: expected.normalizedMinuteRows === actual.normalizedMinuteRows,
      fiveMinuteBars: expected.fiveMinuteBars === actual.fiveMinuteBars,
    };
    const allMatch = Object.values(parity).every((item) => item.match) && Object.values(countChecks).every(Boolean);
    pass &&= allMatch;
    results.push({
      sessionDate,
      status: allMatch ? "SOURCE_PARITY_PASS" : "SOURCE_PARITY_MISMATCH",
      parity,
      countChecks,
      expectedCounts: {
        eligibleJpxSymbolCount: expected.eligibleJpxSymbolCount,
        normalizedMinuteRows: expected.normalizedMinuteRows,
        fiveMinuteBars: expected.fiveMinuteBars,
      },
      actualCounts: {
        eligibleJpxSymbolCount: actual.eligibleJpxSymbolCount,
        normalizedMinuteRows: actual.normalizedMinuteRows,
        fiveMinuteBars: actual.fiveMinuteBars,
      },
      featureCalculationPerformed: false,
      labelGenerationPerformed: false,
      outcomeInspectionPerformed: false,
      rawPersisted: false,
    });
  } catch (error) {
    pass = false;
    results.push({ sessionDate, status: "SOURCE_PARITY_ERROR", error: safeError(error) });
  }
}

const output = {
  schemaVersion: 1,
  phase: precommit.phase,
  status: pass ? "FULL_SOURCE_PARITY_SHARD_PASS" : "FULL_SOURCE_PARITY_SHARD_FAIL",
  purpose: precommit.purpose,
  shardIndex: SHARD_INDEX,
  shardCount: SHARD_COUNT,
  sessions: shardSessions,
  results,
  developmentUnlocked: false,
  featureCalculationPerformed: false,
  labelGenerationPerformed: false,
  outcomeInspectionPerformed: false,
  rawPersisted: false,
  reserve180To282Opened: 0,
  freshValidationOpened: 0,
  freshOosOpened: 0,
  safety: precommit.safety,
};
writeJson(`source-parity-shard-${SHARD_INDEX}.json`, output);
if (!pass) process.exitCode = 20;
