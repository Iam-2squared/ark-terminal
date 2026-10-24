#!/usr/bin/env node
// Fully self-contained *synthetic* No.1.2 end-to-end READ ONLY scenario.
// No env variables, no private records, no downloads, no files created.
import assert from 'node:assert/strict';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {CAUSAL_FRAME_SCHEMA} from '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';
import {NO12_CANDIDATES_SCHEMA} from '../runtime/prebuy_candidates.mjs';
import {runNo12SyntheticSession} from '../runtime/synthetic_cash_lifecycle.mjs';

const session='2026-10-13',decisionAt='2026-10-13T09:36:00+09:00';
const known='2026-10-13T09:35:01+09:00';
function observation(recordId,sourceType){
  return {recordId,sourceType,evidenceMode:'OBSERVED_READ_ONLY',
    sourceAsOf:'2026-10-13T09:35:00+09:00',
    observedAt:known,knownAt:known};
}
const observationFrame={schemaId:CAUSAL_FRAME_SCHEMA,session,decisionAt,
  records:[observation('SEL','TRADINGVIEW_SCANNER_OBSERVATION'),
    observation('S9','ORIGINAL_NATIVE_FEATURE_OBSERVATION'),
    observation('PX','MARKETSPEED_II_RSS_MARKET_OBSERVATION')]};
const candidate=(entryId,symbol)=>({entryId,symbol,
  selectorRecordId:'SEL',stateRecordId:'S9',marketRecordId:'PX',
  candidateKnownAt:known,firstEntryScore:.7,firstEntryThreshold:.5,
  referencePrice:1000,quantity:100,formalState9Primary:'RISE'});
const batch={schemaId:NO12_CANDIDATES_SCHEMA,session,decisionAt,
  candidates:[candidate('test-entry-1','7203'),candidate('test-entry-2','6758')]};
const baselineCore={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',
  frozen:true,capturedAt:known,source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
  externalPositions:[{symbol:'408A.T',quantity:100}],arkManagedPositions:[]};
const ownership={...baselineCore,baselineSha256:digest(baselineCore)};
const ev=(kind,eventId,hhmm,extra)=>({kind,eventId,session,knownAt:'2026-10-13T'+hhmm+':00+09:00',...extra});
const events=[
  ev('ENTRY_SIGNAL','entry-1','09:36',{entryId:'test-entry-1',orderId:'synthetic-buy'}),
  ev('BUY_FILL','buy-fill','09:37',{orderId:'synthetic-buy',quantity:100,fillPriceTenth:10000}),
  ev('SELL_INTENT','exit-intent','10:00',{orderId:'synthetic-sell',symbol:'7203',quantity:100}),
  ev('ENTRY_SIGNAL','entry-after','10:02',{entryId:'test-entry-2',orderId:'should-be-blocked'}),
  ev('SELL_FILL','sell-fill','10:02',{orderId:'synthetic-sell',quantity:100,
    fillPriceTenth:10200,syntheticMatchedOrder:true})
];
const result=runNo12SyntheticSession({mode:'SYNTHETIC_OFFLINE_ONLY',
  candidateInput:{batch,observationFrame,ownership},events,
  startingCashYen:1000000,externalSymbols:['408A.T'],
  now:new Date('2026-10-13T10:03:00+09:00')});
assert.equal(result.status,'SYNTHETIC_SCENARIO_EVALUATED');
assert.equal(result.history.filter(x=>x.type==='SYNTHETIC_BUY_FILL').length,1);
assert.equal(result.history.filter(x=>x.type==='SYNTHETIC_SELL_FILL').length,1);
assert(result.rejected.some(x=>x.reason==='AFTER_FIRST_SYNTHETIC_SELL_FILL_NO_BUY'));
assert.equal(result.positions.length,0);
assert.equal(result.subsequentBuyProhibited,true);
assert.equal(result.orderTransmission,false);
assert.equal(result.originalFrozenR0Reproduced,false);
assert.equal(result.productionReady,false);
console.log('NO12_SYNTHETIC_FULL_LIFECYCLE_PASS=True');
console.log('NO12_SYNTHETIC_PERSONAL_EXCLUDED=True');
console.log('NO12_SYNTHETIC_SELL_FILL_HALTS_NEW_BUY=True');
console.log('NO12_ORIGINAL_NO11_R0_REPRODUCED=False');
console.log('NO12_NATIVE_STRATEGY_CERTIFIED=False');
console.log('NO12_LIVE_ORDER_ENABLED=False');
