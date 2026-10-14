import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {CAUSAL_FRAME_SCHEMA} from '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';
import {NO12_CANDIDATES_SCHEMA} from '../runtime/prebuy_candidates.mjs';
import {
 inspectNo11ProvisionalIntegrationPolicy,
 inspectNo11ProvisionalH235ResearchReceipts,
 runNo11ProvisionalSyntheticShadow,
 NO11_PROVISIONAL_SCENARIO_SCHEMA
} from '../runtime/no11_provisional_shadow_integration.mjs';

const session='2026-10-13',at=s=>'2026-10-13T'+s+'+09:00';
const rec=(recordId,sourceType,stamp='09:35:00',known='09:35:01')=>({
  recordId,sourceType,evidenceMode:'OBSERVED_READ_ONLY',
  sourceAsOf:at(stamp),observedAt:at(known),knownAt:at(known)
});
function ownership(){
 const core={
  schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',frozen:true,
  capturedAt:at('09:35:01'),
  source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
  externalPositions:[{symbol:'408A.T',quantity:100}],
  arkManagedPositions:[]
 };
 return {...core,baselineSha256:digest(core)};
}
function receipt(head,modelSha,probability){
 return {
   schemaId:'ARK_NO11_ASOF_RESEARCH_OFFLINE_SCORE_V1',
   mode:'OFFLINE_RESEARCH_ONLY',head,
   research_probability:probability,
   modelSha256:modelSha.repeat(64),featureSha256:'f'.repeat(64),
   '2026NativeSelectorEntryRebuilt':false,
   '2026SupervisedTrainingRows':0,
   brokerActualKnownAtCertified:false,newModelAutomaticallyPromoted:false,
   productionReady:false,orderTransmission:false
 };
}
const scores=()=>[
 receipt('H2','a',0.453606924416),
 receipt('H3','b',0.253556948826),
 receipt('H5','c',0.079068561129)
];
const event=(kind,eventId,t,extra={})=>({
 kind,eventId,session,knownAt:at(t),...extra
});
function scenario(){
 const decisionAt=at('09:36:00'),known=at('09:35:01');
 const records=[
   rec('sel','TRADINGVIEW_SCANNER_OBSERVATION'),
   rec('s9','ORIGINAL_NATIVE_FEATURE_OBSERVATION'),
   rec('px','MARKETSPEED_II_RSS_MARKET_OBSERVATION')
 ];
 const cand=(entryId,symbol)=>({
   entryId,symbol,selectorRecordId:'sel',stateRecordId:'s9',
   marketRecordId:'px',candidateKnownAt:known,
   firstEntryScore:0.7,firstEntryThreshold:0.5,
   referencePrice:1000,quantity:100,formalState9Primary:'RISE'
 });
 return {
   schemaId:NO11_PROVISIONAL_SCENARIO_SCHEMA,
   evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
   productionReady:false,orderTransmission:false,
   frozenNo11Modified:false,startingCashYen:1000000,
   externalSymbols:['408A.T'],
   candidateInput:{
     batch:{schemaId:NO12_CANDIDATES_SCHEMA,session,decisionAt,
       candidates:[cand('e1','7203.T'),cand('e2','6758.T')]},
     observationFrame:{schemaId:CAUSAL_FRAME_SCHEMA,session,decisionAt,records},
     ownership:ownership()
   },
   entryEvents:[
     event('ENTRY_SIGNAL','signal-e1','09:36:02',
       {entryId:'e1',orderId:'offline-buy'}),
     event('BUY_FILL','fill-e1','09:37:00',
       {orderId:'offline-buy',quantity:100,fillPriceTenth:10000})
   ],
   provisionalH235SampleReceipts:scores(),
   exitObservationFrame:{
     schemaId:CAUSAL_FRAME_SCHEMA,session,
     decisionAt:at('10:00:00'),records:[
       rec('exit-state','ORIGINAL_NATIVE_FEATURE_OBSERVATION',
           '09:59:00','10:00:00')
     ]
   },
   exitCheckpoints:[{
     symbol:'7203.T',stateRecordId:'exit-state',
     stateUsable:true,formalState9Primary:'SHARP_DROP',
     intentAlreadyIssued:false,controlIntentKnownAt:null
   }],
   postExitEvents:[
     event('SELL_FILL','offline-sell-fill','10:02:00',{
       orderId:'no11-offline-exit-1',quantity:100,
       fillPriceTenth:10200,syntheticMatchedOrder:true
     }),
     event('ENTRY_SIGNAL','reoffer-after-sell','10:02:00',{
       entryId:'e2',orderId:'must-not-open-new-buy'
     })
   ]
 };
}
const run=s=>runNo11ProvisionalSyntheticShadow({
 mode:'SYNTHETIC_OFFLINE_ONLY',scenario:s,now:new Date(at('10:03:00'))
});

