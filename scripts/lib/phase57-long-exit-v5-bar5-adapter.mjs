// Mechanical historical-result adapter, NOT a new standalone online EXIT.
// Parity target: final sweep sim(t,5) at aaa99030295ffb447de273881b16aad1eab1a7e9.
export const V5_BAR5 = Object.freeze({candidateId:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5',horizon:5,costPct:0.05});
const blocked=reason=>({status:'V5_RUNTIME_SEMANTICS_BLOCKED',reason,netReturnPct:null,exitTimestamp:null});
export function replayFrozenV5Bar5(t){
  if(t.direction!=='LONG')throw Error('LONG_ONLY');
  if(!Boolean(t.causalEligible??t.causal?.eligible)||!t.v4)return blocked('CAUSAL_V4_CONTINUATION_UNAVAILABLE');
  if(!Number.isFinite(t.v4.netReturnPct))return blocked('INVALID_V4_RESULT');
  const ds=t.management?.v4??t.v4.managementDecisions??[];
  const elapsed=d=>d?.baseScore?.state?.elapsedBars??d?.holdingBars??null;
  // Strict numeric inputs only: do not let Number(null) fabricate a flat first bar.
  let fb;
  if(Number.isFinite(t.firstBarDirectionalCloseReturnBps))fb=t.firstBarDirectionalCloseReturnBps/100;
  else if(Number.isFinite(t.entryQuality?.h1?.gross))fb=t.entryQuality.h1.gross/100;
  else fb=ds.find(d=>elapsed(d)===1)?.currentReturnPct;
  if(!Number.isFinite(fb))return blocked('FIRST_COMPLETED_BAR_UNAVAILABLE');
  const same=(reason)=>({status:'FINAL_SIMULATOR_PARITY_ONLY',reason,netReturnPct:t.v4.netReturnPct,exitTimestamp:t.v4.exitTimestamp??null,onlineRuntimeClaim:false});
  if(fb>=0)return same('FIRST_BAR_NON_ADVERSE_V4');
  const upto=ds.filter(d=>Number.isFinite(elapsed(d))&&elapsed(d)<=5).sort((a,b)=>elapsed(a)-elapsed(b));
  if(upto.some(d=>Number.isFinite(d.currentReturnPct)&&d.currentReturnPct>=0))return same('RECOVERED_TO_V4');
  const at=upto.find(d=>elapsed(d)===5);
  if(at){
    if(!Number.isFinite(at.currentReturnPct))return blocked('BAR5_COMPLETED_CLOSE_UNAVAILABLE');
    return {status:'FINAL_SIMULATOR_PARITY_ONLY',reason:'DEFENSIVE_EXIT_BAR_5',netReturnPct:at.currentReturnPct-0.05,exitTimestamp:at.timestamp??null,onlineRuntimeClaim:false};
  }
  // Exactly the selected simulator's truncated-trace fallback; never invent HOLD.
  return same('HORIZON_FALLBACK_V4');
}

// Market-path prefix observation only. These are NOT v5 trades without causal v4.
export function observeBar5Prefix(event){
  const rows=event.future;
  if(!rows.length)return {state:'UNKNOWN',reason:'NO_REMAINING_BAR',firstAdverse:null};
  const first=rows[0];
  if(first.slot!==1||first.missing||!Number.isFinite(first.c))return {state:'UNKNOWN',reason:'FIRST_BAR_MISSING',firstAdverse:null};
  if(first.c>=0)return {state:'NON_ADVERSE_REQUIRES_V4',firstAdverse:false,firstClosePct:first.c};
  const transitions=[{bar:1,state:'DEFENSIVE_OBSERVED',time:first.end}];
  for(let i=1;i<5;i++){
    const b=rows[i];
    if(!b)return {state:'UNKNOWN',reason:'SESSION_END_BEFORE_BAR5_REQUIRES_V4',firstAdverse:true,transitions};
    if(b.slot!==i+1||b.missing||!Number.isFinite(b.c))return {state:'UNKNOWN',reason:'MISSING_PREFIX_BAR',firstAdverse:true,transitions};
    if(b.c>=0)return {state:'RECLAIM_OBSERVED_REQUIRES_V4',firstAdverse:true,reclaimBar:i+1,reclaimClockMinutes:b.minutes,transitions:[...transitions,{bar:i+1,state:'RECLAIM_OBSERVED',time:b.end}]};
  }
  return {state:'NO_RECLAIM_THROUGH_BAR5_OBSERVED',firstAdverse:true,bar5ClosePct:rows[4].c,transitions};
}
