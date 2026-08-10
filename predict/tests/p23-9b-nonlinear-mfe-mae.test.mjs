import assert from 'node:assert/strict';
import { deriveEntryOpportunityFeatures } from '../daytrade/phase57-entry-opportunity-intelligence.js';
import { PHASE57_P23_9B_SAFETY,P23_9B_CONFIG,fitHistoricalAnalogOpportunity,evaluateNonlinearOpportunityWalkForward } from '../daytrade/phase57-nonlinear-mfe-mae-intelligence.js';

for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed']) assert.equal(PHASE57_P23_9B_SAFETY[key],false);
assert.equal(P23_9B_CONFIG.sameSessionTrainingForbidden,true);

function context(date='2026-07-01',drift=0.2){const start=Date.parse(`${date}T00:00:00Z`);return Array.from({length:12},(_,i)=>{const open=100+i*drift,close=open+drift*0.6;return {timestamp:new Date(start+i*300000).toISOString(),sessionDate:date,open,high:Math.max(open,close)+0.12,low:Math.min(open,close)-0.1,close,volume:1000+i*20};});}
function example(i,positive=true,date=`2026-07-${String(1+Math.floor(i/80)).padStart(2,'0')}`){const dir=i%2?'LONG':'SHORT';const features=deriveEntryOpportunityFeatures({contextBars:context(date,dir==='LONG'?0.22:-0.18),direction:dir});return {symbol:`S${i%5}`,sessionDate:date,featureCutoff:context(date).at(-1).timestamp,direction:dir,features,targets:{mfePct:positive?0.9:0.25,adversePct:positive?0.25:0.65,endpointNetReturnPct:positive?0.4:-0.3,opportunityScorePct:positive?0.6:-0.45},realizedRatchetNetReturnPct:positive?0.32:-0.28,pointInTimeFeaturesOnly:true,futureTargetsEvaluationOnly:true};}

const train=[];for(let i=0;i<1600;i++) train.push(example(i,(i%4)!==0));
const model=fitHistoricalAnalogOpportunity(train,{k:32,minTrainRows:100});
const p=model.predict({...example(2001,true,'2026-07-25'),symbol:'NEW'});
assert.ok(Number.isFinite(p.expectedMfePct));assert.ok(Number.isFinite(p.expectedAdversePct));assert.ok(Number.isFinite(p.expectedRatchetNetReturnPct));assert.ok(p.winProbability>=0&&p.winProbability<=1);assert.equal(p.futureOutcomeUsedForPrediction,false);assert.equal(p.outerOutcomeUsedForPrediction,false);

const test=[example(2001,true,'2026-07-25'),example(2002,false,'2026-07-26')];
const result=evaluateNonlinearOpportunityWalkForward({trainingExamples:train,frozenTestExamples:test,config:{k:32,minTrainRows:100}});
assert.equal(result.integrity.trainingUsesPriorSessionsOnly,true);assert.equal(result.integrity.sameSessionTrainingForbidden,true);assert.equal(result.integrity.futureExtremaUsedAsFeatures,false);assert.equal(result.integrity.historicalRatchetOutcomeUsedAsLabelOnly,true);assert.equal(result.edgeClaimAllowed,false);assert.equal(result.executionAllowed,false);assert.ok(result.predictionCount>=1);
for(const row of result.predictions){assert.ok(String(row.sessionDate)>='2026-07-25');assert.equal(row.futureOutcomeUsedForPrediction,false);}
console.log('P23.9B nonlinear MFE/MAE tests passed');
