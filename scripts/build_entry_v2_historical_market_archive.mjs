import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { once } from 'node:events';
import { createGzip, gunzipSync, gzipSync } from 'node:zlib';
import {
  ENTRY_V2_HISTORICAL_MARKET_POLICY,
  ENTRY_V2_HISTORICAL_MARKET_SAFETY,
  buildYahooChartUrl,
  normalizeYahooChartPayload,
  partitionHistoricalSeriesBySession,
} from '../predict/daytrade/phase57-entry-quality-v2-historical-market-data.js';

const arg = (name, fallback = null) => {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
};
const universePath = path.resolve(arg('--universe', 'data/screener-universe.json'));
const outputDir = path.resolve(arg('--output-dir', 'tmp/entry-v2-historical-market'));
const queryRange = String(arg('--range', ENTRY_V2_HISTORICAL_MARKET_POLICY.defaultRange));
const startSessionDate = String(arg('--start-session', ENTRY_V2_HISTORICAL_MARKET_POLICY.earliestLeakageSafeReplaySessionDate));
const endSessionDate = String(arg('--end-session', '2026-09-04'));
const concurrency = Number(arg('--concurrency', '32'));
const maximumSymbols = Number(arg('--max-symbols', '0'));
const progressEvery = Number(arg('--progress-every', '50'));
if (!/^\d+d$/.test(queryRange)
  || !/^\d{4}-\d{2}-\d{2}$/.test(startSessionDate)
  || !/^\d{4}-\d{2}-\d{2}$/.test(endSessionDate)
  || endSessionDate < startSessionDate
  || startSessionDate < ENTRY_V2_HISTORICAL_MARKET_POLICY.earliestLeakageSafeReplaySessionDate
  || !Number.isInteger(concurrency) || concurrency < 1 || concurrency > 64
  || !Number.isInteger(maximumSymbols) || maximumSymbols < 0
  || !Number.isInteger(progressEvery) || progressEvery < 1) {
  throw new Error('usage: [--universe <json>] [--output-dir <dir>] [--range 30d|60d] '
    + '[--start-session YYYY-MM-DD] [--end-session YYYY-MM-DD] [--concurrency 1..64] [--max-symbols N]');
}

const FALSE_KEYS = [
  'executionAllowed',
  'brokerWriteAllowed',
  'excelOrderWriteAllowed',
  'rssOrderFunctionAllowed',
  'liveTradingAllowed',
  'paperTradingAllowed',
  'automaticPromotionAllowed',
  'productionUpdateAllowed',
  'transmitted',
];
for (const key of FALSE_KEYS) {
  if (ENTRY_V2_HISTORICAL_MARKET_SAFETY[key] !== false) throw new Error(`ENTRY_V2_HISTORICAL_MARKET_UNSAFE_${key}`);
}

const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const relative = file => path.relative(outputDir, file).split(path.sep).join('/');
const safeName = symbol => String(symbol).replace(/[^A-Za-z0-9_-]/g, '_');
const writeAtomicBytes = (file, bytes) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, bytes);
  fs.renameSync(temporary, file);
};
const writeAtomicJson = (file, value) => writeAtomicBytes(file, Buffer.from(`${JSON.stringify(value, null, 2)}\n`));
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

const universeBytes = fs.readFileSync(universePath);
const universe = JSON.parse(universeBytes.toString('utf8'));
const sourceDateRaw = String(universe?.meta?.sourceDate ?? '');
const universeSourceDate = /^\d{8}$/.test(sourceDateRaw)
  ? `${sourceDateRaw.slice(0, 4)}-${sourceDateRaw.slice(4, 6)}-${sourceDateRaw.slice(6, 8)}`
  : sourceDateRaw;
