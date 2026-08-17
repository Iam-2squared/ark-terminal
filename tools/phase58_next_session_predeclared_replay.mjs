import fs from 'node:fs';
import crypto from 'node:crypto';
import {buildPhase58P2P3} from '../predict/scalping/phase58-orderbook-tickflow.js';
import {estimateScalpingCostBps,evaluatePinnedWalkForward} from '../predict/scalping/phase58-integration-benchmark.js';

const EXPECTED_SHA='012445c255125f30663a4237334ba0b6ca144b8c144a5fce3682ed07bade305d';
const PRIMARY_HORIZON_SECONDS=120;
const LOOKBACK=5;
const MIN_NON_OVERLAP_FOR_CLAIM=100;
const finite=x=>Number.isFinite(Number(x));
const sign=x=>x>0?1:x<0?-1:0;
const sha256=buf=>crypto.createHash('sha256').update(buf).digest('hex');

function parseJsonl(buf){return buf.toString('utf8').split(/\r?\n/).filter(Boolean).map((line,i)=>{try{return JSON.parse(line)}catch{throw new Error(`Malformed JSONL row ${i+1}`)}});}
function jstTickIso(capturedAt,time){
  if(!time)return null;
  const d=new Date(capturedAt); if(!Number.isFinite(d.getTime()))return null;
  const jst=new Date(d.getTime()+9*3600_000);
  const date=`${jst.getUTCFullYear()}-${String(jst.getUTCMonth()+1).padStart(2,'0')}-${String(jst.getUTCDate()).padStart(2,'0')}`;
  return `${date}T${String(time).slice(0,8)}+09:00`;
}
function normalizeMarket(market={}){
  const out={...market};
  for(let level=1;level<=10;level++){
    if(out[`askPrice${level}`]==null&&out[`ask${level}`]!=null)out[`askPrice${level}`]=out[`ask${level}`];
    if(out[`bidPrice${level}`]==null&&out[`bid${level}`]!=null)out[`bidPrice${level}`]=out[`bid${level}`];
  }
  return out;
}
function normalizeInput(row,historyRows){
  const snap={...normalizeMarket(row.market),timestamp:row.capturedAt,capturedAt:row.capturedAt};
  const quoteSnapshots=historyRows.map(r=>({...normalizeMarket(r.market),timestamp:r.capturedAt,capturedAt:r.capturedAt}));
  const ticks=(row.ticks??[]).map(t=>({timestamp:jstTickIso(row.capturedAt,t.time),price:t.price,volume:t.volume,size:t.volume}));
  return {snapshot:snap,quoteSnapshots,ticks,asOf:row.capturedAt};
}
function buildIntelAt(raw,i){
  const inputs=[];
  for(let j=i-LOOKBACK+1;j<=i;j++){
    const hist=raw.slice(Math.max(0,j-LOOKBACK+1),j+1);
    inputs.push(normalizeInput(raw[j],hist));
  }
  return buildPhase58P2P3(inputs,{maxQuoteStalenessMs:5000,maxTickStalenessMs:15000,minClassifiedTickFraction:.5,minQuoteSnapshots:2});
}
function mid(row){const b=Number(row?.market?.bestBid),a=Number(row?.market?.bestAsk);return finite(a)&&finite(b)&&a>=b?(a+b)/2:null;}
function findExitIndex(raw,i,horizonSeconds){
  const start=Date.parse(raw[i]?.capturedAt??''); if(!Number.isFinite(start))return null;
  const target=start+horizonSeconds*1000;
  for(let j=i+1;j<raw.length;j++){
    const t=Date.parse(raw[j]?.capturedAt??''); if(Number.isFinite(t)&&t>=target)return j;
  }
  return null;
}
function executionDiagnostics(rows){
  if(!rows.length)return {rowCount:0};
  const moved=rows.filter(r=>Math.abs(r.rawMove)>1e-12),flatRows=rows.length-moved.length;
  const wins=moved.filter(r=>r.grossReturn>0).length,losses=moved.filter(r=>r.grossReturn<0).length;
  const avg=k=>rows.reduce((s,r)=>s+Number(r[k]??0),0)/rows.length;
  return {
    rowCount:rows.length,movedRows:moved.length,flatRows,flatRate:flatRows/rows.length,
    grossDirectionalHitRateOnMoved:moved.length?wins/moved.length:null,
    grossDirectionalLossRateOnMoved:moved.length?losses/moved.length:null,
    averageAbsoluteFutureMoveBps:rows.reduce((s,r)=>s+Math.abs(r.rawMove)*10000,0)/rows.length,
    averageGrossEdgeBps:avg('grossReturn')*10000,
    averageCostBps:avg('costBps'),averageNetEdgeBps:avg('netReturn')*10000,
  };
}
function nonOverlapping(rows){
  const out=[]; let nextAllowedTime=-Infinity;
  for(const row of rows){
    const t=Date.parse(row.capturedAt); if(!Number.isFinite(t)||t<nextAllowedTime)continue;
    out.push(row); nextAllowedTime=Date.parse(row.exitCapturedAt);
  }
  return out;
}

