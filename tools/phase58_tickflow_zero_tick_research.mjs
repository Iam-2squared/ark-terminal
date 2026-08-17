import fs from 'node:fs';
import crypto from 'node:crypto';
import {buildZeroTickFlow} from '../predict/scalping/phase58-zero-tick-classifier.js';

const finite=x=>Number.isFinite(Number(x));
const sign=x=>x>0?1:x<0?-1:0;
const sha256=b=>crypto.createHash('sha256').update(b).digest('hex');
const mid=r=>{const b=Number(r?.market?.bestBid),a=Number(r?.market?.bestAsk);return finite(a)&&finite(b)&&a>=b?(a+b)/2:null;};
const parse=b=>b.toString('utf8').split(/\r?\n/).filter(Boolean).map(JSON.parse);
function diag(rows){
 if(!rows.length)return {rowCount:0};
 const moved=rows.filter(r=>Math.abs(r.rawMove)>1e-12); const wins=moved.filter(r=>r.gross>0).length;
 const avg=x=>x.reduce((s,v)=>s+v,0)/x.length;
 return {rowCount:rows.length,movedRows:moved.length,flatRows:rows.length-moved.length,flatRate:(rows.length-moved.length)/rows.length,grossDirectionalHitRateOnMoved:moved.length?wins/moved.length:null,averageAbsoluteFutureMoveBps:avg(rows.map(r=>Math.abs(r.rawMove)*10000)),averageGrossEdgeBps:avg(rows.map(r=>r.gross*10000))};
}

const [path='data/phase58/next-session-predeclared-retry.jsonl',expected='']=process.argv.slice(2);
const bytes=fs.readFileSync(path),actual=sha256(bytes); if(expected&&actual.toLowerCase()!==expected.toLowerCase()){console.log(JSON.stringify({status:'BLOCKED_DATASET_HASH_MISMATCH',expected,actual},null,2));process.exit(2);}
const raw=parse(bytes); const horizons=[30,60,90,150]; // ~60/120/180/300s at ~2s cadence
const stats={}; let cfSum=0,cfN=0,cfMin=null,cfMax=null,continuation=0,ticks=0;
for(let i=0;i<raw.length;i++){
 const flow=buildZeroTickFlow(raw[i].ticks??[]).features; const cf=Number(flow.classifiedTickFraction);
 if(finite(cf)){cfSum+=cf;cfN++;cfMin=cfMin===null?cf:Math.min(cfMin,cf);cfMax=cfMax===null?cf:Math.max(cfMax,cf);} continuation+=Number(flow.continuationCount)||0;ticks+=Number(flow.tickCount)||0;
}
for(const h of horizons){
 const rows=[];
 for(let i=0;i+h<raw.length;i++){
   const m0=mid(raw[i]),m1=mid(raw[i+h]); if(!finite(m0)||!finite(m1)||m0<=0)continue;
   const flow=buildZeroTickFlow(raw[i].ticks??[]).features; const direction=sign(Number(flow.signedVolumeImbalance)); if(!direction)continue;
   const rawMove=m1/m0-1; rows.push({rawMove,gross:direction*rawMove});
 }
 stats[`${h*2}s`]=diag(rows);
}
console.log(JSON.stringify({phase:'58.tick-classifier.research',datasetSha256:actual,researchOnly:true,promotionEvidence:false,method:'CAUSAL_ZERO_TICK_CONTINUATION',thresholdSweep:false,classifiedTickFraction:{min:cfMin,max:cfMax,mean:cfN?cfSum/cfN:null,n:cfN},continuationShare:ticks?continuation/ticks:null,horizonDiagnostics:stats,safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false}},null,2));
