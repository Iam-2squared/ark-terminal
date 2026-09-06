import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';

const allocation=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const SELECTORS=Object.freeze(['V1','V3','HYBRID']);
const HORIZONS=Object.freeze([1,2,3,6,12]);
const mean=values=>values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null;
const round6=value=>value===null?null:Number(Number(value).toFixed(6));
const sha256=value=>createHash('sha256').update(value).digest('hex');
function findFiles(root,name){const found=[];for(const entry of fs.readdirSync(root,{withFileTypes:true})){const target=path.join(root,entry.name);if(entry.isDirectory())found.push(...findFiles(target,name));else if(entry.name===name)found.push(target);}return found.sort();}
function ndjson(root,name){return findFiles(root,`${name}.ndjson.gz`).flatMap(file=>{const value=gunzipSync(fs.readFileSync(file)).toString('utf8').trim();return value?value.split('\n').map(JSON.parse):[];});}
function distribution(values){const xs=values.filter(Number.isFinite).sort((a,b)=>a-b);if(!xs.length)return {count:0,min:null,median:null,max:null,mean:null};return {count:xs.length,min:xs[0],median:xs[Math.floor((xs.length-1)/2)],max:xs.at(-1),mean:round6(mean(xs))};}
function primary(row){return row.targetsByHorizon?.[6]?.status==='TARGET_READY'?row.targetsByHorizon[6]:null;}
function selectorSummary(records,points,selector){
  const rows=records.filter(row=>row.selector===selector),ready=rows.filter(primary);
  const counts=points.map(point=>Number(point.selectedCounts[selector]));
  const horizons=Object.fromEntries(HORIZONS.map(horizon=>{const available=rows.filter(row=>row.targetsByHorizon?.[horizon]?.status==='TARGET_READY');return [horizon,{observations:available.length,
    meanFinalCloseReturnBps:round6(mean(available.map(row=>row.targetsByHorizon[horizon].finalCloseReturn))*10000),
    meanUpExcursionBps:round6(mean(available.map(row=>row.targetsByHorizon[horizon].upExcursion))*10000),
    meanDownExcursionBps:round6(mean(available.map(row=>row.targetsByHorizon[horizon].downExcursion))*10000),
    meanTwoSidedOpportunityBps:round6(mean(available.map(row=>row.targetsByHorizon[horizon].twoSidedOpportunity))*10000)}];}));
  const calibration={};for(const [name,min,max] of [['TOP_1_5',1,5],['RANK_6_10',6,10],['RANK_11_20',11,20],['RANK_21_PLUS',21,Infinity]]){const slice=ready.filter(row=>row.rank>=min&&row.rank<=max);calibration[name]={observations:slice.length,meanTwoSidedOpportunityBps:round6(mean(slice.map(row=>primary(row).twoSidedOpportunity))*10000)};}
  const sessionMeans=allocation.validation.map(date=>{const values=ready.filter(row=>row.sessionDate===date).map(row=>primary(row).twoSidedOpportunity-0.001);return {sessionDate:date,meanCostAdjustedUtilityBps:values.length?mean(values)*10000:null};});
  return {selectedCount:distribution(counts),totalSelections:rows.length,coverageRate:rows.length?round6(ready.length/rows.length):null,
    meanPreSelectionMoveBps:round6(mean(ready.map(row=>row.preSelectionMove))*10000),lateDetectionRate:ready.length?round6(ready.filter(row=>row.preSelectionMove>primary(row).twoSidedOpportunity).length/ready.length):null,
    meanRemainingOpportunityBps:round6(mean(ready.map(row=>primary(row).twoSidedOpportunity))*10000),meanCostAdjustedUtilityBps:round6(mean(ready.map(row=>primary(row).twoSidedOpportunity-0.001))*10000),
    abstainRate:round6(counts.filter(value=>value===0).length/counts.length),horizons,rankCalibration:calibration,sessionMeans};
}
function sameCapacity(records,points){
  const groups=new Map();for(const row of records){if(!groups.has(row.featureCutoff))groups.set(row.featureCutoff,{});const value=groups.get(row.featureCutoff);if(!value[row.selector])value[row.selector]=[];value[row.selector].push(row);}
  const selected=Object.fromEntries(SELECTORS.map(name=>[name,[]]));const kValues=[];
  for(const point of points){const k=Math.min(...SELECTORS.map(name=>Number(point.selectedCounts[name])));kValues.push(k);const group=groups.get(point.featureCutoff)??{};for(const selector of SELECTORS)selected[selector].push(...(group[selector]??[]).sort((a,b)=>a.rank-b.rank).slice(0,k));}
  return {kDistribution:distribution(kValues),...Object.fromEntries(SELECTORS.map(selector=>{const ready=selected[selector].filter(primary);return [selector,{observations:ready.length,meanCostAdjustedUtilityBps:round6(mean(ready.map(row=>primary(row).twoSidedOpportunity-0.001))*10000)}];}))};
}
function leadTime(records,left,right){
  const first=new Map();for(const row of records){const key=`${row.sessionDate}|${row.symbol}`;if(!first.has(key))first.set(key,{});const value=first.get(key);if(!value[row.selector]||row.featureCutoff<value[row.selector])value[row.selector]=row.featureCutoff;}
  const minutes=[];for(const value of first.values())if(value[left]&&value[right])minutes.push((Date.parse(value[right])-Date.parse(value[left]))/60000);
  return {pairedSessionSymbols:minutes.length,positiveMeansLeftEarlier:true,meanMinutes:round6(mean(minutes)),medianMinutes:distribution(minutes).median};
}
export function summarizeValidation({inputRoot}){
  const records=ndjson(inputRoot,'validation-records').sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff)||a.selector.localeCompare(b.selector)||a.rank-b.rank);
  const points=ndjson(inputRoot,'validation-points').sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
  const shardReports=findFiles(inputRoot,'validation-shard.json').map(file=>JSON.parse(fs.readFileSync(file,'utf8')));
  if(shardReports.length!==3||new Set(shardReports.flatMap(row=>row.dates)).size!==24||points.length!==24*20)throw new Error('Validation shards are incomplete');
  const selectors=Object.fromEntries(SELECTORS.map(name=>[name,selectorSummary(records,points,name)]));
  const sessionEqual=Object.fromEntries(SELECTORS.map(name=>[name,round6(mean(selectors[name].sessionMeans.map(row=>row.meanCostAdjustedUtilityBps).filter(Number.isFinite)))]));
  const ordering=[...SELECTORS].sort((a,b)=>sessionEqual[b]-sessionEqual[a]||a.localeCompare(b));
  const hybridRows=records.filter(row=>row.selector==='HYBRID'&&Number.isFinite(row.v1Rank));
  const core={schemaVersion:1,phase:'57.selector-minimal-hybrid.fresh-validation',status:'FROZEN_SELECTORS_VALIDATION_COMPLETE',datasetId:allocation.datasetId,
    validationSessions:24,decisionTimestamps:points.length,records:records.length,primaryMetric:'SESSION_EQUAL_MEAN_COST_ADJUSTED_TWO_SIDED_UTILITY_6_BAR_BPS',roundTripCostBps:10,
    selectors,sameCapacity:sameCapacity(records,points),detectionLeadTime:{HYBRID_VS_V1:leadTime(records,'HYBRID','V1'),V3_VS_V1:leadTime(records,'V3','V1'),HYBRID_VS_V3:leadTime(records,'HYBRID','V3')},
    v1ToHybridRankMovement:{observations:hybridRows.length,meanAbsoluteMovement:round6(mean(hybridRows.map(row=>Math.abs(row.rank-row.v1Rank))))},
    validationLeader:{status:'VALIDATION_LEADER',selector:ordering[0],sessionEqualPrimaryMetricBps:sessionEqual,finalWinnerClaimAllowed:false},
    downstream:{status:'NOT_RUN_NO_IDENTICAL_FROZEN_JQUANTS_5M_INPUT_ADAPTER',entryChanged:false,exitChanged:false,capitalAllocationChanged:false},
    freezeIntegrity:{hybridModelDigests:[...new Set(shardReports.map(row=>row.modelDigest))],hybridFreezeShas:[...new Set(shardReports.map(row=>row.freezeSha256))],validationRetuningPerformed:false},
    release:{developmentReleased:true,validationReleased:true,untouchedOosReleased:false,untouchedOosPayloadRequested:false},
    claims:{validationLeaderAllowed:true,finalWinnerAllowed:false,mainSelectorAllowed:false,productionReadyAllowed:false},safety:allocation.safety};
  return {...core,validationEvidenceSha256:sha256(JSON.stringify(core))};
}
async function main(){const report=summarizeValidation({inputRoot:process.env.INPUT_ROOT||'artifacts/phase57-validation-results'});const directory='artifacts/phase57-jquants-validation';fs.mkdirSync(directory,{recursive:true,mode:0o700});const bytes=JSON.stringify(report,null,2)+'\n';fs.writeFileSync(`${directory}/validation.json`,bytes,{mode:0o600});fs.writeFileSync(`${directory}/validation.sha256`,`${sha256(bytes)}  validation.json\n`,{mode:0o600});console.log('PHASE57_VALIDATION_REPORT '+JSON.stringify({status:report.status,validationSessions:report.validationSessions,leader:report.validationLeader.selector,primaryMetricBps:report.validationLeader.sessionEqualPrimaryMetricBps,evidenceSha256:report.validationEvidenceSha256,untouchedOosReleased:false,safety:report.safety}));}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(`PHASE57_VALIDATION_FAIL ${String(error?.message??error)}`);process.exitCode=1;});
export const Phase57ValidationSummaryInternals=Object.freeze({findFiles,distribution,selectorSummary,sameCapacity,leadTime});
