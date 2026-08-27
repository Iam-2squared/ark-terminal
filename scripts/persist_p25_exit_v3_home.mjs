import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const evidencePath=arg('--evidence');
const inputPath=arg('--input','data/home/paper-equity.json');
const outputPath=arg('--output',inputPath);
const durableEvidencePath=arg('--durable-evidence');
if(!evidencePath||!durableEvidencePath){console.error('usage: node scripts/persist_p25_exit_v3_home.mjs --evidence <json> --durable-evidence <json> [--input file] [--output file]');process.exit(2);}

const EXPECTED_SOURCE_RUN_ID=33037297017;
const EXPECTED_SOURCE_JSON_SHA256='fd6bdc7ed186459057655a779e39ec339dc7a8beaa0e11af3791273a9bbdef15';
const REQUIRED_FALSE=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'];
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const evidenceBytes=fs.readFileSync(evidencePath);
const sourceJsonSha256=sha(evidenceBytes);
if(sourceJsonSha256!==EXPECTED_SOURCE_JSON_SHA256) throw new Error(`EXIT v3 source JSON SHA mismatch: ${sourceJsonSha256}`);
const evidence=JSON.parse(evidenceBytes.toString('utf8'));
const r=evidence?.result;
if(r?.status!=='P25_EXIT_V3_HISTORICAL_REPLAY_REDUCED') throw new Error(`Unexpected EXIT v3 status: ${r?.status}`);
if(r?.summary?.pairedCount!==27) throw new Error(`EXIT v3 paired n mismatch: ${r?.summary?.pairedCount}`);
if(r?.classification?.diagnosticOnly!==true||r?.classification?.formalOos!==false||r?.classification?.promotionEligible!==false) throw new Error('EXIT v3 classification guard violation');
if(r?.methodology?.resultBasedRetuning!==false||r?.methodology?.freshHoldoutConsumed!==false) throw new Error('EXIT v3 methodology guard violation');
for(const k of REQUIRED_FALSE) if(r?.safety?.[k]!==false&&evidence?.safety?.[k]!==false) throw new Error(`EXIT v3 safety guard violation: ${k}`);

const pairs=Array.isArray(r?.pairs)?r.pairs:[];
if(pairs.length!==27) throw new Error(`EXIT v3 pairs length mismatch: ${pairs.length}`);
const byDate=new Map();
for(const pair of pairs){
  const date=String(pair?.sessionDate??'');
  const ret=Number(pair?.v3?.netReturnPct);
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(ret)) throw new Error('EXIT v3 pair missing date/net return');
  if(!byDate.has(date)) byDate.set(date,[]);
  byDate.get(date).push(ret);
}
const sessionDates=[...byDate.keys()].sort();
const expected=['2026-08-19','2026-08-20','2026-08-24','2026-08-25'];
if(JSON.stringify(sessionDates)!==JSON.stringify(expected)) throw new Error(`EXIT v3 resolved session dates mismatch: ${JSON.stringify(sessionDates)}`);

const home=JSON.parse(fs.readFileSync(inputPath,'utf8'));
const start=Number(home.startingCapitalJpy??1000000);
let equity=start;
const series=[{date:'2026-08-18',equityJpy:start,dailyReturnPct:0,resolvedEntries:0,source:'START'}];
for(const date of sessionDates){
  const values=byDate.get(date);
  const dailyReturnPct=values.reduce((s,x)=>s+x,0)/values.length;
  equity=Math.round((equity*(1+dailyReturnPct/100))*100)/100;
  series.push({date,equityJpy:equity,dailyReturnPct,resolvedEntries:values.length,source:`EXIT_V3_RUN_${EXPECTED_SOURCE_RUN_ID}`});
}
home.schemaVersion=Math.max(2,Number(home.schemaVersion??1));
home.mode='ARK_RESEARCH_EQUITY';
home.variants=['DYNAMIC_30','DYNAMIC_40','DYNAMIC_50','EXIT_V3'];
home.series=home.series??{};
home.series.EXIT_V3=series;
home.latestExitV3={
  evidenceDate:'2026-08-25',
  sourceRunId:EXPECTED_SOURCE_RUN_ID,
  sourceArtifact:'phase57-p25-exit-v3-historical-replay-legacy27',
  sourceJsonSha256,
  policySha256:r.policySha256,
  pairedCount:r.summary.pairedCount,
  afterCostNetPct:Number(r.summary.v3.netReturnPct),
  profitFactor:Number(r.summary.v3.profitFactor),
  maxDrawdownPct:Number(r.summary.v3.maxDrawdownPct),
  winRate:Number(r.summary.v3.winRate),
  meanNetReturnPct:Number(r.summary.v3.meanNetReturnPct),
  diagnosticOnly:true,
  formalOos:false,
  promotionEligible:false,
  primaryFrozenCandidate:true,
  freshHoldoutConsumed:false,
};
home.sourceNote='D30/D40/D50 remain formal Entry-only research series. EXIT_V3 is the frozen Lane B primary candidate and is shown from immutable diagnostic replay evidence; it is not formal OOS or promotion eligible until fresh prospective evidence accumulates.';
home.lastUpdatedAt=new Date().toISOString();
home.safety={researchOnly:true,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false};
fs.writeFileSync(outputPath,JSON.stringify(home,null,2)+'\n','utf8');

const durable={schemaVersion:1,phase:'57.p25.exit-v3.durable-evidence',status:'P25_EXIT_V3_DURABLY_PERSISTED',createdAt:new Date().toISOString(),source:{runId:EXPECTED_SOURCE_RUN_ID,artifact:'phase57-p25-exit-v3-historical-replay-legacy27',jsonSha256:sourceJsonSha256},result:r,methodology:{...r.methodology,primaryFrozenCandidate:true,noV1V2ForwardPersistence:true},safety:home.safety};
fs.mkdirSync(path.dirname(durableEvidencePath),{recursive:true});
fs.writeFileSync(durableEvidencePath,JSON.stringify(durable,null,2)+'\n','utf8');
console.log(JSON.stringify({status:durable.status,pairedCount:r.summary.pairedCount,v3:r.summary.v3,homeExitV3Points:series.length,sourceJsonSha256},null,2));
