import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';

import {auditPhase57MinimalHybridDataset} from '../predict/daytrade/phase57-selector-minimal-hybrid-dataset-audit.js';
import {describePhase57MinimalHybridFeatures,PHASE57_MINIMAL_HYBRID_MODEL_FEATURES,predictPhase57MinimalHybridTargets,trainPhase57MinimalHybridModel} from '../predict/daytrade/phase57-selector-minimal-hybrid-model.js';

const allocation=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const SAFETY=allocation.safety;
const sha256=value=>createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');
const mean=values=>values.reduce((sum,value)=>sum+value,0)/values.length;
const clamp=(value,min=0,max=1)=>Math.min(max,Math.max(min,value));
const round8=value=>Number(Number(value).toFixed(8));

function findFiles(root,name){
  const found=[];
  for(const entry of fs.readdirSync(root,{withFileTypes:true})){
    const target=path.join(root,entry.name);
    if(entry.isDirectory())found.push(...findFiles(target,name));else if(entry.name===name)found.push(target);
  }
  return found.sort();
}

function sessions(){
  return [...allocation.development,...allocation.purgeDevelopmentValidation,...allocation.validation,...allocation.purgeValidationOos,...allocation.untouchedOos]
    .sort().map(sessionDate=>({sessionDate,crossSectionAtomic:true,decisionCutoffs:['10:00','10:05','10:10','10:15','10:20','10:25','10:30','13:30','13:35','13:40','13:45','13:50','13:55','14:00','14:05','14:10','14:15','14:20','14:25','14:30'].map(time=>new Date(`${sessionDate}T${time}:00+09:00`).toISOString())}));
}

function readInputs(root){
  const audits=findFiles(root,'audit.json').map(file=>JSON.parse(fs.readFileSync(file,'utf8')));
  if(audits.length!==6)throw new Error(`expected 6 acquisition shard audits, received ${audits.length}`);
  const sessionAudits=audits.flatMap(row=>row.sessionAudits).sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
  const samples=findFiles(root,'development-samples.ndjson.gz').flatMap(file=>{
    const text=gunzipSync(fs.readFileSync(file)).toString('utf8').trim();
    return text?text.split('\n').map(line=>JSON.parse(line)):[];
  }).sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.featureCutoff.localeCompare(b.featureCutoff)||a.v1Rank-b.v1Rank||a.symbol.localeCompare(b.symbol));
  return {audits,sessionAudits,samples};
}

function manifest(sessionAudits){
  return {datasetId:allocation.datasetId,parentDatasetIds:[],rawSourceSha256:sha256(sessionAudits.map(row=>`${row.sessionDate}|${row.minuteSha256}`).join('\n')),
    sourceProvider:'J-Quants',sourceEndpoint:'/v2/equities/bars/minute + /v2/equities/master',acquisitionMethod:'API_STRUCTURAL_AUDIT_WITH_SEALED_SPLITS',
    acquiredAt:new Date().toISOString(),reconstructionMethod:'TICK_PROVEN_SESSION_ALIGNED_SPARSE_1M_TO_5M',evidenceClassification:'EXACT_POINT_IN_TIME',
    providerEntitlementVerified:true,previouslyUsedForSelectorOutcomeInspection:false,intervalMinutes:5,barTimestampMeaning:'BAR_OPEN',availableAtRule:'BAR_OPEN_PLUS_INTERVAL',
    noTradeMinutePolicy:'MISSING_NEVER_FABRICATE',missingMicrostructurePolicy:'UNKNOWN_WITH_AVAILABILITY_MASK',microstructureZeroFilled:false,
    completeCrossSectionAtomic:true,universeStatus:'POINT_IN_TIME',strongHistoricalClaimAllowed:true,survivorshipLimitation:'NONE_PIT_MASTER_PER_SESSION',
    corporateActionHandling:'RAW_UNADJUSTED_INTRADAY_SAME_SESSION_FEATURES_AND_TARGETS',volumeSemantics:'OBSERVED_TRADED_SHARES_AGGREGATED_FROM_JQUANTS_MINUTE',
    turnoverSemantics:'OBSERVED_TRADED_VALUE_YEN_AGGREGATED_FROM_JQUANTS_MINUTE',targetLabelPolicy:'SAME_SESSION_AFTER_CUTOFF_ONLY',
    datasetAllocationPolicy:'FRESH_120_PLUS_TWO_ONE_SESSION_PURGES',validationReleased:false,untouchedOosReleased:false,safety:SAFETY};
}

