import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { gunzipSync, gzipSync } from 'node:zlib';
import {
  ENTRY_V2_HISTORICAL_DAILY_POLICY,
  ENTRY_V2_HISTORICAL_DAILY_SAFETY,
  buildYahooDailyChartUrl,
  normalizeYahooDailyChartPayload,
} from '../predict/daytrade/phase57-entry-quality-v2-historical-daily-data.js';

const arg = (name, fallback = null) => {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
};
const scopePath = path.resolve(arg('--selection-symbols', 'tmp/entry-v2-market-first-selection-symbols.json'));
const universePath = path.resolve(arg('--universe', 'data/screener-universe.json'));
const outputDir = path.resolve(arg('--output-dir', 'tmp/entry-v2-historical-daily'));
const queryRange = String(arg('--range', ENTRY_V2_HISTORICAL_DAILY_POLICY.defaultRange));
const concurrency = Number(arg('--concurrency', '24'));
const progressEvery = Number(arg('--progress-every', '25'));
const maximumSymbols = Number(arg('--max-symbols', '0'));
if (!/^\d+(?:d|mo|y)$/.test(queryRange)
  || !Number.isInteger(concurrency) || concurrency < 1 || concurrency > 64
  || !Number.isInteger(progressEvery) || progressEvery < 1
  || !Number.isInteger(maximumSymbols) || maximumSymbols < 0) {
  throw new Error('usage: [--selection-symbols <json>] [--universe <json>] [--output-dir <dir>] '
    + '[--range 2y] [--concurrency 1..64] [--max-symbols N]');
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
  if (ENTRY_V2_HISTORICAL_DAILY_SAFETY[key] !== false) throw new Error(`ENTRY_V2_HISTORICAL_DAILY_UNSAFE_${key}`);
}

const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const safeName = symbol => String(symbol).replace(/[^A-Za-z0-9_-]/g, '_');
const relative = file => path.relative(outputDir, file).split(path.sep).join('/');
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
const writeAtomicBytes = (file, bytes) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, bytes);
  fs.renameSync(temporary, file);
};
const writeAtomicJson = (file, value) => writeAtomicBytes(file, Buffer.from(`${JSON.stringify(value, null, 2)}\n`));

const scopeBytes = fs.readFileSync(scopePath);
const scope = JSON.parse(scopeBytes.toString('utf8'));
const scopeCore = structuredClone(scope);
delete scopeCore.selectionScopeContentSha256;
if (scope.phase !== '57.entry-quality-v2.market-first-selection-symbol-scope'
  || scope.sourceClass !== 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED'
  || scope.prospective !== false || scope.formalOos !== false
  || scope.dailyDataMayInfluenceHistoricalSelectorReplay !== false
  || scope.candidateOutcomeUsedToChooseSymbols !== false
  || sha256(Buffer.from(JSON.stringify(scopeCore))) !== scope.selectionScopeContentSha256) {
  throw new Error('ENTRY_V2_HISTORICAL_DAILY_SELECTION_SCOPE_INVALID');
}
for (const key of FALSE_KEYS) {
  if (scope.safety?.[key] !== false) throw new Error(`ENTRY_V2_HISTORICAL_DAILY_SCOPE_UNSAFE_${key}`);
}

const universeBytes = fs.readFileSync(universePath);
const universe = JSON.parse(universeBytes.toString('utf8'));
const universeIndex = new Map((universe?.entries ?? []).map(entry => [String(entry?.symbol ?? '').trim().toUpperCase(), {
  code: String(entry?.code ?? ''),
  symbol: String(entry?.symbol ?? '').trim().toUpperCase(),
  name: String(entry?.name ?? entry?.symbol ?? ''),
  sector: String(entry?.sector ?? '未分類'),
  market: entry?.market ?? null,
}]));
const allSymbols = [...new Set((scope.symbols ?? []).map(value => String(value).trim().toUpperCase()).filter(Boolean))].sort();
if (!allSymbols.length || allSymbols.length !== Number(scope.symbolCount)) {
  throw new Error('ENTRY_V2_HISTORICAL_DAILY_SCOPE_SYMBOLS_INVALID');
}
const symbols = maximumSymbols ? allSymbols.slice(0, maximumSymbols) : allSymbols;
const entries = symbols.map(symbol => universeIndex.get(symbol) ?? {
  code: symbol.replace(/\.T$/i, ''), symbol, name: symbol, sector: '未分類', market: null,
});

