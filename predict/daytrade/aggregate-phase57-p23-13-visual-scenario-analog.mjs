import fs from 'node:fs';
import path from 'node:path';
import { EXPANDED_UNIVERSE } from './phase57-expanded-universe.js';
import {
  P23_13_VISUAL_ANALOG_POLICY,
  PHASE57_P23_13_SAFETY,
  findVisualScenarioAnalogs,
} from './phase57-visual-scenario-analog.js';

const root=process.env.PHASE57_ARTIFACT_ROOT??process.argv[2]??'downloaded';
const files=[];
function walk(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){const full=path.join(dir,entry.name);if(entry.isDirectory())walk(full);else if(entry.isFile()&&entry.name.endsWith('.json'))files.push(full);}}
walk(root);
const shards=files.map(file=>JSON.parse(fs.readFileSync(file,'utf8'))).filter(row=>row?.phase==='57.p23.12-visual-reasoning-development-measurement');
if(shards.length!==3) throw new Error(`expected 3 P23.12 source shards, got ${shards.length}`);
const records=shards.flatMap(row=>row.records??[]).filter(row=>row?.outcome60m&&row?.featureCutoff&&row?.sessionDate);
const symbols=[...new Set(shards.flatMap(row=>row.symbols??[]))].sort();
const expected=[...EXPANDED_UNIVERSE].sort();
if(JSON.stringify(symbols)!==JSON.stringify(expected)) throw new Error('P23.13 source universe mismatch');
if(!records.length) throw new Error('no P23.12 visual records for P23.13');
records.sort((a,b)=>String(a.featureCutoff).localeCompare(String(b.featureCutoff))||String(a.symbol).localeCompare(String(b.symbol))||String(a.setup).localeCompare(String(b.setup)));

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const mean=values=>values.length?values.reduce((sum,value)=>sum+Number(value),0)/values.length:null;
function pearson(xs,ys){
  const pairs=xs.map((x,i)=>[Number(x),Number(ys[i])]).filter(([x,y])=>Number.isFinite(x)&&Number.isFinite(y));
  if(pairs.length<3)return null;
  const mx=mean(pairs.map(row=>row[0])),my=mean(pairs.map(row=>row[1]));
  let num=0,dx=0,dy=0;
  for(const [x,y] of pairs){const a=x-mx,b=y-my;num+=a*b;dx+=a*a;dy+=b*b;}
  return dx>0&&dy>0?num/Math.sqrt(dx*dy):null;
}
function summary(rows){
  const valid=rows.filter(row=>finite(row.actualAlignedReturnPct));
  const predicted=valid.filter(row=>finite(row.expectedAlignedReturnPct));
  return {
    sourceCount:valid.length,
    predictionCount:predicted.length,
    predictionCoverage:valid.length?predicted.length/valid.length:0,
    readyCount:predicted.filter(row=>row.status==='INTRADAY_ANALOGS_READY').length,
    averageAnalogCount:mean(predicted.map(row=>row.analogCount)),
    averageEffectiveAnalogCount:mean(predicted.map(row=>row.effectiveAnalogCount)),
    meanPredictedAlignedReturnPct:mean(predicted.map(row=>row.expectedAlignedReturnPct)),
    meanActualAlignedReturnPct:mean(predicted.map(row=>row.actualAlignedReturnPct)),
    meanPredictedSuccessProbability:mean(predicted.map(row=>row.expectedSetupSuccessProbability).filter(finite)),
    actualHitRate:predicted.length?predicted.filter(row=>row.actualHit).length/predicted.length:null,
    predictedReturnCorrelation:pearson(predicted.map(row=>row.expectedAlignedReturnPct),predicted.map(row=>row.actualAlignedReturnPct)),
    predictedSuccessCorrelation:pearson(predicted.map(row=>row.expectedSetupSuccessProbability),predicted.map(row=>row.actualHit?1:0)),
    meanAbsolutePredictionErrorPct:mean(predicted.map(row=>Math.abs(Number(row.expectedAlignedReturnPct)-Number(row.actualAlignedReturnPct)))),
    meanExpectedAlignedNetAfterCostPct:mean(predicted.map(row=>row.expectedAlignedNetAfterCostPct).filter(finite)),
  };
}
function grouped(rows,keyFn){const groups=new Map();for(const row of rows){const key=keyFn(row);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}return Object.fromEntries([...groups].map(([key,values])=>[key,summary(values)]));}
function predictionBucket(value){const v=Number(value);if(!Number.isFinite(v))return'NO_PREDICTION';if(v<-0.05)return'PRED_LT_NEG_0_05';if(v<0)return'PRED_NEG_TO_0';if(v<0.05)return'PRED_0_TO_0_05';return'PRED_GE_0_05';}

