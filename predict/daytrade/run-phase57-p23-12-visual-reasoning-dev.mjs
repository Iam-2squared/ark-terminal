import fs from 'node:fs';
import { EXPANDED_UNIVERSE } from './phase57-expanded-universe.js';
import { buildSessionAwareMultiTimeframePerception } from './phase57-chart-perception-session-aware.js';
import { classifyHumanStyleSetup, deriveSameSessionOutcome } from './phase57-chart-perception-measurement.js';
import { scoreHumanStyleSetupQuality } from './phase57-chart-setup-quality.js';
import {
  P23_12_VISUAL_REASONING_POLICY,
  PHASE57_P23_12_SAFETY,
  deriveVisualChartReasoning,
  renderMultiTimeframeChartSvg,
  buildMultimodalChartReasoningManifest,
} from './phase57-visual-chart-reasoning.js';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const symbols = process.env.PHASE57_SYMBOLS
  ? process.env.PHASE57_SYMBOLS.split(',').map(value => value.trim()).filter(Boolean)
  : EXPANDED_UNIVERSE.slice(0, 3);
const minHistoryBars = Number(process.env.PHASE57_MIN_HISTORY_BARS ?? 1600);
const stepBars = Number(process.env.PHASE57_STEP_BARS ?? 3);
const maxContextBars = Number(process.env.PHASE57_MAX_CONTEXT_BARS ?? 2600);
const JST = new Intl.DateTimeFormat('en-CA', {
  timeZone:'Asia/Tokyo', year:'numeric', month:'2-digit', day:'2-digit',
  hour:'2-digit', minute:'2-digit', hourCycle:'h23',
});
const JST_DATE = new Intl.DateTimeFormat('en-CA', {
  timeZone:'Asia/Tokyo', year:'numeric', month:'2-digit', day:'2-digit',
});

function parts(timestamp) {
  const p = Object.fromEntries(JST.formatToParts(new Date(timestamp)).map(x => [x.type, x.value]));
  return { date:`${p.year}-${p.month}-${p.day}`, hm:`${p.hour}:${p.minute}` };
}
function normalize(rows = []) {
  return rows.map(row => ({
    timestamp:new Date(row.timestamp).toISOString(), open:Number(row.open), high:Number(row.high), low:Number(row.low), close:Number(row.close), volume:Number(row.volume ?? 0),
  })).filter(row => [row.open,row.high,row.low,row.close].every(Number.isFinite) && row.high >= row.low)
    .sort((a,b) => a.timestamp.localeCompare(b.timestamp));
}
async function fetchJson(urls, symbol) {
  let last;
  for (const url of urls) {
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 30000);
        const response = await fetch(url, {
          headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0',Accept:'application/json'}, signal:controller.signal,
        });
        clearTimeout(timer);
        if (!response.ok) throw new Error(`${symbol} Yahoo HTTP ${response.status}`);
        return await response.json();
      } catch (error) {
        last = error;
        if (attempt < 4) await sleep(attempt * 1000);
      }
    }
  }
  throw last;
}
function parseYahoo(json, symbol) {
  const result = json?.chart?.result?.[0];
  if (!result) throw new Error(`${symbol} missing Yahoo chart result`);
  const quote = result.indicators?.quote?.[0] ?? {};
  const out = [];
  for (let i = 0; i < (result.timestamp ?? []).length; i += 1) {
    const timestamp = Number(result.timestamp[i]) * 1000;
    const p = parts(timestamp);
    if (!((p.hm >= '09:00' && p.hm < '11:30') || (p.hm >= '12:30' && p.hm < '15:30'))) continue;
    const values = [quote.open?.[i],quote.high?.[i],quote.low?.[i],quote.close?.[i]];
    if (values.some(value => value == null || !Number.isFinite(Number(value)))) continue;
    out.push({
      timestamp:new Date(timestamp).toISOString(), open:Number(quote.open[i]), high:Number(quote.high[i]), low:Number(quote.low[i]), close:Number(quote.close[i]), volume:Number(quote.volume?.[i] ?? 0),
    });
  }
  return normalize(out);
}
async function fetchBars(symbol) {
  const end = Math.floor(Date.now() / 1000);
  const start = end - 58 * 86400;
  const query = `period1=${start}&period2=${end}&interval=5m&includePrePost=false&events=div%2Csplits`;
  const urls = [1,2].map(host => `https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${query}`);
  return parseYahoo(await fetchJson(urls, symbol), symbol);
}
function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + Number(value), 0) / values.length : null;
}
function outcomeSummary(rows, key = 'outcome60m') {
  const valid = rows.filter(row => row[key]);
  return {
    count:valid.length,
    hitRate:valid.length ? valid.filter(row => row[key].hit).length / valid.length : null,
    averageDirectionalReturnPct:valid.length ? mean(valid.map(row => row[key].directionalReturnPct)) : null,
    averageMfePct:valid.length ? mean(valid.map(row => row[key].mfePct)) : null,
    averageMaePct:valid.length ? mean(valid.map(row => row[key].maePct)) : null,
  };
}
function groupSummary(rows, keyFn) {
  const groups = new Map();
  for (const row of rows) {
    const key = keyFn(row);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return Object.fromEntries([...groups].map(([key, values]) => [key, {
    count:values.length,
    outcome30m:outcomeSummary(values,'outcome30m'),
    outcome60m:outcomeSummary(values,'outcome60m'),
    averageVisualScore:mean(values.map(row => row.visualScore)),
    averageLegacyQualityScore:mean(values.map(row => row.legacyQualityScore).filter(Number.isFinite)),
  }]));
}
function legacyBand(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) return 'UNSCORED';
  if (value >= 0.70) return 'Q4_HIGH';
  if (value >= 0.55) return 'Q3';
  if (value >= 0.40) return 'Q2';
  return 'Q1_LOW';
}

