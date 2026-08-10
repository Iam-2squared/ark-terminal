import fs from 'node:fs';
import { enrichHistoricalIntradayBars } from './phase57-intraday-multifactor.js';
import { buildMultiHorizonMagnitudeRows } from './phase57-adaptive-horizon-magnitude.js';
import { buildIntradayHorizonDatasets, evaluateNestedAdaptiveHorizon } from './phase57-nested-adaptive-horizon.js';
import { replayNestedAdaptiveOosSignals } from './phase57-adaptive-oos-signal-replay.js';
import { evaluateRealNestedStateMachine } from './phase57-real-nested-state-machine.js';

const scope = (process.env.PHASE57_SCOPE || '7203.T').trim();
const universe = ['7203.T', '6758.T', '9984.T', '8306.T', '8035.T'];
if (scope !== 'COMBINED' && !universe.includes(scope)) throw new Error(`unsupported PHASE57_SCOPE: ${scope}`);
const symbols = scope === 'COMBINED' ? universe : [scope];
const horizonsBars = [1, 3, 6, 12, 24];
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const sessionKey = (symbol, sessionDate) => `${symbol}|${sessionDate}`;
const rowKey = row => `${row?.symbol ?? ''}|${row?.sessionDate ?? ''}|${row?.featureCutoff ?? ''}`;

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

function featureRowsForMagnitude(symbol, sessionDate, sessionBars, enriched, magnitudeBase) {
  const indexByTimestamp = new Map(sessionBars.map((bar, index) => [new Date(bar.timestamp).toISOString(), index]));
  const enrichedByTimestamp = new Map(enriched.map(bar => [new Date(bar.timestamp).toISOString(), bar]));
  const sessionOpen = Number(sessionBars[0]?.open || 0);
  return magnitudeBase.flatMap(row => {
    const timestamp = new Date(row.featureCutoff).toISOString();
    const index = indexByTimestamp.get(timestamp);
    const current = index === undefined ? null : sessionBars[index];
    const enrichedBar = enrichedByTimestamp.get(timestamp);
    if (!current || !enrichedBar) return [];
    const previous = index > 0 ? sessionBars[index - 1] : current;
    const priorVolumes = sessionBars.slice(Math.max(0, index - 5), index).map(bar => Number(bar.volume || 0));
    const avgPriorVolume = priorVolumes.length ? priorVolumes.reduce((sum, value) => sum + value, 0) / priorVolumes.length : 0;
    const features = {
      returnFromOpen: sessionOpen ? (Number(current.close) / sessionOpen - 1) * 100 : 0,
      rangePosition: Number(current.high) > Number(current.low)
        ? (Number(current.close) - Number(current.low)) / (Number(current.high) - Number(current.low))
        : 0.5,
      shortMomentum: Number(previous.close) ? (Number(current.close) / Number(previous.close) - 1) * 100 : 0,
      relativeVolume: avgPriorVolume > 0 ? Number(current.volume || 0) / avgPriorVolume : 1,
      ...(enrichedBar.multiFactor || {}),
    };
    return [{ symbol, sessionDate, featureCutoff: row.featureCutoff, features }];
  });
}

const datasets = Object.fromEntries(horizonsBars.map(horizon => [horizon, []]));
const sessionStore = new Map();
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
    sessionStore.set(sessionKey(symbol, sessionDate), {
      bars: sessionBars,
      indexByTimestamp: new Map(sessionBars.map((bar, index) => [new Date(bar.timestamp).toISOString(), index])),
    });
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

const adaptive = evaluateNestedAdaptiveHorizon(datasets, adaptiveOptions);
const replay = replayNestedAdaptiveOosSignals(datasets, { ...adaptiveOptions, referenceResult: adaptive });
if (replay.reconciliation && !replay.reconciliation.matches) {
  throw new Error(`P23.6 entry signal replay mismatch: ${JSON.stringify(replay.reconciliation)}`);
}

const datasetLookup = new Map();
for (const horizonBars of horizonsBars) {
  for (const row of datasets[horizonBars]) datasetLookup.set(`${horizonBars}|${rowKey(row)}`, row);
}

