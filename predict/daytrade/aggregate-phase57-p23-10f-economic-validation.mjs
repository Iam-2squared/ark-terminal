import fs from 'node:fs';
import path from 'node:path';
import { CHART_ECONOMIC_HOLDOUT_UNIVERSE } from './phase57-chart-economic-holdout-universe.js';
import { P23_10F_ECONOMIC_POLICY, PHASE57_P23_10F_SAFETY, summarizeEconomicTrades } from './phase57-chart-economic-validation.js';

const root=process.argv[2]??'artifacts/p23-10f-input';
const files=fs.existsSync(root)
  ? fs.readdirSync(root,{recursive:true}).filter(name=>String(name).endsWith('.json')).map(name=>path.join(root,String(name)))
  : [];
if (!files.length) throw new Error(`no P23.10F shard JSON found under ${root}`);
const shards=files.map(file=>JSON.parse(fs.readFileSync(file,'utf8'))).filter(row=>row?.status==='FROZEN_CHART_ECONOMIC_VALIDATION_COMPLETE');
if (!shards.length) throw new Error('no valid P23.10F shard payloads');
const symbols=[...new Set(shards.flatMap(row=>row.symbols??[]))].sort();
const expected=[...CHART_ECONOMIC_HOLDOUT_UNIVERSE].sort();
if (JSON.stringify(symbols)!==JSON.stringify(expected)) throw new Error(`economic holdout mismatch: got ${symbols.join(',')}`);
const records=shards.flatMap(row=>row.records??[]).sort((a,b)=>String(a.entryTimestamp).localeCompare(String(b.entryTimestamp))||String(a.symbol).localeCompare(String(b.symbol)));
if (!records.length) throw new Error('aggregate contains no economic trades');
const group=(keyFn)=>{
  const m=new Map();
  for (const row of records) { const key=keyFn(row); if(!m.has(key))m.set(key,[]); m.get(key).push(row); }
  return Object.fromEntries([...m].map(([key,rows])=>[key,summarizeEconomicTrades(rows)]));
};
const counters={};
for (const shard of shards) for (const [key,value] of Object.entries(shard.counters??{})) counters[key]=(counters[key]??0)+Number(value??0);
const result={
  phase:'57.p23.10f-frozen-economic-validation-aggregate',
  status:'FROZEN_CHART_ECONOMIC_VALIDATION_AGGREGATED',
  symbolCount:symbols.length,
  symbols,
  shardCount:shards.length,
  counters,
  aggregate:summarizeEconomicTrades(records),
  bySetup:group(row=>row.setup),
  byDirection:group(row=>row.direction),
  records,
  policy:P23_10F_ECONOMIC_POLICY,
  methodology:{
    exactFrozenEconomicUniverse:true,
    symbolsFreshVersusPriorChart60:true,
    setupRulesFrozen:true,
    qualityRulesFrozen:true,
    q4ThresholdFrozen:true,
    nextBarOpenEntry:true,
    oneActiveTradePerSymbol:true,
    p23_8dExitFrozen:true,
    roundTripFrictionPct:P23_10F_ECONOMIC_POLICY.roundTripFrictionPct,
    futureOutcomeUsedForSelection:false,
    confirmatoryCrossSymbolOos:true,
    untouchedTemporalOos:false,
    ratiosRecomputedFromTradeRecords:true,
  },
  edgeClaimAllowed:false,
  recommendationAllowed:false,
  transmitted:false,
  ...PHASE57_P23_10F_SAFETY,
};
for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed']) if(result[key]!==false) throw new Error(`${key} must remain false`);
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-p23-10f-economic-validation-aggregate.json',JSON.stringify(result,null,2));
console.log(JSON.stringify({status:result.status,symbolCount:result.symbolCount,shardCount:result.shardCount,counters:result.counters,aggregate:result.aggregate,bySetup:result.bySetup},null,2));