const rawDir = path.join(outputDir, 'raw-provider-responses');
const normalizedDir = path.join(outputDir, 'normalized-symbol-series');
const receiptDir = path.join(outputDir, 'receipts');
for (const directory of [rawDir, normalizedDir, receiptDir]) fs.mkdirSync(directory, { recursive: true });

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
  if (!fs.existsSync(files.raw) || !fs.existsSync(files.normalized) || !fs.existsSync(files.receipt)) return null;
  try {
    const receipt = readJson(files.receipt);
    const rawCompressed = fs.readFileSync(files.raw);
    const normalizedCompressed = fs.readFileSync(files.normalized);
    if (receipt.status !== 'ENTRY_V2_YAHOO_DAILY_SYMBOL_FETCH_READY'
      || receipt.symbol !== entry.symbol || receipt.queryRange !== queryRange || receipt.interval !== '1d'
      || sha256(rawCompressed) !== receipt.rawCompressedFileSha256
      || sha256(gunzipSync(rawCompressed)) !== receipt.rawResponseSha256
      || sha256(normalizedCompressed) !== receipt.normalizedCompressedFileSha256
      || sha256(gunzipSync(normalizedCompressed)) !== receipt.normalizedPayloadSha256) return null;
    return receipt;
  } catch {
    return null;
  }
}

async function fetchSymbol(entry) {
  const existing = validExistingReceipt(entry);
  if (existing) return { status: 'resumed', receipt: existing };
  const files = pathsFor(entry.symbol);
  const errors = [];
  for (let attempt = 1; attempt <= 4; attempt += 1) {
    const host = attempt % 2 === 1 ? 1 : 2;
    const requestUrl = buildYahooDailyChartUrl({ symbol: entry.symbol, range: queryRange, host });
    try {
      const response = await fetch(requestUrl, {
        headers: { 'User-Agent': 'Mozilla/5.0 ArkTerminalResearch/1.0', Accept: 'application/json' },
        cache: 'no-store',
        signal: AbortSignal.timeout(60_000),
      });
      const rawBytes = Buffer.from(await response.arrayBuffer());
      if (!response.ok) throw new Error(`HTTP_${response.status}:${rawBytes.toString('utf8').slice(0, 240)}`);
      const fetchedAt = new Date().toISOString();
      const normalized = normalizeYahooDailyChartPayload({
        payload: JSON.parse(rawBytes.toString('utf8')),
        symbol: entry.symbol,
        universeEntry: entry,
        retrievedAt: fetchedAt,
        queryRange,
      });
      const normalizedBytes = Buffer.from(`${JSON.stringify(normalized)}\n`);
      const rawCompressed = gzipSync(rawBytes, { level: 9, mtime: 0 });
      const normalizedCompressed = gzipSync(normalizedBytes, { level: 9, mtime: 0 });
      writeAtomicBytes(files.raw, rawCompressed);
      writeAtomicBytes(files.normalized, normalizedCompressed);
      const records = normalized.series.records;
      const receipt = {
        schemaVersion: 1,
        phase: ENTRY_V2_HISTORICAL_DAILY_POLICY.phase,
        status: 'ENTRY_V2_YAHOO_DAILY_SYMBOL_FETCH_READY',
        sourceClass: ENTRY_V2_HISTORICAL_DAILY_POLICY.sourceClass,
        datasetRole: 'DEVELOPMENT_ONLY',
        prospective: false,
        formalOos: false,
        symbol: entry.symbol,
        provider: ENTRY_V2_HISTORICAL_DAILY_POLICY.provider,
        requestUrl,
        queryRange,
        interval: '1d',
        fetchedAt,
        responseHttpStatus: response.status,
        rawFile: relative(files.raw),
        rawResponseSha256: sha256(rawBytes),
        rawCompressedFileSha256: sha256(rawCompressed),
        normalizedFile: relative(files.normalized),
        normalizedPayloadSha256: sha256(normalizedBytes),
        normalizedCompressedFileSha256: sha256(normalizedCompressed),
        acceptedDailyRecordCount: records.length,
        firstSessionDate: records[0].sessionDate,
        lastSessionDate: records.at(-1).sessionDate,
        corporateActionEventCounts: normalized.series.corporateActionEventCounts,
        parserVersion: 'ENTRY_V2_YAHOO_DAILY_PARSER_V1',
        normalizationVersion: 'ENTRY_V2_YAHOO_DAILY_PROVIDER_SESSION_V1',
        adjustedPriceSemantics: 'PROVIDER_QUOTE_OHLC_USED;ADJUSTED_CLOSE_AUDIT_ONLY;CORPORATE_ACTION_SEMANTICS_UNRESOLVED',
        sourceLineage: { archivedPointInTimeCapture: false, reconstructionFetchedAfterDecision: true },
        safety: ENTRY_V2_HISTORICAL_DAILY_SAFETY,
      };
      writeAtomicJson(files.receipt, receipt);
      return { status: 'fetched', receipt };
    } catch (error) {
      errors.push({ attempt, host, reason: String(error?.message ?? error) });
      if (attempt < 4) await sleep(500 * attempt);
    }
  }
  return { status: 'failed', failure: { symbol: entry.symbol, reason: errors.at(-1)?.reason ?? 'UNKNOWN', attempts: errors } };
}