const exitRows = [];
let missingSourceRows = 0;
let missingSessionPaths = 0;
for (const signal of replay.signals) {
  const source = datasetLookup.get(`${signal.horizonBars}|${rowKey(signal)}`);
  if (!source) {
    missingSourceRows += 1;
    continue;
  }
  const store = sessionStore.get(sessionKey(signal.symbol, signal.sessionDate));
  const index = store?.indexByTimestamp.get(new Date(signal.featureCutoff).toISOString());
  if (!store || index === undefined) {
    missingSessionPaths += 1;
    continue;
  }
  const contextBars = store.bars.slice(0, index + 1);
  const futureBars = store.bars.slice(index + 1);
  if (!futureBars.length) {
    missingSessionPaths += 1;
    continue;
  }
  exitRows.push(Object.freeze({
    id: `${signal.symbol}|${signal.sessionDate}|${signal.featureCutoff}|${signal.horizonBars}|${signal.baseOuterFold}`,
    symbol: signal.symbol,
    sessionDate: signal.sessionDate,
    outcomeSessionDate: signal.sessionDate,
    featureCutoff: signal.featureCutoff,
    pointInTimeValid: true,
    signalPointInTimeValid: signal.signalPointInTimeValid !== false,
    entryPrice: Number(source.entryPrice),
    signalDirection: Number(signal.direction),
    baseHorizonBars: Number(signal.horizonBars),
    baseOuterFold: Number(signal.baseOuterFold),
    baseSignalProbability: Number(signal.probability),
    baseSignalConfidence: Number(signal.confidence),
    baseSignalFeatureFamily: signal.selectedFeatureFamily,
    baseSignalModelType: signal.selectedModelType,
    contextBars: Object.freeze(contextBars.map(bar => Object.freeze({ ...bar }))),
    futureBars: Object.freeze(futureBars.map(bar => Object.freeze({ ...bar }))),
  }));
}
exitRows.sort((a, b) => a.featureCutoff.localeCompare(b.featureCutoff));

const nestedStateMachine = evaluateRealNestedStateMachine(exitRows, {
  outerTrainFraction: 0.6,
  outerTestFraction: 0.1,
  outerMinTrainSessions: 15,
  innerTrainFraction: 0.55,
  innerTestFraction: 0.2,
  innerMinTrainSessions: 8,
  minInnerSignals: scope === 'COMBINED' ? 20 : 5,
  minInnerSignalBearingFolds: 2,
  roundTripCostPct: 0.05,
});

const summary = {
  phase: '57.p23.6-real',
  status: 'REAL_5M_NESTED_STATE_MACHINE_DEVELOPMENT_OOS_MEASURED',
  scope,
  source: 'Yahoo Finance historical 5m OHLCV',
  windowDays: 58,
  symbols,
  horizonsBars,
  horizonsMinutes: horizonsBars.map(value => value * 5),
  rawBars,
  sessionCount,
  rowCountByHorizon: Object.fromEntries(horizonsBars.map(horizon => [horizon, datasets[horizon].length])),
  adaptiveReference: {
    status: adaptive.status,
    signalCount: adaptive.signalCount,
    hitRate: adaptive.hitRate,
    netAverageReturnPct: adaptive.netAverageReturnPct,
    profitFactor: adaptive.profitFactor,
    outerFoldCount: adaptive.outerFoldCount,
  },
  signalReplay: {
    status: replay.status,
    signalCount: replay.signalCount,
    hitRate: replay.hitRate,
    netAverageReturnPct: replay.netAverageReturnPct,
    profitFactor: replay.profitFactor,
    reconciliation: replay.reconciliation,
    missingSourceRows,
    missingSessionPaths,
    stateMachineResearchRows: exitRows.length,
  },
  nestedStateMachine,
  interpretationRules: {
    primaryObjective: 'NET_EXPECTANCY_AFTER_EXPLICIT_COST',
    stateMachineConfigSelectedOnlyInsideEarlierOuterTrainData: true,
    matchedP23_3AndFixedComparatorsUsedForSelection: false,
    reusedRecentResearchWindow: true,
    finalUntouchedOosEdgeClaimAllowed: false,
    postSelectFromOuterOutcomesAllowed: false,
  },
  limitations: [
    'This is development nested evidence on the already-used recent research window, not a final untouched OOS claim.',
    'Historical order-book/tick-flow microstructure is unavailable in Yahoo 5m OHLCV and remains excluded.',
    'Yahoo Finance 5m history is limited to a recent ~58 day window.',
    'Base entry is modeled at the signal bar close; a separate next-bar execution-delay model is not applied here.',
    'Round-trip cost is fixed at 0.05%.',
    'State-machine candidates are frozen before these outer folds; outer outcomes cannot post-select a candidate.',
    'P23.3 dynamic exit and prior fixed-horizon exit are comparators only on the exact same selected outer rows.',
    'No paper/live trading or broker/RSS order path is enabled.',
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
  transmitted: false,
};

fs.mkdirSync('artifacts', { recursive: true });
const output = `artifacts/phase57-real-nested-state-machine-${scope}.json`;
fs.writeFileSync(output, JSON.stringify(summary, null, 2));
console.log('PHASE57_P23_6_REAL_NESTED_STATE_MACHINE_JSON_START');
console.log(JSON.stringify(summary));
console.log('PHASE57_P23_6_REAL_NESTED_STATE_MACHINE_JSON_END');
