import fs from 'node:fs';
import path from 'node:path';
import {simulateLaneCPortfolio,PHASE57_P25_LANE_C_ALLOCATION_PROFILES} from '../predict/portfolio/phase57-p25-lane-c-portfolio-simulator.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const partialDir=arg('--partial-dir'),barsPath=arg('--bars'),shardDir=arg('--shard-dir'),output=arg('--output');
if(!partialDir||!barsPath||!shardDir||!output)throw new Error('usage: --partial-dir <dir> --bars <json> --shard-dir <dir> --output <json>');
const freeze=JSON.parse(fs.readFileSync(path.join(partialDir,'freeze.json'),'utf8'));
const measurements=fs.readFileSync(path.join(partialDir,'partial-measurements.ndjson'),'utf8').split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line));
const barsCombined=JSON.parse(fs.readFileSync(barsPath,'utf8'));
if(barsCombined.status!=='P25_INCOMPLETE_ABCD_BARS_COMBINED'||barsCombined.sessionDate!==freeze.sessionDate)throw new Error('combined bars invalid');
const files=fs.readdirSync(shardDir).filter(x=>x.endsWith('.json')).sort();
if(!files.length)throw new Error('no dynamic point shard outputs');
const shards=files.map(f=>JSON.parse(fs.readFileSync(path.join(shardDir,f),'utf8')));
const shardCount=Number(shards[0]?.shardCount);
if(!Number.isInteger(shardCount)||shardCount<1||shards.length!==shardCount)throw new Error(`dynamic shard count mismatch ${shards.length}/${shardCount}`);
const byIndex=new Map();
for(const s of shards){
  if(s?.status!=='P25_INCOMPLETE_ABCD_DYNAMIC_POINT_SHARD_READY'||s.sessionDate!==freeze.sessionDate||Number(s.shardCount)!==shardCount)throw new Error('invalid dynamic point shard');
  if(byIndex.has(Number(s.shardIndex)))throw new Error(`duplicate dynamic shard ${s.shardIndex}`);
  byIndex.set(Number(s.shardIndex),s);
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])if(s.safety?.[k]!==false)throw new Error(`unsafe ${k}`);
}
for(let i=0;i<shardCount;i++)if(!byIndex.has(i))throw new Error(`missing dynamic shard ${i}`);
const covered=[...shards.flatMap(s=>s.sourcePointIndexes??[])].sort((a,b)=>a-b);
if(JSON.stringify(covered)!==JSON.stringify(measurements.map((_,i)=>i)))throw new Error('dynamic point shard coverage/recombination mismatch');
const pairs=shards.flatMap(s=>s.B?.pairs??[]).sort((a,b)=>a.entry.entryTimestamp.localeCompare(b.entry.entryTimestamp)||a.symbol.localeCompare(b.symbol));
const blocked=shards.flatMap(s=>s.B?.blocked??[]);
const pointAudit=shards.flatMap(s=>s.pointAudit??[]).sort((a,b)=>String(a.observedAt).localeCompare(String(b.observedAt)));
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+x,0)/xs.length:null;
const profitFactor=xs=>{const gp=xs.filter(x=>x>0).reduce((s,x)=>s+x,0),gl=-xs.filter(x=>x<0).reduce((s,x)=>s+x,0);return gl>0?gp/gl:(gp>0?Infinity:null);};
const maxDD=xs=>{let e=1,p=1,m=0;for(const r of xs){e*=1+r/100;p=Math.max(p,e);m=Math.max(m,(p-e)/p*100);}return m;};
function summary(xs){const r=xs.filter(finite).map(Number);let e=1;for(const x of r)e*=1+x/100;return {n:r.length,netReturnPct:(e-1)*100,meanNetReturnPct:mean(r),winRate:r.length?r.filter(x=>x>0).length/r.length:null,profitFactor:profitFactor(r),maxDrawdownPct:maxDD(r)};}
const frozenEntryCount=shards.reduce((n,s)=>n+Number(s.B?.frozenEntryCount??0),0);
const bSummary=summary(pairs.map(x=>x.v3.netReturnPct));
const barsBySymbol=barsCombined.sessionBarsBySymbol??{};
const portfolioBars={};
for(const [symbol,rows] of Object.entries(barsBySymbol)){
  const map=new Map((rows??[]).map(bar=>[String(bar.timestamp),{timestamp:String(bar.timestamp),close:Number(bar.close)}]));
  for(const p of pairs.filter(x=>x.symbol===symbol))map.set(p.entry.entryTimestamp,{timestamp:p.entry.entryTimestamp,close:Number(p.entry.entryPrice)});
  portfolioBars[symbol]=[...map.values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}
const sessionDate=freeze.sessionDate;
const portfolioTrades=pairs.map(p=>({entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,symbol:p.symbol,sector:p.entry.sector,signalDirection:p.entry.signalDirection,sessionDate,entryTimestamp:p.entry.entryTimestamp,entryPrice:Number(p.entry.entryPrice),exitTimestamp:p.v3.exitTimestamp,exitPrice:Number(p.v3.exitPrice),exitReason:p.v3.exitReason,netReturnPct:Number(p.v3.netReturnPct)}));
const portfolioSessions=[{sessionDate,sessionBarsBySymbol:portfolioBars,trades:portfolioTrades}];
const dProfiles={};
for(const profile of PHASE57_P25_LANE_C_ALLOCATION_PROFILES)dProfiles[profile.id]=simulateLaneCPortfolio({sessions:portfolioSessions,profile,managementMode:'EXIT_V3',universeVariant:'DYNAMIC_5M'});
const excludedSymbols=[...new Set(shards.flatMap(s=>s.dynamicBundleAudit?.excludedSymbols??[]))].sort();
const safety={executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false};
const payload={schemaVersion:1,phase:'57.p25.incomplete-abcd-dynamic',status:'P25_INCOMPLETE_ABCD_DYNAMIC_READY',sessionDate,B:{route:'Dynamic 5m Selection -> Frozen Entry -> EXIT v3',pointCount:measurements.length,expectedPointCount:measurements.length,missingExpectedBucketCount:0,frozenEntryCount,resolvedCount:pairs.length,blockedCount:blocked.length,summary:bSummary,pairs,blocked},D:{route:'Dynamic 5m Selection -> Frozen Entry -> EXIT v3 -> Capital Allocation',initialEquityJpy:1_000_000,profileWinnerSelected:false,profiles:dProfiles},dynamicBundleAudit:{pointShardCount:shardCount,recombinedPointCount:covered.length,excludedSymbols},methodology:{sameFrozenDynamicSelectionEvidence:true,sameExistingDynamic5mExitV3PortfolioEvaluator:true,pointShardsRecombinedBeforeGlobalCapitalAllocation:true,globalPairOrderRestored:true,capitalAllocationPolicyUnchanged:true,allocationProfileWinnerSelection:false,resultBasedRetuning:false,noBackfillOrFabrication:true},safety};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,B:payload.B.summary,D:Object.fromEntries(Object.entries(dProfiles).map(([k,v])=>[k,{totalReturnPct:v.return?.totalReturnPct,maxDrawdownPct:v.risk?.maxDrawdownPct}]))},null,2));
