import { buildIntradayWalkForwardFolds } from './phase57-intraday-walkforward-cost.js';
import { DEFAULT_EXIT_POLICIES, selectInnerExitPolicy, evaluateExitPolicy, simulateIntradayExit } from './phase57-exit-optimization.js';

export const PHASE57_P21_3_REAL_EXIT_SAFETY=Object.freeze({
  mode:'PHASE57_REAL_EXIT_OOS_RESEARCH_ONLY',
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  overnightHoldingAllowed:false,humanApprovalRequired:true,
});

export const SAFE_REAL_EXIT_POLICIES=Object.freeze(DEFAULT_EXIT_POLICIES.filter(policy=>policy.type!=='TRAILING'));

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const pathEnd=row=>{
  const bars=Array.isArray(row?.futureBars)?row.futureBars:(Array.isArray(row?.path)?row.path:[]);
  const ts=bars.at(-1)?.timestamp??bars.at(-1)?.time??bars.at(-1)?.datetime;
  return ts?new Date(ts).toISOString():null;
};

function summarize(outcomes=[]){
  const n=outcomes.length;
  const positive=outcomes.filter(x=>x.netReturnPct>0).reduce((s,x)=>s+x.netReturnPct,0);
  const negative=-outcomes.filter(x=>x.netReturnPct<0).reduce((s,x)=>s+x.netReturnPct,0);
  return Object.freeze({
    signalCount:n,
    hitRate:n?outcomes.filter(x=>x.netReturnPct>0).length/n:null,
    netAverageReturnPct:n?outcomes.reduce((s,x)=>s+x.netReturnPct,0)/n:null,
    grossAverageReturnPct:n?outcomes.reduce((s,x)=>s+x.grossReturnPct,0)/n:null,
    profitFactor:negative>0?positive/negative:(positive>0?Infinity:null),
    averageHoldingBars:n?outcomes.reduce((s,x)=>s+x.barsHeld,0)/n:null,
    averageMfePct:n?outcomes.reduce((s,x)=>s+x.mfePct,0)/n:null,
    averageMaePct:n?outcomes.reduce((s,x)=>s+x.maePct,0)/n:null,
    averageCaptureRatio:n?outcomes.filter(x=>finite(x.captureRatio)).reduce((s,x)=>s+x.captureRatio,0)/Math.max(1,outcomes.filter(x=>finite(x.captureRatio)).length):null,
  });
}

function baselineOutcomes(rows,roundTripCostPct){
  return rows.flatMap(row=>{
    const maxBars=Math.max(1,Number(row?.baseHorizonBars)||1);
    const outcome=simulateIntradayExit(row,{id:`ADAPTIVE_BASELINE_${maxBars}`,type:'FIXED',maxBars},{roundTripCostPct});
    return outcome?[Object.freeze({...outcome,baseHorizonBars:maxBars})]:[];
  });
}

function validRow(row){
  if(!row?.symbol||!row?.sessionDate||!row?.featureCutoff||!row?.outcomeAt) return false;
  if(!finite(row?.label)||!finite(row?.entryPrice)||![0,1].includes(Number(row?.signalDirection))) return false;
  if(row?.signalPointInTimeValid===false||row?.pointInTimeValid===false) return false;
  if(row?.outcomeSessionDate&&row.outcomeSessionDate!==row.sessionDate) return false;
  const end=pathEnd(row);
  return Boolean(end)&&Date.parse(row.featureCutoff)<Date.parse(end);
}

