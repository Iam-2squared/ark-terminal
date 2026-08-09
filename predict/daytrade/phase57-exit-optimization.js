import { buildIntradayWalkForwardFolds } from './phase57-intraday-walkforward-cost.js';

export const PHASE57_P21_3_SAFETY=Object.freeze({
  mode:'PHASE57_EXIT_OPTIMIZATION_RESEARCH_ONLY',
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  overnightHoldingAllowed:false,
  humanApprovalRequired:true,
});

export const DEFAULT_EXIT_POLICIES=Object.freeze([
  Object.freeze({id:'FIXED_15M',type:'FIXED',maxBars:3}),
  Object.freeze({id:'FIXED_30M',type:'FIXED',maxBars:6}),
  Object.freeze({id:'FIXED_60M',type:'FIXED',maxBars:12}),
  Object.freeze({id:'FIXED_120M',type:'FIXED',maxBars:24}),
  Object.freeze({id:'BRACKET_0.5_0.5',type:'TP_SL',takeProfitPct:0.5,stopLossPct:0.5,maxBars:24}),
  Object.freeze({id:'BRACKET_1.0_0.5',type:'TP_SL',takeProfitPct:1.0,stopLossPct:0.5,maxBars:24}),
  Object.freeze({id:'BRACKET_1.0_1.0',type:'TP_SL',takeProfitPct:1.0,stopLossPct:1.0,maxBars:24}),
  Object.freeze({id:'TRAIL_0.5',type:'TRAILING',trailingPct:0.5,maxBars:24}),
  Object.freeze({id:'TRAIL_1.0',type:'TRAILING',trailingPct:1.0,maxBars:24}),
  Object.freeze({id:'ATR_1.0_1.0',type:'ATR_BRACKET',takeProfitAtr:1.0,stopLossAtr:1.0,maxBars:24}),
  Object.freeze({id:'ATR_1.5_1.0',type:'ATR_BRACKET',takeProfitAtr:1.5,stopLossAtr:1.0,maxBars:24}),
  Object.freeze({id:'MOMENTUM_DECAY_3',type:'MOMENTUM_DECAY',lookbackBars:3,maxBars:24}),
]);

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const rowTime=row=>Date.parse(row?.featureCutoff??row?.timestamp??0);

function normalizePath(row){
  const path=(row?.futureBars??row?.path??[]).map(bar=>({
    timestamp:new Date(bar.timestamp??bar.time??bar.datetime).toISOString(),
    open:Number(bar.open),high:Number(bar.high),low:Number(bar.low),close:Number(bar.close),volume:finite(bar.volume)?Number(bar.volume):0,
  })).filter(bar=>[bar.open,bar.high,bar.low,bar.close].every(Number.isFinite));
  return path.sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}

function pathReturnPct(entry,price,direction){
  if(!entry||!finite(price)) return null;
  const raw=(Number(price)/entry-1)*100;
  return direction===1?raw:-raw;
}

function thresholdPrice(entry,direction,pct,favorable){
  const move=Number(pct)/100;
  const sign=(direction===1?1:-1)*(favorable?1:-1);
  return entry*(1+sign*move);
}

function touched(bar,price,direction,favorable){
  if(direction===1) return favorable?bar.high>=price:bar.low<=price;
  return favorable?bar.low<=price:bar.high>=price;
}

function conservativeBracketHit(bar,{entry,direction,tpPct,slPct}){
  const tp=thresholdPrice(entry,direction,tpPct,true);
  const sl=thresholdPrice(entry,direction,slPct,false);
  const tpHit=touched(bar,tp,direction,true);
  const slHit=touched(bar,sl,direction,false);
  if(tpHit&&slHit) return {price:sl,reason:'AMBIGUOUS_BAR_STOP_FIRST'};
  if(slHit) return {price:sl,reason:'STOP_LOSS'};
  if(tpHit) return {price:tp,reason:'TAKE_PROFIT'};
  return null;
}

