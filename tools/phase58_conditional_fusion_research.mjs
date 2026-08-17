import fs from 'node:fs';
import crypto from 'node:crypto';
import {buildZeroTickFlow} from '../predict/scalping/phase58-zero-tick-classifier.js';
import {estimateScalpingCostBps} from '../predict/scalping/phase58-integration-benchmark.js';

const HORIZONS=[30,60,90,150]; // ~60/120/180/300s at ~2s cadence
const finite=x=>Number.isFinite(Number(x));
const sign=x=>x>0?1:x<0?-1:0;
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const parse=b=>b.toString('utf8').split(/\r?\n/).filter(Boolean).map(JSON.parse);
function weightedDepth(m={}){
  let bid=0,ask=0;
  for(let i=1;i<=10;i++){
    const bs=Number(m[`bidSize${i}`]??0),as=Number(m[`askSize${i}`]??0);
    if(finite(bs)&&bs>=0)bid+=bs/i;
    if(finite(as)&&as>=0)ask+=as/i;
  }
  return bid+ask>0?(bid-ask)/(bid+ask):null;
}
function mid(r){const b=Number(r?.market?.bestBid),a=Number(r?.market?.bestAsk);return finite(a)&&finite(b)&&a>=b?(a+b)/2:null;}
function summarize(rows){
  const moved=rows.filter(r=>Math.abs(r.rawMove)>1e-12),wins=moved.filter(r=>r.gross>0);
  const avg=k=>rows.length?rows.reduce((s,r)=>s+r[k],0)/rows.length:null;
  return {rowCount:rows.length,movedRows:moved.length,flatRate:rows.length?(rows.length-moved.length)/rows.length:null,grossDirectionalHitRateOnMoved:moved.length?wins.length/moved.length:null,averageAbsoluteFutureMoveBps:rows.length?rows.reduce((s,r)=>s+Math.abs(r.rawMove)*10000,0)/rows.length:null,averageGrossEdgeBps:avg('gross')*10000,averageCostBps:avg('costBps'),averageNetEdgeBps:avg('net')*10000};
}
function nonOverlap(rows,h){const out=[];let next=-1;for(const r of rows){if(r.i<next)continue;out.push(r);next=r.i+h;}return out;}
function ruleDirection(rule,depth,flow){
  const d=sign(depth),f=sign(flow);
  if(rule==='UNANIMOUS')return d!==0&&d===f?d:0;
  if(rule==='DEPTH_WITH_NONOPPOSING_FLOW')return d!==0&&(f===0||f===d)?d:0;
  if(rule==='FLOW_WITH_NONOPPOSING_DEPTH')return f!==0&&(d===0||d===f)?f:0;
  return 0;
}

const [path,expected]=process.argv.slice(2);
if(!path||!expected)throw new Error('usage: node tools/phase58_conditional_fusion_research.mjs <jsonl> <sha256>');
const bytes=fs.readFileSync(path),actual=sha(bytes);
if(actual.toLowerCase()!==expected.toLowerCase()){console.log(JSON.stringify({status:'BLOCKED_DATASET_HASH_MISMATCH',actualSha256:actual,expectedSha256:expected},null,2));process.exit(2);}
const raw=parse(bytes);
const rules=['UNANIMOUS','DEPTH_WITH_NONOPPOSING_FLOW','FLOW_WITH_NONOPPOSING_DEPTH'];
const out={};
for(const h of HORIZONS){
  const byRule=Object.fromEntries(rules.map(r=>[r,[]]));
  for(let i=0;i+h<raw.length;i++){
    const r=raw[i],m=r.market??{};
    const depth=weightedDepth(m);
    const flow=buildZeroTickFlow(r.ticks??[]).features.signedVolumeImbalance;
    const spreadBps=finite(m.bestAsk)&&finite(m.bestBid)&&Number(m.bestAsk)>=Number(m.bestBid)?(Number(m.bestAsk)-Number(m.bestBid))/((Number(m.bestAsk)+Number(m.bestBid))/2)*10000:null;
    const cost=estimateScalpingCostBps({spreadBps,slippageBps:.5,feesBps:0,marketImpactBps:.25});
    const m0=mid(raw[i]),m1=mid(raw[i+h]); if(!cost.ready||!finite(m0)||!finite(m1)||m0<=0)continue;
    for(const rule of rules){
      const dir=ruleDirection(rule,depth,flow); if(!dir)continue;
      const rawMove=m1/m0-1,gross=dir*rawMove,net=gross-cost.totalRoundTripBps/10000;
      byRule[rule].push({i,rawMove,gross,net,costBps:cost.totalRoundTripBps});
    }
  }
  out[`${h*2}s`]={};
  for(const rule of rules){const rows=byRule[rule],non=nonOverlap(rows,h);out[`${h*2}s`][rule]={coverage:raw.length?rows.length/raw.length:null,all:summarize(rows),nonOverlapping:summarize(non),nonOverlappingRows:non.length};}
}
console.log(JSON.stringify({phase:'58.conditional-fusion.research',datasetSha256:actual,researchOnly:true,promotionEvidence:false,postHocOptimizationAllowed:false,thresholdSweep:false,notes:['Same-session exploratory diagnostic only','No result from this run may be treated as OOS promotion evidence','Any candidate must be frozen before a future independent session'],rules,horizonDiagnostics:out,safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false}},null,2));
