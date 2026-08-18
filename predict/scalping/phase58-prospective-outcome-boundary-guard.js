export const PHASE58_P31_OUTCOME_POLICY=Object.freeze({
  maxOutcomeJoinLagMs:60_000,
  lateOutcomeJoinAllowed:false,
  historicalOutcomeReconstructionAllowed:false,
  promotionEvidence:false,
});

export const PHASE58_P31_SAFETY=Object.freeze({
  phase:'58.p31.prospective-outcome-boundary-guard',
  mode:'READ_ONLY_PROSPECTIVE_OUTCOME_BOUNDARY_INTEGRITY',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  overnightHoldingAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

const parseMs=value=>{
  const ms=Date.parse(value??'');
  return Number.isFinite(ms)?ms:null;
};

export function validateProspectiveOutcomeBoundaryJoins(report,{maxOutcomeJoinLagMs=PHASE58_P31_OUTCOME_POLICY.maxOutcomeJoinLagMs}={}){
  const blockers=[];
  const audits=[];
  if(!report||typeof report!=='object')blockers.push('MISSING_PROSPECTIVE_REPORT');
  if(!Number.isFinite(Number(maxOutcomeJoinLagMs))||Number(maxOutcomeJoinLagMs)<0)blockers.push('INVALID_MAX_OUTCOME_JOIN_LAG_MS');
  const events=Array.isArray(report?.eventAudit)?report.eventAudit:[];
  for(const event of events){
    if(event?.status!=='MATURED')continue;
    const targetMs=parseMs(event?.frozenOutcomeTargetAt);
    const exitMs=parseMs(event?.baselineExitAt);
    if(targetMs===null||exitMs===null){
      blockers.push(`MISSING_MATURED_OUTCOME_BOUNDARY:${event?.key??'UNKNOWN'}`);
      continue;
    }
    const lagMs=exitMs-targetMs;
    audits.push(Object.freeze({
      key:event?.key??null,
      frozenOutcomeTargetAt:event?.frozenOutcomeTargetAt??null,
      baselineExitAt:event?.baselineExitAt??null,
      outcomeJoinLagMs:lagMs,
      withinBudget:lagMs>=0&&lagMs<=Number(maxOutcomeJoinLagMs),
    }));
    if(lagMs<0)blockers.push(`OUTCOME_JOIN_BEFORE_FROZEN_BOUNDARY:${event?.key??'UNKNOWN'}`);
    else if(lagMs>Number(maxOutcomeJoinLagMs))blockers.push(`OUTCOME_JOIN_TOO_LATE:${event?.key??'UNKNOWN'}:${lagMs}`);
  }
  return Object.freeze({
    phase:'58.p31.prospective-outcome-boundary-guard',
    status:blockers.length?'BLOCKED_OUTCOME_CAPTURE_LAG':'PROSPECTIVE_OUTCOME_BOUNDARY_INTEGRITY_READY',
    complete:blockers.length===0,
    blockers:Object.freeze(blockers),
    maturedOutcomeAudit:Object.freeze(audits),
    policy:Object.freeze({...PHASE58_P31_OUTCOME_POLICY,maxOutcomeJoinLagMs:Number(maxOutcomeJoinLagMs)}),
    promotionEvidence:false,
    safety:PHASE58_P31_SAFETY,
  });
}

export default {validateProspectiveOutcomeBoundaryJoins,PHASE58_P31_OUTCOME_POLICY,PHASE58_P31_SAFETY};
