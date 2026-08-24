import {assembleP253AutonomousEvidenceInputs,PHASE57_P25_3D_SAFETY} from './phase57-p25-3d-autonomous-evidence-evaluation.js';
import {runP253AKDynamicManagementSession,PHASE57_P25_3AK_SAFETY} from './phase57-p25-3ak-dynamic-management-prospective.js';

export const PHASE57_P25_3AL_SAFETY=Object.freeze({
  ...PHASE57_P25_3AK_SAFETY,
  phase:'57.p25.3al.dynamic-management-multisession',
  mode:'P25_DYNAMIC_HOLD_EXIT_MULTISESSION_RESEARCH_ONLY',
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

export const PHASE57_P25_3AL_POLICY=Object.freeze({
  sameFrozenEvidenceChainAsP253D:true,
  sameFrozenUniverseAndEntryAsFixedBaseline:true,
  fixedBaselineMutationAllowed:false,
  dynamicManagementMaySelectDynamicN:false,
  dynamicManagementMayRetuneEntry:false,
  dynamicManagementMayRetuneModel:false,
  dynamicManagementMayRetuneUniverse:false,
  dynamicManagementMayRetuneThreshold:false,
  resultBasedRuleSelectionAllowed:false,
  freshHoldoutConsumed:false,
  performanceConclusionAllowed:false,
});

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+x,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const s=[...xs].sort((a,b)=>a-b);const m=Math.floor(s.length/2);return s.length%2?s[m]:(s[m-1]+s[m])/2;};
function profitFactor(xs){const gp=xs.filter(x=>x>0).reduce((s,x)=>s+x,0),gl=-xs.filter(x=>x<0).reduce((s,x)=>s+x,0);return gl>0?gp/gl:(gp>0?Infinity:null);}
function maxDrawdownPct(xs){let equity=1,peak=1,max=0;for(const r of xs){equity*=1+r/100;peak=Math.max(peak,equity);if(peak>0)max=Math.max(max,(peak-equity)/peak*100);}return max;}
function summarizeReturns(xs){
  const returns=xs.map(Number).filter(Number.isFinite);
  let equity=1;for(const r of returns)equity*=1+r/100;
  return Object.freeze({
    n:returns.length,
    netReturnPct:(equity-1)*100,
    meanNetReturnPct:mean(returns),
    medianNetReturnPct:median(returns),
    winRate:returns.length?returns.filter(x=>x>0).length/returns.length:null,
    profitFactor:profitFactor(returns),
    maxDrawdownPct:maxDrawdownPct(returns),
  });
}

export function summarizeP253ALPairs(pairs=[]){
  const rows=Array.isArray(pairs)?pairs:[];
  const fixed=rows.map(x=>x?.fixed?.netReturnPct).filter(finite).map(Number);
  const dynamic=rows.map(x=>x?.dynamic?.netReturnPct).filter(finite).map(Number);
  const deltas=rows.map(x=>x?.deltaNetReturnPct).filter(finite).map(Number);
  const barsDelta=rows.map(x=>x?.deltaBarsHeld).filter(finite).map(Number);
  const giveback=rows.map(x=>x?.dynamic?.givebackPct).filter(finite).map(Number);
  const capture=rows.map(x=>x?.dynamic?.captureRatio).filter(finite).map(Number);
  return Object.freeze({
    pairedCount:rows.length,
    fixed:summarizeReturns(fixed),
    dynamic:summarizeReturns(dynamic),
    delta:Object.freeze({
      meanNetReturnPct:mean(deltas),
      medianNetReturnPct:median(deltas),
      dynamicBetterCount:deltas.filter(x=>x>0).length,
      dynamicWorseCount:deltas.filter(x=>x<0).length,
      equalCount:deltas.filter(x=>x===0).length,
      meanBarsHeldDelta:mean(barsDelta),
      meanDynamicGivebackPct:mean(giveback),
      meanDynamicCaptureRatio:mean(capture),
    }),
  });
}

export function summarizeP253ALByVariant(pairs=[]){
  const variants=['FIXED_5','OLD_FIXED_30','DYNAMIC_30','DYNAMIC_40','DYNAMIC_50'];
  return Object.freeze(Object.fromEntries(variants.map(variant=>[
    variant,
    summarizeP253ALPairs(pairs.filter(pair=>Array.isArray(pair?.variantMemberships)&&pair.variantMemberships.includes(variant))),
  ])));
}

/**
 * Reconstructs the same lineage-pinned P25.3D inputs, then evaluates Dynamic HOLD/EXIT
 * only after Entry has already been frozen. Fixed outcomes remain the formal baseline.
 * sessionDates is an execution-only shard selector applied after immutable input assembly;
 * it cannot alter the frozen evidence chain or any Entry/model/universe/threshold decision.
 */
export function runP253ALDynamicManagementMultisession({
  historyPack,
  captureArtifacts=[],
  sessionIntegrityLedger,
  lineageManifest,
  sessionDates=null,
}={}){
  const assembled=assembleP253AutonomousEvidenceInputs({historyPack,captureArtifacts,sessionIntegrityLedger,lineageManifest});
  const requested=sessionDates==null?null:new Set((Array.isArray(sessionDates)?sessionDates:[sessionDates]).map(String));
  const selectedInputs=requested==null?assembled.sessionInputs:assembled.sessionInputs.filter(input=>requested.has(String(input?.universeRecord?.sessionDate??'')));
  if(requested&&selectedInputs.length!==requested.size){
    const found=new Set(selectedInputs.map(input=>String(input?.universeRecord?.sessionDate??'')));
    const missing=[...requested].filter(date=>!found.has(date));
    throw new Error(`P25.3AL requested session shard not ready: ${missing.join(',')}`);
  }
  const sessions=[];
  const pairs=[];
  for(const input of selectedInputs){
    const result=runP253AKDynamicManagementSession({
      universeRecord:input.universeRecord,
      historicalSessions:assembled.historicalSessions,
      sessionBarsBySymbol:input.sessionBarsBySymbol??{},
    });
    const ledgerByKey=new Map((result?.replay?.ledger?.frozenTrades??[]).map(row=>[
      `${String(row.sessionDate)}|${String(row.entryTimestamp)}|${String(row.symbol).toUpperCase()}`,
      row,
    ]));
    for(const pair of result?.dynamicParallel?.pairs??[]){
      const frozen=ledgerByKey.get(pair.key);
      pairs.push(Object.freeze({
        ...pair,
        variantMemberships:Object.freeze([...(frozen?.variantMemberships??[])]),
        sector:frozen?.sector??'UNKNOWN',
      }));
    }
    sessions.push(Object.freeze({
      sessionDate:result.sessionDate,
      frozenTradeCount:Number(result?.adapterAudit?.frozenTradeCount??0),
      fixedResolvedCount:Number(result?.adapterAudit?.fixedResolvedCount??0),
      managementReadyCount:Number(result?.adapterAudit?.managementReadyCount??0),
      pairedCount:Number(result?.adapterAudit?.pairedCount??0),
      missingDynamicPairCount:Number(result?.adapterAudit?.missingDynamicPairCount??0),
    }));
  }
  pairs.sort((a,b)=>String(a.key).localeCompare(String(b.key)));
  return Object.freeze({
    phase:'57.p25.3al.dynamic-management-multisession',
    status:'P25_3AL_DYNAMIC_MANAGEMENT_MULTISESSION_EVALUATED',
    lineageManifestHeadSha256:assembled.lineageManifestHeadSha256,
    lineageNodeCount:assembled.lineageNodeCount,
    expectedSessionCount:assembled.expectedSessionDates.length,
    readySessionCount:selectedInputs.length,
    shardSessionDates:Object.freeze(selectedInputs.map(input=>String(input?.universeRecord?.sessionDate??''))),
    sessions:Object.freeze(sessions),
    pairs:Object.freeze(pairs),
    summary:summarizeP253ALPairs(pairs),
    byVariant:summarizeP253ALByVariant(pairs),
    methodology:Object.freeze({
      sameFrozenEvidenceChainAsP253D:true,
      sameFrozenUniverseAndEntryAsFixedBaseline:true,
      fixedBaselineUntouched:true,
      scorerReceivesPrefixOnly:true,
      futureBarsUsedForEntryDecision:false,
      managementFutureBarsSequentialOnly:true,
      executionShardSelectionOnly:true,
      postOutcomeRuleSelection:false,
      entryRetuning:false,
      modelRetuning:false,
      universeRetuning:false,
      thresholdRetuning:false,
      dynamicNSelectionFromResults:false,
      freshHoldoutConsumed:false,
      performanceConclusionAllowed:false,
    }),
    safety:PHASE57_P25_3AL_SAFETY,
    upstreamSafety:Object.freeze({p253d:PHASE57_P25_3D_SAFETY,p253ak:PHASE57_P25_3AK_SAFETY}),
  });
}

export default {runP253ALDynamicManagementMultisession,summarizeP253ALPairs,summarizeP253ALByVariant,PHASE57_P25_3AL_POLICY,PHASE57_P25_3AL_SAFETY};