function asTrainingSamples(samples,horizon,featureNames){
  return samples.map(row=>({sessionDate:row.sessionDate,features:Object.fromEntries(featureNames.map(name=>[name,row.features[name]])),targets:{
    upExcursion:row.targetsByHorizon[horizon].upExcursion,downExcursion:row.targetsByHorizon[horizon].downExcursion,twoSidedOpportunityUsedAsTrainingTarget:false}}));
}

function featureAssociation(samples,name){
  const values=samples.map(row=>Number(row.features[name]));
  const target=samples.map(row=>Math.max(Number(row.targetsByHorizon[12].upExcursion),Number(row.targetsByHorizon[12].downExcursion)));
  const ranked=x=>x.map((value,index)=>({value,index})).sort((a,b)=>a.value-b.value||a.index-b.index).reduce((out,row,rank)=>(out[row.index]=rank,out),[]);
  const x=ranked(values),y=ranked(target),mx=mean(x),my=mean(y);
  const num=x.reduce((sum,value,index)=>sum+(value-mx)*(y[index]-my),0);
  const den=Math.sqrt(x.reduce((sum,value)=>sum+(value-mx)**2,0)*y.reduce((sum,value)=>sum+(value-my)**2,0));
  return den?Math.abs(num/den):0;
}

function correlation(samples,left,right){
  const a=samples.map(row=>Number(row.features[left])),b=samples.map(row=>Number(row.features[right]));
  const ma=mean(a),mb=mean(b),num=a.reduce((sum,value,index)=>sum+(value-ma)*(b[index]-mb),0);
  const den=Math.sqrt(a.reduce((sum,value)=>sum+(value-ma)**2,0)*b.reduce((sum,value)=>sum+(value-mb)**2,0));
  return den?num/den:0;
}

function selectFeatures(samples,diagnostics){
  const scores=Object.fromEntries(PHASE57_MINIMAL_HYBRID_MODEL_FEATURES.map(name=>[name,featureAssociation(samples,name)]));
  const ordered=PHASE57_MINIMAL_HYBRID_MODEL_FEATURES.filter(name=>diagnostics.byFeature[name].missingRate===0)
    .sort((a,b)=>scores[b]-scores[a]||a.localeCompare(b));
  const selected=[],redundancyDrops=[];
  for(const name of ordered){
    const redundant=selected.find(other=>Math.abs(correlation(samples,name,other))>=0.95);
    if(redundant){redundancyDrops.push({feature:name,retained:redundant,absolutePearson:round8(Math.abs(correlation(samples,name,redundant)))});continue;}
    selected.push(name);if(selected.length===12)break;
  }
  if(selected.length<2)throw new Error('Development feature screening retained fewer than two features');
  return {selected,scores,redundancyDrops};
}

function policy({scale,maximumSelected=50,minimum=0,adjustment=0.1}={}){
  return {source:'ADMITTED_FRESH_DEVELOPMENT',maximumSelected,minimumRemainingOpportunityScore:minimum,opportunityScale:scale,maximumAbsoluteSoftAdjustment:adjustment};
}

function evaluate(model,rows,horizon,{maximumSelected=50,minimum=0,adjustment=0.1}={}){
  const groups=new Map();
  for(const row of rows){if(!groups.has(row.featureCutoff))groups.set(row.featureCutoff,[]);groups.get(row.featureCutoff).push(row);}
  const selected=[];let squaredError=0,predictions=0,rankMovement=0,v1Rows=0,abstain=0;
  for(const group of groups.values()){
    const ranked=group.map(row=>{const target=predictPhase57MinimalHybridTargets({model,features:row.features});
      const actualUp=Number(row.targetsByHorizon[horizon].upExcursion),actualDown=Number(row.targetsByHorizon[horizon].downExcursion);
      squaredError+=(target.expectedUpExcursion-actualUp)**2+(target.expectedDownExcursion-actualDown)**2;predictions+=2;
      const soft=(target.remainingOpportunityScore-0.5)*2*adjustment;
      return {row,target,hybridScore:clamp(Number(row.v1BaseScore)+soft)};
    }).sort((a,b)=>b.hybridScore-a.hybridScore||a.row.v1Rank-b.row.v1Rank||a.row.symbol.localeCompare(b.row.symbol));
    const qualified=ranked.filter(item=>item.target.remainingOpportunityScore>=minimum).slice(0,maximumSelected);
    if(!qualified.length)abstain+=1;
    selected.push(...qualified);
    ranked.forEach((item,index)=>{rankMovement+=Math.abs(index+1-item.row.v1Rank);v1Rows+=1;});
  }
  const observed=selected.map(item=>Math.max(Number(item.row.targetsByHorizon[horizon].upExcursion),Number(item.row.targetsByHorizon[horizon].downExcursion)));
  return {mse:predictions?squaredError/predictions:null,selectedCount:selected.length,meanObservedTwoSided:observed.length?mean(observed):null,
    decisionCount:groups.size,abstainRate:groups.size?abstain/groups.size:null,meanAbsoluteRankMovement:v1Rows?rankMovement/v1Rows:null};
}

