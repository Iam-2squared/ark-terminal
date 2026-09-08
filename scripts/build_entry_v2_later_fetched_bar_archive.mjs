import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {
  buildP252Yahoo5mUrls,
  fetchP252Yahoo5mSession,
  PHASE57_P25_2J_SAFETY,
} from '../predict/daytrade/phase57-p25-2j-routine-nonrss-5m-source.js';

const arg = (name, fallback = null) => {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
};
const sessionDate = String(arg('--session-date', ''));
const measurementsPath = arg('--measurements');
const baseArchivePath = arg('--base-archive');
const outputPath = arg('--output');
const concurrency = Number(arg('--concurrency', '4'));
if (!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate) || !measurementsPath || !outputPath
  || !Number.isInteger(concurrency) || concurrency < 1 || concurrency > 8) {
  throw new Error('usage: --session-date YYYY-MM-DD --measurements <ndjson> --output <json> [--base-archive <json>] [--concurrency 1..8]');
}

const sha256 = value => crypto.createHash('sha256')
  .update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value)).digest('hex');
const symbolOf = value => String(value ?? '').trim().toUpperCase();
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const parseNdjson = file => fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean).map(JSON.parse);
const measurements = parseNdjson(measurementsPath);
const FALSE_SAFETY_KEYS = [
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
for (const key of FALSE_SAFETY_KEYS) {
  if (PHASE57_P25_2J_SAFETY?.[key] !== false) throw new Error(`unsafe reconstruction flag: ${key}`);
}
const jstSessionDate = value => {
  const timestamp = Date.parse(String(value ?? ''));
  if (!Number.isFinite(timestamp)) throw new Error('measurement observedAt invalid');
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(timestamp)).map(part => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
};
const seenMeasurements = new Set();
for (const measurement of measurements) {
  const observedAt = new Date(measurement?.observedAt ?? '').toISOString();
  if (seenMeasurements.has(observedAt)) throw new Error('duplicate measurement observedAt');
  seenMeasurements.add(observedAt);
  if (jstSessionDate(observedAt) !== sessionDate) throw new Error('measurement sessionDate mismatch');
  if (measurement?.status !== 'MARKETWIDE_DYNAMIC_5M_MEASUREMENT_READY'
    || measurement?.policy?.candidateId !== 'INTRADAY_DYNAMIC_5M_UNIVERSE_V1') {
    throw new Error('only current Dynamic5m V1 measurements are accepted');
  }
  for (const key of FALSE_SAFETY_KEYS) {
    if (measurement?.safety?.[key] !== false) throw new Error(`unsafe measurement flag: ${key}`);
  }
  const selected = Array.isArray(measurement?.selected) ? measurement.selected : [];
  if (!selected.length) throw new Error('measurement selected[] required');
  const selectedIds = selected.map(row => symbolOf(row?.symbol));
  if (selectedIds.some(symbol => !symbol) || new Set(selectedIds).size !== selectedIds.length) {
    throw new Error('measurement selected symbols invalid or duplicate');
  }
  if (selected.some(row => new Date(row?.sourceScannedAt ?? '').toISOString() !== observedAt)) {
    throw new Error('measurement selected sourceScannedAt mismatch');
  }
}
const selectedSymbols = [...new Set(measurements.flatMap(measurement => (measurement?.selected ?? [])
  .map(row => symbolOf(row?.symbol)).filter(Boolean)))].sort();
if (!selectedSymbols.length) throw new Error('no selected symbols in measurements');

const baseArchive = baseArchivePath ? readJson(baseArchivePath) : null;
if (baseArchive && String(baseArchive.sessionDate ?? baseArchive?.sessions?.[0]?.sessionDate ?? '') !== sessionDate) {
  throw new Error('base archive sessionDate mismatch');
}
if (baseArchive) {
  for (const key of FALSE_SAFETY_KEYS) {
    if (baseArchive?.safety?.[key] !== false) throw new Error(`unsafe base archive flag: ${key}`);
  }
}
const baseBars = baseArchive?.sessionBarsBySymbol ?? baseArchive?.sessions?.[0]?.sessionBarsBySymbol ?? {};
const sessionBarsBySymbol = structuredClone(baseBars);
const requestedSymbols = selectedSymbols.filter(symbol => !Array.isArray(sessionBarsBySymbol[symbol])
  || !sessionBarsBySymbol[symbol].length);
const sourceBySymbol = {};
const failures = [];
let cursor = 0;

const jst = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});
const jstParts = timestamp => Object.fromEntries(jst.formatToParts(new Date(timestamp))
  .map(part => [part.type, part.value]));
