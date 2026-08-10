import fs from 'node:fs';
import { enrichHistoricalIntradayBars } from './phase57-intraday-multifactor.js';
import { buildMultiHorizonMagnitudeRows } from './phase57-adaptive-horizon-magnitude.js';
import { evaluateIntradayAnalogOos } from './phase57-intraday-analog-oos.js';

const symbol = (process.env.PHASE57_SCOPE || '8035.T').trim();
const horizonsBars = [1, 3, 6, 12, 24];
const horizonsMinutes = horizonsBars.map(value => value * 5);
const roundTripCostPct = 0.05;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

// Historical Yahoo 5m data does not contain order book / tick-flow fields.
// P23.1 therefore freezes an OHLCV-only feature whitelist for this remeasurement.
const historicalFeatureKeys = Object.freeze([
  'returnFromOpen',
  'rangePosition',
  'shortMomentum',
  'relativeVolume',
  'ma5DistancePct',
  'ma10DistancePct',
  'ma20DistancePct',
  'ma5SlopePct',
  'rsi14',
  'macd',
  'macdSignalGap',
  'atrPct',
  'vwapDistancePct',
  'bbPosition',
  'relativeVolume20',
  'range20Position',
  'openingMinutes',
  'isOpening30',
  'isLunchReturn',
  'isClosing30',
]);

function jst(ts) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(ts));
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return { date: `${values.year}-${values.month}-${values.day}`, hm: `${values.hour}:${values.minute}` };
}

function timeBucket(timestamp) {
  const { hm } = jst(Date.parse(timestamp));
  if (hm >= '09:00' && hm < '09:30') return 'OPEN';
  if (hm >= '12:30' && hm < '13:00') return 'LUNCH_RETURN';
  if (hm >= '15:00' && hm <= '15:30') return 'CLOSE';
  return 'MID';
}