function simulateTrailing(path,{entry,direction,trailingPct,maxBars}){
  let best=entry;
  const limit=Math.min(path.length,maxBars);
  for(let i=0;i<limit;i++){
    const bar=path[i];
    if(direction===1){
      best=Math.max(best,bar.high);
      const stop=best*(1-Number(trailingPct)/100);
      if(bar.low<=stop) return {price:stop,barsHeld:i+1,reason:'TRAILING_STOP',outcomeAt:bar.timestamp};
    }else{
      best=Math.min(best,bar.low);
      const stop=best*(1+Number(trailingPct)/100);
      if(bar.high>=stop) return {price:stop,barsHeld:i+1,reason:'TRAILING_STOP',outcomeAt:bar.timestamp};
    }
  }
  const bar=path[Math.max(0,limit-1)];
  return bar?{price:bar.close,barsHeld:limit,reason:'TIME_LIMIT',outcomeAt:bar.timestamp}:null;
}

function simulateMomentumDecay(path,{entry,direction,lookbackBars,maxBars}){
  const limit=Math.min(path.length,maxBars);
  const closes=[entry];
  for(let i=0;i<limit;i++){
    const bar=path[i];
    closes.push(bar.close);
    if(closes.length>lookbackBars){
      const reference=closes[closes.length-1-lookbackBars];
      const momentum=(bar.close/reference-1)*(direction===1?1:-1);
      if(momentum<=0) return {price:bar.close,barsHeld:i+1,reason:'MOMENTUM_DECAY',outcomeAt:bar.timestamp};
    }
  }
  const bar=path[Math.max(0,limit-1)];
  return bar?{price:bar.close,barsHeld:limit,reason:'TIME_LIMIT',outcomeAt:bar.timestamp}:null;
}

export function simulateIntradayExit(row,policy,{roundTripCostPct=0.05}={}){
  const entry=Number(row?.entryPrice);
  const direction=Number(row?.signalDirection);
  const path=normalizePath(row);
  if(!finite(entry)||entry<=0||![0,1].includes(direction)||!path.length) return null;
  const maxBars=Math.max(1,Math.min(path.length,Number(policy?.maxBars)||path.length));
  let exit=null;

  if(policy?.type==='TP_SL'||policy?.type==='ATR_BRACKET'){
    const atrPct=Number(row?.atrPctAtEntry??row?.features?.atrPct);
    const tpPct=policy.type==='ATR_BRACKET'?atrPct*Number(policy.takeProfitAtr):Number(policy.takeProfitPct);
    const slPct=policy.type==='ATR_BRACKET'?atrPct*Number(policy.stopLossAtr):Number(policy.stopLossPct);
    if(!finite(tpPct)||!finite(slPct)||tpPct<=0||slPct<=0) return null;
    for(let i=0;i<maxBars;i++){
      const hit=conservativeBracketHit(path[i],{entry,direction,tpPct,slPct});
      if(hit){exit={...hit,barsHeld:i+1,outcomeAt:path[i].timestamp};break;}
    }
  }else if(policy?.type==='TRAILING'){
    if(!finite(policy.trailingPct)||Number(policy.trailingPct)<=0) return null;
    exit=simulateTrailing(path,{entry,direction,trailingPct:Number(policy.trailingPct),maxBars});
  }else if(policy?.type==='MOMENTUM_DECAY'){
    exit=simulateMomentumDecay(path,{entry,direction,lookbackBars:Math.max(1,Number(policy.lookbackBars)||3),maxBars});
  }else if(policy?.type!=='FIXED') return null;

  if(!exit){
    const bar=path[maxBars-1];
    exit={price:bar.close,barsHeld:maxBars,reason:'FIXED_OR_TIME_LIMIT',outcomeAt:bar.timestamp};
  }
  const grossReturnPct=pathReturnPct(entry,exit.price,direction);
  const netReturnPct=grossReturnPct-Number(roundTripCostPct||0);
  const considered=path.slice(0,exit.barsHeld);
  const favorable=direction===1?Math.max(...considered.map(bar=>bar.high)):Math.min(...considered.map(bar=>bar.low));
  const adverse=direction===1?Math.min(...considered.map(bar=>bar.low)):Math.max(...considered.map(bar=>bar.high));
  const mfePct=Math.max(0,pathReturnPct(entry,favorable,direction));
  const maePct=Math.min(0,pathReturnPct(entry,adverse,direction));
  const captureRatio=mfePct>0?clamp(grossReturnPct/mfePct,-5,5):null;
  return Object.freeze({
    policyId:policy.id,policyType:policy.type,direction,entryPrice:entry,exitPrice:exit.price,
    outcomeAt:exit.outcomeAt,barsHeld:exit.barsHeld,exitReason:exit.reason,
    grossReturnPct,netReturnPct,mfePct,maePct,captureRatio,
  });
}

