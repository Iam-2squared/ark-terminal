import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  LaneCFixedCheckpointRunnerInternals,
  PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
  runLaneCFixedCheckpointedPortfolio,
} from '../predict/portfolio/phase57-p25-lane-c-fixed-checkpoint-runner.js';

const arg=(name,fallback=null)=>{const index=process.argv.indexOf(name);return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;};
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const load=file=>{const bytes=fs.readFileSync(file);return {bytes,sha256:sha(bytes),json:JSON.parse(bytes.toString('utf8'))};};

const historyPath=arg('--history-pack');
const captureDir=arg('--capture-dir');
const integrityPath=arg('--integrity-ledger');
const lineagePath=arg('--lineage-manifest');
const checkpointDir=arg('--checkpoint-dir');
const sourceEvaluationPath=arg('--source-evaluation');
const outputPath=arg('--output','data/p25-lane-c-fixed-portfolio.json');
if(!historyPath||!captureDir||!integrityPath||!lineagePath||!checkpointDir||!sourceEvaluationPath){
  console.error('usage: node scripts/run_p25_lane_c_fixed_portfolio.mjs --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> --checkpoint-dir <dir> --source-evaluation <json> [--output <json>]');
  process.exit(2);
}

try{
  const history=load(historyPath),integrity=load(integrityPath),lineage=load(lineagePath),sourceEvaluation=load(sourceEvaluationPath);
  const captureFiles=fs.readdirSync(captureDir).filter(name=>name.endsWith('.json')).sort();
  const captures=captureFiles.map(name=>{
    const loaded=load(path.join(captureDir,name));
    return {artifact:loaded.json,artifactSha256:loaded.sha256,artifactPath:name};
  });
  const checkpointFiles=fs.readdirSync(checkpointDir).filter(name=>name.endsWith('.json')).sort();
  const checkpointsBySession={};
  for(const name of checkpointFiles){
    const checkpoint=load(path.join(checkpointDir,name)).json;
    const sessionDate=String(checkpoint?.identities?.sessionDate??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`checkpoint session identity invalid: ${name}`);
    (checkpointsBySession[sessionDate]??=[]).push(checkpoint);
  }

  const result=runLaneCFixedCheckpointedPortfolio({
    historyPack:history.json,
    captureArtifacts:captures,
    sessionIntegrityLedger:integrity.json,
    lineageManifest:lineage.json,
    checkpointsBySession,
    sourceEvaluationArtifact:sourceEvaluation.json,
  });
  const resultCanonicalSha256=LaneCFixedCheckpointRunnerInternals.canonicalSha256(result);
  const payload={
    schemaVersion:1,
    phase:'57.p25.lane-c.fixed-checkpoint-portfolio-cli',
    status:'LANE_C_FIXED_CHECKPOINTED_PORTFOLIO_ARTIFACT_WRITTEN',
    createdAt:new Date().toISOString(),
    inputs:{
      historyPack:path.normalize(historyPath),historyPackSha256:history.sha256,
      integrityLedger:path.normalize(integrityPath),integrityLedgerSha256:integrity.sha256,
      lineageManifest:path.normalize(lineagePath),lineageManifestSha256:lineage.sha256,
      sourceEvaluation:path.normalize(sourceEvaluationPath),sourceEvaluationSha256:sourceEvaluation.sha256,
      captureArtifactCount:captures.length,checkpointArtifactCount:checkpointFiles.length,
    },
    resultCanonicalSha256,
    result,
    methodology:{
      formalP25EvaluationReconciledBeforeSimulation:true,
      sameFrozenEntry:true,
      fixedHorizonExitUnchanged:true,
      allFiveUniverseVariantsRetained:true,
      currentExistingReferenceOnly:true,
      max10AssumedEquivalentToCurrent:false,
      dynamicManagementArtifactUsed:false,
      winnerSelectionAllowed:false,
      freshHoldoutConsumed:false,
    },
    safety:PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const temporaryPath=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(temporaryPath,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(temporaryPath,outputPath);
  console.log(JSON.stringify({
    status:payload.status,
    output:outputPath,
    outputSha256:sha(fs.readFileSync(outputPath)),
    resultCanonicalSha256,
    lineageManifestHeadSha256:result.lineageManifestHeadSha256,
    readySessionCount:result.inputAudit.readySessionCount,
    frozenTradeCount:result.inputAudit.frozenTradeCount,
    resolvedTradeCount:result.inputAudit.resolvedTradeCount,
    unresolvedTradeCount:result.inputAudit.unresolvedTradeCount,
    universeVariantOrder:result.universeVariantOrder,
    profileOrder:result.profileOrder,
    safety:PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({
    status:'BLOCKED_LANE_C_FIXED_CHECKPOINTED_PORTFOLIO',
    error:String(error?.message??error),
    safety:PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
  },null,2));
  process.exit(1);
}
