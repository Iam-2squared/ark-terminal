import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildCar1DevelopmentEvidenceLock} from '../predict/portfolio/phase57-car1-independent-validation.js';
import {
  gateCar1IndependentValidationMetadataCandidate,
  runCar1ValidationCandidateMetadata,
} from '../predict/portfolio/phase57-car1-validation-candidate-metadata.js';
import {buildLaneCFixedCheckpointPackets} from '../predict/portfolio/phase57-p25-lane-c-fixed-checkpoint-runner.js';
import {
  PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY,
  runCar1SelectedValidationReplay,
} from '../predict/portfolio/phase57-car1-selected-validation-replay.js';

const arg=(name,fallback=null)=>{
  const index=process.argv.indexOf(name);
  return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;
};
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const load=file=>{
  const bytes=fs.readFileSync(file);
  return {bytes,sha256:sha(bytes),json:JSON.parse(bytes.toString('utf8'))};
};
const equalJson=(left,right)=>JSON.stringify(left)===JSON.stringify(right);

const historyPath=arg('--history-pack');
const captureDir=arg('--capture-dir');
const integrityPath=arg('--integrity-ledger');
const lineagePath=arg('--lineage-manifest');
const checkpointDir=arg('--checkpoint-dir');
const sourceEvaluationPath=arg('--source-evaluation');
const developmentArtifactPath=arg('--development-artifact');
const validationCandidatePath=arg('--validation-candidate');
const outputPath=arg('--output','data/phase57-car1-selected-validation-replay.json');

if(!historyPath||!captureDir||!integrityPath||!lineagePath||!checkpointDir||!sourceEvaluationPath||!developmentArtifactPath||!validationCandidatePath){
  console.error('usage: node scripts/run_phase57_car1_selected_validation_replay.mjs --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> --checkpoint-dir <dir> --source-evaluation <json> --development-artifact <json> --validation-candidate <json> [--output <json>]');
  process.exit(2);
}

