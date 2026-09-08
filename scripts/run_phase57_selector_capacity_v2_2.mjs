import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {FEATURES,SAFETY,MODEL_DIGEST,loadCheckpoints,auditRows,hash,check,finite,mean,sessionMean,writeReport} from './capacity_v22_checkpoint.mjs';

export const PRECOMMIT_SHA='6750071042aa595c1f143e02a6f6e3dc83d4e220c42d45480106a14b1c985323';
const specBytes=fs.readFileSync(new URL('../predict/research/phase57-selector-capacity-v2-2-precommit.json',import.meta.url));
check(hash(specBytes)===PRECOMMIT_SHA,'V22_PRECOMMIT_HASH_MISMATCH');
export const SPEC=JSON.parse(specBytes);
const KS=SPEC.target.prefixes;
const READY='READY_FOR_FRESH_VALIDATION',NO_GO='CAPACITY_V2_2_DEVELOPMENT_NO_GO';

export function targetRows(rows) {
  return rows.map(r=>({...r,relativeTargets:Object.fromEntries(KS.map(k=>[k,
    r.frozenSelectedCount>0&&finite(r.frozenSelectedUtility)&&finite(r.utilityByCapacity[k])
      ?r.utilityByCapacity[k]-r.frozenSelectedUtility:null]))}));
}
function solve(matrix,vector) {
  const a=matrix.map((r,i)=>[...r,vector[i]]),n=vector.length;
  for(let col=0;col<n;col++) {
    let pivot=col;for(let r=col+1;r<n;r++)if(Math.abs(a[r][col])>Math.abs(a[pivot][col]))pivot=r;
    check(Math.abs(a[pivot][col])>=1e-12,'V22_SINGULAR_RIDGE');
    [a[col],a[pivot]]=[a[pivot],a[col]];const d=a[col][col];
    for(let j=col;j<=n;j++)a[col][j]/=d;
    for(let r=0;r<n;r++)if(r!==col){const m=a[r][col];for(let j=col;j<=n;j++)a[r][j]-=m*a[col][j];}
  }
  const result=a.map(r=>r[n]);check(result.every(finite),'V22_NONFINITE_COEFFICIENT');return result;
}
export function scalePast(rows) {
  const usable=rows.filter(r=>FEATURES.every(k=>finite(r.features[k])));
  check(usable.length>0,'V22_INSUFFICIENT_SCALE_ROWS');
  const centers=FEATURES.map(k=>mean(usable.map(r=>r.features[k])));
  const scales=FEATURES.map((k,i)=>Math.sqrt(mean(usable.map(r=>(r.features[k]-centers[i])**2)))||1);
  return {centers,scales};
}
export function fitPast(rows,k,lambda) {
  const scale=scalePast(rows);
  const usable=rows.filter(r=>FEATURES.every(f=>finite(r.features[f]))&&finite(r.relativeTargets[k]));
  check(usable.length>=SPEC.fit.minimumTargetRows,'V22_INSUFFICIENT_TARGET_ROWS');
  const p=FEATURES.length+1,xx=Array.from({length:p},()=>Array(p).fill(0)),xy=Array(p).fill(0);
  for(const r of usable) {
    const x=[1,...FEATURES.map((f,i)=>(r.features[f]-scale.centers[i])/scale.scales[i])];
    for(let i=0;i<p;i++){xy[i]+=x[i]*r.relativeTargets[k];for(let j=0;j<p;j++)xx[i][j]+=x[i]*x[j];}
  }
  for(let i=1;i<p;i++)xx[i][i]+=lambda;
  return {coefficients:solve(xx,xy),...scale,lambda,targetK:k,sampleCount:usable.length,
    firstTrainSession:rows[0].sessionDate,lastTrainSession:rows.at(-1).sessionDate};
}
export function predict(model,features) {
  if(!FEATURES.every(k=>finite(features[k])))return null;
  return model.coefficients[0]+FEATURES.reduce((v,k,i)=>v+model.coefficients[i+1]*(features[k]-model.centers[i])/model.scales[i],0);
}
function datesOf(rows){return [...new Set(rows.map(r=>r.sessionDate))].sort();}
function rowsBetween(rows,dates,first,last){const allowed=new Set(dates.slice(first-1,last));return rows.filter(r=>allowed.has(r.sessionDate));}
export function chooseLambdaPast(pastRows,k) {
  const dates=datesOf(pastRows),folds=SPEC.cv.innerBlocks.filter(b=>b.testEnd<=dates.length);
  check(folds.length>=2,'V22_INSUFFICIENT_INNER_FOLDS');
  const candidates=[];
  for(const lambda of SPEC.cv.lambdaCandidates) {
    const errors=[],ancestry=[];
    for(const f of folds) {
      const train=rowsBetween(pastRows,dates,1,f.trainEnd),test=rowsBetween(pastRows,dates,f.testStart,f.testEnd);
      check(train.at(-1).sessionDate<test[0].sessionDate,'V22_INNER_FUTURE_LEAKAGE');
      const model=fitPast(train,k,lambda);
      ancestry.push({trainEnd:model.lastTrainSession,testStart:test[0].sessionDate,testEnd:test.at(-1).sessionDate});
      for(const r of test) {
        const p=predict(model,r.features),y=r.relativeTargets[k];
        if(finite(p)&&finite(y))errors.push({sessionDate:r.sessionDate,error:Math.abs(p-y)});
      }
    }
    check(errors.length>0,'V22_INSUFFICIENT_INNER_LABELS');
    candidates.push({lambda,mae:sessionMean(errors,r=>r.error),n:errors.length,ancestry});
  }
  candidates.sort((a,b)=>a.mae-b.mae||a.lambda-b.lambda);
  return {...candidates[0],candidates};
}
export function fitBundlePast(pastRows) {
  const models={},choices={};
  for(const k of KS) {
    choices[k]=chooseLambdaPast(pastRows,k);
    models[k]=fitPast(pastRows,k,choices[k].lambda);
  }
  return {models,choices,features:FEATURES,modelFamily:SPEC.target.modelFamily,
    sourceHybridModelDigest:MODEL_DIGEST,mapping:SPEC.mapping,lastTrainSession:pastRows.at(-1).sessionDate};
}
export function mapPredictions({frozenSelectedCount,rankedCount},predictions) {
  if(frozenSelectedCount===0||rankedCount<5)return 0;
  const feasible=KS.filter(k=>k<=rankedCount&&finite(predictions[k])&&predictions[k]>=SPEC.mapping.predictedUtilityDifferenceFloorBps);
  return feasible.length?Math.max(...feasible):5;
}
export function infer(bundle,input) {
  check(JSON.stringify(Object.keys(input).sort())===JSON.stringify(['features','frozenSelectedCount','rankedCount'].sort()),'V22_INFERENCE_INPUT_WHITELIST');
  check(JSON.stringify(Object.keys(input.features).sort())===JSON.stringify([...FEATURES].sort()),'V22_INFERENCE_FEATURE_WHITELIST');
  const predictions=Object.fromEntries(KS.map(k=>[k,predict(bundle.models[k],input.features)]));
  const action=FEATURES.every(k=>finite(input.features[k]))?mapPredictions(input,predictions):0;
  return {action,predictions};
}
export function applyFrozenPrefix(hybrid,action) {
  check(hybrid.modelDigest===MODEL_DIGEST,'V22_FROZEN_MODEL_MISMATCH');
  check(SPEC.scope.actions.includes(action),'V22_ACTION_INVALID');
  check(hybrid.selected.length>0||action===0,'V22_ABSTAIN_VIOLATION');
  check(hybrid.ranked.every((r,i)=>r.hybridRank===i+1),'V22_RANK_IDENTITY');
  const selected=hybrid.ranked.slice(0,action);
  check(selected.every((r,i)=>r===hybrid.ranked[i]),'V22_PREFIX_IDENTITY');return selected;
}
export function metrics(rows) {
  const paired=rows.filter(r=>r.frozenSelectedCount>0&&finite(r.frozenSelectedUtility)&&KS.every(k=>finite(r.utilityByCapacity[k])));
  const evaluable=paired.filter(r=>r.action>0&&finite(r.utilityByCapacity[r.action]));
  const baselineUtility=sessionMean(evaluable,r=>r.frozenSelectedUtility),utility=sessionMean(evaluable,r=>r.utilityByCapacity[r.action]);
  const baselineCount=mean(rows.map(r=>r.frozenSelectedCount)),count=mean(rows.map(r=>Math.min(r.action,r.rankedCount)));
  let jumps=0;for(let i=1;i<rows.length;i++)if(Math.abs(rows[i].action-rows[i-1].action)>5)jumps++;
  return {sessionCount:datesOf(rows).length,decisionCount:rows.length,pairedDecisionCount:paired.length,evaluatedDecisionCount:evaluable.length,
    pairedCoverage:paired.length/Math.max(1,rows.filter(r=>r.frozenSelectedCount>0).length),
    activeAbstainCount:rows.filter(r=>r.frozenSelectedCount>0&&r.action===0).length,
    baselineUtility,utility,utilityDifference:finite(utility)&&finite(baselineUtility)?utility-baselineUtility:null,
    baselineCount,count,countRatio:count/baselineCount,absoluteIncrease:count-baselineCount,
    jumpRate:rows.length>1?jumps/(rows.length-1):0,
    actionDistribution:Object.fromEntries(SPEC.scope.actions.map(k=>[k,rows.filter(r=>r.action===k).length]))};
}
export function developmentGate(global,blocks,guards) {
  const g=SPEC.gates;
  const gates={utility:finite(global.utilityDifference)&&global.utilityDifference>=g.globalUtilityDifferenceMinimumBps,
    relativeCount:finite(global.countRatio)&&global.countRatio>=g.meanCandidateCountMinimumRatio,
    absoluteCount:finite(global.absoluteIncrease)&&global.absoluteIncrease>=g.meanCandidateCountMinimumAbsoluteIncrease,
    stability:finite(global.jumpRate)&&global.jumpRate<=g.maximumAdjacentJumpGreaterThanFiveRate,
    everyBlock:blocks.length===3&&blocks.every(b=>finite(b.utilityDifference)&&b.utilityDifference>=g.minimumEveryOuterBlockUtilityDifferenceBps),
    coverage:global.pairedCoverage>=g.minimumPairedTargetCoverage&&blocks.every(b=>b.pairedCoverage>=g.minimumPairedTargetCoverage),
    noActiveAbstention:global.activeAbstainCount===0,
    prefix:guards.prefixMatch===1,leakage:guards.leakageViolations===0,features:guards.missingFeatures===0};
  return {pass:Object.values(gates).every(Boolean),gates,failed:Object.keys(gates).filter(k=>!gates[k])};
}
export function evaluateDevelopment(rawRows,{onBlock}={}) {
  const rows=targetRows([...rawRows].sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff))),dates=datesOf(rows);
  check(dates.length===89&&rows.length===1780,'V22_DEVELOPMENT_IDENTITY');
  const predictions=[],blocks=[],bundles=[];let leakageViolations=0;
  for(const [i,f] of SPEC.cv.outerBlocks.entries()) {
    // Deliberately pass only past records into fitting/hyperparameter selection.
    const past=rowsBetween(rows,dates,1,f.trainEnd),held=rowsBetween(rows,dates,f.testStart,f.testEnd),bundle=fitBundlePast(past);
    check(bundle.lastTrainSession<held[0].sessionDate,'V22_OUTER_FUTURE_LEAKAGE');
    const lastInner=[...Object.values(bundle.choices)].flatMap(c=>c.ancestry.map(a=>a.testEnd)).sort().at(-1);
    if(lastInner>=held[0].sessionDate)leakageViolations++;
    const predicted=held.map(r=>{
      const decision=infer(bundle,{features:r.features,frozenSelectedCount:r.frozenSelectedCount,rankedCount:r.rankedCount});
      check(SPEC.scope.actions.includes(decision.action),'V22_ACTION_INVALID');
      return {...r,...decision,block:i+1};
    });
    const block={block:i+1,trainStart:past[0].sessionDate,trainEnd:bundle.lastTrainSession,testStart:held[0].sessionDate,testEnd:held.at(-1).sessionDate,
      ...metrics(predicted),lambdaByK:Object.fromEntries(KS.map(k=>[k,bundle.choices[k].lambda])),lastLambdaOutcomeSession:lastInner};
    blocks.push(block);predictions.push(...predicted);bundles.push(bundle);onBlock?.(block,bundle);
  }
  check(predictions.length===880,'V22_OUTER_DECISION_COUNT');
  const global=metrics(predictions),guards={
    prefixMatch:predictions.every(r=>SPEC.scope.actions.includes(r.action)&&r.action<=r.rankedCount&&r.prefixIdentity===true)?1:0,
    prefixEvidence:'FROZEN_PREFIX_INDEX_CONSTRUCTION_AND_ADAPTER_TESTS; source cached flag retained; no symbol-level historical replay',
    leakageViolations,missingFeatures:rows.filter(r=>FEATURES.some(k=>!finite(r.features[k]))).length,
    futureFoldLambdaLeakageRemoved:true,thresholdSearchPerformed:false,architectureUsesPreviouslyOpenedDevelopment:true};
  const gate=developmentGate(global,blocks,guards);
  const classification=[];
  if(!gate.gates.utility)classification.push('utility dilution');
  if(!gate.gates.relativeCount||!gate.gates.absoluteCount)classification.push('capacity mapping failure');
  if(!gate.gates.everyBlock)classification.push('forward-CV instability');
  if(!gate.gates.stability)classification.push('capacity mapping instability');
  if(!gate.gates.coverage)classification.push('insufficient target coverage');
  const errorByK=Object.fromEntries(KS.map(k=>[k,sessionMean(predictions.filter(r=>finite(r.relativeTargets[k])&&finite(r.predictions[k])),r=>Math.abs(r.predictions[k]-r.relativeTargets[k]))]));
  return {status:gate.pass?READY:NO_GO,global,blocks,guards,gate,classification,predictionMaeBpsByK:errorByK,
    causalAttribution:'Failure categories describe observed gate symptoms, not proven causal attribution to target vs signal vs regime.',
    worstForwardHeldOutDifference:Math.min(...blocks.map(b=>b.utilityDifference??-Infinity)),
    model:gate.pass?fitBundlePast(rows):null,
    developmentDecisions:predictions.map(r=>({sessionDate:r.sessionDate,featureCutoff:r.featureCutoff,block:r.block,action:r.action,predictions:r.predictions})),
    blockModels:bundles};
}
export function finalArtifact(result,ancestry) {
  check((result.gate.pass && result.status===READY && result.model!==null)||(!result.gate.pass&&result.status===NO_GO&&result.model===null),'V22_GATE_MODEL_PARITY');
  const core={schemaVersion:1,version:'CAPACITY_V2_2',status:result.status,precommitSha256:PRECOMMIT_SHA,ancestry,
    precommitCommit:'7107e89e6cbb74967598540d77c2d10e9d10213d',codeHeadSha:process.env.GITHUB_SHA??null,
    trainerSha256:hash(fs.readFileSync(fileURLToPath(import.meta.url))),
    global:result.global,blocks:result.blocks,guards:result.guards,gate:result.gate,classification:result.classification,
    predictionMaeBpsByK:result.predictionMaeBpsByK,causalAttribution:result.causalAttribution,
    worstForwardHeldOutDifference:result.worstForwardHeldOutDifference,
    model:result.model,validationReleased:false,untouchedOosReleased:false,reserveReleased:false,newFreshSessionsConsumed:0,
    baselineContract:SPEC.utility.baseline,metricLimitations:SPEC.utility.limitations,
    freezeCreated:result.gate.pass,safety:SAFETY};
  return {...core,resultDigest:hash(JSON.stringify(core))};
}
function main() {
  check(process.argv[2]==='development-only','V22_ONLY_DEVELOPMENT_ALLOWED');
  const {rows,ancestry}=loadCheckpoints();
  check(ancestry.allocationSha256===SPEC.source.allocationSha256,'V22_ALLOCATION_PIN');
  check(ancestry.shards.every(s=>SPEC.source.shards.some(p=>p.shardIndex===s.shardIndex&&p.sha256===s.sha256)),'V22_SHARD_PIN');
  const out='artifacts/capacity-v22-development';
  const audit=auditRows(rows);writeReport(out,'semantics-audit.json',audit);
  let result;
  try {
    result=evaluateDevelopment(rows,{onBlock:(block,bundle)=>{
      writeReport(out,'block-'+block.block+'.json',{block,bundle,precommitSha256:PRECOMMIT_SHA,ancestry});
      console.log('V22_BLOCK_JSON '+JSON.stringify(block));
    }});
  } catch(error) {
    if(!String(error.message).startsWith('V22_INSUFFICIENT_'))throw error;
    const report={status:NO_GO,reason:error.message,classification:['insufficient signal'],model:null,freezeCreated:false,
      precommitSha256:PRECOMMIT_SHA,ancestry,validationReleased:false,untouchedOosReleased:false,reserveReleased:false,safety:SAFETY};
    writeReport(out,'development-no-go.json',report);console.log('V22_RESULT_JSON '+JSON.stringify(report));return;
  }
  const report=finalArtifact(result,ancestry);
  writeReport(out,'decision-predictions.json',{predictions:result.developmentDecisions,precommitSha256:PRECOMMIT_SHA});
  writeReport(out,'development-result.json',report);
  if(report.freezeCreated)writeReport(out,'freeze.json',report);
  else writeReport(out,'development-no-go.json',report);
  console.log('V22_RESULT_JSON '+JSON.stringify({...report,model:report.model?{omittedFromLog:true}:null}));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try{main();}catch(error){console.error('V22_TECHNICAL_FAILURE '+error.message);process.exitCode=1;}
}
