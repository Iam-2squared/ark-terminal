import {buildP253EvidenceLineageManifest} from './phase57-p25-3b-evidence-lineage-manifest.js';
import {runP252EndToEndProspectiveEvaluation} from './phase57-p25-2i-end-to-end-prospective-evaluation.js';
import {PHASE57_P25_2H_VARIANTS} from './phase57-p25-2h-multisession-evidence-accumulator.js';

export const PHASE57_P25_3D_SAFETY=Object.freeze({
  phase:'57.p25.3d.autonomous-evidence-evaluation',
  mode:'READ_ONLY_LINEAGE_PINNED_PROSPECTIVE_EVALUATION',
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

export const PHASE57_P25_3D_POLICY=Object.freeze({
  historyPackPhase:'57.p25.2k.pinned-history-bridge-cli',
  historyPackStatus:'P25_2_PINNED_HISTORY_PACK_READY',
  integrityPhase:'57.p25.3a.session-integrity-ledger',
  lineagePhase:'57.p25.3b.evidence-lineage-manifest',
  capturePhase:'57.p25.2j.routine-nonrss-5m-source-cli',
  allFiveVariantsRetained:true,
  variants:PHASE57_P25_2H_VARIANTS,
  dynamicNSelectedFromCurrentOuterOos:false,
  entryThresholdRelaxationAllowed:false,
  postHocWinnerFilteringAllowed:false,
  dailyMarketSpeedRequired:false,
  boardOrTickUsed:false,
  microstructureUsed:false,
});

const SAFETY_FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  'transmitted','freshHoldoutConsumed',
]);
const validSha=value=>/^[a-f0-9]{64}$/i.test(String(value??''));
const validDate=value=>/^\d{4}-\d{2}-\d{2}$/.test(String(value??''));
const sameArray=(a,b)=>JSON.stringify([...(a??[])])===JSON.stringify([...(b??[])]);

function unwrapCapture(entry){
  if(entry?.artifact&&typeof entry.artifact==='object')return {artifact:entry.artifact,artifactSha256:entry.artifactSha256,artifactPath:entry.artifactPath??null};
  return {artifact:entry,artifactSha256:entry?.artifactSha256,artifactPath:entry?.artifactPath??null};
}
function integrityObject(input){return input?.ledger?.phase===PHASE57_P25_3D_POLICY.integrityPhase?input.ledger:input;}
function lineageObject(input){return input?.manifest?.phase===PHASE57_P25_3D_POLICY.lineagePhase?input.manifest:input;}
function assertSafetyFalse(safety,label){
  for(const key of SAFETY_FALSE_KEYS){
    if(safety?.[key]!==false)throw new Error(`P25.3D ${label} safety ${key} must be false`);
  }
}
function sessionDateOfCapture(artifact){
  return String(artifact?.collection?.sessionDate??artifact?.expectedSessionDates?.[0]??'').trim();
}

/**
 * Reconstruct the exact evaluation inputs from the already-frozen evidence chain.
 * This layer does not inspect performance while deciding which sessions or variants
 * enter the experiment: the lineage, session denominator and five variants are all
 * fixed before P25.2I computes any result.
 */
