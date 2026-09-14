import {createHash} from 'node:crypto';
import {PHASE57_LONG_ONLY_SAFETY,assertLongOnlyResearchContract} from './phase57-long-only-research-contract.js';

export const PHASE57_LONG_ONLY_L0_POLICY=Object.freeze({
  policyId:'PHASE57_LONG_ONLY_L0_OPPORTUNITY_CENSUS_V1',
  thresholdsPct:Object.freeze([3,5,10]),
  segments:Object.freeze(['PRIME','STANDARD','GROWTH']),
  returnDefinition:'100 * (adjustedClose / adjustedPreviousClose - 1)',
  dailyBarOnly:true,
  selectorModelBuilt:false,
  futureOutcomeFeatureAllowed:false,
  developmentOnlyAtInitialRun:true,
  pointInTimeListingMembershipRequired:true,
});

const q=(sorted,p)=>{
  if(!sorted.length)return null;
  const index=(sorted.length-1)*p,lower=Math.floor(index),upper=Math.ceil(index);
  return lower===upper?sorted[lower]:sorted[lower]+(sorted[upper]-sorted[lower])*(index-lower);
};
const rounded=value=>Number.isFinite(value)?Number(value.toFixed(6)):value;
const stats=values=>{
  const sorted=[...values].sort((a,b)=>a-b);
  if(!sorted.length)return Object.freeze({n:0,mean:null,median:null,p25:null,p75:null,min:null,max:null});
  return Object.freeze({n:sorted.length,mean:rounded(sorted.reduce((a,b)=>a+b,0)/sorted.length),median:rounded(q(sorted,.5)),p25:rounded(q(sorted,.25)),p75:rounded(q(sorted,.75)),min:sorted[0],max:sorted.at(-1)});
};
const canonicalSegment=value=>String(value??'').trim().toUpperCase();

function normalizeRows(rows){
  const seen=new Set(),normalized=[];
  for(const [index,row] of (Array.isArray(rows)?rows:[]).entries()){
    const sessionDate=String(row?.sessionDate??row?.date??''),symbol=String(row?.symbol??row?.code??'').trim().toUpperCase();
    const segment=canonicalSegment(row?.segment??row?.marketSegment),close=Number(row?.adjustedClose),previousClose=Number(row?.adjustedPreviousClose);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`invalid L0 sessionDate at row ${index}`);
    if(!symbol)throw new Error(`missing L0 symbol at row ${index}`);
    if(!PHASE57_LONG_ONLY_L0_POLICY.segments.includes(segment))throw new Error(`unsupported or missing point-in-time segment at row ${index}: ${segment||'MISSING'}`);
    if(!Number.isFinite(close)||close<=0||!Number.isFinite(previousClose)||previousClose<=0)throw new Error(`invalid adjusted close pair at row ${index}`);
    if(row?.listingMembershipPointInTime!==true)throw new Error(`point-in-time listing membership is required at row ${index}`);
    const key=`${sessionDate}|${symbol}`;
    if(seen.has(key))throw new Error(`duplicate L0 row: ${key}`);
    seen.add(key);
    normalized.push(Object.freeze({sessionDate,symbol,segment,returnPct:100*(close/previousClose-1)}));
  }
  return normalized.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.symbol.localeCompare(b.symbol));
}

function sessionCounts(rows,threshold,segment=null){
  const sessions=new Map();
  for(const row of rows){
    if(segment&&row.segment!==segment)continue;
    if(!sessions.has(row.sessionDate))sessions.set(row.sessionDate,0);
    if(row.returnPct>=threshold)sessions.set(row.sessionDate,sessions.get(row.sessionDate)+1);
  }
  return [...sessions].sort(([a],[b])=>a.localeCompare(b)).map(([sessionDate,count])=>Object.freeze({sessionDate,count}));
}

export function buildLongOnlyL0OpportunityCensus({rows=[],partition='DEVELOPMENT',sourceManifest={}}={}){
  assertLongOnlyResearchContract();
  if(partition!=='DEVELOPMENT')throw new Error('initial L0 census may consume DEVELOPMENT only');
  const normalized=normalizeRows(rows);
  if(!normalized.length)throw new Error('L0 census requires at least one valid row');
  const sessionDates=[...new Set(normalized.map(row=>row.sessionDate))];
  const overall={},bySegment={};
  for(const threshold of PHASE57_LONG_ONLY_L0_POLICY.thresholdsPct){
    const points=sessionCounts(normalized,threshold);
    overall[`gte${threshold}Pct`]=Object.freeze({summary:stats(points.map(x=>x.count)),sessions:Object.freeze(points)});
  }
  for(const segment of PHASE57_LONG_ONLY_L0_POLICY.segments){
    bySegment[segment]={};
    for(const threshold of PHASE57_LONG_ONLY_L0_POLICY.thresholdsPct){
      const points=sessionCounts(normalized,threshold,segment);
      bySegment[segment][`gte${threshold}Pct`]=Object.freeze({summary:stats(points.map(x=>x.count)),sessions:Object.freeze(points)});
    }
    bySegment[segment]=Object.freeze(bySegment[segment]);
  }
  const lineage=Object.freeze({
    sourceIdentity:String(sourceManifest?.sourceIdentity??''),
    sourceSha256:String(sourceManifest?.sourceSha256??''),
    timestampContract:String(sourceManifest?.timestampContract??''),
    rowCount:normalized.length,
    sessionCount:sessionDates.length,
    symbolCount:new Set(normalized.map(row=>row.symbol)).size,
    canonicalInputSha256:createHash('sha256').update(JSON.stringify(normalized)).digest('hex'),
  });
  if(!lineage.sourceIdentity||!lineage.sourceSha256||!lineage.timestampContract)throw new Error('complete L0 source lineage is required');
  return Object.freeze({
    schemaVersion:1,phase:'57.long-only.l0-opportunity-census',status:'LONG_ONLY_L0_CENSUS_READY',partition,
    policy:PHASE57_LONG_ONLY_L0_POLICY,lineage,overall:Object.freeze(overall),bySegment:Object.freeze(bySegment),
    methodology:Object.freeze({outcomeUsedForSelector:false,modelBuilt:false,thresholdTuned:false,untouchedOosConsumed:false,freshConsumed:false,badSessionsRemoved:false}),
    safety:PHASE57_LONG_ONLY_SAFETY,
  });
}

