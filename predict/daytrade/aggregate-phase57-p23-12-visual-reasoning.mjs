import fs from 'node:fs';
import path from 'node:path';
import { EXPANDED_UNIVERSE } from './phase57-expanded-universe.js';
import { P23_12_VISUAL_REASONING_POLICY, PHASE57_P23_12_SAFETY } from './phase57-visual-chart-reasoning.js';

const root = process.env.PHASE57_ARTIFACT_ROOT ?? process.argv[2] ?? 'downloaded';
const files = [];
function walk(dir) {
  for (const entry of fs.readdirSync(dir,{withFileTypes:true})) {
    const full = path.join(dir,entry.name);
    if (entry.isDirectory()) walk(full);
    else if (entry.isFile() && entry.name.endsWith('.json')) files.push(full);
  }
}
walk(root);
const shards = files.map(file => JSON.parse(fs.readFileSync(file,'utf8')))
  .filter(row => row?.phase === '57.p23.12-visual-reasoning-development-measurement');
if (shards.length !== 3) throw new Error(`expected 3 P23.12 shards, got ${shards.length}`);
const records = shards.flatMap(row => row.records ?? []);
const symbols = [...new Set(shards.flatMap(row => row.symbols ?? []))].sort();
const expected = [...EXPANDED_UNIVERSE].sort();
if (JSON.stringify(symbols) !== JSON.stringify(expected)) throw new Error('P23.12 expanded-universe mismatch');
if (!records.length) throw new Error('empty P23.12 aggregate records');
if (records.some(row => row.futureOutcomeUsedByVisualReasoning !== false || row.visualScoreUsedAsEntryGate !== false)) throw new Error('visual reasoning leakage/gating violation');

const mean = values => values.length ? values.reduce((sum,value) => sum + Number(value),0) / values.length : null;
function outcomeSummary(rows,key) {
  const valid = rows.filter(row => row[key]);
  return {
    count:valid.length,
    hitRate:valid.length ? valid.filter(row => row[key].hit).length / valid.length : null,
    averageDirectionalReturnPct:valid.length ? mean(valid.map(row => row[key].directionalReturnPct)) : null,
    averageMfePct:valid.length ? mean(valid.map(row => row[key].mfePct)) : null,
    averageMaePct:valid.length ? mean(valid.map(row => row[key].maePct)) : null,
  };
}
function groupSummary(rows,keyFn) {
  const groups = new Map();
  for (const row of rows) {
    const key = keyFn(row);
    if (!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(row);
  }
  return Object.fromEntries([...groups].map(([key,values]) => [key,{
    count:values.length,
    outcome30m:outcomeSummary(values,'outcome30m'),
    outcome60m:outcomeSummary(values,'outcome60m'),
    averageVisualScore:mean(values.map(row => row.visualScore)),
    averageLegacyQualityScore:mean(values.map(row => row.legacyQualityScore).filter(Number.isFinite)),
  }]));
}

const counters = Object.fromEntries([...new Set(shards.flatMap(row => Object.keys(row.counters ?? {})))].map(key => [
  key, shards.reduce((sum,row) => sum + Number(row.counters?.[key] ?? 0),0),
]));
const bySymbol = Object.assign({}, ...shards.map(row => row.bySymbol ?? {}));
const aggregate = {
  phase:'57.p23.12-visual-reasoning-development-aggregate',
  status:'VISUAL_CHART_REASONING_DEVELOPMENT_AGGREGATED',
  shardCount:shards.length,
  symbolCount:symbols.length,
  symbols,
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
  records,
  methodology:{
    exactExpandedDevelopmentUniverse:true,
    ratiosRecomputedFromExactRecords:true,
    developmentUniverseOnly:true,
    freshHoldoutConsumed:false,
    untouchedTemporalOos:false,
    futureOutcomesEvaluationOnly:true,
    futureOutcomeUsedByVisualReasoning:false,
    visualScoreOutcomeTuned:false,
    visualScoreUsedAsEntryGate:false,
    externalVisionModelCalled:false,
    svgRenderedFromCausalPrefixOnly:true,
    higherTimeframesCompletedOnly:true,
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
fs.writeFileSync('artifacts/phase57-p23-12-visual-reasoning-dev-aggregate.json',JSON.stringify(aggregate,null,2));
console.log(JSON.stringify({status:aggregate.status,symbolCount:aggregate.symbolCount,aggregate:aggregate.aggregate,byVisualBand:aggregate.byVisualBand,legacyComparison:aggregate.legacyComparison,bySetup:aggregate.bySetup},null,2));
