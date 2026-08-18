import crypto from 'node:crypto';

export const PHASE57_P25_3B_SAFETY=Object.freeze({
  phase:'57.p25.3b.evidence-lineage-manifest',
  mode:'READ_ONLY_IMMUTABLE_PROSPECTIVE_LINEAGE',
  researchOnly:true,
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

export const PHASE57_P25_3B_POLICY=Object.freeze({
  canonicalHistoryRunId:31785422471,
  canonicalHistorySnapshotSha256:'10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a',
  historyPackPhase:'57.p25.2k.pinned-history-bridge-cli',
  capturePhase:'57.p25.2j.routine-nonrss-5m-source-cli',
  integrityPhase:'57.p25.3a.session-integrity-ledger',
  captureShaRequired:true,
  chronologicalHashChain:true,
  performanceFieldsExcludedFromLineageIdentity:true,
  outerOosMayRewriteLineage:false,
  dailyMarketSpeedRequired:false,
  boardOrTickUsed:false,
});

const FORBIDDEN_LINEAGE_PERFORMANCE_KEYS=Object.freeze([
  'netReturnPct','grossReturnPct','profitFactor','pf','winRate','hitRate','maxDrawdown','maxDD',
  'selectedDynamicN','winnerVariant','outerOosScore','performanceRank',
]);
const sha=value=>crypto.createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');
const validSha=value=>/^[a-f0-9]{64}$/i.test(String(value??''));
const validDate=value=>/^\d{4}-\d{2}-\d{2}$/.test(String(value??''));

function rejectPerformanceIdentityFields(object,label){
  if(!object||typeof object!=='object')return;
  const present=FORBIDDEN_LINEAGE_PERFORMANCE_KEYS.filter(key=>Object.prototype.hasOwnProperty.call(object,key));
  if(present.length)throw new Error(`${label} contains forbidden performance identity fields: ${present.join(',')}`);
}
function unwrapCapture(entry){
  if(entry?.artifact&&typeof entry.artifact==='object')return {artifact:entry.artifact,artifactSha256:entry.artifactSha256,artifactPath:entry.artifactPath??null};
  return {artifact:entry,artifactSha256:entry?.artifactSha256,artifactPath:entry?.artifactPath??null};
}
function integrityObject(input){return input?.ledger?.phase===PHASE57_P25_3B_POLICY.integrityPhase?input.ledger:input;}

export function buildP253EvidenceLineageManifest({
  historyPack,
  captureArtifacts=[],
  sessionIntegrityLedger,
}={}){
  if(historyPack?.phase!==PHASE57_P25_3B_POLICY.historyPackPhase||historyPack?.status!=='P25_2_PINNED_HISTORY_PACK_READY')throw new Error('P25.3B requires the pinned P25.2K history pack');
  if(Number(historyPack?.canonicalSourceRunId)!==PHASE57_P25_3B_POLICY.canonicalHistoryRunId)throw new Error('P25.3B canonical history run mismatch');
  if(String(historyPack?.canonicalSnapshotSha256??'').toLowerCase()!==PHASE57_P25_3B_POLICY.canonicalHistorySnapshotSha256)throw new Error('P25.3B canonical history snapshot SHA mismatch');
  if(historyPack?.methodology?.freshHoldoutConsumed!==false)throw new Error('P25.3B pinned history must attest freshHoldoutConsumed=false');
  rejectPerformanceIdentityFields(historyPack,'history pack');

  const integrity=integrityObject(sessionIntegrityLedger);
  if(integrity?.phase!==PHASE57_P25_3B_POLICY.integrityPhase)throw new Error('P25.3B requires a P25.3A session integrity ledger');
  if(integrity?.methodology?.outerOosPerformanceUsedForClassification!==false)throw new Error('P25.3B session classification must be outcome-independent');
  const integrityRows=new Map((Array.isArray(integrity?.rows)?integrity.rows:[]).map(row=>[String(row.sessionDate),row]));

  const captures=[];
  const seen=new Set();
  for(const raw of Array.isArray(captureArtifacts)?captureArtifacts:[]){
    const {artifact,artifactSha256,artifactPath}=unwrapCapture(raw);
    if(artifact?.phase!==PHASE57_P25_3B_POLICY.capturePhase)throw new Error(`P25.3B unexpected capture phase: ${artifact?.phase??'MISSING'}`);
    if(!validSha(artifactSha256))throw new Error('P25.3B each capture artifact requires a SHA-256 fingerprint');
    rejectPerformanceIdentityFields(raw,'capture lineage wrapper');
    rejectPerformanceIdentityFields(artifact,'capture artifact');
    const sessionDate=String(artifact?.collection?.sessionDate??artifact?.expectedSessionDates?.[0]??'');
    if(!validDate(sessionDate))throw new Error('P25.3B capture session date invalid');
    if(seen.has(sessionDate))throw new Error(`duplicate P25.3B capture session: ${sessionDate}`);
    seen.add(sessionDate);
    const row=integrityRows.get(sessionDate);
    if(!row)throw new Error(`P25.3B integrity ledger missing capture session ${sessionDate}`);
    if(row.artifactSha256&&String(row.artifactSha256).toLowerCase()!==String(artifactSha256).toLowerCase())throw new Error(`P25.3B capture SHA disagrees with integrity ledger for ${sessionDate}`);
    const universeFingerprint=artifact?.sessions?.[0]?.universeRecord?.sourceSnapshotFingerprint??null;
    captures.push({
      sessionDate,
      artifactSha256:String(artifactSha256).toLowerCase(),
      artifactPath:artifactPath?String(artifactPath):null,
      classification:String(row.classification??'UNKNOWN'),
      captureReady:artifact?.collection?.ready===true,
      targetSymbolCount:Number(artifact?.collection?.targetSymbolCount??0),
      universeFingerprint:universeFingerprint?String(universeFingerprint):null,
    });
  }
  captures.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
  if(captures.length!==integrityRows.size)throw new Error(`P25.3B capture/integrity cardinality mismatch: captures=${captures.length}, integrity=${integrityRows.size}`);

  const historyIdentity=Object.freeze({
    canonicalSourceRunId:Number(historyPack.canonicalSourceRunId),
    canonicalSnapshotSha256:String(historyPack.canonicalSnapshotSha256).toLowerCase(),
    sessionCount:Number(historyPack.sessionCount??0),
    perSymbolSessionCount:historyPack.perSymbolSessionCount??null,
  });
  const chainSeed=sha({lineage:'PHASE57_P25_3B_V1',historyIdentity});
  let previous=chainSeed;
  const nodes=captures.map(capture=>{
    const identity=Object.freeze({
      sessionDate:capture.sessionDate,
      captureArtifactSha256:capture.artifactSha256,
      classification:capture.classification,
      captureReady:capture.captureReady,
      targetSymbolCount:capture.targetSymbolCount,
      universeFingerprint:capture.universeFingerprint,
    });
    const chainSha256=sha({previousChainSha256:previous,identity});
    const node=Object.freeze({...identity,artifactPath:capture.artifactPath,previousChainSha256:previous,chainSha256});
    previous=chainSha256;
    return node;
  });

  return Object.freeze({
    phase:'57.p25.3b.evidence-lineage-manifest',
    status:'P25_3_EVIDENCE_LINEAGE_MANIFEST_READY',
    historyIdentity,
    chainSeedSha256:chainSeed,
    manifestHeadSha256:previous,
    nodeCount:nodes.length,
    nodes:Object.freeze(nodes),
    sessionSets:Object.freeze({
      confirmedTradingSessionDates:Object.freeze([...(integrity.confirmedTradingSessionDates??[])]),
      unresolvedSessionDates:Object.freeze([...(integrity.unresolvedSessionDates??[])]),
      verifiedNonTradingSessionDates:Object.freeze([...(integrity.verifiedNonTradingSessionDates??[])]),
      recommendedExpectedSessionDatesForP252H:Object.freeze([...(integrity.recommendedExpectedSessionDatesForP252H??[])]),
    }),
    methodology:Object.freeze({
      chronologicalHashChain:true,
      pinnedHistoryIdentityIncluded:true,
      captureArtifactShaRequired:true,
      sessionClassificationOutcomeIndependent:true,
      performanceMetricsExcludedFromLineageIdentity:true,
      outerOosMayRewriteLineage:false,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_3B_SAFETY,
  });
}

export default {buildP253EvidenceLineageManifest,PHASE57_P25_3B_POLICY,PHASE57_P25_3B_SAFETY};
