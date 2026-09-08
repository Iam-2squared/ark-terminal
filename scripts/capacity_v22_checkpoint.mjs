import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
export const SOURCE_RUN = 34189128681;
export const SOURCE_SHA = 'f3543b5a604d25442c28fc3cb475e89274400bd5';
export const MODEL_DIGEST = '444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2';
export const FEATURES = ['hybridQualityDecayRank5To1','qualifiedCandidateCount','marketBreadth','dataQualityConfidence'];
export const SAFETY = Object.fromEntries(['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'].map(k=>[k,false]));
export const hash = b => createHash('sha256').update(b).digest('hex');
export const finite = v => typeof v === 'number' && Number.isFinite(v);
export const mean = xs => xs.length ? xs.reduce((a,b)=>a+b,0)/xs.length : null;
export function check(ok,message) { if(!ok) throw new Error(message); }
export function writeReport(dir,name,value) {
  fs.mkdirSync(dir,{recursive:true}); const bytes=JSON.stringify(value,null,2)+'\n';
  fs.writeFileSync(path.join(dir,name),bytes);fs.writeFileSync(path.join(dir,name+'.sha256'),hash(bytes)+'  '+name+'\n');return hash(bytes);
}
function readVerified(file) {
  const bytes=fs.readFileSync(file);
  check(hash(bytes)===fs.readFileSync(file+'.sha256','utf8').trim().split(/\s+/)[0],'CHECKPOINT_HASH_MISMATCH');
  return {value:JSON.parse(bytes),sha256:hash(bytes)};
}
export function validateRows(rows,dates) {
  check(dates.length===89 && new Set(dates).size===89,'DEVELOPMENT_DATE_COUNT');
  check(rows.length===1780,'DEVELOPMENT_ROW_COUNT');
  check(new Set(rows.map(r=>r.featureCutoff)).size===1780,'DUPLICATE_DECISION');
  for(const date of dates) check(rows.filter(r=>r.sessionDate===date).length===20,'SESSION_DECISION_COUNT');
  for(const row of rows) {
    check(dates.includes(row.sessionDate),'SEALED_DATE_REJECTED');
    check(Number.isFinite(Date.parse(row.featureCutoff)) && new Date(Date.parse(row.featureCutoff)+9*3600000).toISOString().slice(0,10)===row.sessionDate,'TIMESTAMP_SESSION_MISMATCH');
    check(row.modelDigest===MODEL_DIGEST && row.prefixIdentity===true,'FROZEN_SOURCE_IDENTITY');
    check(JSON.stringify(Object.keys(row.features).sort())===JSON.stringify([...FEATURES].sort()),'FEATURE_WHITELIST');
    check(FEATURES.every(k=>row.features[k]===null || finite(row.features[k])),'FEATURE_VALUE');
    check(Number.isInteger(row.frozenSelectedCount)&&row.frozenSelectedCount>=0&&row.frozenSelectedCount<=20,'BASELINE_COUNT');
    check(Number.isInteger(row.rankedCount)&&row.rankedCount>=row.frozenSelectedCount,'RANKED_COUNT');
    for(let k=1;k<=20;k++) check(row.utilityByCapacity[k]===null || finite(row.utilityByCapacity[k]),'UTILITY_VALUE');
    check(row.frozenSelectedUtility===null || finite(row.frozenSelectedUtility),'BASELINE_UTILITY_VALUE');
  }
}
export function loadCheckpoints(root='artifacts/capacity-v22-input') {
  const allocation=readVerified(path.join(root,'allocation/allocation.json'));
  const a=allocation.value;
  check(a.status==='CAPACITY_V2_1_FRESH_ALLOCATION_MATERIALIZED','ALLOCATION_STATUS');
  check(Object.keys(SAFETY).every(k=>a.safety?.[k]===false),'ALLOCATION_SAFETY');
  const dates=[...a.developmentDates].sort(), names=fs.readdirSync(path.join(root,'shards')).sort();
  check(names.length===6,'SHARD_COUNT');const shards=[],rows=[],seen=new Set();
  for(const name of names) {
    const {value:r,sha256}=readVerified(path.join(root,'shards',name,'decision-samples.json'));
    check(r.status==='CAPACITY_V2_1_DEVELOPMENT_SHARD_COMPLETE' && r.datasetId===a.datasetId,'SHARD_IDENTITY');
    check(r.shardCount===6 && Number.isInteger(r.shardIndex)&&r.shardIndex>=0&&r.shardIndex<6&&!seen.has(r.shardIndex),'SHARD_INDEX');seen.add(r.shardIndex);
    check(Object.keys(SAFETY).every(k=>r.safety?.[k]===false),'SHARD_SAFETY');
    const expected=dates.filter((_,i)=>i%6===r.shardIndex);
    check(r.rows.length===expected.length*20 && r.decisionCount===r.rows.length,'SHARD_ROWS');
    check(JSON.stringify([...new Set(r.rows.map(x=>x.sessionDate))].sort())===JSON.stringify(expected),'SHARD_DATES');
    rows.push(...r.rows);shards.push({name,shardIndex:r.shardIndex,sha256});
  }
  rows.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));validateRows(rows,dates);
  return {rows,dates,ancestry:{sourceRunId:SOURCE_RUN,sourceHeadSha:SOURCE_SHA,allocationSha256:allocation.sha256,shards,sessionCount:89,decisionCount:1780,newFreshSessionsConsumed:0}};
}
export function sessionMean(rows,value) {
  const dates=[...new Set(rows.map(r=>r.sessionDate))].sort();
  return mean(dates.map(date=>mean(rows.filter(r=>r.sessionDate===date).map(value).filter(finite))).filter(finite));
}
export function auditRows(rows) {
  const active=rows.filter(r=>r.frozenSelectedCount>0);
  const paired=active.filter(r=>finite(r.frozenSelectedUtility)&&finite(r.utilityByCapacity[r.frozenSelectedCount]));
  const differences=paired.map(r=>r.utilityByCapacity[r.frozenSelectedCount]-r.frozenSelectedUtility);
  const layers=[[5,10,'RANK_6_10'],[10,15,'RANK_11_15'],[15,20,'RANK_16_20']].map(([lo,hi,name])=>{
    const ready=active.filter(r=>finite(r.targets[name])&&finite(r.utilityByCapacity[lo])&&finite(r.utilityByCapacity[hi]));
    return {name,readyDecisions:ready.length,absoluteMarginalMean:sessionMean(ready,r=>r.targets[name]),
      incrementalPrefixMean:sessionMean(ready,r=>r.utilityByCapacity[hi]-r.utilityByCapacity[lo]),
      positiveMarginalButNegativeDelta:ready.filter(r=>r.targets[name]>0&&r.utilityByCapacity[hi]<r.utilityByCapacity[lo]).length,
      equalCandidateCountIdentityMismatch:ready.filter(r=>Math.abs(r.utilityByCapacity[hi]-(lo*r.utilityByCapacity[lo]+(hi-lo)*r.targets[name])/hi)>1e-7).length};
  });
  return {status:'CAPACITY_V2_2_DEVELOPMENT_SEMANTICS_AUDIT',trainingStarted:false,
    sessionCount:new Set(rows.map(r=>r.sessionDate)).size,decisionCount:rows.length,
    activeDecisions:active.length,abstainDecisions:rows.length-active.length,
    baselineAudit:{pairedDecisions:paired.length,mismatchDecisions:differences.filter(v=>Math.abs(v)>1e-7).length,
      actualFrozenSelectedUtility:sessionMean(paired,r=>r.frozenSelectedUtility),
      prefixCountUtility:sessionMean(paired,r=>r.utilityByCapacity[r.frozenSelectedCount]),
      sessionEqualDifference:sessionMean(paired,r=>r.utilityByCapacity[r.frozenSelectedCount]-r.frozenSelectedUtility),
      maximumAbsoluteDifference:Math.max(0,...differences.map(Math.abs))},
    layers,completeTargetDecisions:active.filter(r=>finite(r.frozenSelectedUtility)&&[5,10,15,20].every(k=>finite(r.utilityByCapacity[k]))).length,
    missingFeatures:rows.filter(r=>FEATURES.some(k=>!finite(r.features[k]))).length,
    minimumRankedCount:Math.min(...rows.map(r=>r.rankedCount)),
    limitations:['Cached prefixIdentity is a source declaration, not a stored symbol-level membership proof.','Per-symbol target availability counts and target-end timestamps are not retained. Preserve available-case semantics; do not claim a raw-feed re-audit.'],
    validationReleased:false,untouchedOosReleased:false,reserveReleased:false,safety:SAFETY};
}
