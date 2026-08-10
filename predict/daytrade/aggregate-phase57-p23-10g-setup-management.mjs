import fs from 'node:fs';
import path from 'node:path';
import { CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE } from './phase57-chart-trade-management-holdout-universe.js';
import { summarizeEconomicTrades } from './phase57-chart-economic-validation.js';
import { PHASE57_P23_10G_SAFETY, P23_10G_SETUP_MANAGEMENT_POLICY, summarizePairedExitDelta } from './phase57-setup-specific-trade-management.js';

const root=process.env.PHASE57_ARTIFACT_ROOT??'downloaded';
const files=[];
function walk(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){const full=path.join(dir,entry.name);if(entry.isDirectory())walk(full);else if(entry.isFile()&&entry.name.endsWith('.json'))files.push(full);}}
walk(root);
const shards=files.map(file=>JSON.parse(fs.readFileSync(file,'utf8'))).filter(row=>row?.phase==='57.p23.10g-setup-specific-management-holdout');
if(shards.length!==3) throw new Error(`expected 3 P23.10G shards, got ${shards.length}`);
const pairs=shards.flatMap(row=>row.pairs??[]);
const symbols=[...new Set(shards.flatMap(row=>row.symbols??[]))].sort();
const expected=[...CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE].sort();
if(JSON.stringify(symbols)!==JSON.stringify(expected)) throw new Error('holdout symbol set mismatch');
if(pairs.some(pair=>pair.entrySetFrozenByBaselineOccupancy!==true||pair.exactSameEntryForBothVariants!==true||pair.futureOutcomeUsedForSelection!==false)) throw new Error('paired methodology violation');

function flatten(pair,variant){const exit=pair[variant];return {symbol:pair.symbol,sessionDate:pair.sessionDate,setup:pair.setup,direction:pair.direction,entryTimestamp:pair.entryTimestamp,netReturnPct:exit.netReturnPct,grossReturnPct:exit.grossReturnPct,mfePct:exit.mfePct,maePct:exit.maePct,profitGivebackPctPoints:exit.profitGivebackPctPoints,captureRatio:exit.captureRatio,barsHeld:exit.barsHeld};}
function grouped(keyFn,variant){const groups=new Map();for(const pair of pairs){const key=keyFn(pair);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(flatten(pair,variant));}return Object.fromEntries([...groups].map(([key,rows])=>[key,summarizeEconomicTrades(rows)]));}
function groupedDelta(keyFn){const groups=new Map();for(const pair of pairs){const key=keyFn(pair);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(pair);}return Object.fromEntries([...groups].map(([key,rows])=>[key,summarizePairedExitDelta(rows)]));}
const baselineRows=pairs.map(pair=>flatten(pair,'baseline'));
const managedRows=pairs.map(pair=>flatten(pair,'managed'));
const aggregate={
  phase:'57.p23.10g-setup-specific-management-aggregate',
  status:'SETUP_SPECIFIC_MANAGEMENT_PAIRED_HOLDOUT_AGGREGATED',
  shardCount:shards.length,symbolCount:symbols.length,symbols,
  policy:P23_10G_SETUP_MANAGEMENT_POLICY,
  pairCount:pairs.length,
  baseline:summarizeEconomicTrades(baselineRows),
  managed:summarizeEconomicTrades(managedRows),
  pairedDelta:summarizePairedExitDelta(pairs),
  bySetup:{baseline:grouped(row=>row.setup,'baseline'),managed:grouped(row=>row.setup,'managed'),delta:groupedDelta(row=>row.setup)},
  byDirection:{baseline:grouped(row=>row.direction,'baseline'),managed:grouped(row=>row.direction,'managed'),delta:groupedDelta(row=>row.direction)},
  methodology:{
    exactFourthHoldoutSymbolSet:true,
    exactPairedEntrySet:true,
    entrySetFrozenByBaselineOccupancy:true,
    setupManagementArchitecturePreRegistered:true,
    setupSpecificNumericParameterSearch:false,
    futureOutcomeUsedForSelection:false,
    confirmatoryCrossSymbolOos:true,
    untouchedTemporalOos:false,
    ratiosRecomputedFromExactPairs:true,
  },
  pairs,
  edgeClaimAllowed:false,recommendationAllowed:false,transmitted:false,
  ...PHASE57_P23_10G_SAFETY,
};
for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed'])if(aggregate[key]!==false)throw new Error(`${key} must remain false`);
if(!pairs.length) throw new Error('empty paired aggregate');
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-p23-10g-setup-management-aggregate.json',JSON.stringify(aggregate,null,2));
console.log(JSON.stringify({status:aggregate.status,pairCount:aggregate.pairCount,baseline:aggregate.baseline,managed:aggregate.managed,pairedDelta:aggregate.pairedDelta,byDirection:aggregate.byDirection,bySetup:aggregate.bySetup},null,2));
