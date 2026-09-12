import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { Readable } from "node:stream";
import { createGunzip } from "node:zlib";
import { createHash } from "node:crypto";
import {
  classifyMinuteAbsence,
  classifyTickBulkScope,
  compareTimestampHypotheses,
  minuteLabelFromTickTime,
  parseCsvLine,
  tierFromQuality,
} from "./lib/phase57-jquants-stage1-quality.mjs";

const API_BASE = "https://api.jquants.com/";
const API_KEY = String(process.env.JQUANTS_API_KEY ?? "").trim();
const PRECOMMIT_PATH = process.env.STAGE1_PRECOMMIT_PATH ?? "predict/research/phase57-exit-v4-jquants-stage1-precommit-v1.json";
const OUT_DIR = process.env.OUTPUT_DIR ?? "artifacts/phase57-exit-v4-jquants-stage1";
const MAX_COMPRESSED_BYTES = 750_000_000;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const sha256 = (value) => createHash("sha256").update(value).digest("hex");

function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function safeError(error) { return String(error?.message ?? error).replace(/[A-Za-z0-9_-]{24,}/g, "[REDACTED]"); }
function writeJson(name, value) {
  fs.mkdirSync(OUT_DIR, { recursive: true, mode: 0o700 });
  const text = `${JSON.stringify(value, null, 2)}\n`;
  fs.writeFileSync(path.join(OUT_DIR, name), text, { mode: 0o600 });
  fs.writeFileSync(path.join(OUT_DIR, `${name}.sha256`), `${sha256(text)}  ${name}\n`, { mode: 0o600 });
}

async function requestJson(pathname, query) {
  const url = new URL(pathname, API_BASE);
  for (const [key, value] of Object.entries(query)) if (value !== null && value !== undefined && String(value) !== "") url.searchParams.set(key, String(value));
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const response = await fetch(url, {
      cache: "no-store",
      redirect: "error",
      headers: { Accept: "application/json", "x-api-key": API_KEY },
      signal: AbortSignal.timeout(90_000),
    });
    const responseText = await response.text();
    if (response.ok) return JSON.parse(responseText);
    if ((response.status === 429 || response.status >= 500) && attempt < 3) { await sleep(5000 * (attempt + 1)); continue; }
    if (response.status === 401) throw new Error("AUTH_REJECTED");
    if (response.status === 403) throw new Error("BLOCKED_ENTITLEMENT");
    let providerCode = "UNSPECIFIED";
    try {
      const parsed = JSON.parse(responseText);
      providerCode = String(parsed?.message ?? parsed?.code ?? providerCode).replace(/[^A-Za-z0-9_.-]/g, "_").slice(0, 80);
    } catch {}
    const pathCode = ({
      "v2/bulk/get": "BULK_GET",
      "v2/bulk/list": "BULK_LIST",
      "v2/equities/bars/minute": "MINUTE",
      "v2/equities/bars/daily": "DAILY",
      "v2/equities/master": "MASTER",
    })[pathname] ?? "OTHER";
    throw new Error(`HTTP:${response.status};PATH:${pathCode};CODE:${providerCode}`);
  }
  throw new Error("JQUANTS_REQUEST_EXHAUSTED");
}

async function fetchAll(pathname, query) {
  const rows = [];
  const seen = new Set();
  let paginationKey = "";
  for (let page = 0; page < 100; page += 1) {
    if (page) await sleep(1100);
    const payload = await requestJson(pathname, { ...query, pagination_key: paginationKey });
    assert(Array.isArray(payload?.data), "JQUANTS_SCHEMA_INVALID");
    rows.push(...payload.data);
    const next = String(payload.pagination_key ?? payload.paginationKey ?? "");
    if (!next) return rows;
    assert(!seen.has(next), "JQUANTS_PAGINATION_REPEATED");
    seen.add(next); paginationKey = next;
  }
  throw new Error("JQUANTS_PAGINATION_LIMIT");
}

function normalizeCode(value) { return String(value ?? "").trim().toUpperCase(); }

