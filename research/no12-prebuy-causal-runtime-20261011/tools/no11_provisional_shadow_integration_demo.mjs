#!/usr/bin/env node
/**
 * Fully synthetic No.1.1 integration-stage-1 smoke. ZERO private files,
 * ZERO broker/Excel/network access, ZERO order API. All times 2026-10-13
 * scenario timestamps; this is NOT a historical or live trade replay.
 */
import assert from 'node:assert/strict';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {CAUSAL_FRAME_SCHEMA} from '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';
import {NO12_CANDIDATES_SCHEMA} from '../runtime/prebuy_candidates.mjs';
import {NO11_PROVISIONAL_SCENARIO_SCHEMA,
  runNo11ProvisionalSyntheticShadow} from '../runtime/no11_provisional_shadow_integration.mjs';

const day='2026-10-13',at=t=>day+'T'+t+'+09:00';
const known=at('09:35:01');
const ob=(id,kind,source='09:35:00',received='09:35:01')=>({
 recordId:id,sourceType:kind,evidenceMode:'OBSERVED_READ_ONLY',
 sourceAsOf:at(source),observedAt:at(received),knownAt:at(received)
});
const core={
 schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',
 frozen:true,capturedAt:known,
 source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
 externalPositions:[{symbol:'408A.T',quantity:100}],
 arkManagedPositions:[]
};
const candidate=entryId=>({
 entryId,symbol:entryId==='e1'?'7203.T':'6758.T',
 selectorRecordId:'selector',stateRecordId:'state',
 marketRecordId:'price',candidateKnownAt:known,
 firstEntryScore:0.78,firstEntryThreshold:0.70,
 referencePrice:1000,quantity:100,
 formalState9Primary:'RISE'
});
const event=(kind,eventId,time,extras={})=>({
 kind,eventId,session:day,knownAt:at(time),...extras
});
const scenario={
 schemaId:NO11_PROVISIONAL_SCENARIO_SCHEMA,
 evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
 productionReady:false,orderTransmission:false,
 frozenNo11Modified:false,
 candidateInput:{
  batch:{schemaId:NO12_CANDIDATES_SCHEMA,session:day,
   decisionAt:at('09:36:00'),candidates:[candidate('e1'),candidate('e2')]},
  observationFrame:{schemaId:CAUSAL_FRAME_SCHEMA,
   session:day,decisionAt:at('09:36:00'),
   records:[
    ob('selector','TRADINGVIEW_SCANNER_OBSERVATION'),
    ob('state','ORIGINAL_NATIVE_FEATURE_OBSERVATION'),
    ob('price','MARKETSPEED_II_RSS_MARKET_OBSERVATION')
   ]},
  ownership:{...core,baselineSha256:digest(core)}
 },
 externalSymbols:['408A.T'],startingCashYen:1000000,
 entryEvents:[
  event('ENTRY_SIGNAL','e1-entry','09:36:01',{entryId:'e1',orderId:'buy-sim-1'}),
  event('BUY_FILL','e1-buy','09:37:00',{orderId:'buy-sim-1',
    quantity:100,fillPriceTenth:10000})
 ],
 exitObservationFrame:{schemaId:CAUSAL_FRAME_SCHEMA,
  session:day,decisionAt:at('10:00:00'),
  records:[ob('state-exit','ORIGINAL_NATIVE_FEATURE_OBSERVATION',
    '09:59:00','10:00:00')]},
 exitCheckpoints:[{symbol:'7203.T',stateRecordId:'state-exit',
  formalState9Primary:'SHARP_DROP',stateUsable:true,
  intentAlreadyIssued:false,controlIntentKnownAt:null}],
 postExitEvents:[
  event('SELL_FILL','e1-sell','10:02:00',{
   orderId:'no11-offline-exit-1',quantity:100,
   fillPriceTenth:10200,syntheticMatchedOrder:true
  }),
  event('ENTRY_SIGNAL','e2-replacement','10:02:00',
    {entryId:'e2',orderId:'must-block-after-first-sell'})
 ]
};
const out=runNo11ProvisionalSyntheticShadow({
 mode:'SYNTHETIC_OFFLINE_ONLY',scenario,now:new Date(at('10:03:00'))
});
assert.equal(out.preExitLedger.positions.length,1);
assert.equal(out.exitProposal.exits.length,1);
assert.equal(out.finalLedger.positions.length,0);
assert.equal(out.finalLedger.subsequentBuyProhibited,true);
assert(out.finalLedger.rejected.some(r=>r.reason==='AFTER_FIRST_SYNTHETIC_SELL_FILL_NO_BUY'));
assert.equal(out.nativeReadiness.originalNo11EndToEndCertified,false);
assert.equal(out.productionReady,false);
assert.equal(out.orderTransmission,false);
console.log('NO11_PROVISIONAL_2025_H235_DEVELOPMENT_LEARNING=COMPLETE_RESEARCH_ONLY');
console.log('NO11_INTEGRATION_SYNTHETIC_SOURCE_ASOF=PASS');
console.log('NO11_INTEGRATION_SYNTHETIC_ENTRY_TO_CASH=PASS');
console.log('NO11_INTEGRATION_SYNTHETIC_STATE9_SHARP_DROP_TO_EXIT_INTENT=PASS');
console.log('NO11_INTEGRATION_SYNTHETIC_SELL_FILL_AND_DAY_LATCH=PASS');
console.log('NO11_INTEGRATION_ORIGINAL_FROZEN_SELECTOR_EXECUTED=False');
console.log('NO11_INTEGRATION_ORIGINAL_FROZEN_H235_EXECUTED=False');
console.log('NO11_INTEGRATION_FROZEN_CAPITAL_SAB_EXECUTED=False');
console.log('NO11_INTEGRATION_NATIVE_E2E_CERTIFIED=False');
console.log('NO11_PRODUCTION_READY=False');
console.log('ORDER_TRANSMISSION=False');