export function evaluateExitPolicy(rows=[],policy,options={}){
  const outcomes=(Array.isArray(rows)?rows:[]).map(row=>simulateIntradayExit(row,policy,options)).filter(Boolean);
  const n=outcomes.length;
  const positive=outcomes.filter(x=>x.netReturnPct>0).reduce((s,x)=>s+x.netReturnPct,0);
  const negative=-outcomes.filter(x=>x.netReturnPct<0).reduce((s,x)=>s+x.netReturnPct,0);
  return Object.freeze({
    policyId:policy?.id??null,policyType:policy?.type??null,signalCount:n,
    hitRate:n?outcomes.filter(x=>x.netReturnPct>0).length/n:null,
    netAverageReturnPct:n?outcomes.reduce((s,x)=>s+x.netReturnPct,0)/n:null,
    medianNetReturnPct:n?[...outcomes].sort((a,b)=>a.netReturnPct-b.netReturnPct)[Math.floor(n/2)].netReturnPct:null,
    profitFactor:negative>0?positive/negative:(positive>0?Infinity:null),
    averageHoldingBars:n?outcomes.reduce((s,x)=>s+x.barsHeld,0)/n:null,
    averageMfePct:n?outcomes.reduce((s,x)=>s+x.mfePct,0)/n:null,
    averageMaePct:n?outcomes.reduce((s,x)=>s+x.maePct,0)/n:null,
    averageCaptureRatio:n?outcomes.filter(x=>finite(x.captureRatio)).reduce((s,x)=>s+x.captureRatio,0)/Math.max(1,outcomes.filter(x=>finite(x.captureRatio)).length):null,
    outcomes:Object.freeze(outcomes),
  });
}

function rankCandidate(a,b){
  const an=finite(a?.netAverageReturnPct)?Number(a.netAverageReturnPct):-Infinity;
  const bn=finite(b?.netAverageReturnPct)?Number(b.netAverageReturnPct):-Infinity;
  if(bn!==an) return bn-an;
  const ap=finite(a?.profitFactor)?Number(a.profitFactor):-Infinity;
  const bp=finite(b?.profitFactor)?Number(b.profitFactor):-Infinity;
  if(bp!==ap) return bp-ap;
  return Number(a?.averageHoldingBars??Infinity)-Number(b?.averageHoldingBars??Infinity);
}

export function selectInnerExitPolicy(rows=[],{
  policies=DEFAULT_EXIT_POLICIES,minSignals=30,minimumNetReturnPct=0,roundTripCostPct=0.05,
}={}){
  const candidates=policies.map(policy=>evaluateExitPolicy(rows,policy,{roundTripCostPct}));
  const eligible=candidates.filter(c=>c.signalCount>=minSignals&&finite(c.netAverageReturnPct)&&Number(c.netAverageReturnPct)>=minimumNetReturnPct);
  const ranked=(eligible.length?eligible:candidates.filter(c=>finite(c.netAverageReturnPct))).slice().sort(rankCandidate);
  const selectedSummary=eligible.length?(ranked[0]??null):null;
  const selected=selectedSummary?policies.find(p=>p.id===selectedSummary.policyId)??null:null;
  return Object.freeze({
    selected,selectedSummary,bestObserved:ranked[0]??null,eligibleCount:eligible.length,
    candidates:Object.freeze(candidates.map(c=>Object.freeze({...c,outcomes:undefined}))),
    selectionSource:'INNER_ONLY',outerDataUsedForSelection:false,
  });
}

function validResearchRow(row){
  if(!row?.symbol||!row?.sessionDate||!row?.featureCutoff||!finite(row?.entryPrice)||![0,1].includes(Number(row?.signalDirection))) return false;
  if(row?.signalPointInTimeValid===false) return false;
  if(row?.outcomeSessionDate&&row.outcomeSessionDate!==row.sessionDate) return false;
  return normalizePath(row).length>0;
}

