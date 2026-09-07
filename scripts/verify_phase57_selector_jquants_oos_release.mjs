import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const ROOT=new URL('../predict/research/',import.meta.url);
const allocationUrl=new URL('phase57-selector-jquants-fresh120-allocation.json',ROOT);
const allocationBytes=fs.readFileSync(allocationUrl);
const allocation=JSON.parse(allocationBytes.toString('utf8'));
const release=JSON.parse(fs.readFileSync(new URL('phase57-selector-minimal-hybrid-oos-release.json',ROOT),'utf8'));
const model=JSON.parse(fs.readFileSync(new URL('phase57-selector-minimal-hybrid-development-model.json',ROOT),'utf8'));
const freeze=JSON.parse(fs.readFileSync(new URL('phase57-selector-minimal-hybrid-development-freeze.json',ROOT),'utf8'));
const manifest=JSON.parse(fs.readFileSync(new URL('phase57-selector-jquants-fresh120-dataset-manifest.json',ROOT),'utf8'));
const validation=JSON.parse(fs.readFileSync(new URL('phase57-selector-minimal-hybrid-fresh-validation.json',ROOT),'utf8'));
const sha256=value=>createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');

function findFiles(root,name){
  const found=[];
  for(const entry of fs.readdirSync(root,{withFileTypes:true})){
    const target=path.join(root,entry.name);
    if(entry.isDirectory())found.push(...findFiles(target,name));else if(entry.name===name)found.push(target);
  }
  return found.sort();
}

function invariant(condition,message){if(!condition)throw new Error(message);}
function allFalse(value){return value&&Object.values(value).every(flag=>flag===false);}

