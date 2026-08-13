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
const qkey=r=>`${r.setup}|${r.direction}`;
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
  let score=null,family='P2330';
  if(useCdf){const m=fitCdfContrastModel(hist);score=scoreCdfContrast(query,m);family='P2344';}
  if(!finite(score)){const m=fitDynamicModel(hist);score=scoreDynamic(query,m);family='P2330';}
  return{riskScore:finite(score)?Number(score):null,family,historyCount:hist.length,pooledEvidence,looEvidence};
}

export function buildPriorRiskThresholds(scoredHistoricalRows=[],quantile=P24_6_POLICY.riskTriggerQuantile){
  const groups=new Map();
  for(const r of scoredHistoricalRows){if(!finite(r.riskScore))continue;const k=qkey(r);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r);}
  return function thresholdFor(query){
    const xs=(groups.get(qkey(query))||[]).filter(r=>r.sessionDate<query.sessionDate&&String(r.timestamp)<String(query.timestamp)).map(r=>Number(r.riskScore)).filter(Number.isFinite).sort((a,b)=>a-b);
    if(xs.length<20)return{threshold:null,n:xs.length};
    const i=Math.max(0,Math.min(xs.length-1,Math.ceil(quantile*xs.length)-1));
    return{threshold:xs[i],n:xs.length};
  };
}

export function riskConditionedExitDecision({query,allHistoricalRows,thresholdFor}){
  const scored=scoreP2350PriorQuery(query,allHistoricalRows),t=thresholdFor(query);
  const triggered=finite(scored.riskScore)&&finite(t.threshold)&&scored.riskScore>=t.threshold;
  return Object.freeze({...scored,riskThreshold:t.threshold,thresholdHistoryCount:t.n,triggered});
}