export function evaluateNestedExitOptimization(rows=[],options={}){
  const valid=(Array.isArray(rows)?rows:[]).filter(validResearchRow).sort((a,b)=>rowTime(a)-rowTime(b));
  const outerFolds=buildIntradayWalkForwardFolds(valid,{
    trainFraction:options.outerTrainFraction??0.6,
    testFraction:options.outerTestFraction??0.1,
    minTrainRows:options.outerMinTrainRows??30,
  });
  const outerResults=[],allOutcomes=[];
  for(const fold of outerFolds){
    const innerFolds=buildIntradayWalkForwardFolds(fold.train,{
      trainFraction:options.innerTrainFraction??0.6,
      testFraction:options.innerTestFraction??0.2,
      minTrainRows:options.innerMinTrainRows??15,
    });
    const innerValidation=innerFolds.flatMap(inner=>inner.test).filter(row=>Date.parse(normalizePath(row).at(-1)?.timestamp??0)<=Date.parse(fold.trainCutoff));
    const selection=selectInnerExitPolicy(innerValidation,options);
    if(!selection.selected){
      outerResults.push(Object.freeze({fold:fold.fold,status:'ABSTAIN_NO_ELIGIBLE_INNER_EXIT',outerUntouchedBySelection:true}));
      continue;
    }
    const evaluated=evaluateExitPolicy(fold.test,selection.selected,{roundTripCostPct:options.roundTripCostPct??0.05});
    allOutcomes.push(...evaluated.outcomes);
    outerResults.push(Object.freeze({
      fold:fold.fold,status:'OUTER_EXIT_EVALUATED',selectedPolicyId:selection.selected.id,selectedPolicyType:selection.selected.type,
      innerEligibleCount:selection.eligibleCount,signalCount:evaluated.signalCount,hitRate:evaluated.hitRate,
      netAverageReturnPct:evaluated.netAverageReturnPct,profitFactor:evaluated.profitFactor,averageHoldingBars:evaluated.averageHoldingBars,
      trainCutoff:fold.trainCutoff,testStart:fold.testStart,testEnd:fold.testEnd,
      outerUntouchedBySelection:true,outerNeverUsedForPolicyFit:true,
    }));
  }
  const aggregate=evaluateExitPolicy(allOutcomes.map(outcome=>({
    symbol:'aggregate',sessionDate:'aggregate',featureCutoff:outcome.outcomeAt,entryPrice:outcome.entryPrice,
    signalDirection:outcome.direction,futureBars:[{timestamp:outcome.outcomeAt,open:outcome.exitPrice,high:outcome.exitPrice,low:outcome.exitPrice,close:outcome.exitPrice}],
  })),{id:'AGGREGATE',type:'FIXED',maxBars:1},{roundTripCostPct:0});
  const n=allOutcomes.length;
  const positive=allOutcomes.filter(x=>x.netReturnPct>0).reduce((s,x)=>s+x.netReturnPct,0);
  const negative=-allOutcomes.filter(x=>x.netReturnPct<0).reduce((s,x)=>s+x.netReturnPct,0);
  return Object.freeze({
    phase:'57.p21.3',status:n?'NESTED_EXIT_OOS_READY':'NO_OUTER_EXIT_OUTCOMES',outerFoldCount:outerFolds.length,
    signalCount:n,hitRate:n?allOutcomes.filter(x=>x.netReturnPct>0).length/n:null,
    netAverageReturnPct:n?allOutcomes.reduce((s,x)=>s+x.netReturnPct,0)/n:null,
    profitFactor:negative>0?positive/negative:(positive>0?Infinity:null),
    averageHoldingBars:n?allOutcomes.reduce((s,x)=>s+x.barsHeld,0)/n:null,
    averageMfePct:n?allOutcomes.reduce((s,x)=>s+x.mfePct,0)/n:null,
    averageMaePct:n?allOutcomes.reduce((s,x)=>s+x.maePct,0)/n:null,
    outerResults:Object.freeze(outerResults),
    selectionIntegrity:Object.freeze({exitPolicySelectedOnInnerOnly:true,outerTestNeverUsedForExitSelection:true,outerTestNeverUsedForPolicyFit:true,sameSessionOnly:true,overnightHoldingForbidden:true}),
    recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
    rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
    safety:PHASE57_P21_3_SAFETY,
  });
}

export default {simulateIntradayExit,evaluateExitPolicy,selectInnerExitPolicy,evaluateNestedExitOptimization};