export function assembleP253AutonomousEvidenceInputs({
  historyPack,
  captureArtifacts=[],
  sessionIntegrityLedger,
  lineageManifest,
}={}){
  if(historyPack?.phase!==PHASE57_P25_3D_POLICY.historyPackPhase||historyPack?.status!==PHASE57_P25_3D_POLICY.historyPackStatus)throw new Error('P25.3D requires the pinned P25.2K history pack');
  if(!Array.isArray(historyPack?.sessions))throw new Error('P25.3D history pack sessions[] missing');
  if(historyPack?.methodology?.freshHoldoutConsumed!==false)throw new Error('P25.3D history pack must keep freshHoldoutConsumed=false');
  assertSafetyFalse(historyPack?.safety,'history pack');

  const integrity=integrityObject(sessionIntegrityLedger);
  if(integrity?.phase!==PHASE57_P25_3D_POLICY.integrityPhase)throw new Error('P25.3D requires the P25.3A integrity ledger');
  if(integrity?.methodology?.outerOosPerformanceUsedForClassification!==false)throw new Error('P25.3D integrity classification must be outcome-independent');
  assertSafetyFalse(integrity?.safety,'integrity ledger');

  const storedLineage=lineageObject(lineageManifest);
  if(storedLineage?.phase!==PHASE57_P25_3D_POLICY.lineagePhase||storedLineage?.status!=='P25_3_EVIDENCE_LINEAGE_MANIFEST_READY')throw new Error('P25.3D requires a ready P25.3B lineage manifest');
  assertSafetyFalse(storedLineage?.safety,'lineage manifest');

  const captures=Array.isArray(captureArtifacts)?captureArtifacts:[];
  const rebuiltLineage=buildP253EvidenceLineageManifest({historyPack,captureArtifacts:captures,sessionIntegrityLedger:integrity});
  if(rebuiltLineage.manifestHeadSha256!==storedLineage.manifestHeadSha256)throw new Error('P25.3D stored lineage head does not match rebuilt frozen evidence');
  if(rebuiltLineage.chainSeedSha256!==storedLineage.chainSeedSha256||rebuiltLineage.nodeCount!==storedLineage.nodeCount)throw new Error('P25.3D stored lineage identity does not match rebuilt frozen evidence');

  const storedExpected=[...(storedLineage?.sessionSets?.recommendedExpectedSessionDatesForP252H??[])];
  const integrityExpected=[...(integrity?.recommendedExpectedSessionDatesForP252H??[])];
  if(!sameArray(storedExpected,integrityExpected))throw new Error('P25.3D expected-session denominator differs between lineage and integrity ledger');
  if(storedExpected.some(date=>!validDate(date)))throw new Error('P25.3D expected-session denominator contains invalid date');

  const nodesByDate=new Map((storedLineage.nodes??[]).map(node=>[String(node.sessionDate),node]));
  const sessionInputs=[];
  const seenDates=new Set();
  for(const raw of captures){
    const {artifact,artifactSha256,artifactPath}=unwrapCapture(raw);
    if(artifact?.phase!==PHASE57_P25_3D_POLICY.capturePhase)throw new Error(`P25.3D unexpected capture phase: ${artifact?.phase??'MISSING'}`);
    assertSafetyFalse(artifact?.safety,'capture artifact');
    if(!validSha(artifactSha256))throw new Error('P25.3D each capture artifact requires SHA-256');
    const sessionDate=sessionDateOfCapture(artifact);
    if(!validDate(sessionDate))throw new Error('P25.3D capture session date invalid');
    if(seenDates.has(sessionDate))throw new Error(`duplicate P25.3D capture session: ${sessionDate}`);
    seenDates.add(sessionDate);
    const node=nodesByDate.get(sessionDate);
    if(!node)throw new Error(`P25.3D lineage node missing for ${sessionDate}`);
    if(String(node.captureArtifactSha256??'').toLowerCase()!==String(artifactSha256).toLowerCase())throw new Error(`P25.3D capture SHA does not match lineage for ${sessionDate}`);

    const ready=artifact?.collection?.ready===true;
    if(!ready){
      if(Array.isArray(artifact?.sessions)&&artifact.sessions.length)throw new Error(`P25.3D blocked capture ${sessionDate} may not expose ready session bars`);
      continue;
    }
    if(node.classification!=='READY_CONFIRMED_TRADING_SESSION')throw new Error(`P25.3D ready capture ${sessionDate} is not classified as a ready trading session`);
    if(!Array.isArray(artifact?.sessions)||artifact.sessions.length!==1)throw new Error(`P25.3D ready capture ${sessionDate} must contain exactly one frozen session input`);
    const session=artifact.sessions[0];
    if(String(session?.sessionDate??'')!==sessionDate||session?.universeRecord?.ready!==true||String(session?.universeRecord?.sessionDate??'')!==sessionDate)throw new Error(`P25.3D ready session bundle mismatch for ${sessionDate}`);
    sessionInputs.push(Object.freeze({
      ...session,
      sourceProvenance:Object.freeze({
        ...(session?.sourceProvenance??{}),
        captureArtifactSha256:String(artifactSha256).toLowerCase(),
        captureArtifactPath:artifactPath?String(artifactPath):null,
        lineageNodeSha256:String(node.chainSha256),
        lineageManifestHeadSha256:String(storedLineage.manifestHeadSha256),
      }),
    }));
  }
  sessionInputs.sort((a,b)=>String(a.sessionDate).localeCompare(String(b.sessionDate)));

  return Object.freeze({
    historicalSessions:Object.freeze(historyPack.sessions.slice()),
    sessionInputs:Object.freeze(sessionInputs),
    expectedSessionDates:Object.freeze(storedExpected),
    lineageManifestHeadSha256:String(storedLineage.manifestHeadSha256),
    lineageNodeCount:Number(storedLineage.nodeCount),
    methodology:Object.freeze({
      evidenceMembershipFixedBeforePerformance:true,
      expectedSessionDenominatorFixedBeforePerformance:true,
      allFiveVariantsRetained:true,
      currentOuterOosDoesNotSelectDynamicN:true,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_3D_SAFETY,
  });
}

export function runP253AutonomousEvidenceEvaluation(input={}){
  const assembled=assembleP253AutonomousEvidenceInputs(input);
  const result=runP252EndToEndProspectiveEvaluation({
    historicalSessions:assembled.historicalSessions,
    sessionInputs:assembled.sessionInputs,
    expectedSessionDates:assembled.expectedSessionDates,
  });
  if(result?.methodology?.currentOuterOosDoesNotSelectDynamicN!==true||result?.methodology?.allFiveVariantsRetained!==true)throw new Error('P25.3D evaluator violated the frozen five-variant policy');
  const frequency=result?.evidence?.operationalTradeFrequency??{};
  for(const variant of PHASE57_P25_2H_VARIANTS){
    if(!frequency[variant])throw new Error(`P25.3D evaluator omitted precommitted variant ${variant}`);
  }
  assertSafetyFalse(result?.safety,'P25.2I result');

  return Object.freeze({
    phase:'57.p25.3d.autonomous-evidence-evaluation',
    status:'P25_3_AUTONOMOUS_EVIDENCE_EVALUATED',
    lineageManifestHeadSha256:assembled.lineageManifestHeadSha256,
    lineageNodeCount:assembled.lineageNodeCount,
    frozenReadySessionInputCount:assembled.sessionInputs.length,
    expectedSessionCount:assembled.expectedSessionDates.length,
    result,
    methodology:Object.freeze({...assembled.methodology}),
    safety:PHASE57_P25_3D_SAFETY,
  });
}

export default {assembleP253AutonomousEvidenceInputs,runP253AutonomousEvidenceEvaluation,PHASE57_P25_3D_POLICY,PHASE57_P25_3D_SAFETY};