const records = [];
const bySymbol = {};
let sampleSvg = null;
let sampleMeta = null;
let sampleManifest = null;
const counters = { evaluatedCutoffs:0, directionalSetups:0, outcomeExcluded:0, visualReady:0 };

for (const symbol of symbols) {
  const bars = await fetchBars(symbol);
  const local = { evaluatedCutoffs:0, directionalSetups:0, visualReady:0 };
  for (let index = Math.max(24, minHistoryBars); index < bars.length - 12; index += Math.max(1, stepBars)) {
    counters.evaluatedCutoffs += 1;
    local.evaluatedCutoffs += 1;
    const context = bars.slice(Math.max(0, index + 1 - maxContextBars), index + 1);
    const perception = buildSessionAwareMultiTimeframePerception({ bars5m: context });
    const setup = classifyHumanStyleSetup(perception);
    if (![1,-1].includes(Number(setup.directionSign))) continue;
    counters.directionalSetups += 1;
    local.directionalSetups += 1;

    const future = bars.slice(index + 1, index + 13);
    const outcome30m = deriveSameSessionOutcome({ entryBar:bars[index], futureBars:future, directionSign:setup.directionSign, horizonBars:6 });
    const outcome60m = deriveSameSessionOutcome({ entryBar:bars[index], futureBars:future, directionSign:setup.directionSign, horizonBars:12 });
    if (!outcome30m && !outcome60m) {
      counters.outcomeExcluded += 1;
      continue;
    }

    const visual = deriveVisualChartReasoning({ symbol, bars5m:context, setupInfo:setup });
    const legacy = scoreHumanStyleSetupQuality(perception, setup);
    if (visual.status === 'VISUAL_REASONING_READY') {
      counters.visualReady += 1;
      local.visualReady += 1;
    }
    const row = {
      symbol,
      sessionDate:JST_DATE.format(new Date(bars[index].timestamp)),
      featureCutoff:bars[index].timestamp,
      setup:setup.setup,
      direction:setup.directionSign === 1 ? 'UP' : 'DOWN',
      visualScore:visual.score,
      visualBand:visual.band,
      visualComponents:visual.components,
      visualGeometry:visual.geometry,
      visualNarrative:visual.narrative,
      legacyQualityScore:Number.isFinite(Number(legacy.score)) ? Number(legacy.score) : null,
      legacyQualityBand:legacyBand(legacy.score),
      outcome30m,
      outcome60m,
      futureOutcomeUsedByVisualReasoning:false,
      visualScoreUsedAsEntryGate:false,
    };
    records.push(row);

    const prefer = !sampleSvg || (sampleMeta?.visualBand !== 'V_A_CLEAN' && visual.band === 'V_A_CLEAN');
    if (prefer) {
      sampleSvg = renderMultiTimeframeChartSvg({ symbol, bars5m:context, setupInfo:setup });
      sampleManifest = buildMultimodalChartReasoningManifest({ symbol, bars5m:context, setupInfo:setup });
      sampleMeta = { symbol, featureCutoff:bars[index].timestamp, setup:setup.setup, visualBand:visual.band, visualScore:visual.score };
    }
  }
  bySymbol[symbol] = { sourceBarCount:bars.length, ...local };
  console.log(JSON.stringify({symbol,...bySymbol[symbol]}));
  await sleep(400);
}