export function verifyOosRelease({inputRoot}={}){
  invariant(release.status==='UNTOUCHED_OOS_RELEASE_AUTHORIZED','OOS release is not authorized');
  invariant(release.datasetId===allocation.datasetId&&manifest.datasetId===allocation.datasetId,'dataset identity drift');
  invariant(allocation.status==='FRESH_120_ALLOCATION_FROZEN','Fresh allocation is not frozen');
  const computedAllocationSha256=createHash('sha256').update(allocationBytes).digest('hex');
  invariant(release.expectedAllocationSha256===computedAllocationSha256,'allocation digest drift');

  const modelCore={...model};delete modelCore.modelDigest;
  const computedModelDigest=sha256(modelCore);
  invariant(computedModelDigest===model.modelDigest,'model digest recomputation failed');
  invariant(model.modelDigest===release.expectedModelDigest,'model digest differs from OOS authorization');
  invariant(model.modelFamily==='TWO_INDEPENDENT_RIDGE_REGRESSIONS','model family changed');
  invariant(model.ridgeLambda===0.01&&model.featureNames.length<=12,'frozen model hyperparameters changed');
  invariant(model.guards?.upDownTargetsSeparated===true&&model.guards?.twoSidedDirectTrainingTarget===false,'target contract changed');
  invariant(model.guards?.directExtensionCoefficientAllowed===false&&model.guards?.v3MembershipOrThresholdUsed===false,'architecture guard changed');

  const freezeCore={...freeze};delete freezeCore.freezeSha256;
  const computedFreezeSha256=sha256(freezeCore);
  invariant(computedFreezeSha256===freeze.freezeSha256,'Hybrid Freeze digest recomputation failed');
  invariant(freeze.freezeSha256===release.expectedHybridFreezeSha256,'Hybrid Freeze differs from OOS authorization');
  invariant(freeze.modelDigest===model.modelDigest,'Freeze/model mismatch');
  invariant(JSON.stringify(freeze.featureManifest)===JSON.stringify(model.featureNames),'feature manifest changed');
  invariant(freeze.targetContract?.horizonBars===3&&freeze.targetContract?.upDownSeparated===true,'training target/horizon changed');
  invariant(freeze.ridgeLambda===model.ridgeLambda,'Ridge lambda changed');
  invariant(freeze.softAdjustment===model.selectionPolicy.maximumAbsoluteSoftAdjustment,'soft adjustment changed');
  invariant(freeze.dynamicN?.maximumSelected===model.selectionPolicy.maximumSelected,'Dynamic N changed');
  invariant(freeze.dynamicN?.minimumRemainingOpportunityScore===model.selectionPolicy.minimumRemainingOpportunityScore,'ABSTAIN quality changed');
  invariant(freeze.validationRetuningAllowed===false&&freeze.automaticPromotionAllowed===false,'freeze promotion/retuning guard changed');

  invariant(validation.validationEvidenceSha256===release.expectedValidationEvidenceSha256,'Validation evidence drift');
  invariant(validation.freezeIntegrity?.validationRetuningPerformed===false,'Validation retuning detected');
  invariant(JSON.stringify(validation.freezeIntegrity?.hybridModelDigests)===JSON.stringify([model.modelDigest]),'Validation model mismatch');
  invariant(JSON.stringify(validation.freezeIntegrity?.hybridFreezeShas)===JSON.stringify([freeze.freezeSha256]),'Validation Freeze mismatch');
  invariant(validation.release?.untouchedOosReleased===false&&validation.release?.untouchedOosPayloadRequested===false,'OOS was already released by Validation');

  const folds=[allocation.development,allocation.purgeDevelopmentValidation,allocation.validation,allocation.purgeValidationOos,allocation.untouchedOos];
  const all=folds.flat();
  invariant(all.length===122&&new Set(all).size===122,'allocation sessions are not atomic and unique');
  invariant(allocation.development.length===72&&allocation.validation.length===24&&allocation.untouchedOos.length===24,'72/24/24 split changed');
  invariant(allocation.purgeDevelopmentValidation.length===1&&allocation.purgeValidationOos.length===1,'whole-session purge changed');
  invariant(allocation.untouchedOos.every(date=>date>allocation.purgeValidationOos[0]),'OOS chronology changed');
  invariant(all.every(date=>date<'2026-06-12'||date>'2026-09-04'),'consumed 2026 period entered allocation');

  const auditFiles=findFiles(inputRoot,'audit.json');
  invariant(auditFiles.length===6,`expected 6 immutable acquisition audits, received ${auditFiles.length}`);
  const shardReports=auditFiles.map(file=>JSON.parse(fs.readFileSync(file,'utf8')));
  invariant(shardReports.every(row=>row.status==='FRESH_SHARD_ACQUISITION_PASS'),'source acquisition shard failed');
  invariant(shardReports.every(row=>row.untouchedOosFeaturesGenerated===false&&row.untouchedOosLabelsGenerated===false&&row.untouchedOosScoresGenerated===false),'OOS research payload existed before release');
  invariant(shardReports.every(row=>row.rawPersisted===false&&row.secretPersisted===false&&allFalse(row.safety)),'source audit safety/storage drift');
  const audits=shardReports.flatMap(row=>row.sessionAudits).sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
  invariant(audits.length===122&&new Set(audits.map(row=>row.sessionDate)).size===122,'source session audits are incomplete');
  invariant(audits.map(row=>row.sessionDate).join('|')===all.slice().sort().join('|'),'source audits do not match frozen allocation');
  invariant(sha256(audits.map(row=>`${row.sessionDate}|${row.minuteSha256}`).join('\n'))===manifest.rawSourceSha256,'dataset ancestry digest changed');
  const byDate=new Map(audits.map(row=>[row.sessionDate,row]));
  const oosAudits=allocation.untouchedOos.map(date=>byDate.get(date));
  invariant(oosAudits.every(Boolean),'OOS structural audit missing');
  invariant(oosAudits.every(row=>row.fold==='UNTOUCHED_OOS'&&row.status==='SESSION_STRUCTURAL_AUDIT_PASS'),'OOS fold/audit status changed');
  invariant(oosAudits.every(row=>row.featureCalculationPerformed===false&&row.labelGenerationPerformed===false&&row.outcomeInspectionPerformed===false&&row.researchPayloadReleased===false),'OOS was accessed before release');
  invariant(oosAudits.every(row=>row.rawPersisted===false&&row.secretPersisted===false&&allFalse(row.safety)),'OOS source audit safety/storage drift');

  const compact=oosAudits.map(row=>({sessionDate:row.sessionDate,fold:row.fold,status:row.status,minuteSha256:row.minuteSha256,
    fiveMinuteSha256:row.fiveMinuteSha256,memberSetSha256:row.memberSetSha256,rawMinuteRows:row.rawMinuteRows,
    fiveMinuteBars:row.fiveMinuteBars,eligibleJpxSymbolCount:row.eligibleJpxSymbolCount}));
  const core={schemaVersion:1,phase:'57.selector-minimal-hybrid.untouched-oos-integrity-gate',status:'UNTOUCHED_OOS_INTEGRITY_PASS',
    datasetId:allocation.datasetId,sourceAcquisitionRunId:release.sourceAcquisitionRunId,allocationSha256:computedAllocationSha256,
    computedModelDigest,computedFreezeSha256,validationEvidenceSha256:validation.validationEvidenceSha256,oosSessionCount:compact.length,
    oosFeaturesPreviouslyGenerated:false,oosLabelsPreviouslyGenerated:false,oosScoresPreviouslyGenerated:false,oosOutcomesPreviouslyInspected:false,
    reserveAccessAllowed:false,reserveSessionsTouched:0,validationRetuningAllowed:false,modelMutationAllowed:false,
    safety:release.safety};
  return {gate:{...core,gateSha256:sha256(core)},oosAudits:compact,model,freeze};
}

async function main(){
  const result=verifyOosRelease({inputRoot:process.env.INPUT_ROOT||'artifacts/phase57-oos-integrity-input'});
  const directory='artifacts/phase57-jquants-oos-integrity';fs.mkdirSync(directory,{recursive:true,mode:0o700});
  for(const [name,value] of Object.entries(result)){
    const bytes=JSON.stringify(value,null,2)+'\n';fs.writeFileSync(`${directory}/${name}.json`,bytes,{mode:0o600});
    fs.writeFileSync(`${directory}/${name}.sha256`,`${sha256(bytes)}  ${name}.json\n`,{mode:0o600});
  }
  console.log('PHASE57_OOS_INTEGRITY_REPORT '+JSON.stringify({status:result.gate.status,oosSessionCount:result.gate.oosSessionCount,
    modelDigest:result.gate.computedModelDigest,hybridFreezeSha256:result.gate.computedFreezeSha256,gateSha256:result.gate.gateSha256,
    oosPreviouslyUnaccessed:true,reserveSessionsTouched:0,safety:result.gate.safety}));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(`PHASE57_OOS_INTEGRITY_FAIL ${String(error?.message??error)}`);process.exitCode=1;});

export const Phase57OosIntegrityInternals=Object.freeze({findFiles});