export function developHybrid({inputRoot}){
  const {audits,sessionAudits,samples}=readInputs(inputRoot);
  const dataset={storageMode:'SANITIZED_SESSION_AUDITS_WITH_SEALED_SPLITS',manifest:manifest(sessionAudits),sessions:sessions(),compactSessionAudits:sessionAudits};
  const admission=auditPhase57MinimalHybridDataset(dataset);
  if(admission.status!=='MINIMAL_HYBRID_DATASET_ADMITTED_DEVELOPMENT_ONLY')throw new Error(`Admission failed: ${admission.blockers.join(' | ')}`);
  const developmentSet=new Set(allocation.development);
  if(!samples.length||samples.some(row=>!developmentSet.has(row.sessionDate)))throw new Error('Development samples missing or contaminated');
  const diagnostics=describePhase57MinimalHybridFeatures(samples.map(row=>({features:row.features,targets:{upExcursion:row.targetsByHorizon[12].upExcursion,downExcursion:row.targetsByHorizon[12].downExcursion}})));
  const screened=selectFeatures(samples,diagnostics);
  const tuneDates=allocation.development.slice(0,48),testDates=new Set(allocation.development.slice(48));
  const tuneRows=samples.filter(row=>tuneDates.includes(row.sessionDate)),testRows=samples.filter(row=>testDates.has(row.sessionDate));
  const targetCandidates=[];
  for(const horizon of [3,6,12])for(const lambda of [0.01,0.1,1]){
    const scale=Math.max(1e-6,mean(tuneRows.map(row=>Math.max(row.targetsByHorizon[horizon].upExcursion,row.targetsByHorizon[horizon].downExcursion))));
    const model=trainPhase57MinimalHybridModel({samples:asTrainingSamples(tuneRows,horizon,screened.selected),featureNames:screened.selected,ridgeLambda:lambda,
      selectionPolicy:policy({scale}),trainingContext:{mode:'ADMITTED_FRESH_DEVELOPMENT',datasetAdmission:admission.admission}});
    const metrics=evaluate(model,testRows,horizon,{maximumSelected:50,minimum:0,adjustment:0.1});
    targetCandidates.push({horizon,lambda,scale,metrics});
  }
  targetCandidates.sort((a,b)=>a.metrics.mse-b.metrics.mse||a.horizon-b.horizon||a.lambda-b.lambda);
  const targetChoice=targetCandidates[0];
  const provisional=trainPhase57MinimalHybridModel({samples:asTrainingSamples(tuneRows,targetChoice.horizon,screened.selected),featureNames:screened.selected,ridgeLambda:targetChoice.lambda,
    selectionPolicy:policy({scale:targetChoice.scale}),trainingContext:{mode:'ADMITTED_FRESH_DEVELOPMENT',datasetAdmission:admission.admission}});
  const policyCandidates=[];
  for(const maximumSelected of [20,30,40,50])for(const minimum of [0.35,0.45,0.55,0.65])for(const adjustment of [0.05,0.1,0.15,0.2,0.25]){
    const metrics=evaluate(provisional,testRows,targetChoice.horizon,{maximumSelected,minimum,adjustment});
    if(metrics.selectedCount)policyCandidates.push({maximumSelected,minimum,adjustment,metrics});
  }
  policyCandidates.sort((a,b)=>b.metrics.meanObservedTwoSided-a.metrics.meanObservedTwoSided||b.metrics.selectedCount-a.metrics.selectedCount||a.maximumSelected-b.maximumSelected||a.minimum-b.minimum||a.adjustment-b.adjustment);
  const policyChoice=policyCandidates[0];
  if(!policyChoice)throw new Error('Development policy tuning produced no candidates');
  const finalPolicy=policy({scale:targetChoice.scale,maximumSelected:policyChoice.maximumSelected,minimum:policyChoice.minimum,adjustment:policyChoice.adjustment});
  const model=trainPhase57MinimalHybridModel({samples:asTrainingSamples(samples,targetChoice.horizon,screened.selected),featureNames:screened.selected,ridgeLambda:targetChoice.lambda,
    selectionPolicy:finalPolicy,trainingContext:{mode:'ADMITTED_FRESH_DEVELOPMENT',datasetAdmission:admission.admission}});
  const finalMetrics=evaluate(model,samples,targetChoice.horizon,policyChoice);
  const developmentSummary={schemaVersion:1,status:'MINIMAL_HYBRID_DEVELOPMENT_COMPLETE',datasetId:allocation.datasetId,developmentSessions:72,
    developmentSampleCount:samples.length,featureDiagnostics:diagnostics,featureScreening:{selected:screened.selected,redundancyDrops:screened.redundancyDrops,targetAssociation:screened.scores},
    targetSelection:{selectedHorizonBars:targetChoice.horizon,selectedRidgeLambda:targetChoice.lambda,candidates:targetCandidates},
    selectionPolicy:{maximumSelected:policyChoice.maximumSelected,minimumRemainingOpportunityScore:policyChoice.minimum,maximumAbsoluteSoftAdjustment:policyChoice.adjustment,opportunityScale:targetChoice.scale},
    developmentMetrics:finalMetrics,validationReleased:false,untouchedOosReleased:false,performanceWinnerClaimAllowed:false,safety:SAFETY};
  const freezeCore={schemaVersion:1,phase:'57.selector-minimal-hybrid.development-freeze-candidate',status:'MINIMAL_HYBRID_FROZEN_BEFORE_VALIDATION',
    datasetId:allocation.datasetId,datasetManifestSha256:sha256(dataset.manifest),datasetAdmissionSha256:admission.reportSha256,
    modelDigest:model.modelDigest,featureManifest:model.featureNames,targetContract:{horizonBars:targetChoice.horizon,upDownSeparated:true,twoSidedDirectTrainingTarget:false},
    ridgeLambda:model.ridgeLambda,softAdjustment:model.selectionPolicy.maximumAbsoluteSoftAdjustment,dynamicN:{maximumSelected:model.selectionPolicy.maximumSelected,minimumRemainingOpportunityScore:model.selectionPolicy.minimumRemainingOpportunityScore},
    developmentSummarySha256:sha256(developmentSummary),validationReleased:false,untouchedOosReleased:false,validationRetuningAllowed:false,automaticPromotionAllowed:false,safety:SAFETY};
  const freeze={...freezeCore,freezeSha256:sha256(freezeCore)};
  return {datasetManifest:dataset.manifest,datasetAdmission:admission,model,developmentSummary,freeze,shardDigests:audits.map(row=>row.shardSha256).sort()};
}

