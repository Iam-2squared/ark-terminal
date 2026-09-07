import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';

const allocation=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const release=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-minimal-hybrid-oos-release.json',import.meta.url),'utf8'));
const SELECTORS=Object.freeze(['V1','V3','HYBRID']);
const HORIZONS=Object.freeze([1,2,3,6,12]);
const mean=values=>values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null;
const round6=value=>value===null?null:Number(Number(value).toFixed(6));
const sha256=value=>createHash('sha256').update(value).digest('hex');
function findFiles(root,name){const found=[];for(const entry of fs.readdirSync(root,{withFileTypes:true})){const target=path.join(root,entry.name);if(entry.isDirectory())found.push(...findFiles(target,name));else if(entry.name===name)found.push(target);}return found.sort();}
function ndjson(root,name){return findFiles(root,`${name}.ndjson.gz`).flatMap(file=>{const value=gunzipSync(fs.readFileSync(file)).toString('utf8').trim();return value?value.split('\n').map(JSON.parse):[];});}
function distribution(values){const xs=values.filter(Number.isFinite).sort((a,b)=>a-b);if(!xs.length)return {count:0,min:null,median:null,max:null,mean:null};return {count:xs.length,min:xs[0],median:quantile(xs,0.5),max:xs.at(-1),mean:round6(mean(xs))};}
function quantile(values,q){const xs=values.filter(Number.isFinite).sort((a,b)=>a-b);if(!xs.length)return null;const index=(xs.length-1)*q,lower=Math.floor(index),upper=Math.ceil(index),weight=index-lower;return round6(xs[lower]*(1-weight)+xs[upper]*weight);}
function primary(row){return row.targetsByHorizon?.[6]?.status==='TARGET_READY'?row.targetsByHorizon[6]:null;}
function sessionDispersion(sessionMeans){const values=sessionMeans.map(row=>row.meanCostAdjustedUtilityBps).filter(Number.isFinite);const q1=quantile(values,0.25),q3=quantile(values,0.75);return {count:values.length,median:quantile(values,0.5),q1,q3,iqr:round6(q3-q1),worst:values.length?round6(Math.min(...values)):null,best:values.length?round6(Math.max(...values)):null,positiveSessionRate:values.length?round6(values.filter(value=>value>0).length/values.length):null};}
function monotonicCalibration(calibration){const values=['TOP_1_5','RANK_6_10','RANK_11_20','RANK_21_PLUS'].map(name=>calibration[name]?.meanTwoSidedOpportunityBps);return values.every(Number.isFinite)&&values.every((value,index)=>index===0||values[index-1]>=value);}

function selectorSummary(records,points,selector){
  const rows=records.filter(row=>row.selector===selector),ready=rows.filter(primary),counts=points.map(point=>Number(point.selectedCounts[selector]));
  const horizons=Object.fromEntries(HORIZONS.map(horizon=>{const available=rows.filter(row=>row.targetsByHorizon?.[horizon]?.status==='TARGET_READY');return [horizon,{observations:available.length,
    meanFinalCloseReturnBps:round6(mean(available.map(row=>row.targetsByHorizon[horizon].finalCloseReturn))*10000),
    meanUpExcursionBps:round6(mean(available.map(row=>row.targetsByHorizon[horizon].upExcursion))*10000),
    meanDownExcursionBps:round6(mean(available.map(row=>row.targetsByHorizon[horizon].downExcursion))*10000),
    meanTwoSidedOpportunityBps:round6(mean(available.map(row=>row.targetsByHorizon[horizon].twoSidedOpportunity))*10000)}];}));
  const rankCalibration={};for(const [name,min,max] of [['TOP_1_5',1,5],['RANK_6_10',6,10],['RANK_11_20',11,20],['RANK_21_PLUS',21,Infinity]]){const slice=ready.filter(row=>row.rank>=min&&row.rank<=max);rankCalibration[name]={observations:slice.length,meanTwoSidedOpportunityBps:round6(mean(slice.map(row=>primary(row).twoSidedOpportunity))*10000)};}
  const sessionMeans=allocation.untouchedOos.map(date=>{const values=ready.filter(row=>row.sessionDate===date).map(row=>primary(row).twoSidedOpportunity-release.roundTripCostBps/10000);return {sessionDate:date,meanCostAdjustedUtilityBps:values.length?mean(values)*10000:null};});
  return {selectedCount:distribution(counts),totalSelections:rows.length,coverageRate:rows.length?round6(ready.length/rows.length):null,
    meanPreSelectionMoveBps:round6(mean(ready.map(row=>row.preSelectionMove))*10000),lateDetectionRate:ready.length?round6(ready.filter(row=>row.preSelectionMove>primary(row).twoSidedOpportunity).length/ready.length):null,
    meanRemainingOpportunityBps:round6(mean(ready.map(row=>primary(row).twoSidedOpportunity))*10000),meanCostAdjustedUtilityBps:round6(mean(ready.map(row=>primary(row).twoSidedOpportunity-release.roundTripCostBps/10000))*10000),
    abstainRate:round6(counts.filter(value=>value===0).length/counts.length),horizons,rankCalibration,rankCalibrationMonotonic:monotonicCalibration(rankCalibration),sessionMeans,sessionDispersion:sessionDispersion(sessionMeans)};
}