if (!/^\d{4}-\d{2}-\d{2}$/.test(universeSourceDate) || universeSourceDate > startSessionDate) {
  throw new Error('ENTRY_V2_HISTORICAL_UNIVERSE_NOT_KNOWN_BEFORE_REPLAY_START');
}
const allEntries = Array.isArray(universe?.entries) ? universe.entries : [];
const entries = (maximumSymbols ? allEntries.slice(0, maximumSymbols) : allEntries).map(entry => ({
  code: String(entry?.code ?? ''),
  symbol: String(entry?.symbol ?? '').trim().toUpperCase(),
  name: String(entry?.name ?? entry?.symbol ?? ''),
  sector: String(entry?.sector ?? '未分類'),
  market: entry?.market ?? null,
}));
if (!entries.length || entries.some(entry => !entry.symbol)
  || new Set(entries.map(entry => entry.symbol)).size !== entries.length) {
  throw new Error('ENTRY_V2_HISTORICAL_UNIVERSE_INVALID_OR_DUPLICATE');
}

const rawDir = path.join(outputDir, 'raw-provider-responses');
const normalizedDir = path.join(outputDir, 'normalized-symbol-series');
const receiptDir = path.join(outputDir, 'receipts');
const sessionDir = path.join(outputDir, 'normalized-session-shards');
for (const directory of [rawDir, normalizedDir, receiptDir, sessionDir]) fs.mkdirSync(directory, { recursive: true });

function pathsFor(symbol) {
  const name = safeName(symbol);
  return {
    raw: path.join(rawDir, `${name}.json.gz`),
    normalized: path.join(normalizedDir, `${name}.json.gz`),
    receipt: path.join(receiptDir, `${name}.json`),
  };
}

function validExistingReceipt(entry) {
  const files = pathsFor(entry.symbol);
  if (!fs.existsSync(files.receipt) || !fs.existsSync(files.raw) || !fs.existsSync(files.normalized)) return null;
  try {
    const receipt = readJson(files.receipt);
    if (receipt.symbol !== entry.symbol || receipt.queryRange !== queryRange || receipt.interval !== '5m'
      || receipt.status !== 'ENTRY_V2_YAHOO_CHART_SYMBOL_FETCH_READY') return null;
    const rawCompressed = fs.readFileSync(files.raw);
    const normalizedCompressed = fs.readFileSync(files.normalized);
    if (sha256(rawCompressed) !== receipt.rawCompressedFileSha256
      || sha256(gunzipSync(rawCompressed)) !== receipt.rawResponseSha256
      || sha256(normalizedCompressed) !== receipt.normalizedCompressedFileSha256
      || sha256(gunzipSync(normalizedCompressed)) !== receipt.normalizedPayloadSha256) return null;
    return receipt;
  } catch {
    return null;
  }
}