async function main(){
  const result=developHybrid({inputRoot:process.env.INPUT_ROOT||'artifacts/phase57-jquants-fresh-input'});
  const directory='artifacts/phase57-jquants-development';fs.mkdirSync(directory,{recursive:true,mode:0o700});
  for(const [name,value] of Object.entries(result)){
    const bytes=JSON.stringify(value,null,2)+'\n';fs.writeFileSync(`${directory}/${name}.json`,bytes,{mode:0o600});fs.writeFileSync(`${directory}/${name}.sha256`,`${sha256(bytes)}  ${name}.json\n`,{mode:0o600});
  }
  console.log('PHASE57_JQUANTS_DEVELOPMENT_REPORT '+JSON.stringify({status:result.developmentSummary.status,datasetAdmission:result.datasetAdmission.status,
    developmentSessions:72,developmentSampleCount:result.developmentSummary.developmentSampleCount,featureCount:result.model.featureNames.length,
    targetHorizonBars:result.freeze.targetContract.horizonBars,modelDigest:result.model.modelDigest,hybridFreezeSha256:result.freeze.freezeSha256,
    validationReleased:false,untouchedOosReleased:false,safety:SAFETY}));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(`PHASE57_JQUANTS_DEVELOPMENT_FAIL ${String(error?.message??error)}`);process.exitCode=1;});

export const Phase57DevelopmentInternals=Object.freeze({findFiles,sessions,selectFeatures,evaluate});