async function fetchJson(urls) {
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

function parse(json) {
  const result = json?.chart?.result?.[0];
  if (!result) throw new Error(`${symbol} no chart result`);
  const quote = result.indicators?.quote?.[0] || {};
  const out = [];
  for (let index = 0; index < (result.timestamp || []).length; index += 1) {
    const timestamp = Number(result.timestamp[index]) * 1000;
    const { date, hm } = jst(timestamp);
    if (hm < '09:00' || hm > '15:30') continue;
    const values = [quote.open?.[index], quote.high?.[index], quote.low?.[index], quote.close?.[index]];
    if (values.some(value => value == null || !Number.isFinite(Number(value)))) continue;
    out.push({
      timestamp: new Date(timestamp).toISOString(),
      open: Number(quote.open[index]),
      high: Number(quote.high[index]),
      low: Number(quote.low[index]),
      close: Number(quote.close[index]),
      volume: Number(quote.volume?.[index] || 0),
      sessionDate: date,
    });
  }
  return out;
}

async function fetchBars() {
  const end = Math.floor(Date.now() / 1000);
  const day = 86400;
  const windows = [[end - 58 * day, end - 29 * day], [end - 29 * day, end]];
  const all = [];
  for (const [period1, period2] of windows) {
    const query = `period1=${period1}&period2=${period2}&interval=5m&includePrePost=false&events=div%2Csplits`;
    const urls = [1, 2].map(host => `https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${query}`);
    all.push(...parse(await fetchJson(urls)));
    await sleep(500);
  }
  return [...new Map(all.map(bar => [bar.timestamp, bar])).values()]
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function buildRowsForSession(sessionDate, sessionBars) {
  const enriched = enrichHistoricalIntradayBars(sessionBars);
  const enrichedByTimestamp = new Map(enriched.map(bar => [new Date(bar.timestamp).toISOString(), bar]));
  const indexByTimestamp = new Map(sessionBars.map((bar, index) => [new Date(bar.timestamp).toISOString(), index]));
  const open0 = Number(sessionBars[0]?.open || 0);
  const baseRows = buildMultiHorizonMagnitudeRows({ symbol, sessionDate, bars: sessionBars, horizons: horizonsBars });
  const byHorizon = Object.fromEntries(horizonsBars.map(horizon => [horizon, []]));

  for (const base of baseRows) {
    const timestamp = new Date(base.featureCutoff).toISOString();
    const index = indexByTimestamp.get(timestamp);
    const current = index === undefined ? null : sessionBars[index];
    const enrichedBar = enrichedByTimestamp.get(timestamp);
    if (!current || !enrichedBar) continue;
    const previous = index > 0 ? sessionBars[index - 1] : current;
    const priorVolumes = sessionBars.slice(Math.max(0, index - 5), index).map(bar => Number(bar.volume || 0));
    const averagePriorVolume = priorVolumes.length
      ? priorVolumes.reduce((sum, value) => sum + value, 0) / priorVolumes.length
      : 0;
    const features = Object.freeze({
      returnFromOpen: open0 ? (Number(current.close) / open0 - 1) * 100 : 0,
      rangePosition: Number(current.high) > Number(current.low)
        ? (Number(current.close) - Number(current.low)) / (Number(current.high) - Number(current.low))
        : 0.5,
      shortMomentum: Number(previous.close) ? (Number(current.close) / Number(previous.close) - 1) * 100 : 0,
      relativeVolume: averagePriorVolume > 0 ? Number(current.volume || 0) / averagePriorVolume : 1,
      ...(enrichedBar.multiFactor || {}),
    });

    for (const horizonBars of horizonsBars) {
      const target = base.targets?.[horizonBars];
      if (!target) continue;
      byHorizon[horizonBars].push(Object.freeze({
        id: `${symbol}|${sessionDate}|${timestamp}|${horizonBars}`,
        symbol,
        sessionDate,
        outcomeSessionDate: target.outcomeSessionDate ?? sessionDate,
        featureCutoff: timestamp,
        outcomeAt: target.outcomeAt,
        horizonBars,
        features,
        context: Object.freeze({ timeBucket: timeBucket(timestamp), regime: null }),
        actualReturnPct: Number(target.actualReturnPct),
        absMovePct: Number(target.absMovePct),
        mfePct: Number(target.mfePct),
        maePct: Number(target.maePct),
        pointInTimeValid: true,
        intradayOnly: true,
        sourceMode: 'Yahoo Finance historical 5m OHLCV',
      }));
    }
  }
  return byHorizon;
}

const bars = await fetchBars();
const sessions = new Map();
for (const bar of bars) {
  if (!sessions.has(bar.sessionDate)) sessions.set(bar.sessionDate, []);
  sessions.get(bar.sessionDate).push(bar);
}

const datasets = Object.fromEntries(horizonsBars.map(horizon => [horizon, []]));
let eligibleSessionCount = 0;
for (const [sessionDate, sessionBars] of sessions) {
  sessionBars.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  if (sessionBars.length < 30) continue;
  eligibleSessionCount += 1;
  const rows = buildRowsForSession(sessionDate, sessionBars);
  for (const horizonBars of horizonsBars) datasets[horizonBars].push(...rows[horizonBars]);
}
for (const horizonBars of horizonsBars) datasets[horizonBars].sort((a, b) => a.featureCutoff.localeCompare(b.featureCutoff));

const horizonResults = [];
for (const horizonBars of horizonsBars) {
  const evaluated = evaluateIntradayAnalogOos(datasets[horizonBars], {
    featureKeys: historicalFeatureKeys,
    topK: 25,
    minimumAnalogs: 20,
    minFeatureFraction: 0.8,
    roundTripCostPct,
    minimumExpectedNetPct: 0,
    contextPenalties: {},
    sameSymbolOnly: true,
    excludeCurrentSession: true,
    moveThresholdsPct: [0.5, 1, 2, 3],
    initialTrainFraction: 0.6,
    testFraction: 0.1,
    minimumTrainSessions: 20,
  });
  const { predictionFingerprint, ...compact } = evaluated;
  horizonResults.push(Object.freeze({
    horizonMinutes: horizonBars * 5,
    ...compact,
    predictionFingerprintCount: predictionFingerprint.length,
  }));
}

const summary = {
  phase: '57.p23.1-real',
  status: 'INTRADAY_HISTORICAL_ANALOG_5M_OOS_MEASURED',
  symbol,
  source: 'Yahoo Finance historical 5m OHLCV',
  windowDays: 58,
  rawBars: bars.length,
  eligibleSessionCount,
  horizonsBars,
  horizonsMinutes,
  historicalFeatureKeys,
  fixedResearchConfiguration: {
    topK: 25,
    minimumAnalogs: 20,
    minFeatureFraction: 0.8,
    roundTripCostPct,
    minimumExpectedNetPct: 0,
    sameSymbolOnly: true,
    excludeCurrentSession: true,
    contextPenalties: {},
    initialTrainFraction: 0.6,
    testFraction: 0.1,
    minimumTrainSessions: 20,
  },
  rowCountByHorizon: Object.fromEntries(horizonsBars.map(horizon => [String(horizon), datasets[horizon].length])),
  horizonResults,
  interpretationRules: {
    primaryObjective: 'NET_EXPECTANCY_AFTER_EXPLICIT_COST',
    horizonsAreReportedSeparately: true,
    postSelectBestHorizonFromTheseOuterResults: false,
    compareAnalogToMatchedUnconditionalTrainDirection: true,
    edgeClaimFromThisSingleRecentWindowAllowed: false,
  },
  limitations: [
    'Historical order-book and tick-flow microstructure is unavailable in Yahoo 5m OHLCV and is excluded from this remeasurement.',
    'The recent Yahoo 5m history window is limited to about 58 days.',
    'Each horizon is a separate predeclared OOS diagnostic; no best horizon may be selected from these outer results.',
    'The analog candidate pool is restricted to pre-outer training sessions and excludes the current session.',
    'Round-trip cost is fixed at 0.05%.',
    'No paper/live trading or broker/RSS order path is enabled.',
  ],
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
};

fs.mkdirSync('artifacts', { recursive: true });
const output = `artifacts/phase57-intraday-analog-oos-${symbol}.json`;
fs.writeFileSync(output, JSON.stringify(summary, null, 2));
console.log('PHASE57_P23_1_REAL_JSON_START');
console.log(JSON.stringify(summary));
console.log('PHASE57_P23_1_REAL_JSON_END');