export function evaluateNestedRealExitOos(rows=[],options={}){
  const valid=(Array.isArray(rows)?rows:[]).filter(validRow).sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
  const roundTripCostPct=Number(options.roundTripCostPct??0.05);
  const policies=options.policies??SAFE_REAL_EXIT_POLICIES;
  const outerFolds=buildIntradayWalkForwardFolds(valid,{
    trainFraction:options.outerTrainFraction??0.6,
    testFraction:options.outerTestFraction??0.1,
    minTrainRows:options.outerMinTrainRows??20,
  });

  const optimizedOutcomes=[];
  const baselineAllOutcomes=[];
  const baselineMatchedOutcomes=[];
  const outerResults=[];
  const selectedPolicyCounts={};

  for(const fold of outerFolds){
    const foldBaseline=baselineOutcomes(fold.test,roundTripCostPct);
    baselineAllOutcomes.push(...foldBaseline);
    const innerFolds=buildIntradayWalkForwardFolds(fold.train,{
      trainFraction:options.innerTrainFraction??0.6,
      testFraction:options.innerTestFraction??0.2,
      minTrainRows:options.innerMinTrainRows??8,
    });
    const innerValidation=innerFolds.flatMap(inner=>inner.test).filter(row=>{
      const end=pathEnd(row);
      return end&&Date.parse(end)<=Date.parse(fold.trainCutoff);
    });
    const selection=selectInnerExitPolicy(innerValidation,{
      policies,
      minSignals:options.minSignals??8,
      minimumNetReturnPct:options.minimumNetReturnPct??0,
      roundTripCostPct,
    });
    if(!selection.selected){
      outerResults.push(Object.freeze({
        fold:fold.fold,status:'ABSTAIN_NO_ELIGIBLE_INNER_EXIT',trainRows:fold.train.length,testRows:fold.test.length,
        innerValidationRows:innerValidation.length,innerEligibleCount:selection.eligibleCount,
        baselineSignalCount:foldBaseline.length,baselineNetAverageReturnPct:summarize(foldBaseline).netAverageReturnPct,
        trainCutoff:fold.trainCutoff,testStart:fold.testStart,testEnd:fold.testEnd,
        outerUntouchedBySelection:true,
      }));
      continue;
    }
    const optimized=evaluateExitPolicy(fold.test,selection.selected,{roundTripCostPct});
    optimizedOutcomes.push(...optimized.outcomes);
    baselineMatchedOutcomes.push(...foldBaseline);
    selectedPolicyCounts[selection.selected.id]=(selectedPolicyCounts[selection.selected.id]||0)+1;
    const baselineSummary=summarize(foldBaseline);
    outerResults.push(Object.freeze({
      fold:fold.fold,status:'OUTER_EXIT_EVALUATED',selectedPolicyId:selection.selected.id,selectedPolicyType:selection.selected.type,
      trainRows:fold.train.length,testRows:fold.test.length,innerValidationRows:innerValidation.length,innerEligibleCount:selection.eligibleCount,
      signalCount:optimized.signalCount,hitRate:optimized.hitRate,netAverageReturnPct:optimized.netAverageReturnPct,profitFactor:optimized.profitFactor,
      averageHoldingBars:optimized.averageHoldingBars,
      baselineSignalCount:baselineSummary.signalCount,baselineHitRate:baselineSummary.hitRate,baselineNetAverageReturnPct:baselineSummary.netAverageReturnPct,
      deltaVsAdaptiveBaselinePct:finite(optimized.netAverageReturnPct)&&finite(baselineSummary.netAverageReturnPct)?Number(optimized.netAverageReturnPct)-Number(baselineSummary.netAverageReturnPct):null,
      trainCutoff:fold.trainCutoff,testStart:fold.testStart,testEnd:fold.testEnd,
      outerUntouchedBySelection:true,outerNeverUsedForPolicyFit:true,
    }));
  }

  const optimized=summarize(optimizedOutcomes);
  const baselineAll=summarize(baselineAllOutcomes);
  const baselineMatched=summarize(baselineMatchedOutcomes);
  const deltaMatched=finite(optimized.netAverageReturnPct)&&finite(baselineMatched.netAverageReturnPct)?Number(optimized.netAverageReturnPct)-Number(baselineMatched.netAverageReturnPct):null;

  return Object.freeze({
    phase:'57.p21.3-real-exit-oos',status:optimized.signalCount?'NESTED_REAL_EXIT_OOS_READY':'NO_OUTER_EXIT_OUTCOMES',
    researchRowCount:valid.length,outerFoldCount:outerFolds.length,
    optimized,baselineAll,baselineMatched,deltaMatchedNetAverageReturnPct:deltaMatched,
    selectedPolicyCounts:Object.freeze({...selectedPolicyCounts}),outerResults:Object.freeze(outerResults),
    policyUniverse:Object.freeze(policies.map(policy=>policy.id)),
    trailingPolicyQuarantined:true,
    trailingQuarantineReason:'5m OHLC does not reveal intrabar high/low ordering; current trailing-stop simulator can otherwise use same-bar favorable extremes before adverse extremes. Trailing is excluded from real OOS until conservative prior-bar-stop semantics or higher-frequency ordering is implemented.',
    selectionIntegrity:Object.freeze({
      baseSignalsArePriorOuterOos:true,exitPolicySelectedOnInnerOnly:true,outerExitTestNeverUsedForSelection:true,
      outerExitTestNeverUsedForPolicyFit:true,baselineComparedOnMatchedOuterRows:true,sameSessionOnly:true,overnightHoldingForbidden:true,
    }),
    executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
    liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
    safety:PHASE57_P21_3_REAL_EXIT_SAFETY,
  });
}

export default {SAFE_REAL_EXIT_POLICIES,evaluateNestedRealExitOos};
