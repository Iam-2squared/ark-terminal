import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  buildEntryOpportunityExample,
  evaluateEntryOpportunityWalkForward,
  PHASE57_P23_9A_SAFETY,
} from './phase57-entry-opportunity-intelligence.js';
import { simulateFrozenRatchetExit } from './phase57-frozen-ratchet-exit.js';

const SHARD_INDEX = Number(process.env.PHASE57_SHARD_INDEX ?? 0);
if (!Number.isInteger(SHARD_INDEX) || SHARD_INDEX < 0 || SHARD_INDEX > 2) throw new Error('PHASE57_SHARD_INDEX must be 0, 1, or 2');
const SHARD_NUMBER = SHARD_INDEX + 1;
const HORIZON_BARS = 12;
const ROUND_TRIP_COST_PCT = 0.05;
const MIN_TRAIN_ROWS = 500;
const RIDGE_LAMBDA = 8;
const here = path.dirname(fileURLToPath(import.meta.url));
const frozenMeta = JSON.parse(fs.readFileSync(path.join(here, 'phase57-p23-8-frozen-outer-trades.json'), 'utf8'));
const shardMeta = frozenMeta.shards.find(item => Number(item.matrixIndex) === SHARD_INDEX);
if (!shardMeta) throw new Error(`missing frozen shard metadata for ${SHARD_INDEX}`);

const sourceRoot = path.resolve(process.env.PHASE57_FROZEN_ARTIFACT_DIR || 'frozen-source');
function findJson(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? findJson(full) : (entry.name.endsWith('.json') ? [full] : []);
  });
}
const sourceFiles = findJson(sourceRoot);
if (sourceFiles.length !== 1) throw new Error(`expected exactly one frozen P23.8 source JSON, found ${sourceFiles.length}`);
const source = JSON.parse(fs.readFileSync(sourceFiles[0], 'utf8'));
if (source.phase !== `57.p23.8-entry-exit-quality-shard-${SHARD_NUMBER}`) throw new Error(`unexpected frozen source phase ${source.phase}`);
if (Number(source.qualityShardPolicy?.shardIndex) !== SHARD_INDEX) throw new Error('frozen source shard mismatch');
if (source.qualityShardPolicy?.futureExtremaUsedForDecision !== false) throw new Error('source future-extrema contamination');
const frozenRecords = source.entryExitQuality?.records ?? [];
if (frozenRecords.length !== Number(shardMeta.tradeCount)) throw new Error(`frozen count mismatch ${frozenRecords.length} != ${shardMeta.tradeCount}`);

for (const key of [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
]) {
  if (source[key] !== false) throw new Error(`source ${key} must be false`);
  if (PHASE57_P23_9A_SAFETY[key] !== false) throw new Error(`P23.9A ${key} must be false`);
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
function jst(ts) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(ts));
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return { date: `${values.year}-${values.month}-${values.day}`, hm: `${values.hour}:${values.minute}` };
}

async function fetchJson(urls, symbol) {
  let lastError;
  for (const url of urls) {
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 30000);
        const response = await fetch(url, {
          headers: { 'User-Agent': 'Mozilla/5.0 ArkTerminalResearch/1.0', Accept: 'application/json', Connection: 'close' },
          signal: controller.signal,
        });
        clearTimeout(timer);
        if (!response.ok) throw new Error(`${symbol} Yahoo HTTP ${response.status}`);
        return await response.json();
      } catch (error) {
        lastError = error;
        if (attempt < 4) await sleep(attempt * 1000);
      }
    }
  }
  throw lastError;
}

function parse(json, symbol) {
  const result = json?.chart?.result?.[0];
  if (!result) throw new Error(`${symbol} no chart result`);
  const quote = result.indicators?.quote?.[0] || {};
  const rows = [];
  for (let index = 0; index < (result.timestamp || []).length; index += 1) {
    const timestamp = Number(result.timestamp[index]) * 1000;
    const { date, hm } = jst(timestamp);
    if (hm < '09:00' || hm > '15:30') continue;
    const values = [quote.open?.[index], quote.high?.[index], quote.low?.[index], quote.close?.[index]];
    if (values.some(value => value == null || !Number.isFinite(Number(value)))) continue;
    rows.push({
      timestamp: new Date(timestamp).toISOString(),
      open: Number(quote.open[index]), high: Number(quote.high[index]), low: Number(quote.low[index]), close: Number(quote.close[index]),
      volume: Number(quote.volume?.[index] || 0), sessionDate: date,
    });
  }
  return rows;
}