function sameCapacity(records,points){
  const groups=new Map();for(const row of records){if(!groups.has(row.featureCutoff))groups.set(row.featureCutoff,{});const value=groups.get(row.featureCutoff);if(!value[row.selector])value[row.selector]=[];value[row.selector].push(row);}
  const selected=Object.fromEntries(SELECTORS.map(name=>[name,[]])),kValues=[];
  for(const point of points){const k=Math.min(...SELECTORS.map(name=>Number(point.selectedCounts[name])));kValues.push(k);const group=groups.get(point.featureCutoff)??{};for(const selector of SELECTORS)selected[selector].push(...(group[selector]??[]).sort((a,b)=>a.rank-b.rank).slice(0,k));}
  return {kDefinition:'MIN_SELECTED_COUNT_ACROSS_V1_V3_HYBRID_AT_EACH_TIMESTAMP',kDistribution:distribution(kValues),...Object.fromEntries(SELECTORS.map(selector=>{const ready=selected[selector].filter(primary);return [selector,{observations:ready.length,meanCostAdjustedUtilityBps:round6(mean(ready.map(row=>primary(row).twoSidedOpportunity-release.roundTripCostBps/10000))*10000)}];}))};
}

function leadTime(records,left,right){
  const first=new Map();for(const row of records){const key=`${row.sessionDate}|${row.symbol}`;if(!first.has(key))first.set(key,{});const value=first.get(key);if(!value[row.selector]||row.featureCutoff<value[row.selector])value[row.selector]=row.featureCutoff;}
  const minutes=[];for(const value of first.values())if(value[left]&&value[right])minutes.push((Date.parse(value[right])-Date.parse(value[left]))/60000);
  return {pairedSessionSymbols:minutes.length,positiveMeansLeftEarlier:true,meanMinutes:round6(mean(minutes)),medianMinutes:distribution(minutes).median};
}

function validationDispersion(validation,selector){return sessionDispersion(validation.selectors[selector].sessionMeans);}
function delta(oos,validation){return Number.isFinite(oos)&&Number.isFinite(validation)?round6(oos-validation):null;}
function metricLeader(values,direction='max'){return [...SELECTORS].sort((a,b)=>direction==='max'?values[b]-values[a]||a.localeCompare(b):values[a]-values[b]||a.localeCompare(b))[0];}