async function fetchSymbol(entry) {
  const files = pathsFor(entry.symbol);
  const existing = validExistingReceipt(entry);
  if (existing) return { status: 'resumed', receipt: existing };
  const errors = [];
  for (let attempt = 1; attempt <= 4; attempt += 1) {
    const host = attempt % 2 === 1 ? 1 : 2;
    const url = buildYahooChartUrl({ symbol: entry.symbol, range: queryRange, interval: '5m', host });
    try {
      const response = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0 ArkTerminalResearch/1.0', Accept: 'application/json' },
        cache: 'no-store',
        signal: AbortSignal.timeout(60_000),
      });
      const rawBytes = Buffer.from(await response.arrayBuffer());
      if (!response.ok) throw new Error(`HTTP_${response.status}:${rawBytes.toString('utf8').slice(0, 240)}`);
      const retrievedAt = new Date().toISOString();
      const payload = JSON.parse(rawBytes.toString('utf8'));
      const normalized = normalizeYahooChartPayload({
        payload,
        symbol: entry.symbol,
        universeEntry: entry,
        retrievedAt,
        queryRange,
        interval: '5m',
      });
      if (Date.parse(retrievedAt) <= Date.parse(`${endSessionDate}T15:30:00+09:00`)) {
        throw new Error('FETCH_NOT_AFTER_RECONSTRUCTED_DECISIONS');
      }
      const normalizedBytes = Buffer.from(`${JSON.stringify(normalized)}\n`);
      const rawCompressed = gzipSync(rawBytes, { level: 9, mtime: 0 });
      const normalizedCompressed = gzipSync(normalizedBytes, { level: 9, mtime: 0 });
      writeAtomicBytes(files.raw, rawCompressed);
      writeAtomicBytes(files.normalized, normalizedCompressed);
      const receipt = {
        schemaVersion: 1,
        phase: ENTRY_V2_HISTORICAL_MARKET_POLICY.phase,
        status: 'ENTRY_V2_YAHOO_CHART_SYMBOL_FETCH_READY',
        sourceClass: ENTRY_V2_HISTORICAL_MARKET_POLICY.sourceClass,
        datasetRole: 'DEVELOPMENT_ONLY',
        prospective: false,
        formalOos: false,
        symbol: entry.symbol,
        provider: ENTRY_V2_HISTORICAL_MARKET_POLICY.provider,
        requestUrl: url,
        queryRange,
        interval: '5m',
        fetchedAt: retrievedAt,
        responseHttpStatus: response.status,
        rawFile: relative(files.raw),
        rawResponseSha256: sha256(rawBytes),
        rawCompressedFileSha256: sha256(rawCompressed),
        normalizedFile: relative(files.normalized),
        normalizedPayloadSha256: sha256(normalizedBytes),
        normalizedCompressedFileSha256: sha256(normalizedCompressed),
        acceptedRegularSessionBarCount: normalized.series.bars.length,
        firstBarTimestamp: normalized.series.bars[0].timestamp,
        lastBarTimestamp: normalized.series.bars.at(-1).timestamp,
        parserVersion: 'ENTRY_V2_YAHOO_CHART_PARSER_V1',
        normalizationVersion: 'ENTRY_V2_PROVIDER_NATIVE_TIMESTAMP_V1',
        adjustedPriceSemantics: 'UNADJUSTED_QUOTE_OHLC_USED;CORPORATE_ACTION_EVENTS_RETAINED_IN_RAW_RESPONSE',
        timestampSemantics: 'PROVIDER_NATIVE_TIMESTAMP_PRESERVED;OPEN_VS_CLOSE_CLASSIFICATION_REQUIRES_GOLDEN_AUDIT',
        sourceLineage: {
          archivedPointInTimeCapture: false,
          reconstructionFetchedAfterDecision: true,
        },
        safety: ENTRY_V2_HISTORICAL_MARKET_SAFETY,
      };
      writeAtomicJson(files.receipt, receipt);
      return { status: 'fetched', receipt };
    } catch (error) {
      errors.push({ attempt, host, reason: String(error?.message ?? error) });
      if (attempt < 4) await sleep(500 * attempt);
    }
  }
  return {
    status: 'failed',
    failure: { symbol: entry.symbol, reason: errors.at(-1)?.reason ?? 'UNKNOWN', attempts: errors },
  };
}

let cursor = 0;
let completed = 0;
let fetchedCount = 0;
let resumedCount = 0;
const receiptBySymbol = new Map();
const failures = [];
async function worker() {
  while (cursor < entries.length) {
    const index = cursor;
    cursor += 1;
    const result = await fetchSymbol(entries[index]);
    completed += 1;
    if (result.status === 'failed') failures.push(result.failure);
    else {
      receiptBySymbol.set(result.receipt.symbol, result.receipt);
      if (result.status === 'fetched') fetchedCount += 1;
      else resumedCount += 1;
    }
    if (completed % progressEvery === 0 || completed === entries.length) {
      console.log(JSON.stringify({ phase: 'FETCH', completed, total: entries.length, fetchedCount, resumedCount, failedCount: failures.length }));
    }
  }
}
await Promise.all(Array.from({ length: Math.min(concurrency, entries.length) }, () => worker()));
failures.sort((left, right) => left.symbol.localeCompare(right.symbol));

