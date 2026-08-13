import {fitDynamicModel,scoreDynamic,walkForwardDynamic,orderingAuc} from './phase57-dynamic-walkforward-risk.js';
import {fitCdfContrastModel,scoreCdfContrast,walkForwardCdfContrastExact} from './phase57-prior-cdf-contrast-risk.js';

export const P24_6_POLICY=Object.freeze({
  phase:'57.p24.6',
  riskFamily:'P23.50_CONSERVATIVE_PRIOR_CONSENSUS_P2330_VS_P2344',
  priorSessionsOnly:true,
  riskTriggerQuantile:0.75,
  triggerMeaning:'Q4_HIGH_RISK_WITHIN_MATCHING_PRIOR_SETUP_DIRECTION',
  preserveProfitProtection:true,
  ignoreUnconfirmedLegacyBreakdownExit:true,
  preserveFrozenEntryHorizon:true,
  thresholdSearchAllowed:false,
  parameterSweepAllowed:false,
  postHocSymbolFilteringAllowed:false,
  entryRetuningAllowed:false,
  freshHoldoutConsumed:false,
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
});

const finite=x=>Number.isFinite(Number(x));
const quantile=(xs,q)=>{const z=xs.filter(Number.isFinite).sort((a,b)=>a-b);if(z.length<20)return{value:null,n:z.length};const i=Math.max(0,Math.min(z.length-1,Math.ceil(q*z.length)-1));return{value:z[i],n:z.length};};
function evidence(hist=[]){
  const b=walkForwardDynamic(hist);
  if(b.length<8)return{family:'P2330',baselineAuc:null,cdfAuc:null,evidenceCount:b.length};
  const c=walkForwardCdfContrastExact(hist,b).rows,ba=orderingAuc(b),ca=orderingAuc(c);
  if(!finite(ba)||!finite(ca))return{family:'P2330',baselineAuc:ba,cdfAuc:ca,evidenceCount:b.length};
  return{family:ca>ba?'P2344':'P2330',baselineAuc:ba,cdfAuc:ca,evidenceCount:b.length};
}

export function scoreP2350PriorQuery(query,allHistoricalRows=[]){
  const hist=(Array.isArray(allHistoricalRows)?allHistoricalRows:[]).filter(r=>
    r.setup===query.setup&&r.direction===query.direction&&r.sessionDate<query.sessionDate&&String(r.fullyRealizedAt)<String(query.timestamp)
  );
  const loo=hist.filter(r=>r.symbol!==query.symbol),pooledEvidence=evidence(hist),looEvidence=evidence(loo);
  const useCdf=pooledEvidence.family==='P2344'&&looEvidence.family==='P2344';
  let score=null,family='P2330',model=null,scoreFn=null;
  if(useCdf){model=fitCdfContrastModel(hist);score=scoreCdfContrast(query,model);scoreFn=scoreCdfContrast;family='P2344';}
  if(!finite(score)){model=fitDynamicModel(hist);score=scoreDynamic(query,model);scoreFn=scoreDynamic;family='P2330';}
  const priorScores=model?.ready&&scoreFn?hist.map(r=>scoreFn(r,model)).map(Number).filter(Number.isFinite):[];
  const threshold=quantile(priorScores,P24_6_POLICY.riskTriggerQuantile);
  return{riskScore:finite(score)?Number(score):null,family,historyCount:hist.length,pooledEvidence,looEvidence,riskThreshold:threshold.value,thresholdHistoryCount:threshold.n};
}

export function riskConditionedExitDecision({query,allHistoricalRows}){
  const scored=scoreP2350PriorQuery(query,allHistoricalRows);
  const triggered=finite(scored.riskScore)&&finite(scored.riskThreshold)&&scored.riskScore>=scored.riskThreshold;
  return Object.freeze({...scored,triggered});
}
