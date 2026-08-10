import fs from 'node:fs';
import {
  measureChartPerceptionHistory,
} from './phase57-chart-perception-measurement.js';
import {
  PHASE57_CHART_PERCEPTION_SAFETY,
} from './phase57-chart-perception-2.js';
import { EXPANDED_UNIVERSE } from './phase57-expanded-universe.js';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const symbols = (process.env.PHASE57_SYMBOLS
  ? process.env.PHASE57_SYMBOLS.split(',').map(value => value.trim()).filter(Boolean)
  : EXPANDED_UNIVERSE.slice(0, 3));
const minHistoryBars = Number(process.env.PHASE57_MIN_HISTORY_BARS ?? 1600);
const stepBars = Number(process.env.PHASE57_STEP_BARS ?? 3);

const JST_FORMATTER = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Tokyo',
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});

function jst(timestamp) {
  const values = Object.fromEntries(JST_FORMATTER.formatToParts(new Date(timestamp)).map(part => [part.type, part.value]));
  return {
    date: `${values.year}-${values.month}-${values.day}`,
    hm: `${values.hour}:${values.minute}`,
  };
}

async function fetchJson(urls, symbol) {
  let lastError;
  for (const url of urls) {
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 30000);
        const response = await fetch(url, {
          headers: { 'User-Agent': 'Mozilla/5.0 ArkTerminalResearch/1.0', Accept: 'application/json' },
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
  if (!result) throw new Error(`${symbol} missing Yahoo chart result`);
  const quote = result.indicators?.quote?.[0] ?? {};
  const out = [];
  for (let index = 0; index < (result.timestamp ?? []).length; index += 1) {
    const timestamp = Number(result.timestamp[index]) * 1000;
    const { date, hm } = jst(timestamp);
    const inMorning = hm >= '09:00' && hm < '11:30';
    const inAfternoon = hm >= '12:30' && hm < '15:30';
    if (!inMorning && !inAfternoon) continue;
    const values = [quote.open?.[index], quote.high?.[index], quote.low?.[index], quote.close?.[index]];
    if (values.some(value => value == null || !Number.isFinite(Number(value)))) continue;
    out.push({
      timestamp: new Date(timestamp).toISOString(),
      open: Number(quote.open[index]),
      high: Number(quote.high[index]),
      low: Number(quote.low[index]),
      close: Number(quote.close[index]),
      volume: Number(quote.volume?.[index] ?? 0),
      sessionDate: date,
    });
  }
  return out;
}

async function fetchBars(symbol) {
  const end = Math.floor(Date.now() / 1000);
  const start = end - 58 * 86400;
  const query = `period1=${start}&period2=${end}&interval=5m&includePrePost=false&events=div%2Csplits`;
  const urls = [1, 2].map(host => `https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${query}`);
  const json = await fetchJson(urls, symbol);
  return parseYahoo(json, symbol);
}

function combineRecords(measurements) {
  return measurements.flatMap(item => item.records ?? []);
}

function summarize(records, key) {
  const rows = records.filter(row => row[key]);
  if (!rows.length) return { count: 0, hitRate: null, averageDirectionalReturnPct: null, averageMfePct: null, averageMaePct: null };
  const mean = values => values.reduce((sum, value) => sum + Number(value), 0) / values.length;
  return {
    count: rows.length,
    hitRate: rows.filter(row => row[key].hit).length / rows.length,
    averageDirectionalReturnPct: mean(rows.map(row => row[key].directionalReturnPct)),
    averageMfePct: mean(rows.map(row => row[key].mfePct)),
    averageMaePct: mean(rows.map(row => row[key].maePct)),
  };
}

function bySetup(records) {
  const groups = new Map();
  for (const row of records) {
    if (!groups.has(row.setup)) groups.set(row.setup, []);
    groups.get(row.setup).push(row);
  }
  return Object.fromEntries([...groups.entries()].map(([setup, rows]) => [setup, {
    signalCount: rows.length,
    outcome30m: summarize(rows, 'outcome30m'),
    outcome60m: summarize(rows, 'outcome60m'),
  }]));
}

const measurements = [];
for (const symbol of symbols) {
  const bars = await fetchBars(symbol);
  const measurement = measureChartPerceptionHistory({ symbol, bars5m: bars, minHistoryBars, stepBars });
  measurements.push(measurement);
  console.log(JSON.stringify({
    symbol,
    sourceBarCount: measurement.sourceBarCount,
    directionalSetupCount: measurement.directionalSetupCount,
    coverage: measurement.directionalSetupCoverage,
    outcome30m: measurement.aggregate.outcome30m,
    outcome60m: measurement.aggregate.outcome60m,
  }));
  await sleep(600);
}

const records = combineRecords(measurements);
const result = {
  phase: '57.p23.10b-chart-perception-real-remeasurement',
  status: 'REAL_HISTORICAL_CHART_PERCEPTION_REMEASUREMENT_COMPLETE',
  symbols,
  symbolCount: symbols.length,
  minHistoryBars,
  stepBars,
  source: 'Yahoo Finance historical 5m OHLCV',
  totalDirectionalSetups: records.length,
  aggregate: {
    outcome30m: summarize(records, 'outcome30m'),
    outcome60m: summarize(records, 'outcome60m'),
  },
  bySetup: bySetup(records),
  bySymbol: Object.fromEntries(measurements.map(item => [item.symbol, {
    sourceBarCount: item.sourceBarCount,
    directionalSetupCount: item.directionalSetupCount,
    directionalSetupCoverage: item.directionalSetupCoverage,
    aggregate: item.aggregate,
  }])),
  interpretation: {
    architectureSmokeAndDescriptiveMeasurement: true,
    fixedSetupRulesNotOutcomeTuned: true,
    p23_8FrozenOutcomeReuse: false,
    finalUntouchedOos: false,
    edgeClaimAllowed: false,
  },
  integrity: {
    perceptionBuiltFromPrefixOnly: true,
    futureOutcomesEvaluationOnly: true,
    sessionAwareHigherTimeframes: true,
    partialHigherTimeframeBarsExcluded: true,
    sameSessionOutcomesOnly: true,
  },
  edgeClaimAllowed: false,
  recommendationAllowed: false,
  transmitted: false,
  ...PHASE57_CHART_PERCEPTION_SAFETY,
  safety: PHASE57_CHART_PERCEPTION_SAFETY,
};

if (result.totalDirectionalSetups < 1) throw new Error('remeasurement produced no directional chart setups');
for (const key of [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
]) if (result[key] !== false) throw new Error(`${key} must remain false`);

fs.mkdirSync('artifacts', { recursive: true });
const out = 'artifacts/phase57-p23-10-chart-perception-remeasurement.json';
fs.writeFileSync(out, JSON.stringify(result, null, 2));
console.log(JSON.stringify({
  status: result.status,
  symbolCount: result.symbolCount,
  totalDirectionalSetups: result.totalDirectionalSetups,
  aggregate: result.aggregate,
  bySetup: result.bySetup,
}, null, 2));
