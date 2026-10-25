import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const A=read(process.env.BLOCK_A_TRADES??'artifacts/block-a/trades.json');
const B=read(process.env.BLOCK_B_TRADES??'artifacts/block-b/trades.json');
const out=process.env.OUTPUT_DIR??'artifacts/phase57-exit-v5-development-final';
fs.mkdirSync(out,{recursive:true});

const horizons=[2,3,4,5,6,8,10,12];
const costPct=0.05;
const decisions=t=>t.management?.v4??t.v4?.managementDecisions??[];
const elapsed=d=>d?.baseScore?.state?.elapsedBars??d?.holdingBars??null;
const cur=d=>Number(d?.currentReturnPct);
const firstBar=t=>{
  if(Number.isFinite(Number(t.firstBarDirectionalCloseReturnBps)))return Number(t.firstBarDirectionalCloseReturnBps)/100;
  if(Number.isFinite(Number(t.entryQuality?.h1?.gross)))return Number(t.entryQuality.h1.gross)/100;
  const d=decisions(t).find(x=>elapsed(x)===1);return d&&Number.isFinite(cur(d))?cur(d):null;
};
const eligible=t=>Boolean(t.causalEligible??t.causal?.eligible)&&t.v4;
const sim=(t,h)=>{
  if(!eligible(t))return null;
  const fb=firstBar(t);if(!Number.isFinite(fb))return null;
  if(fb>=0)return {net:t.v4.netReturnPct,reason:'FIRST_BAR_NON_ADVERSE_V4'};
  const ds=decisions(t).filter(d=>Number.isFinite(elapsed(d))&&elapsed(d)<=h).sort((a,b)=>elapsed(a)-elapsed(b));
  const reclaim=ds.find(d=>Number.isFinite(cur(d))&&cur(d)>=0);
  if(reclaim)return {net:t.v4.netReturnPct,reason:'RECOVERED_TO_V4'};
  const at=ds.find(d=>elapsed(d)===h);
  if(at)return {net:cur(at)-costPct,reason:`DEFENSIVE_EXIT_BAR_${h}`};
  return {net:t.v4.netReturnPct,reason:'HORIZON_FALLBACK_V4'};
};
const dd=xs=>{let eq=0,peak=0,worst=0;for(const x of xs){eq+=x;peak=Math.max(peak,eq);worst=Math.min(worst,eq-peak);}return worst;};
const block=(rows,h)=>{
  const rs=rows.filter(eligible).map(t=>({t,s:sim(t,h)})).filter(x=>x.s);
  const deltas=rs.map(({t,s})=>s.net-t.v4.netReturnPct),nets=rs.map(x=>x.s.net),v4=rs.map(x=>x.t.v4.netReturnPct);
  const abs=deltas.map(Math.abs),sumAbs=abs.reduce((a,b)=>a+b,0),top1=sumAbs?Math.max(0,...abs)/sumAbs:0;
  const wins=nets.filter(x=>x>0).reduce((a,b)=>a+b,0),loss=Math.abs(nets.filter(x=>x<0).reduce((a,b)=>a+b,0));
  const v4wins=v4.filter(x=>x>0).reduce((a,b)=>a+b,0),v4loss=Math.abs(v4.filter(x=>x<0).reduce((a,b)=>a+b,0));
  return {n:rs.length,net:nets.reduce((a,b)=>a+b,0),v4Net:v4.reduce((a,b)=>a+b,0),delta:deltas.reduce((a,b)=>a+b,0),profitFactor:loss?wins/loss:null,v4ProfitFactor:v4loss?v4wins/v4loss:null,maxDrawdown:dd(nets),v4MaxDrawdown:dd(v4),top1AbsDeltaShare:top1,stateCounts:Object.fromEntries([...new Set(rs.map(x=>x.s.reason))].map(k=>[k,rs.filter(x=>x.s.reason===k).length]))};
};
const candidates=horizons.map(h=>{const a=block(A,h),b=block(B,h);const combinedDelta=a.delta+b.delta;const worstBlockDelta=Math.min(a.delta,b.delta);const ddWorsening=Math.min(0,a.maxDrawdown-a.v4MaxDrawdown)+Math.min(0,b.maxDrawdown-b.v4MaxDrawdown);const concentration=Math.max(a.top1AbsDeltaShare,b.top1AbsDeltaShare);return {id:`DYNAMIC_RECLAIM_BAR_${h}`,horizon:h,blockA:a,blockB:b,combinedDelta,worstBlockDelta,ddWorsening,concentration,robustPass:a.delta>=0&&b.delta>=0&&a.maxDrawdown>=a.v4MaxDrawdown-1&&b.maxDrawdown>=b.v4MaxDrawdown-1};});
const robust=candidates.filter(x=>x.robustPass).sort((x,y)=>y.worstBlockDelta-x.worstBlockDelta||y.combinedDelta-x.combinedDelta||x.concentration-y.concentration||x.horizon-y.horizon);
const selected=robust[0]??[...candidates].sort((x,y)=>y.worstBlockDelta-x.worstBlockDelta||y.combinedDelta-x.combinedDelta)[0];
assert(selected,'NO_CANDIDATE');
const report={schemaVersion:1,schemaId:'PHASE57_EXIT_V5_DEVELOPMENT_FINAL_SWEEP_V1',role:'EXPOSED_DEVELOPMENT_ONLY_NOT_VALIDATION',inputs:{blockA:{rows:A.length,role:'EXPOSED'},blockB:{rows:B.length,role:'EXPOSED'}},fixedArchitecture:{firstBarNonAdverse:'CONTINUE_FROZEN_V4',firstBarAdverse:'DEFENSIVE',recovery:'DIRECTIONAL_CLOSE_RECLAIM_TO_ENTRY_PRICE',recovered:'CONTINUE_FROZEN_V4',unrecovered:'EXIT_AT_FIXED_HORIZON_CLOSE',costPct},candidateFamily:horizons,candidates,selectionRule:'Prefer candidates non-negative versus v4 in BOTH exposed blocks and <=1pt DD worsening in each; maximize worst-block delta, then combined delta, then lower concentration, then shorter horizon.',selected,guards:{symbolRules:false,directionSpecificRules:false,extraFeatures:false,outcomeDrivenExceptions:false,formalValidation:false,unseenClaim:false},safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false}};
fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');
console.log('PHASE57_EXIT_V5_DEVELOPMENT_FINAL='+JSON.stringify({selected:selected.id,horizon:selected.horizon,blockADelta:selected.blockA.delta,blockBDelta:selected.blockB.delta,combinedDelta:selected.combinedDelta,worstBlockDelta:selected.worstBlockDelta,robustPass:selected.robustPass}));