const sessionWriters = new Map();
function writerFor(sessionDate) {
  if (sessionWriters.has(sessionDate)) return sessionWriters.get(sessionDate);
  const file = path.join(sessionDir, `${sessionDate}.ndjson.gz`);
  const output = fs.createWriteStream(file);
  const gzip = createGzip({ level: 9, mtime: 0 });
  gzip.pipe(output);
  const writer = { sessionDate, file, output, gzip, count: 0, uncompressedHash: crypto.createHash('sha256') };
  sessionWriters.set(sessionDate, writer);
  return writer;
}

for (let index = 0; index < entries.length; index += 1) {
  const entry = entries[index];
  const receipt = receiptBySymbol.get(entry.symbol);
  if (!receipt) continue;
  const normalizedBytes = gunzipSync(fs.readFileSync(path.join(outputDir, receipt.normalizedFile)));
  const normalized = JSON.parse(normalizedBytes.toString('utf8'));
  const sessions = partitionHistoricalSeriesBySession({
    series: [normalized.series],
    startSessionDate,
    endSessionDate,
  });
  for (const [sessionDate, rows] of sessions) {
    const writer = writerFor(sessionDate);
    for (const row of rows) {
      const line = Buffer.from(`${JSON.stringify(row)}\n`);
      writer.uncompressedHash.update(line);
      writer.count += 1;
      if (!writer.gzip.write(line)) await once(writer.gzip, 'drain');
    }
  }
  if ((index + 1) % 250 === 0 || index + 1 === entries.length) {
    console.log(JSON.stringify({ phase: 'SESSION_SHARDS', completed: index + 1, total: entries.length, discoveredSessions: sessionWriters.size }));
  }
}

await Promise.all([...sessionWriters.values()].map(writer => new Promise((resolve, reject) => {
  writer.output.once('close', resolve);
  writer.output.once('error', reject);
  writer.gzip.once('error', reject);
  writer.gzip.end();
})));

const sessionShards = [...sessionWriters.values()].sort((left, right) => left.sessionDate.localeCompare(right.sessionDate)).map(writer => {
  const compressedBytes = fs.readFileSync(writer.file);
  return {
    sessionDate: writer.sessionDate,
    file: relative(writer.file),
    retainedSymbolCount: writer.count,
    uncompressedNdjsonSha256: writer.uncompressedHash.digest('hex'),
    compressedFileSha256: sha256(compressedBytes),
    compressedByteCount: compressedBytes.length,
  };
});

