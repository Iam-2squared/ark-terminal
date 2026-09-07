import assert from 'node:assert/strict';
import test from 'node:test';

import {acquireFreshSession,evaluateFreshValidationSession,Phase57FreshSessionInternals} from '../../scripts/lib/phase57-selector-jquants-fresh-session.mjs';
import {trainPhase57MinimalHybridModel} from '../daytrade/phase57-selector-minimal-hybrid-model.js';

const date='2024-10-01';
const times=[];
for(const [hour,minute,count] of [[9,0,30],[12,30,36]]){
  const start=hour*60+minute;
  for(let index=0;index<count;index+=1){const value=start+index*5;times.push(`${String(Math.floor(value/60)).padStart(2,'0')}:${String(value%60).padStart(2,'0')}`);}
}
const codes=Array.from({length:15},(_,index)=>`${String(1001+index)}0`);
const minuteRows=codes.flatMap((Code,symbolIndex)=>times.map((Time,index)=>{
  const base=100+symbolIndex+index*0.1;
  return {Date:date,Time,Code,O:base,H:base+0.2,L:base-0.1,C:base+0.1,Vo:1000+index*10,Va:(1000+index*10)*(base+0.1)};
}));
const masterRows=codes.map((Code,index)=>({Date:date,Code,S33Nm:`S${index%4}`,Mkt:'0111',MktNm:'Prime',ProdCat:'011'}));

function provider({minutes=minuteRows,master=masterRows}={}){
  return async url=>new Response(JSON.stringify({data:String(url).includes('/equities/master')?master:minutes}),{status:200});
}

test('Fresh session structural audit is deterministic and sealed outside Development',async()=>{
  const first=await acquireFreshSession({apiKey:'hidden',date,fold:'UNTOUCHED_OOS',fetchImpl:provider(),paceMs:0});
  const second=await acquireFreshSession({apiKey:'hidden',date,fold:'UNTOUCHED_OOS',fetchImpl:provider(),paceMs:0});
  assert.deepEqual(first,second);
  assert.equal(first.structuralAudit.status,'SESSION_STRUCTURAL_AUDIT_PASS');
  assert.equal(first.structuralAudit.pointInTimeUniverse,true);
  assert.equal(first.structuralAudit.featureCalculationPerformed,false);
  assert.equal(first.structuralAudit.labelGenerationPerformed,false);
  assert.equal(first.structuralAudit.untouchedOosReleased,false);
  assert.equal(first.developmentSamples.length,0);
  assert.equal(first.developmentDiagnostics,null);
  assert.equal(first.structuralAudit.symbolCoverage.length,15);
  assert.ok(Object.values(first.structuralAudit.safety).every(value=>value===false));
});

test('Fresh Development emits only V1-candidate causal feature and separate target rows',async()=>{
  const result=await acquireFreshSession({apiKey:'hidden',date,fold:'DEVELOPMENT',fetchImpl:provider(),paceMs:0});
  assert.equal(result.structuralAudit.featureCalculationPerformed,true);
  assert.equal(result.structuralAudit.labelGenerationPerformed,true);
  assert.ok(result.developmentSamples.length>0);
  assert.ok(result.developmentSamples.every(row=>row.targetsByHorizon[12].status==='TARGET_READY'));
  assert.ok(result.developmentSamples.every(row=>Number.isFinite(row.targetsByHorizon[12].upExcursion)&&Number.isFinite(row.targetsByHorizon[12].downExcursion)));
  assert.ok(result.developmentSamples.every(row=>Object.keys(row.features).length===12));
  assert.equal(Phase57FreshSessionInternals.DECISION_TIMES.length,20);
});

test('Fresh PIT universe excludes non-common issue suffixes and non-domestic-stock products before symbol mapping',async()=>{
  const excludedRows=[
    {...minuteRows[0],Code:'10015'},
    {...minuteRows[0],Code:'13050'},
  ];
  const excludedMaster=[
    {Date:date,Code:'10015',S33Nm:'S0',Mkt:'0111',MktNm:'Prime',ProdCat:'011'},
    {Date:date,Code:'13050',S33Nm:'S0',Mkt:'0111',MktNm:'Prime',ProdCat:'014'},
  ];
  const result=await acquireFreshSession({
    apiKey:'hidden',date,fold:'UNTOUCHED_OOS',
    fetchImpl:provider({minutes:[...minuteRows,...excludedRows],master:[...masterRows,...excludedMaster]}),paceMs:0,
  });
  assert.equal(result.structuralAudit.status,'SESSION_STRUCTURAL_AUDIT_PASS');
  assert.equal(result.structuralAudit.eligibleJpxSymbolCount,15);
  assert.equal(result.structuralAudit.symbolCoverage.length,15);
});

test('Validation opens only after a frozen model and verifies admitted source hashes',async()=>{
  const development=await acquireFreshSession({apiKey:'hidden',date,fold:'DEVELOPMENT',fetchImpl:provider(),paceMs:0});
  const training=development.developmentSamples.map(row=>({sessionDate:date,features:row.features,targets:{upExcursion:row.targetsByHorizon[6].upExcursion,downExcursion:row.targetsByHorizon[6].downExcursion}}));
  const model=trainPhase57MinimalHybridModel({samples:training,ridgeLambda:0.1,selectionPolicy:{source:'ADMITTED_FRESH_DEVELOPMENT',maximumSelected:10,minimumRemainingOpportunityScore:0.2,opportunityScale:0.01,maximumAbsoluteSoftAdjustment:0.1},
    trainingContext:{mode:'ADMITTED_FRESH_DEVELOPMENT',datasetAdmission:{status:'MINIMAL_HYBRID_NEW_DATASET_ADMITTED_DEVELOPMENT_ONLY',datasetId:'fixture',split:{development:[date]}}}});
  const admitted=await acquireFreshSession({apiKey:'hidden',date,fold:'VALIDATION',fetchImpl:provider(),paceMs:0});
  const result=await evaluateFreshValidationSession({apiKey:'hidden',date,expectedAudit:admitted.structuralAudit,model,fetchImpl:provider(),paceMs:0});
  assert.equal(result.status,'VALIDATION_SESSION_EVALUATED_FROZEN_HYBRID');
  assert.equal(result.points.length,20);
  assert.ok(result.records.some(row=>row.selector==='V1'));
  assert.ok(result.records.some(row=>row.selector==='HYBRID'));
  assert.equal(result.validationReleased,true);
  assert.equal(result.untouchedOosReleased,false);
  await assert.rejects(()=>evaluateFreshValidationSession({apiKey:'hidden',date,expectedAudit:{...admitted.structuralAudit,minuteSha256:'0'.repeat(64)},model,fetchImpl:provider(),paceMs:0}),/source drift/);
});
