import fs from 'node:fs';
import { enrichHistoricalIntradayBars } from './phase57-intraday-multifactor.js';
import { buildMultiHorizonMagnitudeRows } from './phase57-adaptive-horizon-magnitude.js';
import { buildIntradayHorizonDatasets } from './phase57-nested-adaptive-horizon.js';
import { replayNestedAdaptiveOosSignals } from './phase57-adaptive-oos-signal-replay.js';
import { evaluateRealNetExpectancyOos } from './phase57-real-net-expectancy-oos.js';

const scope = (process.env.PHASE57_SCOPE || 'COMBINED').trim();
const universe = ['7203.T', '6758.T', '9984.T', '8306.T', '8035.T'];
const symbols = scope === 'COMBINED' ? universe : [scope];
const horizonsBars = [1, 3, 6, 12, 24];
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function jst(ts) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(ts));
  const out = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return { date: `${out.year}-${out.month}-${out.day}`, hm: `${out.hour}:${out.minute}` };
}

async function fetchJson(urls, symbol) {
  let lastError;
  for (const url of urls) {
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 30000);
        const response = await fetch(url, {
          headers: {
            'User-Agent': 'Mozilla/5.0 ArkTerminalResearch/1.0',
            Accept: 'application/json',
            Connection: 'close',
          },
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

function parseYahoo(json, symbol) {
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
      open: Number(quote.open[index]),
      high: Number(quote.high[index]),
      low: Number(quote.low[index]),
      close: Number(quote.close[index]),
      volume: Number(quote.volume?.[index] || 0),
      sessionDate: date,
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
    all.push(...parseYahoo(await fetchJson(urls, symbol), symbol));
    await sleep(500);
  }
  return [...new Map(all.map(bar => [bar.timestamp, bar])).values()].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function featureRowsForMagnitude(symbol, sessionDate, sessionBars, enriched, magnitudeBase) {
  const indexByTimestamp = new Map(sessionBars.map((bar, index) => [new Date(bar.timestamp).toISOString(), index]));
  const enrichedByTimestamp = new Map(enriched.map(bar => [new Date(bar.timestamp).toISOString(), bar]));
  const open0 = Number(sessionBars[0]?.open || 0);
  return magnitudeBase.flatMap(row => {
    const timestamp = new Date(row.featureCutoff).toISOString();
    const index = indexByTimestamp.get(timestamp);
    const current = index === undefined ? null : sessionBars[index];
    const enrichedBar = enrichedByTimestamp.get(timestamp);
    if (!current || !enrichedBar) return [];
    const previous = index > 0 ? sessionBars[index - 1] : current;
    const priorVolumes = sessionBars.slice(Math.max(0, index - 5), index).map(bar => Number(bar.volume || 0));
    const averagePriorVolume = priorVolumes.length ? priorVolumes.reduce((a, b) => a + b, 0) / priorVolumes.length : 0;
    return [{
      symbol,
      sessionDate,
      featureCutoff: row.featureCutoff,
      features: {
        returnFromOpen: open0 ? (Number(current.close) / open0 - 1) * 100 : 0,
        rangePosition: Number(current.high) > Number(current.low)
          ? (Number(current.close) - Number(current.low)) / (Number(current.high) - Number(current.low)) : 0.5,
        shortMomentum: Number(previous.close) ? (Number(current.close) / Number(previous.close) - 1) * 100 : 0,
        relativeVolume: averagePriorVolume > 0 ? Number(current.volume || 0) / averagePriorVolume : 1,
        ...(enrichedBar.multiFactor || {}),
      },
    }];
  });
}

const datasets = Object.fromEntries(horizonsBars.map(horizon => [horizon, []]));
let rawBars = 0;
let sessionCount = 0;
for (const symbol of symbols) {
  const bars = await fetchBars(symbol);
  rawBars += bars.length;
  const sessions = new Map();
  for (const bar of bars) {
    if (!sessions.has(bar.sessionDate)) sessions.set(bar.sessionDate, []);
    sessions.get(bar.sessionDate).push(bar);
  }
  for (const [sessionDate, sessionBars] of sessions) {
    sessionBars.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
    if (sessionBars.length < 30) continue;
    sessionCount += 1;
    const enriched = enrichHistoricalIntradayBars(sessionBars);
    const magnitudeBase = buildMultiHorizonMagnitudeRows({ symbol, sessionDate, bars: sessionBars, horizons: horizonsBars });
    const featureRows = featureRowsForMagnitude(symbol, sessionDate, sessionBars, enriched, magnitudeBase);
    const sessionDatasets = buildIntradayHorizonDatasets(magnitudeBase, { horizons: horizonsBars, featureRows });
    for (const horizonBars of horizonsBars) datasets[horizonBars].push(...(sessionDatasets[horizonBars] || []));
  }
}
for (const horizonBars of horizonsBars) datasets[horizonBars].sort((a, b) => a.featureCutoff.localeCompare(b.featureCutoff));

const adaptiveOptions = {
  outerTrainFraction: 0.6,
  outerTestFraction: 0.1,
  outerMinTrainRows: scope === 'COMBINED' ? 500 : 200,
  innerTrainFraction: 0.6,
  innerTestFraction: 0.15,
  innerMinTrainRows: scope === 'COMBINED' ? 200 : 100,
  thresholds: [0.55, 0.60, 0.65],
  minInnerSignals: scope === 'COMBINED' ? 50 : 20,
  minimumInnerNetReturnPct: 0,
  roundTripCostPct: 0.05,
};

// Replay performs the same nested inner-only horizon/model/feature/threshold selection as P21.1
// and emits only the untouched outer-OOS signals. P21.4 evaluates the full emitted set;
// it is forbidden from choosing a symbol, fold, threshold, model or horizon after seeing OOS.
const replay = replayNestedAdaptiveOosSignals(datasets, adaptiveOptions);
const realEvidence = evaluateRealNetExpectancyOos({
  scope,
  replayResult: replay,
  researchRowCount: replay.commonRowCount,
  evidenceOptions: {
    bootstrap: { iterations: 4000, confidence: 0.95, seed: 57214 },
  },
});

const summary = {
  phase: '57.p21.4-real',
  status: 'REAL_5M_NET_EXPECTANCY_EVIDENCE_MEASURED',
  scope,
  source: 'Yahoo Finance historical 5m OHLCV',
  windowDays: 58,
  symbols,
  horizonsBars,
  horizonsMinutes: horizonsBars.map(value => value * 5),
  rawBars,
  sessionCount,
  rowCountByHorizon: Object.fromEntries(horizonsBars.map(horizon => [horizon, datasets[horizon].length])),
  replay: {
    status: replay.status,
    commonRowCount: replay.commonRowCount,
    outerFoldCount: replay.outerFoldCount,
    signalCount: replay.signalCount,
    directionalHitRate: replay.hitRate,
    grossAverageReturnPct: replay.grossAverageReturnPct,
    netAverageReturnPct: replay.netAverageReturnPct,
    profitFactor: replay.profitFactor,
    outerResults: replay.outerResults,
    selectionIntegrity: replay.selectionIntegrity,
  },
  p21_4: realEvidence,
  interpretationRules: [
    'Net Expectancy is the primary KPI; directional hit rate is diagnostic only',
    'The P21.4 evidence gate is evaluation-only and cannot select or promote any candidate',
    'Per-symbol outputs are diagnostics only; they must not be used to post-select a winner from OOS',
    'A positive point estimate is insufficient unless the 95% lower confidence bound is positive',
    'Small high-return samples fail the minimum-sample gate rather than being promoted as hero results',
  ],
  limitations: [
    'Yahoo Finance 5m history is limited to a recent rolling window',
    'Historical order-book and tick-flow are not reconstructed',
    'Only same-session 5/15/30/60/120 minute horizons are eligible',
    'Round-trip cost is fixed at 0.05%',
    'No session-end candidate is included yet',
  ],
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  oosSelectionAllowed: false,
};

fs.mkdirSync('artifacts', { recursive: true });
const output = `artifacts/phase57-real-net-expectancy-oos-${scope}.json`;
fs.writeFileSync(output, JSON.stringify(summary, null, 2));
console.log('PHASE57_P21_4_REAL_NET_JSON_START');
console.log(JSON.stringify(summary, null, 2));
console.log('PHASE57_P21_4_REAL_NET_JSON_END');