async function fetchBars(symbol) {
  const end = Math.floor(Date.now() / 1000);
  const day = 86400;
  const windows = [[end - 58 * day, end - 29 * day], [end - 29 * day, end]];
  const all = [];
  for (const [period1, period2] of windows) {
    const query = `period1=${period1}&period2=${period2}&interval=5m&includePrePost=false&events=div%2Csplits`;
    const urls = [1, 2].map(host => `https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${query}`);
    all.push(...parse(await fetchJson(urls, symbol), symbol));
    await sleep(500);
  }
  return [...new Map(all.map(bar => [bar.timestamp, bar])).values()].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

const symbols = [...new Set((source.symbols ?? frozenRecords.map(row => row.symbol)).map(String))].sort();
const fetchedPairs = [];
for (let start = 0; start < symbols.length; start += 5) {
  const batch = symbols.slice(start, start + 5);
  fetchedPairs.push(...await Promise.all(batch.map(async symbol => [symbol, await fetchBars(symbol)])));
  if (start + 5 < symbols.length) await sleep(1000);
}
const fetchedBySymbol = new Map(fetchedPairs);
const sessions = new Map();
for (const [symbol, bars] of fetchedBySymbol) {
  for (const bar of bars) {
    const key = `${symbol}|${bar.sessionDate}`;
    if (!sessions.has(key)) sessions.set(key, []);
    sessions.get(key).push(bar);
  }
}
for (const rows of sessions.values()) rows.sort((a, b) => a.timestamp.localeCompare(b.timestamp));

const maxFrozenDate = frozenRecords.map(row => String(row.sessionDate)).sort().at(-1);
const trainingExamples = [];
for (const [key, bars] of sessions) {
  const [symbol, sessionDate] = key.split('|');
  if (sessionDate > maxFrozenDate || bars.length < HORIZON_BARS + 5) continue;
  for (let index = 3; index + HORIZON_BARS < bars.length; index += 1) {
    const contextBars = bars.slice(0, index + 1);
    const futureBars = bars.slice(index + 1, index + 1 + HORIZON_BARS);
    for (const direction of ['LONG', 'SHORT']) {
      const example = buildEntryOpportunityExample({
        symbol,
        sessionDate,
        featureCutoff: bars[index].timestamp,
        contextBars,
        futureBars,
        entryPrice: Number(bars[index].close),
        direction,
        horizonBars: HORIZON_BARS,
        roundTripCostPct: ROUND_TRIP_COST_PCT,
      });
      if (example) trainingExamples.push(example);
    }
  }
}
trainingExamples.sort((a, b) => a.featureCutoff.localeCompare(b.featureCutoff));

const frozenTestExamples = [];
const reconstructionErrors = [];
for (const record of frozenRecords) {
  const bars = sessions.get(`${record.symbol}|${record.sessionDate}`) ?? [];
  const cutoff = new Date(record.featureCutoff).toISOString();
  const index = bars.findIndex(bar => new Date(bar.timestamp).toISOString() === cutoff);
  if (index < 0 || index + HORIZON_BARS >= bars.length) {
    reconstructionErrors.push({ symbol: record.symbol, sessionDate: record.sessionDate, featureCutoff: cutoff, reason: 'MISSING_FIXED_60M_PATH' });
    continue;
  }
  const contextBars = bars.slice(0, index + 1);
  const futureBars = bars.slice(index + 1);
  const rowForExit = {
    symbol: String(record.symbol),
    sessionDate: String(record.sessionDate),
    featureCutoff: cutoff,
    entryPrice: Number(record.entryPrice),
    signalDirection: record.direction,
    contextBars,
    futureBars,
  };
  const ratchet = simulateFrozenRatchetExit(rowForExit);
  if (!ratchet) {
    reconstructionErrors.push({ symbol: record.symbol, sessionDate: record.sessionDate, featureCutoff: cutoff, reason: 'RATCHET_REPLAY_NULL' });
    continue;
  }
  const example = buildEntryOpportunityExample({
    symbol: record.symbol,
    sessionDate: record.sessionDate,
    featureCutoff: cutoff,
    contextBars,
    futureBars: futureBars.slice(0, HORIZON_BARS),
    entryPrice: Number(record.entryPrice),
    direction: record.direction,
    horizonBars: HORIZON_BARS,
    roundTripCostPct: ROUND_TRIP_COST_PCT,
  });
  if (!example) {
    reconstructionErrors.push({ symbol: record.symbol, sessionDate: record.sessionDate, featureCutoff: cutoff, reason: 'OPPORTUNITY_EXAMPLE_NULL' });
    continue;
  }
  frozenTestExamples.push(Object.freeze({ ...example, realizedRatchetNetReturnPct: Number(ratchet.netReturnPct) }));
}
if (reconstructionErrors.length) {
  fs.mkdirSync('artifacts', { recursive: true });
  fs.writeFileSync(`artifacts/phase57-p23-9a-entry-opportunity-reconstruction-failure-shard-${SHARD_NUMBER}.json`, JSON.stringify({
    phase: `57.p23.9a-entry-opportunity-shard-${SHARD_NUMBER}`,
    status: 'FROZEN_ENTRY_RECONSTRUCTION_FAILED',
    expected: frozenRecords.length,
    reconstructed: frozenTestExamples.length,
    reconstructionErrors,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    overnightHoldingAllowed: false,
    transmitted: false,
  }, null, 2));
  throw new Error(`P23.9A reconstruction failed for ${reconstructionErrors.length} frozen signals`);
}
if (frozenTestExamples.length !== frozenRecords.length) throw new Error('P23.9A frozen test count changed');

const evaluation = evaluateEntryOpportunityWalkForward({
  trainingExamples,
  frozenTestExamples,
  minTrainRows: MIN_TRAIN_ROWS,
  lambda: RIDGE_LAMBDA,
  roundTripCostPct: ROUND_TRIP_COST_PCT,
});

const result = {
  phase: `57.p23.9a-entry-opportunity-shard-${SHARD_NUMBER}`,
  status: 'HISTORICAL_ENTRY_OPPORTUNITY_SHARD_DEVELOPMENT_MEASURED',
  shardIndex: SHARD_INDEX,
  shardNumber: SHARD_NUMBER,
  symbols,
  frozenSource: {
    workflowRunId: frozenMeta.sourceWorkflowRunId,
    sourceHeadSha: frozenMeta.sourceHeadSha,
    expectedTradeCount: shardMeta.tradeCount,
    exactFrozenTradeCountReconciled: frozenTestExamples.length === Number(shardMeta.tradeCount),
    entryDirectionAndTimestampFrozen: true,
  },
  opportunityPolicy: {
    source: 'Yahoo Finance historical 5m OHLCV',
    fixedHorizonBars: HORIZON_BARS,
    fixedHorizonMinutes: HORIZON_BARS * 5,
    roundTripCostPct: ROUND_TRIP_COST_PCT,
    ridgeLambda: RIDGE_LAMBDA,
    minimumPriorTrainingRows: MIN_TRAIN_ROWS,
    trainingExamples: trainingExamples.length,
    twoDirectionalTrainingExamplesPerHistoricalCutoff: true,
    trainingSessionsStrictlyEarlierThanEachTestSession: true,
    gateRule: 'EXPECTED_ENDPOINT_NET_GT_0_AND_EXPECTED_MFE_MINUS_ADVERSE_MINUS_COST_GT_0',
    gateThresholdTunedOnFrozenOuterOutcomes: false,
    futureExtremaUsedAsPredictor: false,
  },
  evaluation,
  interpretation: {
    historicalOnlyPriority: true,
    developmentDiagnosticAndGateEvidenceOnly: true,
    reusedP23_8DevelopmentWindow: true,
    notFreshUntouchedOos: true,
    noEdgeClaim: true,
    noAutomaticPromotion: true,
  },
  edgeClaimAllowed: false,
  recommendationAllowed: false,
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  transmitted: false,
  safety: PHASE57_P23_9A_SAFETY,
};
fs.mkdirSync('artifacts', { recursive: true });
const out = `artifacts/phase57-p23-9a-entry-opportunity-shard-${SHARD_NUMBER}.json`;
fs.writeFileSync(out, JSON.stringify(result, null, 2));
console.log(JSON.stringify({
  shard: SHARD_NUMBER,
  trainingExamples: trainingExamples.length,
  frozenTestCount: frozenTestExamples.length,
  predictionCount: evaluation.predictionCount,
  gateCoverage: evaluation.gateCoverage,
  allFrozenRatchet: evaluation.allFrozenRatchet,
  gatedFrozenRatchet: evaluation.gatedFrozenRatchet,
  deltas: evaluation.deltas,
  correlations: evaluation.correlations,
}, null, 2));
