import {assembleP253AutonomousEvidenceInputs} from './phase57-p25-3d-autonomous-evidence-evaluation.js';
import {runP253AKDynamicManagementSession,buildP253AKManagementRows} from './phase57-p25-3ak-dynamic-management-prospective.js';
import {buildP25DataDrivenExitAnalogPool} from './phase57-p25-data-driven-exit.js';
import {simulateP25ExitV2StateConditioned,P25_EXIT_V2_STATE_CONDITIONED_SAFETY,P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256} from './phase57-p25-exit-v2-state-conditioned.js';
import {P25_EXIT_V2_FROZEN_CANDIDATE,validateP25ExitV2FrozenCandidateIdentity} from './phase57-p25-exit-v2-freeze.js';
import {validateP25ExitV2FreshCandidate} from './phase57-p25-exit-v2-independent-protocol.js';

export const P25_EXIT_V2_PROSPECTIVE_SAFETY=Object.freeze({
  ...P25_EXIT_V2_STATE_CONDITIONED_SAFETY,
  phase:'57.p25.data-driven-exit.v2.prospective-paired',
  mode:'FROZEN_EXACT_D50_PROSPECTIVE_RESEARCH_ONLY',
  freshHoldoutConsumed:false,
});

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+x,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;};
const keyOf=row=>`${String(row?.sessionDate??'')}|${String(row?.entryTimestamp??'')}|${String(row?.symbol??'').trim().toUpperCase()}`;
function profitFactor(xs){const gp=xs.filter(x=>x>0).reduce((s,x)=>s+x,0),gl=-xs.filter(x=>x<0).reduce((s,x)=>s+x,0);return gl>0?gp/gl:(gp>0?Infinity:null);}
function maxDrawdownPct(xs){let e=1,p=1,m=0;for(const r of xs){e*=1+r/100;p=Math.max(p,e);m=Math.max(m,(p-e)/p*100);}return m;}
function summarizeReturns(xs){const r=xs.map(Number).filter(Number.isFinite);let e=1;for(const x of r)e*=1+x/100;return Object.freeze({n:r.length,netReturnPct:(e-1)*100,meanNetReturnPct:mean(r),medianNetReturnPct:median(r),winRate:r.length?r.filter(x=>x>0).length/r.length:null,profitFactor:profitFactor(r),maxDrawdownPct:maxDrawdownPct(r)});}
function summarizePairs(rows=[]){
  const fixed=rows.map(x=>x.fixed?.netReturnPct).filter(finite).map(Number),v2=rows.map(x=>x.v2?.netReturnPct).filter(finite).map(Number),delta=rows.map(x=>x.deltaNetReturnPct).filter(finite).map(Number);
  return Object.freeze({pairedCount:rows.length,fixed:summarizeReturns(fixed),v2:summarizeReturns(v2),delta:Object.freeze({meanNetReturnPct:mean(delta),medianNetReturnPct:median(delta),v2BetterCount:delta.filter(x=>x>0).length,v2WorseCount:delta.filter(x=>x<0).length,equalCount:delta.filter(x=>x===0).length,meanBarsHeld:mean(rows.map(x=>x.v2?.barsHeld).filter(finite).map(Number)),meanMfePct:mean(rows.map(x=>x.v2?.mfePct).filter(finite).map(Number)),meanMaePct:mean(rows.map(x=>x.v2?.maePct).filter(finite).map(Number)),meanGivebackPct:mean(rows.map(x=>x.v2?.givebackPct).filter(finite).map(Number)),meanCaptureRatio:mean(rows.map(x=>x.v2?.captureRatio).filter(finite).map(Number))})});
}

