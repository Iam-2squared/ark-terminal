import fs from 'node:fs';
import crypto from 'node:crypto';
import {buildPhase58P2P3} from '../predict/scalping/phase58-orderbook-tickflow.js';
import {estimateScalpingCostBps,evaluatePinnedWalkForward} from '../predict/scalping/phase58-integration-benchmark.js';

const EXPECTED_DEFAULT='cdc01619363e8eb909b26d5441a75b3fd5aa8f9c6e8ea1f8855bf283db29d5da';
const LOOKBACK=5;
const HORIZON=5;
const HORIZON_GRID=[5,10,15,30,60]; // ~10/20/30/60/120 seconds at ~2s capture cadence.
const sign=x=>x>0?1:x<0?-1:0;
const finite=x=>Number.isFinite(Number(x));

function sha256(buf){return crypto.createHash('sha256').update(buf).digest('hex');}
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
function mid(row){const b=Number(row?.market?.bestBid),a=Number(row?.market?.bestAsk);return finite(a)&&finite(b)&&a>=b?(a+b)/2:null;}
function makeEvalRow(raw,i,direction,costBps,horizon=HORIZON){
  const m0=mid(raw[i]),m1=mid(raw[i+horizon]); if(!finite(m0)||!finite(m1)||m0<=0||!direction)return null;
  const rawMove=m1/m0-1; const gross=direction*rawMove; return {index:i,capturedAt:raw[i].capturedAt,direction,rawMove,grossReturn:gross,costBps,netReturn:gross-costBps/10000,horizonSnapshots:horizon};
}
function pushDirectional(rows,raw,i,value,costBps,multiplier=1,horizon=HORIZON){
  if(!finite(value))return;
  const direction=sign(Number(value))*multiplier; if(!direction)return;
  const row=makeEvalRow(raw,i,direction,costBps,horizon); if(row)rows.push(row);
}
function summarize(rows,bytes,actual){return evaluatePinnedWalkForward({datasetBytes:bytes,datasetSha256:actual,rows});}
function executionDiagnostics(rows){
  if(!rows.length)return {rowCount:0};
  const moved=rows.filter(r=>Math.abs(r.rawMove)>1e-12);
  const flats=rows.length-moved.length;
  const grossWins=moved.filter(r=>r.grossReturn>0).length;
  const grossLosses=moved.filter(r=>r.grossReturn<0).length;
  const grossSum=rows.reduce((s,r)=>s+r.grossReturn,0);
  const netSum=rows.reduce((s,r)=>s+r.netReturn,0);
  const avgCostBps=rows.reduce((s,r)=>s+r.costBps,0)/rows.length;
  const avgAbsMoveBps=rows.reduce((s,r)=>s+Math.abs(r.rawMove)*10000,0)/rows.length;
  const avgGrossEdgeBps=grossSum/rows.length*10000;
  const avgNetEdgeBps=netSum/rows.length*10000;
  return {rowCount:rows.length,movedRows:moved.length,flatRows:flats,flatRate:flats/rows.length,grossDirectionalHitRateOnMoved:moved.length?grossWins/moved.length:null,grossDirectionalLossRateOnMoved:moved.length?grossLosses/moved.length:null,averageAbsoluteFutureMoveBps:avgAbsMoveBps,averageGrossEdgeBps:avgGrossEdgeBps,averageCostBps:avgCostBps,averageNetEdgeBps:avgNetEdgeBps};
}
function nonOverlapping(rows,horizon=HORIZON){
  const out=[]; let nextAllowed=-Infinity;
  for(const row of rows){if(row.index<nextAllowed)continue;out.push(row);nextAllowed=row.index+horizon;}
  return out;
}
function buildIntelAt(raw,i){
  const inputs=[];
  for(let j=i-LOOKBACK+1;j<=i;j++){
    const hist=raw.slice(Math.max(0,j-LOOKBACK+1),j+1); inputs.push(normalizeInput(raw[j],hist));
  }
  return buildPhase58P2P3(inputs,{maxQuoteStalenessMs:5000,maxTickStalenessMs:15000,minClassifiedTickFraction:.5,minQuoteSnapshots:2});
}

