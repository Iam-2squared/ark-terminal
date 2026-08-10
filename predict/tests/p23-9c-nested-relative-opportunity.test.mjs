import assert from 'node:assert/strict';
import { deriveEntryOpportunityFeatures } from '../daytrade/phase57-entry-opportunity-intelligence.js';
import { PHASE57_P23_9C_SAFETY,calibrateRelativeOpportunityGate,evaluateNestedRelativeOpportunity } from '../daytrade/phase57-nested-relative-opportunity-gate.js';

for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed'])assert.equal(PHASE57_P23_9C_SAFETY[key],false);

function bars(date,drift){const start=Date.parse(`${date}T00:00:00Z`);return Array.from({length:12},(_,i)=>{const o=100+i*drift,c=o+drift*0.7;return{timestamp:new Date(start+i*300000).toISOString(),sessionDate:date,open:o,high:Math.max(o,c)+0.1,low:Math.min(o,c)-0.1,close:c,volume:1000+i*30};});}
function row(date,i,good){const direction=i%2?'LONG':'SHORT';const drift=(direction==='LONG'?1:-1)*(good?0.28:-0.12);const context=bars(date,drift);const f=deriveEntryOpportunityFeatures({contextBars:context,direction});return{symbol:`S${i%4}`,sessionDate:date,featureCutoff:context.at(-1).timestamp,direction,features:f,targets:{mfePct:good?1.2:0.25,adversePct:good?0.2:0.8,endpointNetReturnPct:good?0.5:-0.4,opportunityScorePct:good?0.95:-0.6},realizedRatchetNetReturnPct:good?0.35:-0.3,pointInTimeFeaturesOnly:true,futureTargetsEvaluationOnly:true};}
const train=[];for(let d=1;d<=12;d++){const date=`2026-07-${String(d).padStart(2,'0')}`;for(let i=0;i<80;i++)train.push(row(date,i,(i%3)!==0));}
const cfg={calibrationSessionCount:4,maxCalibrationRows:200,minimumCalibrationSignals:10,minimumCalibrationNetPct:0,minimumCalibrationProfitFactor:1.01,analogConfig:{k:16,minTrainRows:100}};
const cal=calibrateRelativeOpportunityGate(train,cfg);assert.equal(cal.integrity.frozenOuterOutcomesUsedForSelection,false);assert.ok(cal.calibrationDates.every(d=>d<'2026-07-13'));assert.ok(cal.selected||cal.bestObserved);
const frozen=[];for(let i=0;i<30;i++)frozen.push(row('2026-07-13',2000+i,(i%3)!==0));
const ev=evaluateNestedRelativeOpportunity({trainingExamples:train,frozenTestExamples:frozen,config:cfg});assert.equal(ev.integrity.frozenOuterOutcomesUsedForSelection,false);assert.equal(ev.integrity.calibrationPrecedesFrozenWindow,true);assert.equal(ev.integrity.sameSessionTrainingForbidden,true);assert.equal(ev.edgeClaimAllowed,false);assert.equal(ev.executionAllowed,false);if(ev.status==='NESTED_RELATIVE_OPPORTUNITY_EVALUATED'){for(const p of ev.predictions)assert.equal(p.outerOutcomeUsedForSelection,false);}
console.log('P23.9C nested relative opportunity tests passed');
