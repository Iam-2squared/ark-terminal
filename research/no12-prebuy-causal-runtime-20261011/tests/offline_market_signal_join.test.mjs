import test from 'node:test';
import assert from 'node:assert/strict';
import {assembleNo12OfflineChartCandidate as join} from '../runtime/offline_market_signal_join.mjs';
import {inspectNo12RssChartSnapshot as chart,NO12_CHART_SCHEMA,RSS_CHART_COLUMNS} from '../runtime/msii_rss_chart_observation.mjs';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
const decisionAt='2026-10-13T09:36:20+09:00';
function specimen(){
 const capture='2026-10-13T09:36:10+09:00';
 const snap={schemaId:NO12_CHART_SCHEMA,sourceFunction:'RssChart',period:'5M',
  evidenceMode:'OBSERVED_READ_ONLY',symbol:'7203.T',
  capturedAt:capture,columns:[...RSS_CHART_COLUMNS],
  rows:[{'日付':'2026/10/13','時刻':'09:30','足種':'5M','始値':1020,'高値':1022,
   '安値':1018,'終値':1020,'出来高':1000}]};
 const chartAudit=chart({snapshot:snap,decisionAt,now:new Date('2026-10-13T09:36:22+09:00')});
 const record=(recordId,sourceType,knownAt)=>({
   recordId,sourceType,evidenceMode:'OBSERVED_READ_ONLY',
   sourceAsOf:'2026-10-13T09:35:00+09:00',
   observedAt:knownAt,knownAt
 });
 const selectorInput={evidenceMode:'OBSERVED_READ_ONLY',symbol:'7203.T',
   entryId:'first-20261013-01',firstEntryScore:.7,firstEntryThreshold:.5,
   observation:record('selector-01','TRADINGVIEW_SCANNER_OBSERVATION','2026-10-13T09:36:12+09:00')};
 const stateInput={evidenceMode:'OBSERVED_READ_ONLY',symbol:'7203.T',
   formalState9Primary:'RISE',observation:record('state-01','ORIGINAL_NATIVE_FEATURE_OBSERVATION','2026-10-13T09:36:14+09:00')};
 const core={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',frozen:true,capturedAt:capture,
  source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
  externalPositions:[{symbol:'408A.T',quantity:100}],arkManagedPositions:[]};
 return {mode:'SYNTHETIC_OFFLINE_ONLY',chartAudit,selectorInput,stateInput,
   ownership:{...core,baselineSha256:digest(core)},
   decisionAt,syntheticQuantity:100,now:new Date('2026-10-13T09:36:22+09:00')};
}
test('READ ONLY market price and later State9/Selector receipt become a single non-trading synthetic candidate',()=>{
 const x=join(specimen());
 assert.equal(x.status,'SYNTHETIC_CHART_SELECTOR_STATE_JOIN_NOT_LIVE');
 assert.equal(x.candidateResult.eligible.length,1);
 const r=x.candidateResult.eligible[0];
 assert.equal(r.syntheticReferencePrice,1020);
 assert.equal(Date.parse(x.latestInputKnownAt),
  Date.parse('2026-10-13T09:36:14+09:00'));
 assert.equal(Date.parse(r.sourceKnownAt),Date.parse(x.latestInputKnownAt));
 assert.equal(x.selectedRecordIds.length,3);
 assert.equal(x.originalNativeState9Certified,false);
 assert.equal(x.originalNativeSelectorCertified,false);
 assert.equal(x.orderTransmission,false);
 assert.equal(x.productionReady,false);
});
test('no automatic trading when State9 rejects PULLBACK/SHARP_DROP or unknown',()=>{
 for(const state of ['PULLBACK','SHARP_DROP','UNKNOWN']){
  const f=specimen();f.stateInput.formalState9Primary=state;
  const r=join(f);assert.equal(r.candidateResult.eligible.length,0);
  assert.equal(r.candidateResult.declined.length,1);
 }
});
test('personal EXTERNAL stock symbol cannot enter new Ark BUY',()=>{
 const f=specimen();
 const core={...f.ownership,externalPositions:[{symbol:'7203.T',quantity:100}]};
 delete core.baselineSha256;
 f.ownership={...core,baselineSha256:digest(core)};
 const r=join(f);
 assert.equal(r.candidateResult.eligible.length,0);
 assert.equal(r.candidateResult.declined[0].reason,'EXTERNAL_PERSONAL_SYMBOL_PROTECTED');
});
test('wrong symbol, future State9, missing entry score and fake LIVE source all fail',()=>{
 const s=specimen();s.stateInput.symbol='6758.T';
 assert.throws(()=>join(s),/NO12_SOURCE_JOIN_SYMBOL_MISMATCH/);
 const f=specimen();f.stateInput.observation.knownAt='2026-10-13T09:37:00+09:00';
 assert.throws(()=>join(f),/NO12_SOURCE_JOIN_FUTURE_INPUT/);
 const v=specimen();delete v.selectorInput.firstEntryScore;
 assert.throws(()=>join(v),/NO12_SOURCE_JOIN_FIRST_ENTRY_SCORE_NOT_PROVIDED/);
 const z=specimen();z.mode='LIVE_ATTESTED';
 assert.throws(()=>join(z),/NO12_REAL_SOURCE_JOIN_NOT_IMPLEMENTED/);
 const a=specimen();a.selectorInput.sourceCertified=true;
 assert.throws(()=>join(a),/NO12_SELECTOR_LIVE_SOURCE_CLAIM_FORBIDDEN/);
});
test('unavailable market chart and unsafe State9 origin never manufacture a live signal',()=>{
 const f=specimen();f.chartAudit={...f.chartAudit,status:'NO_CURRENT_SESSION_COMPLETED_BAR'};
 assert.throws(()=>join(f),/NO12_CHART_NOT_A_VERIFIED_READONLY_OBSERVATION/);
 const x=specimen();x.stateInput.observation.sourceType='FABRICATED';
 assert.throws(()=>join(x),/NO12_STATE9_OBSERVATION_CONTRACT_INVALID/);
 const n=specimen();n.syntheticQuantity=50;
 assert.throws(()=>join(n),/NO12_SOURCE_JOIN_SYNTHETIC_100_LOT_REQUIRED/);
});