test('Original No.1.1 immutable policy and user-selected provisional H2/H3/H5 are pinned',()=>{
 const m=inspectNo11ProvisionalIntegrationPolicy();
 assert.equal(m.status,'2025_H235_PROVISIONAL_RESEARCH_FIXED_FOR_SYNTHETIC_INTEGRATION');
 assert.equal(m.trainingExamples2026,0);
 assert.equal(m.frozenOriginalModelsReplaced,false);
 assert.equal(m.orderTransmission,false);
});

test('H2/H3/H5 2025 smoke receives a separate, NEVER 2026 ranking input',()=>{
 const p=inspectNo11ProvisionalH235ResearchReceipts(scores());
 assert.equal(p.modelReceiptsInspected,3);
 assert.equal(p.researchSampleProbabilities.H2,0.453606924416);
 assert.equal(p.usableFor2026CandidateRanking,false);
 const noModel=inspectNo11ProvisionalH235ResearchReceipts();
 assert.equal(noModel.modelReceiptsInspected,0);
 const bad=scores();bad[1].featureSha256='d'.repeat(64);
 assert.throws(()=>inspectNo11ProvisionalH235ResearchReceipts(bad),
   /FEATURE_ROW_MISMATCH/);
 const unsafe=scores();unsafe[0].newModelAutomaticallyPromoted=true;
 assert.throws(()=>inspectNo11ProvisionalH235ResearchReceipts(unsafe),
   /UNAPPROVED/);
 const repeated=scores();repeated[2].modelSha256=repeated[1].modelSha256;
 assert.throws(()=>inspectNo11ProvisionalH235ResearchReceipts(repeated),
   /DUPLICATED_MODEL_HASH/);
});

test('Full synthetic chain executes chronological BUY, State9 emergency EXIT, SELL FILL, and frozen wait latch',()=>{
 const result=run(scenario());
 assert.equal(result.status,'SYNTHETIC_STAGE_WIRING_PASS_NATIVE_NO11_NOT_CERTIFIED');
 assert.equal(result.stages.firstEntry.eligible,2);
 assert.equal(result.stages.h235.modelReceiptsInspected,3);
 assert.equal(result.stages.h235.usableFor2026CandidateRanking,false);
 assert.equal(result.preExitLedger.positions.length,1);
 assert.equal(result.preExitLedger.positions[0].symbol,'7203.T');
 assert.equal(result.exitProposal.exits.length,1);
 assert.equal(result.syntheticExitIntents.length,1);
 assert.equal(result.syntheticExitIntents[0].orderId,'no11-offline-exit-1');
 assert.equal(result.finalLedger.positions.length,0);
 assert.equal(result.finalLedger.history.filter(x=>x.type==='SYNTHETIC_SELL_FILL').length,1);
 assert.equal(result.finalLedger.subsequentBuyProhibited,true);
 assert.ok(result.finalLedger.rejected.some(x=>x.reason==='AFTER_FIRST_SYNTHETIC_SELL_FILL_NO_BUY'));
 assert.equal(result.stages.capital.nativeCapitalV5Executed,false);
 assert.equal(result.stages.exit.originalStructuralExitExecuted,false);
 assert.equal(result.nativeReadiness.originalNo11EndToEndCertified,false);
 assert.equal(result.productionReady,false);
 assert.equal(result.orderTransmission,false);
});

test('Neither missing 2025 model samples nor modified probability drives synthetic Capital or Entry',()=>{
 const withScores=scenario();
 const ordinary=run(withScores);
 const absent=scenario();delete absent.provisionalH235SampleReceipts;
 const a=run(absent);
 assert.deepEqual(a.finalLedger,ordinary.finalLedger);
 const changed=scenario();changed.provisionalH235SampleReceipts[0].research_probability=0.01;
 assert.deepEqual(run(changed).finalLedger,ordinary.finalLedger);
 assert.equal(a.stages.h235.modelReceiptsInspected,0);
});

test('No positive/negative future label or actual fill can reach pre-BUY observation graph',()=>{
 for(const [key,val] of [['futureHigh',1500],['teacherLabel',1],
    ['fill_price',1200],['realizedPnl',10000],['outcome',true]]){
   const s=scenario();
   s.candidateInput.batch.candidates[0][key]=val;
   assert.throws(()=>run(s),/PREBUY_FUTURE_OR_FILL_FIELD/);
 }
});