const fetchImpl = (url, options = {}) => fetch(url, { ...options, signal: AbortSignal.timeout(20_000) });

async function fetchSparseYahooSession(symbol) {
  const errors = [];
  for (const url of buildP252Yahoo5mUrls({ symbol, sessionDate })) {
    try {
      const response = await fetchImpl(url, {
        headers: { 'User-Agent': 'Mozilla/5.0 ArkTerminalResearch/1.0', Accept: 'application/json' },
        cache: 'no-store',
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const result = payload?.chart?.result?.[0];
      if (payload?.chart?.error) throw new Error(payload.chart.error?.description ?? 'Yahoo chart error');
      if (!result) throw new Error('Yahoo chart result missing');
      const quote = result.indicators?.quote?.[0] ?? {};
      const bars = (result.timestamp ?? []).map((epoch, index) => {
        const timestamp = new Date(Number(epoch) * 1000).toISOString();
        const parts = jstParts(timestamp);
        const date = `${parts.year}-${parts.month}-${parts.day}`;
        const hm = `${parts.hour}:${parts.minute}`;
        const values = [quote.open?.[index], quote.high?.[index], quote.low?.[index], quote.close?.[index], quote.volume?.[index]];
        if (date !== sessionDate || hm < '09:00' || hm > '15:30'
          || values.some(value => value === null || value === undefined || !Number.isFinite(Number(value)))) return null;
        const [open, high, low, close, volume] = values.map(Number);
        if (Math.min(open, high, low, close) <= 0 || high < Math.max(open, close)
          || low > Math.min(open, close) || volume < 0) return null;
        return { timestamp, open, high, low, close, volume };
      }).filter(Boolean).sort((left, right) => left.timestamp.localeCompare(right.timestamp));
      if (!bars.length || new Set(bars.map(bar => bar.timestamp)).size !== bars.length) {
        throw new Error('no valid unique sparse bars');
      }
      return {
        bars,
        provider: 'YAHOO_FINANCE_CHART_5M',
        requestHost: new URL(url).host,
        sourcePayloadSha256: sha256(payload),
        sparseBelowRoutineMinimum: bars.length < 30,
      };
    } catch (error) {
      errors.push(String(error?.message ?? error));
    }
  }
  throw new Error(errors.join(' | '));
}

async function fetchOne(symbol) {
  try {
    const result = await fetchP252Yahoo5mSession({ symbol, sessionDate, fetchImpl });
    return { ...result, sparseBelowRoutineMinimum: false };
  } catch {
    return fetchSparseYahooSession(symbol);
  }
}

async function worker() {
  while (cursor < requestedSymbols.length) {
    const symbol = requestedSymbols[cursor];
    cursor += 1;
    let failure = null;
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      try {
        const result = await fetchOne(symbol);
        sessionBarsBySymbol[symbol] = result.bars;
        sourceBySymbol[symbol] = {
          provider: result.provider ?? 'YAHOO_FINANCE_CHART_5M',
          requestHost: result.requestHost,
          sourcePayloadSha256: result.sourcePayloadSha256,
          acceptedBarCount: result.bars.length,
          sparseBelowRoutineMinimum: result.sparseBelowRoutineMinimum === true,
          fetchedAt: new Date().toISOString(),
        };
        failure = null;
        break;
      } catch (error) {
        failure = String(error?.message ?? error);
        if (attempt < 3) await new Promise(resolve => setTimeout(resolve, 750 * attempt));
      }
    }
    if (failure) failures.push({ symbol, reason: failure });
  }
}

await Promise.all(Array.from({ length: Math.min(concurrency, requestedSymbols.length || 1) }, () => worker()));
failures.sort((left, right) => left.symbol.localeCompare(right.symbol));
const retainedSymbols = selectedSymbols.filter(symbol => Array.isArray(sessionBarsBySymbol[symbol])
  && sessionBarsBySymbol[symbol].length);
const sourceManifest = Object.entries(sourceBySymbol).sort(([left], [right]) => left.localeCompare(right));
const createdAt = new Date().toISOString();
const inputMeasurementsSha256 = sha256(fs.readFileSync(measurementsPath));
const baseArchiveSha256 = baseArchivePath ? sha256(fs.readFileSync(baseArchivePath)) : null;
const sourceManifestSha256 = sha256(sourceManifest);
const reconstructionSourceSha256 = sha256({
  sessionDate,
  inputMeasurementsSha256,
  baseArchiveSha256,
  sourceManifest,
  sessionBarsBySymbol,
});
const payload = {
  schemaVersion: 1,
  phase: '57.entry-quality-v2.historical-reconstruction',
  status: failures.length || retainedSymbols.length !== selectedSymbols.length
    ? 'ENTRY_V2_HISTORICAL_RECONSTRUCTION_INCOMPLETE'
    : 'ENTRY_V2_HISTORICAL_RECONSTRUCTION_READY',
  sessionDate,
  createdAt,
  sourceClass: 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED',
  datasetRole: 'DEVELOPMENT_ONLY',
  prospective: false,
  formalOos: false,
  promotionEligible: false,
  inputMeasurementCount: measurements.length,
  inputMeasurementsSha256,
  selectedSymbolCount: selectedSymbols.length,
  selectedSymbols,
  baseArchivedSymbolCount: Object.keys(baseBars).length,
  baseArchiveSha256,
  requestedLaterFetchedSymbolCount: requestedSymbols.length,
  requestedLaterFetchedSymbols: requestedSymbols,
  laterFetchedSymbolCount: Object.keys(sourceBySymbol).length,
  retainedSelectedSymbolCount: retainedSymbols.length,
  missingSelectedSymbols: selectedSymbols.filter(symbol => !retainedSymbols.includes(symbol)),
  failedSymbolCount: failures.length,
  failures,
  sourceBySymbol,
  sourceManifestSha256,
  sourceLineage: {
    sourceClass: 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED',
    sourceArtifact: `${path.basename(outputPath)}#reconstruction-source-manifest`,
    sourceArtifactSha256: reconstructionSourceSha256,
    sourceArtifactHashScope: 'SESSION_DATE_INPUT_MEASUREMENTS_BASE_ARCHIVE_SOURCE_MANIFEST_SESSION_BARS',
    retrievedAt: createdAt,
    sessionDate,
    provider: 'YAHOO_FINANCE_CHART_5M',
    sourceRef: 'LOCAL_DEVELOPMENT_ONLY_LATER_FETCH_RECONSTRUCTION',
    archivedPointInTimeCapture: false,
    reconstructionFetchedAfterDecision: true,
  },
  sessionBarsBySymbol,
  methodology: {
    measurementAcceptedOnlyForCurrentDynamic5mV1: true,
    rawSnapshotReplayParityRequiredBeforeCandidateGeneration: true,
    measurementAloneNeverCreatesCandidate: true,
    archivedPointInTimeSelectorMeasurementsRemainFixed: true,
    currentDynamic5mSelectorRemainsFixed: true,
    frozenP21EntryRemainsFixed: true,
    laterFetchedBarsNeverRepresentedAsArchivedPit: true,
    completedBarRule: 'bar.timestamp + 5 minutes <= decisionTimestamp',
    futureBarsLabelsOnlyAfterFeatureFreeze: true,
    sparseValidBarsRetainedWithoutFabrication: true,
    missingBarsNeverInterpolatedOrFabricated: true,
  },
  safety: PHASE57_P25_2J_SAFETY,
};
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, `${JSON.stringify(payload, null, 2)}\n`);
console.log(JSON.stringify({
  status: payload.status,
  sessionDate,
  measurementCount: measurements.length,
  selectedSymbols: selectedSymbols.length,
  requested: requestedSymbols.length,
  fetched: Object.keys(sourceBySymbol).length,
  retained: retainedSymbols.length,
  failures,
  output: outputPath,
}, null, 2));
