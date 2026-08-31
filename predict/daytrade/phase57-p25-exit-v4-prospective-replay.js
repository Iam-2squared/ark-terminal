import {assembleP253AutonomousEvidenceInputs} from './phase57-p25-3d-autonomous-evidence-evaluation.js';
import {runP253AKDynamicManagementSession,buildP253AKManagementRows} from './phase57-p25-3ak-dynamic-management-prospective.js';
import {buildP25DataDrivenExitAnalogPool} from './phase57-p25-data-driven-exit.js';
import {simulateP25ExitV4,P25_EXIT_V4_POLICY,P25_EXIT_V4_POLICY_SHA256,P25_EXIT_V4_SAFETY} from './phase57-p25-exit-v4-structural-risk.js';
import {P25_EXIT_V3_INDEPENDENT_PROTOCOL} from './phase57-p25-exit-v3-independent-protocol.js';

export const P25_EXIT_V4_PROSPECTIVE_SAFETY=Object.freeze({...P25_EXIT_V4_SAFETY,mode:'PROSPECTIVE_RESEARCH_CHALLENGER_ONLY'});
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;};
const keyOf=row=>`${String(row?.sessionDate??'')}|${String(row?.entryTimestamp??'')}|${String(row?.symbol??'').trim().toUpperCase()}`;
function pf(xs){const gp=xs.filter(x=>x>0).reduce((a,b)=>a+b,0),gl=-xs.filter(x=>x<0).reduce((a,b)=>a+b,0);return gl>0?gp/gl:(gp>0?Infinity:null);}
function dd(xs){let e=1,p=1,m=0;for(const r of xs){e*=1+r/100;p=Math.max(p,e);m=Math.max(m,(p-e)/p*100);}return m;}
function summary(xs){const r=xs.map(Number).filter(Number.isFinite);let e=1;for(const x of r)e*=1+x/100;return Object.freeze({n:r.length,netReturnPct:(e-1)*100,meanNetReturnPct:mean(r),medianNetReturnPct:median(r),winRate:r.length?r.filter(x=>x>0).length/r.length:null,profitFactor:pf(r),maxDrawdownPct:dd(r)});}

export function classifyP25ExitV4Date(sessionDate){
  const d=String(sessionDate??'');if(!/^\d{4}-\d{2}-\d{2}$/.test(d))throw new Error('EXIT v4 requires YYYY-MM-DD');
  if(d==='2026-08-31')return Object.freeze({bucket:'AUG31_FAILURE_ANALYSIS_ONLY',freshEligible:false,formalOos:false,promotionEligible:false});
  if(d<P25_EXIT_V4_POLICY.firstFreshEligibleDate)return Object.freeze({bucket:'PRE_V4_DEVELOPMENT_ONLY',freshEligible:false,formalOos:false,promotionEligible:false});
  return Object.freeze({bucket:'FRESH_CHALLENGER_PROSPECTIVE',freshEligible:true,formalOos:false,promotionEligible:false});
}

export function runP25ExitV4ProspectiveReplay({historyPack,captureArtifacts=[],sessionIntegrityLedger,lineageManifest,sessionDate,scorePrefix=null,roundTripCostPct=0.05}={}){
  const classification=classifyP25ExitV4Date(sessionDate);
  const assembled=assembleP253AutonomousEvidenceInputs({historyPack,captureArtifacts,sessionIntegrityLedger,lineageManifest});
  const selected=assembled.sessionInputs.filter(x=>String(x?.universeRecord?.sessionDate??'')===String(sessionDate));
  if(selected.length!==1)throw new Error('EXIT v4 requires exactly one complete immutable captured session');
  const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:assembled.historicalSessions}).filter(x=>String(x.sessionDate)<=P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff);
  if(!analogPool.length||analogPool.some(x=>String(x.sessionDate)>P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff))throw new Error('EXIT v4 analog pool cutoff violation');
  const input=selected[0];
  const base=runP253AKDynamicManagementSession({universeRecord:input.universeRecord,historicalSessions:assembled.historicalSessions,sessionBarsBySymbol:input.sessionBarsBySymbol??{},...(typeof scorePrefix==='function'?{scorePrefix}:{})});
  const frozenTrades=base?.replay?.ledger?.frozenTrades??[],managed=buildP253AKManagementRows({frozenTrades,sessionBarsBySymbol:input.sessionBarsBySymbol??{}}),rowByKey=new Map(managed.rows.map(r=>[keyOf(r),r])),fixedByKey=new Map((base?.fixedOutcomes?.resolvedTrades??[]).map(r=>[keyOf(r),r]));
  const pairs=[];let dynamic50FrozenCount=0;
  for(const trade of frozenTrades){
    if(!(trade?.variantMemberships??[]).includes('DYNAMIC_50'))continue;dynamic50FrozenCount++;
    const key=keyOf(trade),row=rowByKey.get(key),fixed=fixedByKey.get(key);if(!row||!fixed)continue;
    const fixedNet=Number(fixed.netReturnPct??fixed.afterCostReturnPct??fixed.returnPct);if(!Number.isFinite(fixedNet))throw new Error(`EXIT v4 fixed net missing ${key}`);
    const v4=simulateP25ExitV4({row,analogPool,roundTripCostPct});if(v4.policySha256!==P25_EXIT_V4_POLICY_SHA256)throw new Error('EXIT v4 policy hash mismatch');
    pairs.push(Object.freeze({key,sessionDate:trade.sessionDate,symbol:trade.symbol,variantMemberships:Object.freeze([...(trade.variantMemberships??[])]),fixed:Object.freeze({...fixed,netReturnPct:fixedNet}),v4,deltaNetReturnPct:v4.netReturnPct-fixedNet}));
  }
  pairs.sort((a,b)=>a.key.localeCompare(b.key));
  const delta=pairs.map(x=>x.deltaNetReturnPct).filter(finite).map(Number);
  return Object.freeze({phase:'57.p25.exit-v4.prospective-replay',status:'P25_EXIT_V4_PROSPECTIVE_REPLAY_EVALUATED',classification,policySha256:P25_EXIT_V4_POLICY_SHA256,sessionDate:String(sessionDate),lineageManifestHeadSha256:assembled.lineageManifestHeadSha256,analogPoolCount:analogPool.length,dynamic50FrozenCount,pairedCount:pairs.length,managementBlockedCount:managed.blocked.length,pairs:Object.freeze(pairs),summary:Object.freeze({pairedCount:pairs.length,fixed:summary(pairs.map(x=>x.fixed.netReturnPct)),v4:summary(pairs.map(x=>x.v4.netReturnPct)),delta:Object.freeze({meanNetReturnPct:mean(delta),medianNetReturnPct:median(delta),v4BetterCount:delta.filter(x=>x>0).length,v4WorseCount:delta.filter(x=>x<0).length,equalCount:delta.filter(x=>x===0).length})}),methodology:Object.freeze({exactDynamic50Only:true,sameFrozenEntryAsFixed:true,fixedBaselineUntouched:true,developmentCutoff:P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff,august31UsedForV4PerformanceClaim:false,replayOutcomeUsedForFitting:false,resultBasedRetuning:false,formalOosEvidence:false,promotionEligible:false,freshHoldoutConsumed:false}),safety:P25_EXIT_V4_PROSPECTIVE_SAFETY});
}

export default {classifyP25ExitV4Date,runP25ExitV4ProspectiveReplay,P25_EXIT_V4_PROSPECTIVE_SAFETY};