if (!records.length) throw new Error('P23.12 produced no directional visual reasoning records');
const aggregate = {
  phase:'57.p23.12-visual-reasoning-development-measurement',
  status:'VISUAL_CHART_REASONING_DEVELOPMENT_MEASURED',
  symbols,
  symbolCount:symbols.length,
  policy:P23_12_VISUAL_REASONING_POLICY,
  counters,
  aggregate:{
    count:records.length,
    outcome30m:outcomeSummary(records,'outcome30m'),
    outcome60m:outcomeSummary(records,'outcome60m'),
    averageVisualScore:mean(records.map(row => row.visualScore)),
  },
  byVisualBand:groupSummary(records,row => row.visualBand),
  bySetup:groupSummary(records,row => row.setup),
  bySetupAndVisualBand:groupSummary(records,row => `${row.setup}|${row.visualBand}`),
  legacyComparison:groupSummary(records,row => row.legacyQualityBand),
  bySymbol,
  sampleMeta,
  records,
  methodology:{
    developmentUniverseOnly:true,
    freshHoldoutConsumed:false,
    untouchedTemporalOos:false,
    currentSessionFutureBarsNotUsedByVisualReasoning:true,
    futureOutcomesEvaluationOnly:true,
    visualScoreOutcomeTuned:false,
    visualScoreUsedAsEntryGate:false,
    externalVisionModelCalled:false,
    svgRenderedFromCausalPrefixOnly:true,
    higherTimeframesCompletedOnly:true,
    sameSessionOutcomeOnly:true,
  },
  edgeClaimAllowed:false,
  recommendationAllowed:false,
  transmitted:false,
  ...PHASE57_P23_12_SAFETY,
};
for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed']) {
  if (aggregate[key] !== false) throw new Error(`${key} must remain false`);
}
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-p23-12-visual-reasoning-dev.json',JSON.stringify(aggregate,null,2));
if (sampleSvg) fs.writeFileSync('artifacts/phase57-p23-12-visual-sample.svg',sampleSvg);
if (sampleManifest) fs.writeFileSync('artifacts/phase57-p23-12-multimodal-manifest-sample.json',JSON.stringify(sampleManifest,null,2));
console.log(JSON.stringify({status:aggregate.status,symbolCount:aggregate.symbolCount,counters:aggregate.counters,aggregate:aggregate.aggregate,byVisualBand:aggregate.byVisualBand,legacyComparison:aggregate.legacyComparison,sampleMeta:aggregate.sampleMeta},null,2));