const [path='data/phase58/phase58-canonical-microstructure.jsonl',expected=EXPECTED_DEFAULT]=process.argv.slice(2);
const bytes=fs.readFileSync(path); const actual=sha256(bytes);
if(actual.toLowerCase()!==expected.toLowerCase()){console.log(JSON.stringify({status:'BLOCKED_DATASET_HASH_MISMATCH',expectedSha256:expected,actualSha256:actual},null,2));process.exit(2);}
const raw=parseJsonl(bytes); if(raw.length<100){console.log(JSON.stringify({status:'BLOCKED_INSUFFICIENT_PINNED_ROWS',rowCount:raw.length},null,2));process.exit(2);}

const strictRows=[],bookOnlyRows=[]; let strictReady=0,bookReady=0,zeroPressure=0;
const qualityFailureCounts={},orderBookStatusCounts={},tickFlowStatusCounts={};
let classifiedFractionMin=null,classifiedFractionMax=null,classifiedFractionSum=0,classifiedFractionN=0;
const componentRows={pressureConsensus:[],pressureConsensusReversed:[],topBookImbalance:[],topBookImbalanceReversed:[],weightedDepthImbalance:[],weightedDepthImbalanceReversed:[],micropriceEdgeBps:[],micropriceEdgeBpsReversed:[]};
for(let i=LOOKBACK-1;i+HORIZON<raw.length;i++){
  const intel=buildIntelAt(raw,i);
  const obStatus=intel.orderBook?.status??'NULL'; orderBookStatusCounts[obStatus]=(orderBookStatusCounts[obStatus]??0)+1;
  const tfStatus=intel.tickFlow?.status??'NULL'; tickFlowStatusCounts[tfStatus]=(tickFlowStatusCounts[tfStatus]??0)+1;
  const latestFrame=intel.frames?.at(-1);
  for(const [name,passed] of Object.entries(latestFrame?.quality?.checks??{}))if(!passed)qualityFailureCounts[name]=(qualityFailureCounts[name]??0)+1;
  const cf=Number(latestFrame?.features?.classifiedTickFraction);
  if(Number.isFinite(cf)){classifiedFractionMin=classifiedFractionMin===null?cf:Math.min(classifiedFractionMin,cf);classifiedFractionMax=classifiedFractionMax===null?cf:Math.max(classifiedFractionMax,cf);classifiedFractionSum+=cf;classifiedFractionN++;}
  if(obStatus==='ORDER_BOOK_INTELLIGENCE_READY'){
    bookReady++;
    const b=intel.orderBook.features??{};
    const cost=estimateScalpingCostBps({spreadBps:b.latestSpreadBps,slippageBps:.5,feesBps:0,marketImpactBps:.25});
    if(cost.ready){
      const bookVotes=[b.pressureConsensus,b.micropriceEdgeBps].filter(finite).map(Number);
      const bookPressure=bookVotes.length?bookVotes.reduce((s,x)=>s+sign(x),0)/bookVotes.length:0;
      const bookDirection=sign(bookPressure);
      if(bookDirection){const row=makeEvalRow(raw,i,bookDirection,cost.totalRoundTripBps,HORIZON);if(row)bookOnlyRows.push(row);}
      pushDirectional(componentRows.pressureConsensus,raw,i,b.pressureConsensus,cost.totalRoundTripBps,1);
      pushDirectional(componentRows.pressureConsensusReversed,raw,i,b.pressureConsensus,cost.totalRoundTripBps,-1);
      pushDirectional(componentRows.topBookImbalance,raw,i,b.topBookImbalance,cost.totalRoundTripBps,1);
      pushDirectional(componentRows.topBookImbalanceReversed,raw,i,b.topBookImbalance,cost.totalRoundTripBps,-1);
      pushDirectional(componentRows.weightedDepthImbalance,raw,i,b.weightedDepthImbalance,cost.totalRoundTripBps,1);
      pushDirectional(componentRows.weightedDepthImbalanceReversed,raw,i,b.weightedDepthImbalance,cost.totalRoundTripBps,-1);
      pushDirectional(componentRows.micropriceEdgeBps,raw,i,b.micropriceEdgeBps,cost.totalRoundTripBps,1);
      pushDirectional(componentRows.micropriceEdgeBpsReversed,raw,i,b.micropriceEdgeBps,cost.totalRoundTripBps,-1);
    }
  }
  if(obStatus!=='ORDER_BOOK_INTELLIGENCE_READY'||tfStatus!=='TICK_FLOW_INTELLIGENCE_READY')continue;
  strictReady++;
  const b=intel.orderBook.features??{},f=intel.tickFlow.features??{};
  const votes=[b.pressureConsensus,f.signedVolumeImbalance,f.flowMomentum,b.micropriceEdgeBps].filter(finite).map(Number);
  const pressure=votes.length?votes.reduce((s,x)=>s+sign(x),0)/votes.length:0; const direction=sign(pressure); if(direction===0){zeroPressure++;continue;}
  const cost=estimateScalpingCostBps({spreadBps:b.latestSpreadBps,slippageBps:.5,feesBps:0,marketImpactBps:.25});
  if(cost.ready){const row=makeEvalRow(raw,i,direction,cost.totalRoundTripBps,HORIZON);if(row)strictRows.push(row);}
}
const strictResult=summarize(strictRows,bytes,actual);
const bookOnlyResult=summarize(bookOnlyRows,bytes,actual);
const bookNonOverlapRows=nonOverlapping(bookOnlyRows,HORIZON);
const bookNonOverlapResult=summarize(bookNonOverlapRows,bytes,actual);
const componentDiagnostics={};
for(const [name,rows] of Object.entries(componentRows))componentDiagnostics[name]={rowCount:rows.length,execution:executionDiagnostics(rows),result:summarize(rows,bytes,actual)};