async function fetchTickProbe(probe) {
  const listPayload = await requestJson("v2/bulk/list", { endpoint: "/equities/trades", from: probe.sessionDate, to: probe.sessionDate });
  assert(Array.isArray(listPayload?.data), "TICK_BULK_LIST_SCHEMA_INVALID");
  assert(listPayload.data.length > 0, "TICK_BULK_FILE_NOT_FOUND");
  const scope = classifyTickBulkScope(listPayload.data, probe.sessionDate);
  if (scope.scope !== "DAY") {
    if (scope.scope === "MONTH") throw new Error("POLICY_STOP:TICK_FILE_SCOPE_MONTH:RAW_DOWNLOAD_NOT_STARTED");
    throw new Error("POLICY_STOP:TICK_FILE_SCOPE_UNKNOWN:RAW_DOWNLOAD_NOT_STARTED");
  }
  const daily = scope.file;
  assert(daily.size <= MAX_COMPRESSED_BYTES, "POLICY_STOP:TICK_DAILY_FILE_TOO_LARGE:RAW_DOWNLOAD_NOT_STARTED");
  const payload = await requestJson("v2/bulk/get", { key: daily.key });
  const signedUrl = String(payload?.url ?? payload?.URL ?? payload?.Url ?? "");
  assert(/^https:\/\//.test(signedUrl), "BULK_SIGNED_URL_MISSING");
  const response = await fetch(signedUrl, { cache: "no-store", redirect: "follow", signal: AbortSignal.timeout(45 * 60_000) });
  assert(response.ok && response.body, `TICK_BULK_HTTP_${response.status}`);
  const compressedLength = Number(response.headers.get("content-length") ?? 0);
  assert(!compressedLength || compressedLength <= MAX_COMPRESSED_BYTES, "TICK_BULK_TOO_LARGE_FOR_MINIMAL_PILOT");

  const selectedLabels = new Set(probe.minuteLabels);
  const selectedRows = [];
  let header = null;
  let scannedRows = 0;
  let sessionDistinctionViolations = 0;
  const input = Readable.fromWeb(response.body).pipe(createGunzip());
  const lines = readline.createInterface({ input, crlfDelay: Infinity });
  for await (const rawLine of lines) {
    const line = rawLine.replace(/^\uFEFF/, "");
    if (!header) { header = parseCsvLine(line); continue; }
    if (!line) continue;
    scannedRows += 1;
    const values = parseCsvLine(line);
    const row = Object.fromEntries(header.map((name, index) => [name, values[index] ?? ""]));
    if (String(row.Date) !== probe.sessionDate || normalizeCode(row.Code) !== probe.sourceCode) continue;
    const label = minuteLabelFromTickTime(row.Time);
    if (!selectedLabels.has(label)) continue;
    const expectedSession = label < "12:00" ? "01" : "02";
    if (String(row.SessionDistinction) !== expectedSession) sessionDistinctionViolations += 1;
    selectedRows.push({ Time: row.Time, Price: row.Price, TradingVolume: row.TradingVolume });
  }
  assert(header, "TICK_CSV_HEADER_MISSING");
  return { selectedRows, scannedRows, sessionDistinctionViolations, compressedLength };
}

function aggregateMinuteDay(rows) {
  const observed = rows.filter((row) => Number.isFinite(Number(row.O)) && Number.isFinite(Number(row.C)));
  if (!observed.length) return null;
  return {
    open: Number(observed[0].O), high: Math.max(...observed.map((row) => Number(row.H))),
    low: Math.min(...observed.map((row) => Number(row.L))), close: Number(observed.at(-1).C),
    volume: observed.reduce((sum, row) => sum + Number(row.Vo), 0),
  };
}

function dailyRawMatchesMinute(daily, minute) {
  if (!daily || !minute) return false;
  return Number(daily.O) === minute.open && Number(daily.H) === minute.high && Number(daily.L) === minute.low &&
    Number(daily.C) === minute.close && Number(daily.Vo) === minute.volume;
}

const precommit = readJson(PRECOMMIT_PATH);
assert(precommit.status === "PRECOMMITTED_BEFORE_PROVIDER_PROBE", "STAGE1_NOT_PRECOMMITTED");
assert(precommit.sessions.length === 3 && precommit.sessionClassification === "ALREADY_EXPOSED_PURGE_QUALITY_EVIDENCE", "PILOT_SCOPE_INVALID");
assert(API_KEY, "JQUANTS_API_KEY_REQUIRED");

let output;
try {
  const probe = precommit.tickProbe;
  const tick = await fetchTickProbe(probe);
  const [minuteRows, dailyRows, masterRows] = await Promise.all([
    fetchAll("v2/equities/bars/minute", { code: probe.sourceCode, date: probe.sessionDate }),
    fetchAll("v2/equities/bars/daily", { code: probe.sourceCode, date: probe.sessionDate }),
    fetchAll("v2/equities/master", { date: probe.sessionDate }),
  ]);
  const sourceMinutes = minuteRows.filter((row) => normalizeCode(row.Code) === probe.sourceCode);
  const sourceTicks = tick.selectedRows;
  const timestamp = compareTimestampHypotheses(sourceMinutes, sourceTicks, probe.minuteLabels);
  const daily = dailyRows.find((row) => normalizeCode(row.Code) === probe.sourceCode) ?? null;
  const listedAtSession = masterRows.some((row) => normalizeCode(row.Code) === probe.sourceCode && String(row.Date) === probe.sessionDate);
  const minuteByLabel = new Map(sourceMinutes.map((row) => [String(row.Time), row]));
  const tickLabels = new Set(sourceTicks.map((row) => minuteLabelFromTickTime(row.Time)));
  const dailyHasTrade = Number(daily?.Vo ?? 0) > 0;
  const absenceCounts = {};
  for (const label of probe.minuteLabels) {
    const classification = classifyMinuteAbsence({ listedAtSession, dailyRowPresent: Boolean(daily), dailyHasTrade, tickObserved: tickLabels.has(label), minuteObserved: minuteByLabel.has(label) });
    absenceCounts[classification] = (absenceCounts[classification] ?? 0) + 1;
  }
  const adjustmentFactor = daily?.AdjFactor ?? null;
  const exRightType = daily?.ExRT ?? null;
  const rawDailyParity = dailyRawMatchesMinute(daily, aggregateMinuteDay(sourceMinutes));
  const timestampPass = timestamp.conclusion === "BAR_START_HALF_OPEN" && tick.sessionDistinctionViolations === 0;
  const quality = {
    timestamp: timestampPass ? "PASS" : "FAIL",
    fiveMinuteAggregation: timestampPass ? "PASS" : "FAIL",
    historicalProviderAvailableAt: "FAIL",
    universe: listedAtSession ? "CONDITIONAL_PASS" : "FAIL",
    adjustment: rawDailyParity ? "CONDITIONAL_PASS" : "FAIL",
    missing: Object.hasOwn(absenceCounts, "MISSING_PROVIDER_MINUTE") ? "FAIL" : "CONDITIONAL_PASS",
    hybridParity: "NOT_EXECUTED_INPUT_SUBSTRATE_ONLY",
    entryParity: "NOT_EXECUTED_INPUT_SUBSTRATE_ONLY",
    pitViolations: listedAtSession ? 0 : 1,
  };
  const tier = tierFromQuality(quality);
  output = {
    schemaVersion: 1,
    phase: "57.exit-v4.jquants-stage1-minimal-quality-parity",
    status: timestampPass && rawDailyParity ? "QUALITY_PILOT_PASS_WITH_LIMITATIONS" : "QUALITY_PILOT_FAIL",
    pilotId: precommit.pilotId,
    sessionsOpened: [probe.sessionDate],
    sessionsReusedFromExistingEvidence: precommit.sessions,
    newSessionAccess: 0,
    timestamp: {
      conclusion: timestamp.conclusion,
      observedProbeCount: timestamp.observedProbeCount,
      sameLabelMatches: timestamp.sameMatches,
      nextLabelMatches: timestamp.nextMatches,
      timezone: "JST_INFERRED_FROM_TSE_CLOCK_AND_TICK_SESSION_NOT_EXPLICIT_ENDPOINT_FIELD",
      rawPricesPersisted: false,
    },
    fiveMinuteContract: {
      sourceMinuteMeaning: timestampPass ? "BAR_START_HALF_OPEN" : "UNRESOLVED",
      firstRegularBar: timestampPass ? { includedMinuteLabels: ["09:00", "09:01", "09:02", "09:03", "09:04"], barStartJst: "09:00", barEndJst: "09:05", decisionTimestampJst: "09:05", replayAvailableAtJst: "09:05", providerHistoricalAvailableAtJst: "DAILY_AROUND_16:30_NOT_INTRADAY" } : null,
      lunchCrossingAllowed: false,
      terminalAuctionMinutesSeparated: true,
      missingMinuteFillAllowed: false,
    },
    providerAvailability: {
      endpointAvailableAtField: false,
      officialUpdateCadence: "DAILY_AROUND_16:30_JST",
      causalClaim: "RECONSTRUCTED_EVENT_TIME_ONLY_NOT_PROVIDER_INTRADAY_AVAILABILITY",
    },
    sessionBoundary: {
      sessionDistinctionViolations: tick.sessionDistinctionViolations,
      morningTerminalMinuteObserved: minuteByLabel.has("11:30"),
      afternoonOpeningMinuteObserved: minuteByLabel.has("12:30"),
      afternoonTerminalMinuteObserved: minuteByLabel.has("15:30"),
    },
    missingSemantics: {
      absenceCounts,
      fullReasonClassificationPossible: false,
      unresolvedAbsenceRemainsUnknown: true,
      providerFailureRule: "TICK_PRESENT_AND_MINUTE_ABSENT_ONLY",
      suspensionEndpointFound: false,
    },
    adjustmentAndCorporateAction: {
      minuteSchemaAdjustmentFields: false,
      tickAdjustedPricesProvided: false,
      dailyRawOhlcvParity: rawDailyParity,
      dailyAdjustmentFactorPresent: adjustmentFactor !== null && adjustmentFactor !== "",
      dailyExRightTypePresent: exRightType !== null && exRightType !== "",
      selectedSessionCorporateActionFlagged: (adjustmentFactor !== null && adjustmentFactor !== "" && Number(adjustmentFactor) !== 1) || (exRightType !== null && exRightType !== ""),
      priceBasis: rawDailyParity ? "UNADJUSTED_RAW_CONFIRMED_FOR_SELECTED_SYMBOL_SESSION" : "UNKNOWN",
      historicalCoverage: "PARTIAL_SPLIT_REVERSE_SPLIT_RIGHTS_ONLY_OTHER_ACTIONS_AND_CODE_CHANGES_REQUIRE_EXCLUSION_OR_SEPARATE_LEDGER",
    },
    pitUniverse: {
      datedMasterContainsPilotCode: listedAtSession,
      historicalSnapshotAvailable: true,
      exactCodeChangeMergerDelistingMappingAvailable: false,
      status: listedAtSession ? "CONDITIONAL_PASS" : "FAIL",
    },
    inputParity: {
      existingThreeSessionSourceHashesRemainPrecommitted: true,
      hybridFeatureCalculationPerformed: false,
      mshEntryCalculationPerformed: false,
      exitCalculationPerformed: false,
      status: "SUBSTRATE_PARITY_ONLY_FEATURE_LEVEL_GOLDEN_PARITY_NOT_ESTABLISHED",
    },
    quality,
    tier,
    fullReplayEligibleSessions: 0,
    rawPersisted: false,
    developmentUnlocked: false,
    validationUnlocked: false,
    outcomeInspectionPerformed: false,
    labelGenerationPerformed: false,
    protected180To282Opened: 0,
    freshValidationOpened: 0,
    freshOosOpened: 0,
    safety: precommit.safety,
  };
} catch (error) {
  const policyStop = String(error?.message ?? error).startsWith("POLICY_STOP:");
  output = {
    schemaVersion: 1,
    phase: "57.exit-v4.jquants-stage1-minimal-quality-parity",
    status: policyStop ? "STOP_DATA_SOURCE_NOT_READY" : "QUALITY_PILOT_BLOCKED",
    pilotId: precommit.pilotId,
    error: safeError(error),
    stage1Gate: policyStop ? "STOP_DATA_SOURCE_NOT_READY" : "BLOCKED_TECHNICAL_ERROR",
    rawDownloadStarted: policyStop ? false : "UNKNOWN_FAIL_CLOSED",
    newSessionAccess: 0,
    fullReplayEligibleSessions: 0,
    rawPersisted: false,
    developmentUnlocked: false,
    outcomeInspectionPerformed: false,
    protected180To282Opened: 0,
    freshValidationOpened: 0,
    freshOosOpened: 0,
    safety: precommit.safety,
  };
}
writeJson("stage1-quality-pilot.json", output);
if (!output.status.startsWith("QUALITY_PILOT_PASS") && output.status !== "STOP_DATA_SOURCE_NOT_READY") process.exitCode = 20;