const predictions=[];
for(let index=0;index<records.length;index+=1){
  const record=records[index];
  const analog=findVisualScenarioAnalogs({record,historyRecords:records});
  predictions.push({
    symbol:record.symbol,
    sessionDate:record.sessionDate,
    featureCutoff:record.featureCutoff,
    setup:record.setup,
    direction:record.direction,
    visualBand:record.visualBand,
    visualScore:record.visualScore,
    status:analog.status,
    analogCount:analog.analogCount,
    effectiveAnalogCount:analog.effectiveAnalogCount,
    analogQualityScore:analog.analogQualityScore,
    expectedAlignedReturnPct:analog.expectedAlignedReturnPct,
    expectedAlignedNetAfterCostPct:analog.expectedAlignedNetAfterCostPct,
    expectedSetupSuccessProbability:analog.expectedSetupSuccessProbability,
    weightedMeanMfePct:analog.weightedMeanMfePct,
    weightedMeanMaePct:analog.weightedMeanMaePct,
    actualAlignedReturnPct:Number(record.outcome60m.directionalReturnPct),
    actualHit:Boolean(record.outcome60m.hit),
    actualMfePct:Number(record.outcome60m.mfePct),
    actualMaePct:Number(record.outcome60m.maePct),
    maxOutcomeAtUsed:analog.candidateAudit?.maxOutcomeAtUsed??null,
    candidateOutcomesFullyRealizedBeforeQuery:analog.candidateAudit?.candidateOutcomesFullyRealizedBeforeQuery===true,
    currentSessionExcluded:analog.candidateAudit?.currentSessionExcluded===true,
    sameSetupOnly:analog.sameSetupOnly===true,
    distanceUsesOutcomeLabels:analog.distanceUsesOutcomeLabels,
    futureOutcomeUsedForSimilarity:analog.futureOutcomeUsedForSimilarity,
    predictionUsedAsEntryGate:analog.predictionUsedAsEntryGate,
  });
  if((index+1)%500===0)console.log(JSON.stringify({progress:index+1,total:records.length}));
}
if(predictions.some(row=>row.distanceUsesOutcomeLabels!==false||row.futureOutcomeUsedForSimilarity!==false||row.predictionUsedAsEntryGate!==false))throw new Error('P23.13 leakage/gating invariant violated');
if(predictions.some(row=>row.status==='INTRADAY_ANALOGS_READY'&&(row.candidateOutcomesFullyRealizedBeforeQuery!==true||row.currentSessionExcluded!==true||row.sameSetupOnly!==true)))throw new Error('P23.13 causal analog audit failed');

const dates=[...new Set(predictions.map(row=>row.sessionDate))].sort();
const tailStartIndex=Math.max(0,Math.floor(dates.length*0.75));
const tailDates=new Set(dates.slice(tailStartIndex));
const chronologicalTail=predictions.filter(row=>tailDates.has(row.sessionDate));
const ready=predictions.filter(row=>row.status==='INTRADAY_ANALOGS_READY');
const aggregate={
  phase:'57.p23.13-visual-scenario-analog-development',
  status:'VISUAL_SCENARIO_CAUSAL_ANALOG_DEVELOPMENT_MEASURED',
  shardCount:shards.length,
  symbolCount:symbols.length,
  symbols,
  policy:P23_13_VISUAL_ANALOG_POLICY,
  sourceRecordCount:records.length,
  predictionRecordCount:predictions.length,
  readyPredictionCount:ready.length,
  aggregate:summary(predictions),
  bySetup:grouped(predictions,row=>row.setup),
  byVisualBand:grouped(predictions,row=>row.visualBand),
  byPredictionBucket:grouped(predictions,row=>predictionBucket(row.expectedAlignedReturnPct)),
  chronologicalDevelopmentTail:{
    dateCount:tailDates.size,
    startDate:[...tailDates].sort()[0]??null,
    endDate:[...tailDates].sort().at(-1)??null,
    ...summary(chronologicalTail),
    label:'DEVELOPMENT_CHRONOLOGICAL_TAIL_NOT_UNTOUCHED_OOS',
  },
  predictions,
  methodology:{
    exactExpandedDevelopmentUniverse:true,
    sourceVisualRepresentationFrozenFromP23_12:true,
    sameSetupAnalogsOnly:true,
    sameSessionAnalogsExcluded:true,
    candidateOutcomesMustBeFullyRealizedBeforeQuery:true,
    robustScalerFitCausalPoolOnly:true,
    outcomeLabelsNeverUsedInSimilarityDistance:true,
    futureOutcomeUsedForPredictionSelection:false,
    predictionUsedAsEntryGate:false,
    thresholdSearchPerformed:false,
    externalVisionModelCalled:false,
    developmentUniverseOnly:true,
    freshCrossSymbolHoldoutConsumed:false,
    untouchedTemporalOos:false,
    chronologicalTailIsDevelopmentDiagnosticOnly:true,
  },
  edgeClaimAllowed:false,
  recommendationAllowed:false,
  transmitted:false,
  ...PHASE57_P23_13_SAFETY,
};
for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed'])if(aggregate[key]!==false)throw new Error(`${key} must remain false`);
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-p23-13-visual-scenario-analog-development.json',JSON.stringify(aggregate,null,2));
console.log(JSON.stringify({status:aggregate.status,sourceRecordCount:aggregate.sourceRecordCount,readyPredictionCount:aggregate.readyPredictionCount,aggregate:aggregate.aggregate,chronologicalDevelopmentTail:aggregate.chronologicalDevelopmentTail,bySetup:aggregate.bySetup,byPredictionBucket:aggregate.byPredictionBucket},null,2));