test('No live mode, no unsafe owner, no real transmission, no fake EXIT fill',()=>{
 const x=scenario();
 assert.throws(()=>runNo11ProvisionalSyntheticShadow({
    mode:'LIVE_TRADING',scenario:x,now:new Date(at('10:03:00'))
  }),/LIVE_OR_BROKER_MODE_DISABLED/);
 const y=scenario();y.productionReady=true;
 assert.throws(()=>run(y),/SCENARIO_FLAGS_INVALID/);
 const z=scenario();z.postExitEvents[0].orderId='not-issued';
 assert.throws(()=>run(z),/EXIT_FILL_WITHOUT_PROPOSAL/);
 const q=scenario();q.entryEvents[1].quantity=30;
 assert.throws(()=>run(q),/ENTRY_RECONCILIATION_BLOCK/);
 const f=scenario();f.candidateInput.batch.candidates[0].symbol='408A.T';
 assert.throws(()=>run(f),/EXIT_FILL_WITHOUT_PROPOSAL/);
 delete f.postExitEvents;
 assert.equal(run(f).stages.firstEntry.eligible,1);
});

test('EXIT cannot be injected before BUY fill or without a State9 checkpoint',()=>{
 const x=scenario();x.exitObservationFrame.decisionAt=at('09:36:00');
 assert.throws(()=>run(x),/EXIT_BEFORE_OR_AT_ENTRY/);
 const y=scenario();delete y.exitObservationFrame;
 assert.throws(()=>run(y),/EXIT_EVENTS_WITHOUT_CHECKPOINT/);
 const z=scenario();z.exitCheckpoints[0].controlIntentKnownAt=at('10:00:00');
 delete z.postExitEvents;
 const plan=run(z);
 assert.equal(plan.exitProposal.exits.length,0);
 assert.equal(plan.exitProposal.pending[0].reason,'ORIGINAL_CONTROL_EXIT_PRIORITY');
 assert.equal(plan.finalLedger.positions.length,1);
});

test('Integration stage never imports live broker/Excel/order APIs or marks production true',()=>{
 const source=fs.readFileSync(new URL('../runtime/no11_provisional_shadow_integration.mjs',import.meta.url),'utf8');
 for(const forbidden of [
   /RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/Excel\.Application/,
   /node:net/,/node:http/,/fetch\s*\(/,/productionReady\s*:\s*true/,
   /orderTransmission\s*:\s*true/
 ])assert.doesNotMatch(source,forbidden);
});

test('Actual frozen Capital V5 Python S/A/B is executed on synthetic ranked entry before cash and EXIT',()=>{
 const s=scenario();
 s.startingCashYen=700000;
 s.candidateInput.batch.candidates[0].quantity=300;
 s.entryEvents[1].quantity=300;
 s.postExitEvents[0].quantity=300;
 s.syntheticFrozenV5Request={
   schemaId:'ARK_NO11_FROZEN_V5_SYNTHETIC_BRIDGE_V1',
   evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
   strategyFreezeCommit:'10c94c92c4bd2a59a22744667fd0210252602df4',
   capitalAuthorityCommit:'710656491be06235901b45c50a8b5cbd714ba4eb',
   researchInputProvenance:'EXPLICIT_SYNTHETIC_NOT_H235_RANK',
   productionReady:false,orderTransmission:false,
   afterFirstLegalSellFill:false,pendingBrokerOrders:false,sessionVerified:false,
   arkCapitalInputs:{cash:700000,equity:700000,exposure:0},
   externalSymbols:['408A.T'],arkManagedSymbols:[],existingBands:[],
   minute:576,
   preorderedCandidates:[{
     entry_id:'e1',brokerSymbol:'7203.T',rank:'S',
     ML:2.5,capital_score:2.2,raw_reference:'1000',block:'1'
   }],
   syntheticTrainingTables:{'1':{
      minute_counts:{'576':[1,0,2]},training_session_N:10,
      B_median:1.3,B_p75:1.4,minute_bucket:{'576':'synthetic'}
   }}
 };
 const r=run(s);
 assert.equal(r.frozenV5SyntheticAllocation.fundedCount,1);
 assert.equal(r.frozenV5SyntheticAllocation.fundedEntries[0].quantity,300);
 assert.equal(r.frozenV5SyntheticAllocation.allocatedDebitJpy,'300150.0000');
 assert.equal(r.stages.capital.originalFrozenCapitalV5PythonExecutedOnSynthetic,true);
 assert.equal(r.stages.capital.nativeCapitalV5Executed,false);
 assert.equal(r.preExitLedger.endingCashYen,'399850.00');
 assert.equal(r.preExitLedger.positions[0].quantity,300);
 assert.equal(r.exitProposal.exits[0].quantity,300);
 assert.equal(r.finalLedger.endingCashYen,'705697.00');
 assert.equal(r.finalLedger.positions.length,0);
 assert.equal(r.finalLedger.subsequentBuyProhibited,true);
 assert.equal(r.nativeReadiness.originalFrozenCapitalV5PythonRunOnSynthetic,true);
 assert.equal(r.nativeReadiness.frozenCapitalV5SabExecuted,false);
 assert.equal(r.productionReady,false);
 assert.equal(r.orderTransmission,false);
});
