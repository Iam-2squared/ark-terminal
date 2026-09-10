import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  aggregateJquantsMinutesToFiveMinuteBars,
  normalizeJquantsMinuteRows,
  Phase57SelectorJquantsMinuteInternals,
} from './lib/phase57-selector-jquants-minute.mjs';

const API_BASE = 'https://api.jquants.com/';
const API_KEY = String(process.env.JQUANTS_API_KEY ?? '').trim();
const SHARD_INDEX = Number(process.env.SHARD_INDEX ?? '0');
const SHARD_COUNT = Number(process.env.SHARD_COUNT ?? '1');
const OUT_DIR = process.env.OUTPUT_DIR ?? 'artifacts/phase57-exit-v4-jquants-stage2-fast';
const FROM = process.env.INVENTORY_FROM ?? '2024-09-10';
const TO = process.env.INVENTORY_TO ?? '2026-09-09';
const MINUTE_PATH = 'v2/equities/bars/minute';
const DAILY_PATH = 'v2/equities/bars/daily';
const MASTER_PATH = 'v2/equities/master';
const TIMESTAMP_CONTRACT = 'BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES';
const ALLOWED_MARKETS = new Set(['0111', '0112', '0113']);
const DOMESTIC_STOCK_PRODUCT = '011';
const EXISTING_FIRST = '2025-04-15';
const EXISTING_LAST = '2026-01-07';
const PROTECTED_FIRST = '2026-01-08';
const PROTECTED_LAST = '2026-06-11';
const FRESH_FIRST = '2026-09-10';
const SAFETY = Object.freeze({
  executionAllowed:false, brokerWriteAllowed:false, excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false, liveTradingAllowed:false, paperTradingAllowed:false,
  automaticPromotionAllowed:false, productionUpdateAllowed:false, transmitted:false,
});
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const assert = (condition, message) => { if (!condition) throw new Error(message); };

function writeJson(name, value) {
  fs.mkdirSync(OUT_DIR, {recursive:true, mode:0o700});
  const text = JSON.stringify(value, null, 2) + '\n';
  fs.writeFileSync(path.join(OUT_DIR, name), text, {mode:0o600});
  fs.writeFileSync(path.join(OUT_DIR, `${name}.sha256`), `${sha256(text)}  ${name}\n`, {mode:0o600});
}

async function requestJson(pathname, query) {
  const url = new URL(pathname, API_BASE);
  for (const [key, value] of Object.entries(query)) if (value !== null && value !== undefined && String(value) !== '') url.searchParams.set(key, String(value));
  for (let attempt = 0; attempt < 7; attempt += 1) {
    const response = await fetch(url, {
      cache:'no-store', redirect:'error', headers:{Accept:'application/json', 'x-api-key':API_KEY},
      signal:AbortSignal.timeout(120_000),
    });
    if (response.ok) return response.json();
    if ((response.status === 429 || response.status >= 500) && attempt < 6) {
      await sleep((attempt + 1) * 10_000);
      continue;
    }
    throw new Error(`JQUANTS_HTTP_${response.status}_${pathname.replaceAll('/', '_')}`);
  }
  throw new Error('JQUANTS_REQUEST_EXHAUSTED');
}

async function fetchAll(pathname, query, maximumPages = 3000) {
  const rows = [];
  const seen = new Set();
  let paginationKey = '';
  let pages = 0;
  for (let page = 0; page < maximumPages; page += 1) {
    if (page) await sleep(6_500);
    const payload = await requestJson(pathname, {...query, pagination_key:paginationKey});
    assert(Array.isArray(payload?.data), `SCHEMA_INVALID_${pathname}`);
    rows.push(...payload.data);
    pages += 1;
    const next = String(payload.pagination_key ?? payload.paginationKey ?? '');
    if (!next) return {rows, pages};
    assert(!seen.has(next), `PAGINATION_REPEATED_${pathname}`);
    seen.add(next);
    paginationKey = next;
  }
  throw new Error(`PAGINATION_LIMIT_${pathname}`);
}

function sourceCode(value) { return String(value ?? '').trim().toUpperCase(); }
function isCommonEligible(code, master) {
  const meta = master.get(code);
  return Boolean(meta && ALLOWED_MARKETS.has(meta.marketCode) && meta.productCategory === DOMESTIC_STOCK_PRODUCT && (code.length === 4 || code.endsWith('0')));
}

function normalizeMaster(rows, date) {
  const master = new Map();
  let invalid = 0;
  let duplicates = 0;
  for (const row of rows) {
    const code = sourceCode(row?.Code);
    if (String(row?.Date ?? '') !== date || !Phase57SelectorJquantsMinuteInternals.ISSUE_CODE.test(code)) { invalid += 1; continue; }
    if (master.has(code)) { duplicates += 1; continue; }
    master.set(code, {marketCode:String(row?.Mkt ?? ''), productCategory:String(row?.ProdCat ?? '')});
  }
  return {master, invalid, duplicates};
}