const receipts = entries.map(entry => receiptBySymbol.get(entry.symbol)).filter(Boolean);
const createdAt = new Date().toISOString();
const manifestCore = {
  schemaVersion: 1,
  phase: ENTRY_V2_HISTORICAL_MARKET_POLICY.phase,
  status: failures.length ? 'ENTRY_V2_HISTORICAL_MARKET_ARCHIVE_INCOMPLETE' : 'ENTRY_V2_HISTORICAL_MARKET_ARCHIVE_READY',
  createdAt,
  sourceClass: ENTRY_V2_HISTORICAL_MARKET_POLICY.sourceClass,
  classification: {
    datasetRole: 'DEVELOPMENT_ONLY',
    nonProspective: true,
    prospective: false,
    formalOos: false,
    archivedPointInTime: false,
    actualDurable: false,
    promotionEligible: false,
  },
  provider: ENTRY_V2_HISTORICAL_MARKET_POLICY.provider,
  queryRange,
  interval: '5m',
  startSessionDate,
  endSessionDate,
  requestedSymbolCount: entries.length,
  fetchedSymbolCount: receiptBySymbol.size,
  failedSymbolCount: failures.length,
  failures,
  universe: {
    source: universe?.meta?.source ?? null,
    sourceDate: universeSourceDate,
    sourceSha256: sha256(universeBytes),
    fullSnapshotSymbolCount: allEntries.length,
    requestedSnapshotSymbolCount: entries.length,
    snapshotKnownBeforeReplayStart: universeSourceDate <= startSessionDate,
    newListingsAfterSnapshotMayBeMissing: true,
    delistingsAndSymbolChangesRequireSeparateAudit: true,
    claimedAsCompleteHistoricalJpxUniverse: false,
    survivorshipBiasRisk: 'PARTIAL_PRIOR_SNAPSHOT;POST_SNAPSHOT_IPOS_MISSING_AND_CORPORATE_ACTIONS_REQUIRE_AUDIT',
  },
  receipts: receipts.map(receipt => ({
    symbol: receipt.symbol,
    fetchedAt: receipt.fetchedAt,
    rawFile: receipt.rawFile,
    rawResponseSha256: receipt.rawResponseSha256,
    rawCompressedFileSha256: receipt.rawCompressedFileSha256,
    normalizedFile: receipt.normalizedFile,
    normalizedPayloadSha256: receipt.normalizedPayloadSha256,
    normalizedCompressedFileSha256: receipt.normalizedCompressedFileSha256,
    acceptedRegularSessionBarCount: receipt.acceptedRegularSessionBarCount,
  })),
  sessionShards,
  dataSemantics: {
    currentDynamic5mSelectorAppliedDuringAcquisition: false,
    selectedSymbolsDeterminedAcquisition: false,
    oldSelectorMembershipReused: false,
    yahooSparkRejectedForMarketReplayBecauseItReturnedCloseOnly: true,
    yahooFiveMinuteEmpiricalMaximumRange: '60d',
    providerTimestampPreservedWithoutShift: true,
    providerBarOpenVsCloseSemanticClassification: 'UNRESOLVED_GOLDEN_AUDIT_REQUIRED',
    completedBarRuleForDownstreamReplay: ENTRY_V2_HISTORICAL_MARKET_POLICY.completedBarRule,
    quoteOhlcAdjusted: false,
    corporateActionEventsRetainedInRawResponse: true,
    missingBarsInterpolatedOrFabricated: false,
  },
  frozenBoundaries: {
    currentDynamic5mSelectorFixed: true,
    frozenP21EntryFixed: true,
    frozenP21HistoryEndSessionDate: ENTRY_V2_HISTORICAL_MARKET_POLICY.frozenP21HistoryEndSessionDate,
    preFrozenHistoryReplayForbidden: true,
    replayStartAfterFrozenHistory: startSessionDate > ENTRY_V2_HISTORICAL_MARKET_POLICY.frozenP21HistoryEndSessionDate,
  },
  versions: {
    parser: 'ENTRY_V2_YAHOO_CHART_PARSER_V1',
    normalization: 'ENTRY_V2_PROVIDER_NATIVE_TIMESTAMP_V1',
    archive: 'ENTRY_V2_MARKET_FIRST_ARCHIVE_V1',
  },
  safety: ENTRY_V2_HISTORICAL_MARKET_SAFETY,
};
const manifest = { ...manifestCore, manifestContentSha256: sha256(Buffer.from(JSON.stringify(manifestCore))) };
const manifestPath = path.join(outputDir, 'manifest.json');
writeAtomicJson(manifestPath, manifest);
console.log(JSON.stringify({
  status: manifest.status,
  manifest: manifestPath,
  manifestContentSha256: manifest.manifestContentSha256,
  requestedSymbolCount: manifest.requestedSymbolCount,
  fetchedSymbolCount: manifest.fetchedSymbolCount,
  failedSymbolCount: manifest.failedSymbolCount,
  sessionShards: manifest.sessionShards.map(row => ({ sessionDate: row.sessionDate, symbols: row.retainedSymbolCount })),
  sourceClass: manifest.sourceClass,
  prospective: manifest.classification.prospective,
  safety: manifest.safety,
}, null, 2));
