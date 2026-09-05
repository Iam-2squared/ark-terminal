import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  PHASE57_CAR1_CHECKPOINT_SAFETY,
  runCar1CheckpointedSizingAttribution,
} from '../predict/portfolio/phase57-car1-checkpoint-runner.js';

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
const outputPath=arg('--output','data/phase57-car1-sizing-attribution.json');

if(!historyPath||!captureDir||!integrityPath||!lineagePath||!checkpointDir||!sourceEvaluationPath){
  console.error('usage: node scripts/run_phase57_car1_checkpointed_sizing.mjs --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> --checkpoint-dir <dir> --source-evaluation <json> [--output <json>]');
  process.exit(2);
}

try{
  const history=load(historyPath);
  const integrity=load(integrityPath);
  const lineage=load(lineagePath);
  const sourceEvaluation=load(sourceEvaluationPath);

  const captureFiles=fs.readdirSync(captureDir).filter(name=>name.endsWith('.json')).sort();
  if(!captureFiles.length)throw new Error('CAR-1 capture directory is empty');
  const captureArtifacts=captureFiles.map(name=>{
    const loaded=load(path.join(captureDir,name));
    return {artifact:loaded.json,artifactSha256:loaded.sha256,artifactPath:name};
  });

  const checkpointFiles=fs.readdirSync(checkpointDir).filter(name=>name.endsWith('.json')).sort();
  if(!checkpointFiles.length)throw new Error('CAR-1 checkpoint directory is empty');
  const checkpointsBySession={};
  for(const name of checkpointFiles){
    const checkpoint=load(path.join(checkpointDir,name)).json;
    const sessionDate=String(checkpoint?.identities?.sessionDate??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`CAR-1 checkpoint session identity invalid: ${name}`);
    (checkpointsBySession[sessionDate]??=[]).push(checkpoint);
  }

  const result=runCar1CheckpointedSizingAttribution({
    historyPack:history.json,
    captureArtifacts,
    sessionIntegrityLedger:integrity.json,
    lineageManifest:lineage.json,
    checkpointsBySession,
    sourceEvaluationArtifact:sourceEvaluation.json,
  });

  const payload={
    schemaVersion:1,
    phase:'57.car1.checkpointed-sizing-attribution-cli',
    status:'CAR1_CHECKPOINTED_PAIRED_SIZING_ARTIFACT_WRITTEN',
    createdAt:new Date().toISOString(),
    inputs:{
      historyPack:path.normalize(historyPath),historyPackSha256:history.sha256,
      integrityLedger:path.normalize(integrityPath),integrityLedgerSha256:integrity.sha256,
      lineageManifest:path.normalize(lineagePath),lineageManifestSha256:lineage.sha256,
      sourceEvaluation:path.normalize(sourceEvaluationPath),sourceEvaluationSha256:sourceEvaluation.sha256,
      captureArtifactCount:captureArtifacts.length,
      checkpointArtifactCount:checkpointFiles.length,
    },
    result,
    methodology:{
      developmentEvidenceOnly:true,
      sameFrozenEntry:true,
      sameEntryPrice:true,
      sameDirection:true,
      sameFrozenExit:true,
      sameCostAssumption:true,
      sameCandidatePriority:true,
      baselineBudgetEnvelopeAnchored:true,
      parameterSearchAllowed:false,
      winnerSelectionAllowed:false,
      promotionEligible:false,
      formalOos:false,
      incompleteProspectiveBackfillAllowed:false,
    },
    safety:PHASE57_CAR1_CHECKPOINT_SAFETY,
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
    lineageManifestHeadSha256:result.lineageManifestHeadSha256,
    readySessionCount:result.inputAudit.readySessionCount,
    frozenTradeCount:result.inputAudit.frozenTradeCount,
    resolvedTradeCount:result.inputAudit.resolvedTradeCount,
    unresolvedTradeCount:result.inputAudit.unresolvedTradeCount,
    universeVariantOrder:result.universeVariantOrder,
    baselineProfileOrder:result.baselineProfileOrder,
    sizingProfileOrder:result.sizingProfileOrder,
    matrixRows:result.matrixRows,
    safety:PHASE57_CAR1_CHECKPOINT_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({
    status:'BLOCKED_CAR1_CHECKPOINTED_PAIRED_SIZING',
    error:String(error?.message??error),
    safety:PHASE57_CAR1_CHECKPOINT_SAFETY,
  },null,2));
  process.exit(1);
}
