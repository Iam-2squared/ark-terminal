import fs from 'node:fs';
import path from 'node:path';
import { CHART_QUALITY_HOLDOUT_UNIVERSE } from './phase57-chart-quality-holdout-universe.js';
import { PHASE57_CHART_PERCEPTION_SAFETY } from './phase57-chart-perception-2.js';

const root = process.argv[2] ?? 'artifacts/p23-16-shards';
const COST_PCT = 0.05;

function filesRecursively(dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...filesRecursively(p));
    else if (entry.isFile() && entry.name.endsWith('.json')) out.push(p);
  }
  return out;
}

function mean(values) {
  return values.length ? values.reduce((a,b)=>a+Number(b),0)/values.length : null;
}

function profitFactor(values) {
  const gains = values.filter(x=>x>0).reduce((a,b)=>a+b,0);
  const losses = -values.filter(x=>x<0).reduce((a,b)=>a+b,0);
  return losses > 0 ? gains/losses : gains > 0 ? Infinity : null;
}

function summarize(rows, horizon='outcome60m') {
  const valid = rows.filter(r => Number.isFinite(Number(r?.[horizon]?.directionalReturnPct)));
  const gross = valid.map(r=>Number(r[horizon].directionalReturnPct));
  const net = gross.map(x=>x-COST_PCT);
  return {
    count: valid.length,
    hitRate: valid.length ? valid.filter(r=>Boolean(r[horizon]?.hit)).length/valid.length : null,
    averageDirectionalReturnPct: mean(gross),
    averageNetAfterCostPct: mean(net),
    profitFactorAfterCost: profitFactor(net),
    averageMfePct: mean(valid.map(r=>Number(r[horizon]?.mfePct)).filter(Number.isFinite)),
    averageMaePct: mean(valid.map(r=>Number(r[horizon]?.maePct)).filter(Number.isFinite)),
  };
}

function group(rows, keyFn) {
  const map = new Map();
  for (const row of rows) {
    const key = keyFn(row);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(row);
  }
  return Object.fromEntries([...map].map(([k,v])=>[k,summarize(v)]));
}

const files = filesRecursively(root).filter(f=>f.includes('phase57-p23-10d-setup-quality'));
if (files.length !== 3) throw new Error(`expected 3 shard files, got ${files.length}`);
const shards = files.map(f=>JSON.parse(fs.readFileSync(f,'utf8')));
const symbols = shards.flatMap(s=>s.symbols ?? []);
if (symbols.length !== 30 || new Set(symbols).size !== 30) throw new Error('expected exactly 30 unique symbols');
for (const s of CHART_QUALITY_HOLDOUT_UNIVERSE) if (!symbols.includes(s)) throw new Error(`missing frozen holdout symbol ${s}`);
const records = shards.flatMap(s=>s.records ?? []);
if (!records.length) throw new Error('no records');

const q4 = records.filter(r=>r.qualityBand==='Q4_HIGH');
const result = {
  phase: '57.p23.16-strong-entry-baseline',
  status: 'STRONG_ENTRY_BASELINE_REMEASURED',
  baselineSource: 'P23.10E_Q4_HIGH_FROZEN_CROSS_SYMBOL_RULES',
  symbolCount: 30,
  totalDirectionalSetups: records.length,
  q4Coverage: q4.length/records.length,
  allDirectional: summarize(records),
  q4High: summarize(q4),
  q4BySetup: group(q4, r=>r.setup),
  q4ByDirection: group(q4, r=>String(r.direction ?? 'UNKNOWN')),
  methodology: {
    remeasurementOfPreviouslyObservedCrossSymbolHoldout: true,
    freshHoldoutConsumed: false,
    untouchedTemporalOos: false,
    setupRulesFrozen: true,
    qualityScoreFrozen: true,
    q4ThresholdFrozen: true,
    outcomeBasedRetuningAllowed: false,
    sameSession60mOutcomeEvaluation: true,
    transactionCostPct: COST_PCT,
    useAsRestoredEntryBaselineOnly: true,
    edgeClaimAllowed: false,
  },
  edgeClaimAllowed: false,
  recommendationAllowed: false,
  transmitted: false,
  ...PHASE57_CHART_PERCEPTION_SAFETY,
};
for (const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed']) {
  if (result[k] !== false) throw new Error(`${k} must remain false`);
}
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-p23-16-strong-entry-baseline.json',JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
