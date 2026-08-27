import {runP25ExitV2ProspectivePaired} from './phase57-p25-exit-v2-prospective.js';
import {P25_EXIT_V2_FROZEN_CANDIDATE} from './phase57-p25-exit-v2-freeze.js';

export const P25_EXIT_V2_HISTORICAL_REPLAY_SAFETY=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
  mode:'DIAGNOSTIC_REPLAY_ONLY_NOT_OOS_NOT_PROMOTION_ELIGIBLE',
});

export function classifyP25ExitV2ReplayDate(sessionDate){
  const d=String(sessionDate??'');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(d))throw new Error('P25 EXIT v2 replay requires YYYY-MM-DD session date');
  if(d<=P25_EXIT_V2_FROZEN_CANDIDATE.developmentCutoff)return Object.freeze({bucket:'DEVELOPMENT_REPLAY',formalOos:false,diagnosticOnly:true});
  if(d>='2026-08-19'&&d<='2026-08-25')return Object.freeze({bucket:'LEGACY27_DIAGNOSTIC_REPLAY',formalOos:false,diagnosticOnly:true});
  return Object.freeze({bucket:'OTHER_HISTORICAL_REPLAY',formalOos:false,diagnosticOnly:true});
}

// Historical replay deliberately reuses the exact frozen prospective engine but supplies an
// evaluation-only candidate timestamp immediately before the historical session open. This
// bypasses only the calendar eligibility gate; policy identity, exact D50 Entry, Fixed baseline,
// cutoff analog pool, and EXIT semantics remain unchanged. The output can never be OOS evidence.
export function runP25ExitV2HistoricalReplay({sessionDate,...inputs}={}){
  const classification=classifyP25ExitV2ReplayDate(sessionDate);
  const originalFrozenAt=P25_EXIT_V2_FROZEN_CANDIDATE.candidateFrozenAt;
  throw new Error(`P25 EXIT v2 historical replay calendar adapter required; refusing to mutate frozen candidate identity (${originalFrozenAt}). bucket=${classification.bucket}`);
}

export default {classifyP25ExitV2ReplayDate,runP25ExitV2HistoricalReplay,P25_EXIT_V2_HISTORICAL_REPLAY_SAFETY};