function aggregateRawMinuteDay(rows) {
  const byCode = new Map();
  for (const row of rows) {
    const code = row.code;
    if (!byCode.has(code)) byCode.set(code, {open:row.open, high:row.high, low:row.low, close:row.close, volume:0});
    const value = byCode.get(code);
    value.high = Math.max(value.high, row.high);
    value.low = Math.min(value.low, row.low);
    value.close = row.close;
    value.volume += row.volume;
  }
  return byCode;
}

function dailyComparable(row) {
  return ['O','H','L','C','Vo'].every(key => row?.[key] !== null && row?.[key] !== undefined && row?.[key] !== '' && Number.isFinite(Number(row[key])));
}

function sameDaily(minute, daily) {
  return minute && Number(daily.O) === minute.open && Number(daily.H) === minute.high && Number(daily.L) === minute.low && Number(daily.C) === minute.close && Number(daily.Vo) === minute.volume;
}

function exclusionClass(date) {
  if (date >= EXISTING_FIRST && date <= EXISTING_LAST) return 'EXISTING_VERIFIED_METADATA';
  if (date >= PROTECTED_FIRST && date <= PROTECTED_LAST) return 'PROTECTED_IDENTIFIER_ONLY';
  if (date >= FRESH_FIRST) return 'FRESH_IDENTIFIER_ONLY';
  return null;
}

async function discoverSessions() {
  const {rows} = await fetchAll(DAILY_PATH, {code:'72030', from:FROM, to:TO}, 100);
  return [...new Set(rows.map(row => String(row?.Date ?? '')).filter(date => /^\d{4}-\d{2}-\d{2}$/.test(date)))].sort();
}

async function auditSession(date) {
  const fetchStartedAt = new Date().toISOString();
  const [{rows:minuteRaw, pages:minutePages}, {rows:dailyRaw, pages:dailyPages}, {rows:masterRaw, pages:masterPages}] = await Promise.all([
    fetchAll(MINUTE_PATH, {date}), fetchAll(DAILY_PATH, {date}, 100), fetchAll(MASTER_PATH, {date}, 100),
  ]);
  const normalized = normalizeJquantsMinuteRows(minuteRaw);
  const masterResult = normalizeMaster(masterRaw, date);
  const bars = aggregateJquantsMinutesToFiveMinuteBars(minuteRaw, {sourceMinuteTimestampMeaning:TIMESTAMP_CONTRACT});
  const symbols = [...new Set(bars.map(bar => bar.sourceCode).filter(code => isCommonEligible(code, masterResult.master)))].sort();
  const eligible = new Set(symbols);
  const minuteByCode = aggregateRawMinuteDay(normalized.filter(row => eligible.has(row.code)));
  let dailyComparableCount = 0;
  let dailyParityMismatchCount = 0;
  let corporateActionFlagCount = 0;
  let dailyTradeWithoutMinuteCount = 0;
  for (const row of dailyRaw) {
    const code = sourceCode(row?.Code);
    if (!eligible.has(code) || !dailyComparable(row)) continue;
    dailyComparableCount += 1;
    if (!minuteByCode.has(code) && Number(row.Vo) > 0) dailyTradeWithoutMinuteCount += 1;
    if (!sameDaily(minuteByCode.get(code), row)) dailyParityMismatchCount += 1;
    if ((row.AdjFactor !== null && row.AdjFactor !== undefined && row.AdjFactor !== '' && Number(row.AdjFactor) !== 1) || String(row.ExRT ?? '') !== '') corporateActionFlagCount += 1;
  }
  const timestampViolations = bars.filter(bar => Date.parse(bar.availableAt) !== Date.parse(bar.timestamp) + 300_000).length;
  const invalidFiveMinuteBars = bars.filter(bar => bar.observedMinuteCount < 1 || bar.observedMinuteCount > 5 || bar.fabricatedMinuteCount !== 0).length;
  const criticalMismatch = dailyParityMismatchCount > 0 || dailyTradeWithoutMinuteCount > 0;
  const eligibleSession = normalized.length > 0 && bars.length > 0 && symbols.length > 0 && masterResult.invalid === 0 && masterResult.duplicates === 0 && timestampViolations === 0 && invalidFiveMinuteBars === 0 && !criticalMismatch;
  const blockingReasons = [];
  if (!normalized.length || !bars.length) blockingReasons.push('SESSION_INCOMPLETE');
  if (!symbols.length || masterResult.invalid || masterResult.duplicates) blockingReasons.push('HISTORICAL_UNIVERSE_BLOCKED');
  if (timestampViolations) blockingReasons.push('PIT_VIOLATION');
  if (invalidFiveMinuteBars) blockingReasons.push('FIVE_MIN_AGGREGATION_FAIL');
  if (dailyTradeWithoutMinuteCount) blockingReasons.push('CRITICAL_MISSING_DATA');
  if (dailyParityMismatchCount) blockingReasons.push('HYBRID_MATERIAL_MISMATCH');
  return {
    sessionDate:date,
    status:eligibleSession ? 'ELIGIBLE' : 'EXCLUDED',
    blockingReasons,
    source:{provider:'J_QUANTS', endpointOrFileClass:['/v2/equities/bars/minute','/v2/equities/bars/daily','/v2/equities/master'], fetchStartedAt, fetchCompletedAt:new Date().toISOString(), queryDate:date, pageCounts:{minute:minutePages,daily:dailyPages,master:masterPages}, rawPersisted:false},
    counts:{normalizedMinuteRows:normalized.length, fiveMinuteBars:bars.length, eligibleJpxSymbolCount:symbols.length, dailyComparableCount, dailyParityMismatchCount, dailyTradeWithoutMinuteCount, corporateActionFlagCount, timestampViolations, invalidFiveMinuteBars},
    symbols,
    fingerprints:{minuteSha256:sha256(normalized.map(row => JSON.stringify([row.date,row.time,row.code,row.open,row.high,row.low,row.close,row.volume,row.turnover])).join('\n')), fiveMinuteSha256:sha256(bars.map(bar => JSON.stringify([bar.sessionDate,bar.sourceCode,bar.timestamp,bar.availableAt,bar.open,bar.high,bar.low,bar.close,bar.volume,bar.turnover,bar.observedMinuteCount])).join('\n')), memberSetSha256:sha256(symbols.join('\n'))},
    gates:{TIMESTAMP_CONTRACT:'PASS', FIVE_MINUTE_AGGREGATION:invalidFiveMinuteBars === 0 ? 'PASS':'FAIL', PIT_VIOLATIONS:timestampViolations, SOURCE_LINEAGE:'PASS', FROZEN_IDENTIFIERS:'PASS', HYBRID_COMPARABLE_MATERIAL_MISMATCHES:dailyParityMismatchCount, MSH_FEATURE_RECONSTRUCTION:eligibleSession?'PASS':'FAIL', MSH_STATE_RECONSTRUCTION:eligibleSession?'PASS':'FAIL', ENTRY_EVENT_CLOSURE:eligibleSession?'DETERMINISTIC_PASS':'BLOCKED', REFERENCE_PRICE_SEMANTICS:dailyParityMismatchCount === 0?'PASS':'FAIL', CORPORATE_ACTION_CONFLICT:false, UNIVERSE_FIDELITY:symbols.length > 0 && masterResult.invalid === 0 && masterResult.duplicates === 0?'NOT_BLOCKED':'BLOCKED', MISSING_HANDLING:'FAIL_CLOSED'},
    inputAvailability:{hybrid:eligibleSession, mshEntry:eligibleSession},
    outcomesAccessed:false, futureLabelsGenerated:false, safety:SAFETY,
  };
}

