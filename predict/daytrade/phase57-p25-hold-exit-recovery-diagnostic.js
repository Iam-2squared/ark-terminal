import {simulateTradeManagementStateMachine} from './phase57-trade-management-state-machine.js';
import {evaluateP25DynamicManagementParallel} from './phase57-p25-dynamic-management-parallel.js';

export const P25_HOLD_EXIT_RECOVERY_SAFETY=Object.freeze({
  phase:'57.p25.recovery.r1-r2',
  mode:'HOLD_EXIT_RECOVERY_DIAGNOSTIC_RESEARCH_ONLY',
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const keyOf=row=>`${String(row?.sessionDate??'')}|${String(row?.entryTimestamp??'')}|${String(row?.symbol??'').toUpperCase()}`;
const mean=xs=>xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const s=[...xs].sort((a,b)=>a-b),m=Math.floor(s.length/2);return s.length%2?s[m]:(s[m-1]+s[m])/2;};
function pf(xs){const gp=xs.filter(x=>x>0).reduce((a,b)=>a+b,0),gl=-xs.filter(x=>x<0).reduce((a,b)=>a+b,0);return gl>0?gp/gl:(gp>0?Infinity:null);}
function maxDd(xs){let eq=1,peak=1,max=0;for(const r of xs){eq*=1+r/100;peak=Math.max(peak,eq);if(peak>0)max=Math.max(max,(peak-eq)/peak*100);}return max;}
function summary(rows,key){const rs=rows.map(x=>Number(x?.[key]?.netReturnPct)).filter(Number.isFinite);let eq=1;for(const r of rs)eq*=1+r/100;return Object.freeze({n:rs.length,netReturnPct:(eq-1)*100,meanNetReturnPct:mean(rs),medianNetReturnPct:median(rs),winRate:rs.length?rs.filter(x=>x>0).length/rs.length:null,profitFactor:pf(rs),maxDrawdownPct:maxDd(rs)});}

function legacySelectiveFallback(row,fixed){
  const horizon=Math.max(1,Math.floor(Number(row?.baseHorizonBars||fixed?.barsHeld||1)));
  const legacy=simulateTradeManagementStateMachine(row,{roundTripCostPct:0.05,maxHoldBars:horizon});
  if(legacy?.exitReason==='STATE_AWARE_PROFIT_PROTECTION'){
    return Object.freeze({
      source:'LEGACY_STATE_AWARE_PROFIT_PROTECTION',
      exitTimestamp:legacy.outcomeAt,
      exitReason:legacy.exitReason,
      netReturnPct:Number(legacy.netReturnPct),
      barsHeld:Number(legacy.barsHeld),
      mfePct:Number(legacy.mfePct),
      maePct:Number(legacy.maePct),
      givebackPct:Number(legacy.mfePct)-Number(legacy.grossReturnPct),
      captureRatio:legacy.captureRatio==null?null:Number(legacy.captureRatio),
    });
  }
  return Object.freeze({
    source:'FROZEN_HORIZON_FALLBACK',
    exitTimestamp:fixed.exitTimestamp,
    exitReason:fixed.exitReason,
    netReturnPct:Number(fixed.netReturnPct),
    barsHeld:Number(fixed.barsHeld),
    mfePct:null,maePct:null,givebackPct:null,captureRatio:null,
  });
}

export function evaluateP25HoldExitRecoveryDiagnostic({frozenEntryRows=[],fixedResolvedTrades=[]}={}){
  const rows=Array.isArray(frozenEntryRows)?frozenEntryRows:[];
  const fixedByKey=new Map((Array.isArray(fixedResolvedTrades)?fixedResolvedTrades:[]).map(x=>[keyOf(x),x]));
  const current=evaluateP25DynamicManagementParallel({frozenEntryRows:rows,fixedResolvedTrades});
  const currentByKey=new Map(current.pairs.map(x=>[x.key,x]));
  const tri=[];
  for(const row of rows){
    const key=keyOf(row),fixed=fixedByKey.get(key),cur=currentByKey.get(key);if(!fixed||!cur)continue;
    const legacy=legacySelectiveFallback(row,fixed);
    const fixedNet=Number(fixed.netReturnPct),legacyNet=Number(legacy.netReturnPct),currentNet=Number(cur.dynamic.netReturnPct);
    tri.push(Object.freeze({
      key,symbol:row.symbol,sessionDate:row.sessionDate,entryTimestamp:row.entryTimestamp,
      fixed:Object.freeze({exitTimestamp:fixed.exitTimestamp,exitReason:fixed.exitReason,netReturnPct:fixedNet,barsHeld:Number(fixed.barsHeld)}),
      legacySelective:legacy,
      currentFull:cur.dynamic,
      deltaLegacyVsFixed:legacyNet-fixedNet,
      deltaCurrentVsFixed:currentNet-fixedNet,
      classification:currentNet<fixedNet&&legacyNet>=fixedNet?'CURRENT_FULL_HARM_LEGACY_PRESERVED':currentNet>fixedNet&&legacyNet<=fixedNet?'CURRENT_FULL_HELPED':'MIXED_OR_EQUAL',
    }));
  }
  const byCurrentExitReason={};
  for(const pair of tri){const k=String(pair.currentFull.exitReason??'UNKNOWN');(byCurrentExitReason[k]??=[]).push(pair);}
  const attribution=Object.freeze(Object.fromEntries(Object.entries(byCurrentExitReason).map(([k,v])=>[k,Object.freeze({n:v.length,meanDeltaVsFixed:mean(v.map(x=>x.deltaCurrentVsFixed)),meanBarsDelta:mean(v.map(x=>Number(x.currentFull.barsHeld)-Number(x.fixed.barsHeld))),meanGivebackPct:mean(v.map(x=>Number(x.currentFull.givebackPct)).filter(Number.isFinite)),meanCaptureRatio:mean(v.map(x=>Number(x.currentFull.captureRatio)).filter(Number.isFinite))})])));
  return Object.freeze({
    phase:'57.p25.recovery.r1-r2',status:'HOLD_EXIT_RECOVERY_DIAGNOSTIC_READY',pairedCount:tri.length,
    summary:Object.freeze({fixed:summary(tri,'fixed'),legacySelective:summary(tri,'legacySelective'),currentFull:summary(tri,'currentFull')}),
    pairs:Object.freeze(tri),attribution,
    limitations:Object.freeze([
      'P23.50 Dynamic Risk exact replay is not claimed here because the persisted P25 session evidence does not prove the multi-session historical context required by the old P24.7 risk gate for every current symbol.',
      'legacySelective therefore reproduces only the old P24.7 non-risk fallback semantics exactly: state-aware profit protection is allowed; unconfirmed hard-stop/chart-breakdown exits fall back to the frozen horizon.',
      'This diagnostic must not be used for parameter retuning or winner selection on the same five-session evidence.',
    ]),
    methodology:Object.freeze({sameFrozenEntries:true,fixedBaselineUntouched:true,currentFullUnchanged:true,legacyHardStopsSuppressed:true,legacyBreakdownExitsSuppressed:true,legacyProfitProtectionPreserved:true,p2350DynamicRiskExactReplay:false,resultBasedRetuning:false,winnerSelection:false,freshHoldoutConsumed:false}),
    safety:P25_HOLD_EXIT_RECOVERY_SAFETY,
  });
}

export default {evaluateP25HoldExitRecoveryDiagnostic,P25_HOLD_EXIT_RECOVERY_SAFETY};