export function summarizeOos({inputRoot,validationPath}={}){
  const records=ndjson(inputRoot,'oos-records').sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff)||a.selector.localeCompare(b.selector)||a.rank-b.rank);
  const points=ndjson(inputRoot,'oos-points').sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
  const shardReports=findFiles(inputRoot,'oos-shard.json').map(file=>JSON.parse(fs.readFileSync(file,'utf8')));
  if(shardReports.length!==3||new Set(shardReports.flatMap(row=>row.dates)).size!==24||points.length!==24*20)throw new Error('OOS shards are incomplete');
  if(shardReports.some(row=>row.validationRetuningPerformed||row.modelMutationPerformed||row.reserveSessionsTouched!==0))throw new Error('OOS mutation or reserve access detected');
  const digests=[...new Set(shardReports.map(row=>row.modelDigest))],freezes=[...new Set(shardReports.map(row=>row.freezeSha256))],gates=[...new Set(shardReports.map(row=>row.integrityGateSha256))];
  if(JSON.stringify(digests)!==JSON.stringify([release.expectedModelDigest])||JSON.stringify(freezes)!==JSON.stringify([release.expectedHybridFreezeSha256])||gates.length!==1)throw new Error('OOS Freeze integrity failed');
  const validation=JSON.parse(fs.readFileSync(validationPath,'utf8'));
  if(validation.validationEvidenceSha256!==release.expectedValidationEvidenceSha256)throw new Error('Validation evidence changed');
  const selectors=Object.fromEntries(SELECTORS.map(name=>[name,selectorSummary(records,points,name)]));
  const sessionEqual=Object.fromEntries(SELECTORS.map(name=>[name,round6(mean(selectors[name].sessionMeans.map(row=>row.meanCostAdjustedUtilityBps).filter(Number.isFinite)))]));
  const same=sameCapacity(records,points),sameValues=Object.fromEntries(SELECTORS.map(name=>[name,same[name].meanCostAdjustedUtilityBps]));
  const opportunityPrimaryLeader=metricLeader(sessionEqual),sameCapacityLeader=metricLeader(sameValues);
  const preMoveLeader=metricLeader(Object.fromEntries(SELECTORS.map(name=>[name,selectors[name].meanPreSelectionMoveBps])),'min');
  const lateDetectionLeader=metricLeader(Object.fromEntries(SELECTORS.map(name=>[name,selectors[name].lateDetectionRate])),'min');
  const earlyDetectionLeader=preMoveLeader===lateDetectionLeader?preMoveLeader:`MIXED_PREMOVE_${preMoveLeader}_LATE_${lateDetectionLeader}`;
  const validationLeader=validation.validationLeader.selector;
  const opportunityLeader=opportunityPrimaryLeader===sameCapacityLeader?opportunityPrimaryLeader:`MIXED_PRIMARY_${opportunityPrimaryLeader}_SAME_CAPACITY_${sameCapacityLeader}`;
  const overallSelectorCandidate=opportunityLeader===earlyDetectionLeader&&validationLeader===opportunityLeader?opportunityLeader:'NO_SINGLE_OVERALL_CANDIDATE_OPPORTUNITY_EARLY_TRADEOFF';
  const validationToOos=Object.fromEntries(SELECTORS.map(name=>[name,{
    validationPrimaryUtilityBps:validation.validationLeader.sessionEqualPrimaryMetricBps[name],oosPrimaryUtilityBps:sessionEqual[name],primaryUtilityDeltaBps:delta(sessionEqual[name],validation.validationLeader.sessionEqualPrimaryMetricBps[name]),
    validationSameCapacityUtilityBps:validation.sameCapacity[name].meanCostAdjustedUtilityBps,oosSameCapacityUtilityBps:same[name].meanCostAdjustedUtilityBps,sameCapacityDeltaBps:delta(same[name].meanCostAdjustedUtilityBps,validation.sameCapacity[name].meanCostAdjustedUtilityBps),
    validationSelectedCountMean:validation.selectors[name].selectedCount.mean,oosSelectedCountMean:selectors[name].selectedCount.mean,selectedCountMeanDelta:delta(selectors[name].selectedCount.mean,validation.selectors[name].selectedCount.mean),
    validationPreSelectionMoveBps:validation.selectors[name].meanPreSelectionMoveBps,oosPreSelectionMoveBps:selectors[name].meanPreSelectionMoveBps,preSelectionMoveDeltaBps:delta(selectors[name].meanPreSelectionMoveBps,validation.selectors[name].meanPreSelectionMoveBps),
    validationLateDetectionRate:validation.selectors[name].lateDetectionRate,oosLateDetectionRate:selectors[name].lateDetectionRate,lateDetectionDelta:delta(selectors[name].lateDetectionRate,validation.selectors[name].lateDetectionRate),
    validationRankCalibration:validation.selectors[name].rankCalibration,oosRankCalibration:selectors[name].rankCalibration,
    validationSessionDispersion:validationDispersion(validation,name),oosSessionDispersion:selectors[name].sessionDispersion,
  }]));
  const core={schemaVersion:1,phase:'57.selector-minimal-hybrid.untouched-oos-final',status:'FROZEN_SELECTORS_UNTOUCHED_OOS_COMPLETE',datasetId:allocation.datasetId,
    oosSessions:24,decisionTimestamps:points.length,records:records.length,primaryMetric:release.primaryMetric,roundTripCostBps:release.roundTripCostBps,
    selectors,sameCapacity:same,detectionLeadTime:{HYBRID_VS_V1:leadTime(records,'HYBRID','V1'),V3_VS_V1:leadTime(records,'V3','V1'),HYBRID_VS_V3:leadTime(records,'HYBRID','V3')},
    v1ToHybridRankMovement:{observations:records.filter(row=>row.selector==='HYBRID'&&Number.isFinite(row.v1Rank)).length,meanAbsoluteMovement:round6(mean(records.filter(row=>row.selector==='HYBRID'&&Number.isFinite(row.v1Rank)).map(row=>Math.abs(row.rank-row.v1Rank))))},
    validationToOos,leaders:{validationLeader,oosOpportunityLeader:opportunityLeader,oosPrimaryLeader:opportunityPrimaryLeader,oosSameCapacityLeader:sameCapacityLeader,earlyDetectionLeader,preMoveLeader,lateDetectionLeader,overallSelectorCandidate},
    freezeIntegrity:{hybridModelDigests:digests,hybridFreezeShas:freezes,integrityGateShas:gates,validationRetuningPerformed:false,oosRetuningPerformed:false,modelMutationPerformed:false},
    downstream:{status:'DOWNSTREAM_EVALUATION_PENDING',reason:'NO_IDENTICAL_FROZEN_JQUANTS_5M_INPUT_ADAPTER',entryChanged:false,exitChanged:false,capitalAllocationChanged:false},
    release:{developmentReleased:true,validationReleased:true,untouchedOosReleased:true,reserveReleased:false,reserveSessionsTouched:0,reserveSessionsRemaining:release.reserveSessionCount},
    claims:{opportunityLeaderAllowed:true,earlyDetectionLeaderAllowed:true,overallCandidateAllowed:true,guaranteedSuperiorAllowed:false,productionReadyAllowed:false,automaticPromotionAllowed:false},safety:release.safety};
  return {...core,oosEvidenceSha256:sha256(JSON.stringify(core))};
}

