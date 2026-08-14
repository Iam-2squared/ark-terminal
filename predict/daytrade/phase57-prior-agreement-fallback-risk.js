import {P23_32_POLICY,fitHierLevel,scoreHierLevel} from './phase57-hierarchical-dynamic-risk.js';

export const P23_35_POLICY=Object.freeze({
  phase:'57.p23.35',
  priorSessionsOnly:true,
  exactP2330Preserved:true,
  fallbackOnlyWhenExactUnavailable:true,
  recentWindowRows:P23_32_POLICY.minHistory*2,
  minSharedFeatures:2,
  minFeaturePolarityAgreement:0.5,
  requireFullRecentScoreSignAgreement:true,
  thresholdSearchAllowed:false,
  selectionAllowed:false,
  exitPolicyChangeAllowed:false,
  entryRetuningAllowed:false,
  symbolFilteringAllowed:false,
  freshHoldoutConsumed:false,
  purpose:'TEST_PREREGISTERED_PRIOR_FULL_VS_RECENT_DIRECTION_MODEL_AGREEMENT_BEFORE_FALLBACK'
});

export const p2335Key=r=>`${r.symbol}|${r.timestamp}|${r.offsetBars}|${r.setup}|${r.direction}`;
const sign=x=>x>0?1:x<0?-1:0;

export function priorAgreementEvidence({fullModel,recentModel,fullScore,recentScore}={}){
  const fullFeatures=fullModel?.features??{},recentFeatures=recentModel?.features??{};
  const shared=Object.keys(fullFeatures).filter(k=>recentFeatures[k]);
  const polarityAgree=shared.filter(k=>fullFeatures[k].polarity===recentFeatures[k].polarity).length;
  const polarityAgreement=shared.length?polarityAgree/shared.length:0;
  const scoresFinite=Number.isFinite(fullScore)&&Number.isFinite(recentScore);
  const scoreSignAgreement=scoresFinite&&sign(fullScore)===sign(recentScore)&&sign(fullScore)!==0;
  const trusted=Boolean(fullModel?.ready&&recentModel?.ready&&scoresFinite&&shared.length>=P23_35_POLICY.minSharedFeatures&&polarityAgreement>=P23_35_POLICY.minFeaturePolarityAgreement&&scoreSignAgreement);
  return{trusted,sharedFeatureCount:shared.length,polarityAgreeCount:polarityAgree,polarityAgreement,scoreSignAgreement,fullScore,recentScore,fullHistoryCount:Number(fullModel?.n??0),recentHistoryCount:Number(recentModel?.n??0)};
}

export function walkForwardPriorAgreementFallback(rows=[],baselineRows=[]){
  const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  const exactKeys=new Set(baselineRows.map(p2335Key));
  const fallback=[];let candidateCount=0,rejectedCount=0;
  for(const q of xs){
    if(exactKeys.has(p2335Key(q)))continue;
    const prior=xs.filter(r=>r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
    const fullModel=fitHierLevel(prior),fullScore=scoreHierLevel(q,fullModel);
    if(!fullModel.ready||!Number.isFinite(fullScore))continue;
    candidateCount++;
    const recentRows=prior.slice(-P23_35_POLICY.recentWindowRows),recentModel=fitHierLevel(recentRows),recentScore=scoreHierLevel(q,recentModel);
    const evidence=priorAgreementEvidence({fullModel,recentModel,fullScore,recentScore});
    if(!evidence.trusted){rejectedCount++;continue;}
    fallback.push({...q,riskScore:fullScore,directionScore:fullScore,recentDirectionScore:recentScore,directionHistoryCount:fullModel.n,recentDirectionHistoryCount:recentModel.n,exactReady:false,directionReady:true,scoreSource:'PRIOR_AGREEMENT_DIRECTION_FALLBACK',trustedFallback:true,trustEvidence:evidence});
  }
  const combined=new Map(baselineRows.map(r=>[p2335Key(r),{...r,scoreSource:'EXACT_P23_30',exactReady:true,trustedFallback:false}]));
  for(const r of fallback)if(!combined.has(p2335Key(r)))combined.set(p2335Key(r),r);
  return{rows:[...combined.values()],fallback,candidateCount,trustedFallbackCount:fallback.length,rejectedFallbackCount:rejectedCount,exactCount:baselineRows.length};
}
