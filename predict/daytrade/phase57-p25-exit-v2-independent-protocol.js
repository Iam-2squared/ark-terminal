export const P25_EXIT_V2_INDEPENDENT_PROTOCOL=Object.freeze({
  phase:'57.p25.data-driven-exit.v2.independent-protocol',
  developmentCutoff:'2026-08-12',
  legacyDiagnosticWindow:Object.freeze(['2026-08-19','2026-08-20','2026-08-21','2026-08-24','2026-08-25']),
  firstEligibleFreshSession:'2026-08-26',
  freshSessionOpenUtc:'00:00:00.000Z',
  existing27AllowedForDiagnosticsOnly:true,
  existing27AllowedForThresholdTuning:false,
  existing27AllowedForFeatureTuning:false,
  existing27AllowedForHorizonTuning:false,
  existing27AllowedForCoefficientTuning:false,
  candidateMustFreezeBeforeFreshEvaluation:true,
  candidateMustFreezeBeforeFreshSessionOpen:true,
  incompleteFreshSessionAllowed:false,
  freshHoldoutConsumed:false,
  automaticPromotionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
});

const isoDate=x=>/^\d{4}-\d{2}-\d{2}$/.test(String(x??''));

export function validateP25ExitV2DevelopmentDates(sessionDates=[]){
  const dates=[...new Set((Array.isArray(sessionDates)?sessionDates:[]).map(String))].sort();
  if(!dates.length)return Object.freeze({ready:false,status:'BLOCKED_V2_EMPTY_DEVELOPMENT_SET'});
  if(dates.some(d=>!isoDate(d)))return Object.freeze({ready:false,status:'BLOCKED_V2_INVALID_DEVELOPMENT_DATE'});
  if(dates.some(d=>d>P25_EXIT_V2_INDEPENDENT_PROTOCOL.developmentCutoff))return Object.freeze({ready:false,status:'BLOCKED_V2_POST_CUTOFF_DEVELOPMENT_DATA'});
  return Object.freeze({ready:true,status:'V2_DEVELOPMENT_DATES_CAUSAL',sessionDates:Object.freeze(dates)});
}

export function validateP25ExitV2FreshCandidate({candidateFrozenAt,freshSessionDate,freshSessionComplete,freshSessionImmutable}={}){
  const frozen=String(candidateFrozenAt??''),fresh=String(freshSessionDate??'');
  const frozenMs=Date.parse(frozen);
  if(!frozen||Number.isNaN(frozenMs))return Object.freeze({ready:false,status:'BLOCKED_V2_CANDIDATE_NOT_FROZEN'});
  if(!isoDate(fresh)||fresh<P25_EXIT_V2_INDEPENDENT_PROTOCOL.firstEligibleFreshSession)return Object.freeze({ready:false,status:'BLOCKED_V2_NOT_FRESH_SESSION'});
  if(P25_EXIT_V2_INDEPENDENT_PROTOCOL.legacyDiagnosticWindow.includes(fresh))return Object.freeze({ready:false,status:'BLOCKED_V2_LEGACY_DIAGNOSTIC_WINDOW'});
  if(freshSessionComplete!==true)return Object.freeze({ready:false,status:'BLOCKED_V2_FRESH_SESSION_INCOMPLETE'});
  if(freshSessionImmutable!==true)return Object.freeze({ready:false,status:'BLOCKED_V2_FRESH_SESSION_NOT_IMMUTABLE'});
  const sessionOpenIso=`${fresh}T${P25_EXIT_V2_INDEPENDENT_PROTOCOL.freshSessionOpenUtc}`;
  const sessionOpenMs=Date.parse(sessionOpenIso);
  if(!(frozenMs<sessionOpenMs))return Object.freeze({ready:false,status:'BLOCKED_V2_CANDIDATE_NOT_FROZEN_BEFORE_SESSION_OPEN',freshSessionDate:fresh,sessionOpenAt:sessionOpenIso,candidateFrozenAt:frozen});
  return Object.freeze({ready:true,status:'V2_FRESH_EVALUATION_ELIGIBLE',freshSessionDate:fresh,sessionOpenAt:sessionOpenIso,candidateFrozenAt:frozen});
}

export default {P25_EXIT_V2_INDEPENDENT_PROTOCOL,validateP25ExitV2DevelopmentDates,validateP25ExitV2FreshCandidate};