async function main(){
  const report=summarizeOos({inputRoot:process.env.INPUT_ROOT||'artifacts/phase57-oos-results',validationPath:process.env.VALIDATION_PATH||'predict/research/phase57-selector-minimal-hybrid-fresh-validation.json'});
  const directory='artifacts/phase57-jquants-oos-final';fs.mkdirSync(directory,{recursive:true,mode:0o700});const bytes=JSON.stringify(report,null,2)+'\n';
  fs.writeFileSync(`${directory}/oos-final.json`,bytes,{mode:0o600});fs.writeFileSync(`${directory}/oos-final.sha256`,`${sha256(bytes)}  oos-final.json\n`,{mode:0o600});
  console.log('PHASE57_OOS_FINAL_REPORT '+JSON.stringify({status:report.status,leaders:report.leaders,primaryMetricBps:Object.fromEntries(SELECTORS.map(name=>[name,report.selectors[name].sessionDispersion.count?round6(mean(report.selectors[name].sessionMeans.map(row=>row.meanCostAdjustedUtilityBps).filter(Number.isFinite))):null])),
    sameCapacityBps:Object.fromEntries(SELECTORS.map(name=>[name,report.sameCapacity[name].meanCostAdjustedUtilityBps])),oosEvidenceSha256:report.oosEvidenceSha256,
    reserveSessionsTouched:0,reserveSessionsRemaining:report.release.reserveSessionsRemaining,safety:report.safety}));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(`PHASE57_OOS_FINAL_FAIL ${String(error?.message??error)}`);process.exitCode=1;});

export const Phase57OosSummaryInternals=Object.freeze({findFiles,distribution,quantile,sessionDispersion,sameCapacity,leadTime});