try{
  const history=load(historyPath);
  const integrity=load(integrityPath);
  const lineage=load(lineagePath);
  const sourceEvaluation=load(sourceEvaluationPath);
  const developmentArtifact=load(developmentArtifactPath);
  const validationCandidate=load(validationCandidatePath);

  if(developmentArtifact.json?.status!=='CAR1_CHECKPOINTED_PAIRED_SIZING_ARTIFACT_WRITTEN'||developmentArtifact.json?.result?.status!=='CAR1_CHECKPOINTED_PAIRED_SIZING_ATTRIBUTION_READY'){
    throw new Error('CAR-1 pinned development artifact is not ready');
  }
  if(validationCandidate.json?.status!=='CAR1_METADATA_ONLY_VALIDATION_GATE_READY'){
    throw new Error('CAR-1 validation candidate artifact is not metadata-gate ready');
  }
  if(validationCandidate.json?.methodology?.cumulativeChallengerReplayExecuted!==false||validationCandidate.json?.methodology?.cumulativeChallengerPerformanceMaterialized!==false){
    throw new Error('CAR-1 validation candidate must remain metadata-only before selected replay');
  }

  const developmentLock=buildCar1DevelopmentEvidenceLock({result:developmentArtifact.json.result});
  if(validationCandidate.json?.inputs?.developmentArtifactSha256!==developmentArtifact.sha256){
    throw new Error('CAR-1 validation candidate development artifact identity mismatch');
  }
  if(validationCandidate.json?.developmentLock?.configurationSha256!==developmentLock.configurationSha256||
     validationCandidate.json?.developmentLock?.developmentEvidenceSha256!==developmentLock.developmentEvidenceSha256){
    throw new Error('CAR-1 validation candidate development lock mismatch');
  }

  const captureFiles=fs.readdirSync(captureDir).filter(name=>name.endsWith('.json')).sort();
  if(!captureFiles.length)throw new Error('CAR-1 selected validation capture directory is empty');
  const captureArtifacts=captureFiles.map(name=>{
    const loaded=load(path.join(captureDir,name));
    return {artifact:loaded.json,artifactSha256:loaded.sha256,artifactPath:name};
  });

  const checkpointFiles=fs.readdirSync(checkpointDir).filter(name=>name.endsWith('.json')).sort();
  if(!checkpointFiles.length)throw new Error('CAR-1 selected validation checkpoint directory is empty');
  const checkpointsBySession={};
  for(const name of checkpointFiles){
    const checkpoint=load(path.join(checkpointDir,name)).json;
    const sessionDate=String(checkpoint?.identities?.sessionDate??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`CAR-1 selected validation checkpoint session identity invalid: ${name}`);
    (checkpointsBySession[sessionDate]??=[]).push(checkpoint);
  }

  const candidateMetadata=runCar1ValidationCandidateMetadata({
    historyPack:history.json,
    captureArtifacts,
    sessionIntegrityLedger:integrity.json,
    lineageManifest:lineage.json,
    checkpointsBySession,
    sourceEvaluationArtifact:sourceEvaluation.json,
  });
  const gate=gateCar1IndependentValidationMetadataCandidate({developmentLock,candidateMetadata});
  const priorGate=validationCandidate.json.gate??{};
  const priorMetadata=validationCandidate.json.candidateMetadata??{};
  if(!equalJson(priorGate.selectedSessionDates,gate.selectedSessionDates)||
     priorGate.configurationSha256!==gate.configurationSha256||
     priorGate.candidateLineageManifestHeadSha256!==gate.candidateLineageManifestHeadSha256||
     priorMetadata.lineageManifestHeadSha256!==candidateMetadata.lineageManifestHeadSha256){
    throw new Error('CAR-1 selected validation gate/source drift detected');
  }

  const packetBundle=buildLaneCFixedCheckpointPackets({
    historyPack:history.json,
    captureArtifacts,
    sessionIntegrityLedger:integrity.json,
    lineageManifest:lineage.json,
    checkpointsBySession,
  });
  if(packetBundle.assembled?.lineageManifestHeadSha256!==candidateMetadata.lineageManifestHeadSha256){
    throw new Error('CAR-1 selected validation packet lineage mismatch');
  }

  const result=runCar1SelectedValidationReplay({
    developmentLock,
    validationGate:gate,
    sessionPackets:packetBundle.packets,
  });
  if(result?.status!=='CAR1_SELECTED_SESSION_ONLY_VALIDATION_REPLAY_READY'||result?.inputAudit?.selectedSessionOnly!==true||result?.inputAudit?.selectedSessionCount!==5){
    throw new Error('CAR-1 selected validation replay did not remain five-session-only');
  }

  const payload={
    schemaVersion:1,
    phase:'57.car1.selected-validation-replay-cli',
    status:'CAR1_SELECTED_SESSION_ONLY_VALIDATION_ARTIFACT_WRITTEN',
    createdAt:new Date().toISOString(),
    inputs:{
      historyPackSha256:history.sha256,
      integrityLedgerSha256:integrity.sha256,
      lineageManifestSha256:lineage.sha256,
      sourceEvaluationSha256:sourceEvaluation.sha256,
      developmentArtifactSha256:developmentArtifact.sha256,
      validationCandidateArtifactSha256:validationCandidate.sha256,
      captureArtifactCount:captureArtifacts.length,
      checkpointArtifactCount:checkpointFiles.length,
    },
    gateIdentity:{
      protocolId:gate.protocolId,
      configurationSha256:gate.configurationSha256,
      candidateLineageManifestHeadSha256:gate.candidateLineageManifestHeadSha256,
      selectedSessionDates:gate.selectedSessionDates,
    },
    result,
    methodology:{
      independentValidation:true,
      precommittedSelectedSessionOnly:true,
      cumulativeChallengerPerformanceConsumed:false,
      performanceExtractionScope:'SELECTED_PRECOMMITTED_SESSIONS_ONLY',
      parameterSearchAllowed:false,
      winnerSelectionAllowed:false,
      promotionEligible:false,
      retrospectiveBackfillAllowed:false,
    },
    safety:PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY,
  };

  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const temporaryPath=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(temporaryPath,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(temporaryPath,outputPath);
  const outputSha256=sha(fs.readFileSync(outputPath));
  console.log(JSON.stringify({
    status:payload.status,
    output:outputPath,
    outputSha256,
    selectedSessionDates:result.selectedSessionDates,
    matrixRows:result.matrixRows,
    performanceExtractionScope:payload.methodology.performanceExtractionScope,
    winnerSelectionAllowed:false,
    promotionEligible:false,
    safety:PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({
    status:'BLOCKED_CAR1_SELECTED_SESSION_ONLY_VALIDATION_REPLAY',
    error:String(error?.message??error),
    safety:PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY,
  },null,2));
  process.exit(1);
}
