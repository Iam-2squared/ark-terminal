import fs from 'node:fs';
import crypto from 'node:crypto';
import {buildPhase58P2P3} from '../predict/scalping/phase58-orderbook-tickflow.js';
import {estimateScalpingCostBps,evaluatePinnedWalkForward} from '../predict/scalping/phase58-integration-benchmark.js';

const EXPECTED_DEFAULT='cdc01619363e8eb909b26d5441a75b3fd5aa8f9c6e8ea1f8855bf283db29d5da';
const LOOKBACK=5;
const HORIZON=5;
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
  // Phase58 foundation consumes askPriceN/bidPriceN aliases; captured RSS uses askN/bidN.
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

const [path='data/phase58/phase58-canonical-microstructure.jsonl',expected=EXPECTED_DEFAULT]=process.argv.slice(2);
const bytes=fs.readFileSync(path); const actual=sha256(bytes);
if(actual.toLowerCase()!==expected.toLowerCase()){
 console.log(JSON.stringify({status:'BLOCKED_DATASET_HASH_MISMATCH',expectedSha256:expected,actualSha256:actual},null,2)); process.exit(2);
}
const raw=parseJsonl(bytes);
if(raw.length<100){console.log(JSON.stringify({status:'BLOCKED_INSUFFICIENT_PINNED_ROWS',rowCount:raw.length},null,2));process.exit(2);}

const evalRows=[]; let ready=0,zeroPressure=0;
const qualityFailureCounts={}; const orderBookStatusCounts={}; const tickFlowStatusCounts={};
let classifiedFractionMin=null,classifiedFractionMax=null,classifiedFractionSum=0,classifiedFractionN=0;
for(let i=LOOKBACK-1;i+HORIZON<raw.length;i++){
  const inputs=[];
  for(let j=i-LOOKBACK+1;j<=i;j++){
    const hist=raw.slice(Math.max(0,j-LOOKBACK+1),j+1);
    inputs.push(normalizeInput(raw[j],hist));
  }
  const intel=buildPhase58P2P3(inputs,{maxQuoteStalenessMs:5000,maxTickStalenessMs:15000,minClassifiedTickFraction:.5,minQuoteSnapshots:2});
  const obStatus=intel.orderBook?.status??'NULL'; orderBookStatusCounts[obStatus]=(orderBookStatusCounts[obStatus]??0)+1;
  const tfStatus=intel.tickFlow?.status??'NULL'; tickFlowStatusCounts[tfStatus]=(tickFlowStatusCounts[tfStatus]??0)+1;
  const latestFrame=intel.frames?.at(-1);
  for(const [name,passed] of Object.entries(latestFrame?.quality?.checks??{}))if(!passed)qualityFailureCounts[name]=(qualityFailureCounts[name]??0)+1;
  const cf=Number(latestFrame?.features?.classifiedTickFraction);
  if(Number.isFinite(cf)){classifiedFractionMin=classifiedFractionMin===null?cf:Math.min(classifiedFractionMin,cf);classifiedFractionMax=classifiedFractionMax===null?cf:Math.max(classifiedFractionMax,cf);classifiedFractionSum+=cf;classifiedFractionN++;}
  if(obStatus!=='ORDER_BOOK_INTELLIGENCE_READY'||tfStatus!=='TICK_FLOW_INTELLIGENCE_READY')continue;
  ready++;
  const b=intel.orderBook.features??{},f=intel.tickFlow.features??{};
  const votes=[b.pressureConsensus,f.signedVolumeImbalance,f.flowMomentum,b.micropriceEdgeBps].filter(finite).map(Number);
  const pressure=votes.length?votes.reduce((s,x)=>s+sign(x),0)/votes.length:0;
  const direction=sign(pressure); if(direction===0){zeroPressure++;continue;}
  const m0=mid(raw[i]),m1=mid(raw[i+HORIZON]); if(!finite(m0)||!finite(m1)||m0<=0)continue;
  const gross=direction*(m1/m0-1);
  const cost=estimateScalpingCostBps({spreadBps:b.latestSpreadBps,slippageBps:.5,feesBps:0,marketImpactBps:.25});
  if(!cost.ready)continue;
  const netReturn=gross-cost.totalRoundTripBps/10000;
  evalRows.push({index:i,capturedAt:raw[i].capturedAt,direction,grossReturn:gross,costBps:cost.totalRoundTripBps,netReturn});
}
const result=evaluatePinnedWalkForward({datasetBytes:bytes,datasetSha256:actual,rows:evalRows});
const diagnostics={
  method:'PREDECLARED_MICROSTRUCTURE_ONLY_DIAGNOSTIC',lookbackSnapshots:LOOKBACK,horizonSnapshots:HORIZON,approxHorizonSeconds:10,
  thresholdSweep:false,postHocSymbolFilter:false,phase57DirectionIntegrated:false,readyObservations:ready,zeroPressureObservations:zeroPressure,evaluableRows:evalRows.length,
  orderBookStatusCounts,tickFlowStatusCounts,qualityFailureCounts,
  classifiedTickFraction:{min:classifiedFractionMin,max:classifiedFractionMax,mean:classifiedFractionN?classifiedFractionSum/classifiedFractionN:null,n:classifiedFractionN},
};
console.log(JSON.stringify({datasetSha256:actual,diagnostics,result},null,2));
process.exit(result.complete?0:2);