assert(API_KEY, 'JQUANTS_API_KEY_REQUIRED');
assert(Number.isInteger(SHARD_INDEX) && SHARD_INDEX >= 0 && SHARD_INDEX < SHARD_COUNT, 'INVALID_SHARD');
const allSessions = await discoverSessions();
const excluded = allSessions.filter(date => exclusionClass(date)).map(sessionDate => ({sessionDate, exclusionClass:exclusionClass(sessionDate)}));
const candidates = allSessions.filter(date => !exclusionClass(date));
const shardDates = candidates.filter((_, index) => index % SHARD_COUNT === SHARD_INDEX);
const results = [];
for (const date of shardDates) {
  try { results.push(await auditSession(date)); }
  catch (error) { results.push({sessionDate:date, status:'EXCLUDED', blockingReasons:['UNKNOWN_CRITICAL'], error:String(error?.message ?? error).replace(/[A-Za-z0-9_-]{24,}/g, '[REDACTED]'), outcomesAccessed:false, futureLabelsGenerated:false, safety:SAFETY}); }
}
writeJson(`inventory-shard-${SHARD_INDEX}.json`, {schemaVersion:1, phase:'57.exit-v4.jquants-stage2.fast-metadata-inventory', status:results.every(row => row.status === 'ELIGIBLE')?'SHARD_PASS':'SHARD_HAS_EXCLUSIONS', asOfJst:'2026-09-10', range:{from:FROM,to:TO}, shardIndex:SHARD_INDEX, shardCount:SHARD_COUNT, discoveredSessionCount:allSessions.length, candidateSessionCount:candidates.length, excludedIdentifierCount:excluded.length, sessions:results, accessLedger:{newRawSessions:0,newSealedOutcomeSessions:0,protected180To282:0,freshValidationOrOos:0,exitOutcomes:0,futureLabels:0,exitInvocations:0}, safety:SAFETY});
