import {P23_32_POLICY} from './phase57-hierarchical-dynamic-risk.js';

export const P23_34_POLICY=Object.freeze({
  phase:'57.p23.34',
  priorSessionsOnly:true,
  exactP2330Preserved:true,
  fallbackOnlyWhenExactUnavailable:true,
  trustGatePreregistered:true,
  minDirectionHistory:P23_32_POLICY.minHistory,
  minDirectionInvalidated:P23_32_POLICY.minInvalidated,
  minDirectionSurvived:P23_32_POLICY.minSurvived,
  requireFiniteDirectionScore:true,
  thresholdSearchAllowed:false,
  selectionAllowed:false,
  exitPolicyChangeAllowed:false,
  entryRetuningAllowed:false,
  symbolFilteringAllowed:false,
  freshHoldoutConsumed:false,
  purpose:'PRESERVE_P23_30_EXACT_AND_ALLOW_ONLY_PRIOR_SUPPORTED_DIRECTION_FALLBACK'
});

export const p2334Key=r=>`${r.symbol}|${r.timestamp}|${r.offsetBars}|${r.setup}|${r.direction}`;

export function fallbackTrustEvidence(row={}){
  const n=Number(row.directionHistoryCount??0);
  const bad=Number(row.directionInvalidatedCount??row.directionBadCount??0);
  const good=Number(row.directionSurvivedCount??row.directionGoodCount??0);
  const scoreFinite=Number.isFinite(row.directionScore??row.riskScore);
  const historyReady=n>=P23_34_POLICY.minDirectionHistory;
  const classBalanceReady=bad>=P23_34_POLICY.minDirectionInvalidated&&good>=P23_34_POLICY.minDirectionSurvived;
  const trusted=Boolean(!row.exactReady&&row.directionReady&&historyReady&&classBalanceReady&&scoreFinite);
  return{trusted,n,bad,good,scoreFinite,historyReady,classBalanceReady};
}

export function combineConditionalTrustedFallback(baselineRows=[],hierarchicalRows=[]){
  const rows=new Map(baselineRows.map(r=>[p2334Key(r),{...r,scoreSource:'EXACT_P23_30',exactReady:true,trustedFallback:false}]));
  let fallbackCandidateCount=0,trustedFallbackCount=0,rejectedFallbackCount=0;
  for(const r of hierarchicalRows){
    const key=p2334Key(r);
    if(rows.has(key)||r.exactReady||!r.directionReady)continue;
    fallbackCandidateCount++;
    const trust=fallbackTrustEvidence(r);
    if(!trust.trusted){rejectedFallbackCount++;continue;}
    const riskScore=Number.isFinite(r.directionScore)?r.directionScore:r.riskScore;
    rows.set(key,{...r,riskScore,scoreSource:'TRUSTED_DIRECTION_FALLBACK',trustedFallback:true,trustEvidence:trust});
    trustedFallbackCount++;
  }
  return{rows:[...rows.values()],exactCount:baselineRows.length,fallbackCandidateCount,trustedFallbackCount,rejectedFallbackCount};
}
