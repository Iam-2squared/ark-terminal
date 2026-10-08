import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildCar1DevelopmentEvidenceLock} from '../predict/portfolio/phase57-car1-independent-validation.js';
import {
  PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY,
  gateCar1IndependentValidationMetadataCandidate,
  runCar1ValidationCandidateMetadata,
} from '../predict/portfolio/phase57-car1-validation-candidate-metadata.js';

const arg=(name,fallback=null)=>{
  const index=process.argv.indexOf(name);
  return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;
};
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const load=file=>{
  const bytes=fs.readFileSync(file);
  return {bytes,sha256:sha(bytes),json:JSON.parse(bytes.toString('utf8'))};
};

const historyPath=arg('--history-pack');
const captureDir=arg('--capture-dir');
const integrityPath=arg('--integrity-ledger');
const lineagePath=arg('--lineage-manifest');
const checkpointDir=arg('--checkpoint-dir');
const sourceEvaluationPath=arg('--source-evaluation');
const developmentArtifactPath=arg('--development-artifact');
const outputPath=arg('--output','data/phase57-car1-validation-candidate-metadata.json');

if(!historyPath||!captureDir||!integrityPath||!lineagePath||!checkpointDir||!sourceEvaluationPath||!developmentArtifactPath){
  console.error('usage: node scripts/run_phase57_car1_validation_candidate_metadata.mjs --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> --checkpoint-dir <dir> --source-evaluation <json> --development-artifact <json> [--output <json>]');
  process.exit(2);
}

try{
  const history=load(historyPath);
  const integrity=load(integrityPath);
  const lineage=load(lineagePath);
  const sourceEvaluation=load(sourceEvaluationPath);
  const developmentArtifact=load(developmentArtifactPath);
  if(developmentArtifact.json?.status!=='CAR1_CHECKPOINTED_PAIRED_SIZING_ARTIFACT_WRITTEN'||developmentArtifact.json?.result?.status!=='CAR1_CHECKPOINTED_PAIRED_SIZING_ATTRIBUTION_READY'){
    throw new Error('CAR-1 pinned development artifact is not ready');
  }
  const developmentLock=buildCar1DevelopmentEvidenceLock({result:developmentArtifact.json.result});

  const captureFiles=fs.readdirSync(captureDir).filter(name=>name.endsWith('.json')).sort();
  if(!captureFiles.length)throw new Error('CAR-1 candidate capture directory is empty');
  const captureArtifacts=captureFiles.map(name=>{
    const loaded=load(path.join(captureDir,name));
    return {artifact:loaded.json,artifactSha256:loaded.sha256,artifactPath:name};
  });

  const checkpointFiles=fs.readdirSync(checkpointDir).filter(name=>name.endsWith('.json')).sort();
  if(!checkpointFiles.length)throw new Error('CAR-1 candidate checkpoint directory is empty');
  const checkpointsBySession={};
  for(const name of checkpointFiles){
    const checkpoint=load(path.join(checkpointDir,name)).json;
    const sessionDate=String(checkpoint?.identities?.sessionDate??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`CAR-1 candidate checkpoint session identity invalid: ${name}`);
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

  const payload={
    schemaVersion:1,
    phase:'57.car1.validation-candidate-metadata-cli',
    status:'CAR1_METADATA_ONLY_VALIDATION_GATE_READY',
    createdAt:new Date().toISOString(),
    inputs:{
      historyPackSha256:history.sha256,
      integrityLedgerSha256:integrity.sha256,
      lineageManifestSha256:lineage.sha256,
      sourceEvaluationSha256:sourceEvaluation.sha256,
      developmentArtifactSha256:developmentArtifact.sha256,
      captureArtifactCount:captureArtifacts.length,
      checkpointArtifactCount:checkpointFiles.length,
    },
    developmentLock:Object.freeze({
      status:developmentLock.status,
      protocolId:developmentLock.validationPlan.protocolId,
      configurationSha256:developmentLock.configurationSha256,
      developmentEvidenceSha256:developmentLock.developmentEvidenceSha256,
      lineageManifestHeadSha256:developmentLock.developmentEvidence.lineageManifestHeadSha256,
      lockedBeforeValidationOutcomes:developmentLock.lockedBeforeValidationOutcomes,
    }),
    candidateMetadata,
    gate,
    methodology:{
      cumulativeChallengerReplayExecuted:false,
      cumulativeChallengerPerformanceMaterialized:false,
      selectedSessionReplayRequiredForPerformance:true,
      parameterSearchAllowed:false,
      winnerSelectionAllowed:false,
      promotionEligible:false,
      retrospectiveBackfillAllowed:false,
    },
    safety:PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY,
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
    selectedSessionDates:gate.selectedSessionDates,
    candidateLineageManifestHeadSha256:candidateMetadata.lineageManifestHeadSha256,
    configurationSha256:gate.configurationSha256,
    cumulativeChallengerPerformanceMaterialized:false,
    performanceExtractionAllowed:false,
    safety:PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({
    status:'BLOCKED_CAR1_METADATA_ONLY_VALIDATION_GATE',
    error:String(error?.message??error),
    safety:PHASE57_CAR1_VALIDATION_CANDIDATE_SAFETY,
  },null,2));
  process.exit(1);
}