// Exploratory persistence only. This grid was added after observing the 10-second result,
// so it is explicitly NOT promotion/OOS evidence. Any promising horizon must be frozen and
// validated on a future independent capture/session.
const horizonPersistence={};
for(const horizon of HORIZON_GRID){
  const rows=[];
  for(let i=LOOKBACK-1;i+horizon<raw.length;i++){
    const intel=buildIntelAt(raw,i);
    if(intel.orderBook?.status!=='ORDER_BOOK_INTELLIGENCE_READY')continue;
    const b=intel.orderBook.features??{};
    const cost=estimateScalpingCostBps({spreadBps:b.latestSpreadBps,slippageBps:.5,feesBps:0,marketImpactBps:.25});
    if(!cost.ready)continue;
    pushDirectional(rows,raw,i,b.weightedDepthImbalance,cost.totalRoundTripBps,1,horizon);
  }
  const nonOverlap=nonOverlapping(rows,horizon);
  horizonPersistence[`${horizon}snap`]={approxSeconds:horizon*2,exploratoryOnly:true,notPromotionEvidence:true,all:executionDiagnostics(rows),nonOverlapping:executionDiagnostics(nonOverlap),rowCount:rows.length,nonOverlappingRowCount:nonOverlap.length};
}

const diagnostics={method:'PREDECLARED_MICROSTRUCTURE_DIAGNOSTICS',lookbackSnapshots:LOOKBACK,horizonSnapshots:HORIZON,approxHorizonSeconds:10,thresholdSweep:false,postHocSymbolFilter:false,phase57DirectionIntegrated:false,strictTickClassificationThreshold:.5,componentSignTestsAreDebugDiagnostics:true,componentSignTestsNotPromotionEvidence:true,horizonPersistenceExploratoryOnly:true,horizonPersistenceNotPromotionEvidence:true,strictReadyObservations:strictReady,bookReadyObservations:bookReady,zeroPressureObservations:zeroPressure,strictEvaluableRows:strictRows.length,bookOnlyEvaluableRows:bookOnlyRows.length,bookOnlyExecution:executionDiagnostics(bookOnlyRows),bookOnlyNonOverlappingExecution:executionDiagnostics(bookNonOverlapRows),bookOnlyNonOverlappingRows:bookNonOverlapRows.length,orderBookStatusCounts,tickFlowStatusCounts,qualityFailureCounts,classifiedTickFraction:{min:classifiedFractionMin,max:classifiedFractionMax,mean:classifiedFractionN?classifiedFractionSum/classifiedFractionN:null,n:classifiedFractionN}};
console.log(JSON.stringify({datasetSha256:actual,diagnostics,strictTickAndBookResult:strictResult,bookOnlyDiagnosticResult:bookOnlyResult,bookOnlyNonOverlappingResult:bookNonOverlapResult,componentDiagnostics,horizonPersistence},null,2));
process.exit(bookOnlyResult.complete?0:2);