let cursor = 0;
let completed = 0;
let fetchedCount = 0;
let resumedCount = 0;
const receipts = [];
const failures = [];
async function worker() {
  while (cursor < entries.length) {
    const index = cursor;
    cursor += 1;
    const result = await fetchSymbol(entries[index]);
    completed += 1;
    if (result.status === 'failed') failures.push(result.failure);
    else {
      receipts.push(result.receipt);
      if (result.status === 'fetched') fetchedCount += 1;
      else resumedCount += 1;
    }
    if (completed % progressEvery === 0 || completed === entries.length) {
      console.log(JSON.stringify({ phase: 'DAILY_FETCH', completed, total: entries.length, fetchedCount, resumedCount, failedCount: failures.length }));
    }
  }
}
await Promise.all(Array.from({ length: Math.min(concurrency, entries.length) }, () => worker()));
receipts.sort((left, right) => left.symbol.localeCompare(right.symbol));
failures.sort((left, right) => left.symbol.localeCompare(right.symbol));

const manifestCore = {
  schemaVersion: 1,
  phase: ENTRY_V2_HISTORICAL_DAILY_POLICY.phase,
  status: failures.length ? 'ENTRY_V2_HISTORICAL_DAILY_ARCHIVE_INCOMPLETE' : 'ENTRY_V2_HISTORICAL_DAILY_ARCHIVE_READY',
  createdAt: new Date().toISOString(),
  sourceClass: ENTRY_V2_HISTORICAL_DAILY_POLICY.sourceClass,
  classification: {
    datasetRole: 'DEVELOPMENT_ONLY', nonProspective: true, prospective: false, formalOos: false,
    archivedPointInTime: false, actualDurable: false, promotionEligible: false,
  },
  provider: ENTRY_V2_HISTORICAL_DAILY_POLICY.provider,
  queryRange,
  interval: '1d',
  requestedSymbolCount: entries.length,
  fetchedSymbolCount: receipts.length,
  failedSymbolCount: failures.length,
  failures,
  selectionScope: {
    file: path.relative(process.cwd(), scopePath),
    fileSha256: sha256(scopeBytes),
    selectionScopeContentSha256: scope.selectionScopeContentSha256,
    marketArchiveManifestContentSha256: scope.marketArchiveManifestContentSha256,
    fullSelectionSymbolCount: allSymbols.length,
    requestedSelectionSymbolCount: entries.length,
    currentDynamic5mSelectionOnly: true,
    candidateOutcomeUsedToChooseSymbols: false,
    dailyDataUsedByHistoricalSelector: false,
  },
  universe: {
    file: path.relative(process.cwd(), universePath),
    fileSha256: sha256(universeBytes),
    metadataMatchedSymbolCount: entries.filter(entry => universeIndex.has(entry.symbol)).length,
    metadataMissingSymbolCount: entries.filter(entry => !universeIndex.has(entry.symbol)).length,
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
    acceptedDailyRecordCount: receipt.acceptedDailyRecordCount,
    firstSessionDate: receipt.firstSessionDate,
    lastSessionDate: receipt.lastSessionDate,
    corporateActionEventCounts: receipt.corporateActionEventCounts,
  })),
  dataSemantics: {
    priorSessionSliceAppliedSeparatelyPerDecision: true,
    sameSessionFinalDailyForbidden: true,
    adjustedCloseStoredForAuditOnly: true,
    adjustedCloseUsedAsFeature: false,
    providerQuoteCorporateActionSemanticsResolved: false,
    missingDailyBarsInterpolatedOrFabricated: false,
  },
  versions: {
    parser: 'ENTRY_V2_YAHOO_DAILY_PARSER_V1',
    normalization: 'ENTRY_V2_YAHOO_DAILY_PROVIDER_SESSION_V1',
    archive: 'ENTRY_V2_HISTORICAL_DAILY_ARCHIVE_V1',
  },
  safety: ENTRY_V2_HISTORICAL_DAILY_SAFETY,
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
  sourceClass: manifest.sourceClass,
  prospective: manifest.classification.prospective,
  safety: manifest.safety,
}, null, 2));