const [path='data/phase58/next-session-predeclared-retry.jsonl',expected=EXPECTED_SHA]=process.argv.slice(2);
const bytes=fs.readFileSync(path),actual=sha256(bytes);
if(actual.toLowerCase()!==expected.toLowerCase()){
  console.log(JSON.stringify({status:'BLOCKED_DATASET_HASH_MISMATCH',expectedSha256:expected,actualSha256:actual},null,2));process.exit(2);
}
const raw=parseJsonl(bytes);
if(raw.length<1200){console.log(JSON.stringify({status:'BLOCKED_PREDECLARED_MINIMUM_SAMPLES',rowCount:raw.length},null,2));process.exit(2);}

const rows=[]; let orderBookReady=0,orderBookBlocked=0;
for(let i=LOOKBACK-1;i<raw.length;i++){
  const exitIndex=findExitIndex(raw,i,PRIMARY_HORIZON_SECONDS); if(exitIndex===null)break;
  const intel=buildIntelAt(raw,i);
  if(intel.orderBook?.status!=='ORDER_BOOK_INTELLIGENCE_READY'){orderBookBlocked++;continue;}
  orderBookReady++;
  const b=intel.orderBook.features??{};
  const direction=sign(Number(b.weightedDepthImbalance)); if(!direction)continue;
  const m0=mid(raw[i]),m1=mid(raw[exitIndex]); if(!finite(m0)||!finite(m1)||m0<=0)continue;
  const cost=estimateScalpingCostBps({spreadBps:b.latestSpreadBps,slippageBps:.5,feesBps:0,marketImpactBps:.25}); if(!cost.ready)continue;
  const rawMove=m1/m0-1,grossReturn=direction*rawMove,netReturn=grossReturn-cost.totalRoundTripBps/10000;
  rows.push({index:i,exitIndex,capturedAt:raw[i].capturedAt,exitCapturedAt:raw[exitIndex].capturedAt,direction,rawMove,grossReturn,costBps:cost.totalRoundTripBps,netReturn});
}
const nonOverlap=nonOverlapping(rows);
const allExecution=executionDiagnostics(rows),nonOverlapExecution=executionDiagnostics(nonOverlap);
const overlappingResult=evaluatePinnedWalkForward({datasetBytes:bytes,datasetSha256:actual,rows});
const nonOverlappingResult=evaluatePinnedWalkForward({datasetBytes:bytes,datasetSha256:actual,rows:nonOverlap});
const claimEligible=nonOverlap.length>=MIN_NON_OVERLAP_FOR_CLAIM;
const successOnPrimary=claimEligible&&nonOverlapExecution.averageNetEdgeBps>0;
const result={
  phase:'58.p8.next-session-predeclared',status:successOnPrimary?'PREDECLARED_PRIMARY_SUCCESS':claimEligible?'PREDECLARED_PRIMARY_FAILED':'PREDECLARED_PRIMARY_MEASURED_CLAIM_BLOCKED_SAMPLE_COUNT',
  datasetSha256:actual,rowCount:raw.length,signal:'weightedDepthImbalance',directionRule:'sign(weightedDepthImbalance)',primaryHorizonSeconds:PRIMARY_HORIZON_SECONDS,
  thresholdSweep:false,postHocSymbolFilter:false,noParameterChangesAfterCapture:true,orderBookReady,orderBookBlocked,
  overlapping:{execution:allExecution,result:overlappingResult},nonOverlapping:{execution:nonOverlapExecution,result:nonOverlappingResult},
  minimumNonOverlappingRowsForClaim:MIN_NON_OVERLAP_FOR_CLAIM,claimEligible,successOnPrimary,
  safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false}
};
console.log(JSON.stringify(result,null,2));
process.exit(0);