export function runP25ExitV2ProspectivePaired({historyPack,captureArtifacts=[],sessionIntegrityLedger,lineageManifest,freshSessionDate,scorePrefix=null,roundTripCostPct=0.05}={}){
  const frozen=validateP25ExitV2FrozenCandidateIdentity();
  if(!frozen.ready)throw new Error(`P25 EXIT v2 frozen identity blocked: ${frozen.status}`);
  const fresh=validateP25ExitV2FreshCandidate({candidateFrozenAt:P25_EXIT_V2_FROZEN_CANDIDATE.candidateFrozenAt,freshSessionDate,freshSessionComplete:true,freshSessionImmutable:true});
  if(!fresh.ready)throw new Error(`P25 EXIT v2 fresh session blocked: ${fresh.status}`);
  const assembled=assembleP253AutonomousEvidenceInputs({historyPack,captureArtifacts,sessionIntegrityLedger,lineageManifest});
  const selected=assembled.sessionInputs.filter(x=>String(x?.universeRecord?.sessionDate??'')===String(freshSessionDate));
  if(selected.length!==1)throw new Error('P25 EXIT v2 prospective evaluator requires exactly one complete immutable fresh session');
  const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:assembled.historicalSessions}).filter(x=>String(x.sessionDate)<=P25_EXIT_V2_FROZEN_CANDIDATE.developmentCutoff);
  if(!analogPool.length)throw new Error('P25 EXIT v2 prospective evaluator: frozen causal analog pool empty');
  if(analogPool.some(x=>String(x.sessionDate)>P25_EXIT_V2_FROZEN_CANDIDATE.developmentCutoff))throw new Error('P25 EXIT v2 prospective evaluator: post-cutoff analog contamination');
  const input=selected[0];
  const base=runP253AKDynamicManagementSession({universeRecord:input.universeRecord,historicalSessions:assembled.historicalSessions,sessionBarsBySymbol:input.sessionBarsBySymbol??{},...(typeof scorePrefix==='function'?{scorePrefix}:{}),});
  const frozenTrades=base?.replay?.ledger?.frozenTrades??[];
  const managed=buildP253AKManagementRows({frozenTrades,sessionBarsBySymbol:input.sessionBarsBySymbol??{}});
  const rowByKey=new Map(managed.rows.map(r=>[keyOf(r),r]));
  const fixedByKey=new Map((base?.fixedOutcomes?.resolvedTrades??[]).map(r=>[keyOf(r),r]));
  const pairs=[];let dynamic50FrozenCount=0;
  for(const trade of frozenTrades){
    if(!(trade?.variantMemberships??[]).includes('DYNAMIC_50'))continue;
    dynamic50FrozenCount+=1;
    const key=keyOf(trade),row=rowByKey.get(key),fixedOutcome=fixedByKey.get(key);
    if(!row||!fixedOutcome)continue;
    const fixedNet=Number(fixedOutcome.netReturnPct??fixedOutcome.afterCostReturnPct??fixedOutcome.returnPct);
    if(!Number.isFinite(fixedNet))throw new Error(`P25 EXIT v2 prospective evaluator: fixed net missing for ${key}`);
    const v2=simulateP25ExitV2StateConditioned({row,analogPool,roundTripCostPct});
    if(v2.policySha256!==P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256)throw new Error('P25 EXIT v2 prospective evaluator: runtime policy hash mismatch');
    pairs.push(Object.freeze({key,sessionDate:trade.sessionDate,symbol:trade.symbol,sector:trade.sector??'UNKNOWN',variantMemberships:Object.freeze([...(trade.variantMemberships??[])]),fixed:Object.freeze({...fixedOutcome,netReturnPct:fixedNet}),v2,deltaNetReturnPct:v2.netReturnPct-fixedNet,deltaBarsHeld:Number(v2.barsHeld)-Number(fixedOutcome.barsHeld??0)}));
  }
  pairs.sort((a,b)=>a.key.localeCompare(b.key));
  if(pairs.some(p=>!p.variantMemberships.includes('DYNAMIC_50')))throw new Error('P25 EXIT v2 prospective evaluator: non-DYNAMIC_50 pair detected');
  return Object.freeze({phase:'57.p25.data-driven-exit.v2.prospective-paired',status:'P25_EXIT_V2_PROSPECTIVE_PAIRED_EVALUATED',candidate:P25_EXIT_V2_FROZEN_CANDIDATE,policySha256:P25_EXIT_V2_STATE_CONDITIONED_POLICY_SHA256,freshSessionDate:String(freshSessionDate),lineageManifestHeadSha256:assembled.lineageManifestHeadSha256,analogPoolCount:analogPool.length,dynamic50FrozenCount,pairedCount:pairs.length,managementBlockedCount:managed.blocked.length,pairs:Object.freeze(pairs),summary:summarizePairs(pairs),methodology:Object.freeze({exactDynamic50Only:true,sameFrozenEntryAsFixed:true,fixedBaselineUntouched:true,developmentCutoff:P25_EXIT_V2_FROZEN_CANDIDATE.developmentCutoff,legacy27UsedForTuning:false,currentFreshOutcomeUsedForFitting:false,resultBasedRetuning:false,fixedHorizonUsedAsDecisionInput:false,candidateFrozenBeforeFreshSessionOpen:true,freshHoldoutConsumed:false}),safety:P25_EXIT_V2_PROSPECTIVE_SAFETY});
}

export default {runP25ExitV2ProspectivePaired,P25_EXIT_V2_PROSPECTIVE_SAFETY};
