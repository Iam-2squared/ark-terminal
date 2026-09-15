import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_MSII_ORDER_STYLE,
  createShadowOrderIntent,
  normalizeMarketSpeedReadOnlyEvent,
} from '../realtime/phase57-msii-shadow-execution.js';
import {cashUpstreamActionFromShadowIntent,validateCashUpstreamAction} from '../../tools/phase57_cash_upstream_action.mjs';

const AT='2026-09-03T00:35:00.000Z';
const SAFE={executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false};
function sourceEvent(){
  return normalizeMarketSpeedReadOnlyEvent({
    schemaVersion:2,phase:'58.p9.sync-capture',sourceMode:'MARKETSPEED_II_RSS_READ_ONLY',capturedAt:AT,symbol:'7203',sourceFunctions:['RssMarket','RssTickList'],
    market:{bestBid:100,bestAsk:100.2,bestBidSize:500,bestAskSize:500},ticks:[],
    phase57Snapshot:{direction:1,asOf:AT,modelId:'fixture',artifactSha256:'a'.repeat(64),frozen:true,futureOutcomeUsed:false,thresholdSearchAfterCapture:false,entryRetunedAfterCapture:false},
    methodology:{phase57DirectionIsFrozenBase:true,phase58MayConfirmDeferOrAbstainOnly:true,phase58MayReverseDirection:false,pointInTimeOnly:true,sameCaptureBoundary:true,futureOutcomeUsed:false,historicalDecisionReconstructionAllowed:false},safety:SAFE,
  },{marketSizeUnit:'SHARES',tickSizeUnit:'SHARES'});
}
function shadow(side='BUY',intentKind='ENTRY'){
  const referenceEvent=sourceEvent();
  return createShadowOrderIntent({strategyId:'V1_V3__MAX_3',symbol:'7203',side,intentKind,decisionAt:AT,decisionSequence:0,requestedQuantity:300,referencePrice:100.1,referenceEvent,orderStyleResearchLabel:PHASE57_MSII_ORDER_STYLE.MARKETABLE_QUOTE,ttlMs:5000,decisionLatencyMs:100,selectorVersion:'S',entryVersion:'E',exitVersion:'X',allocationVersion:'A',futureOutcomeUsed:false});
}

test('creates a hash-bound portable cash action from frozen upstream intent',()=>{
  const action=cashUpstreamActionFromShadowIntent(shadow());
  assert.equal(action.schemaId,'ARK_CASH_UPSTREAM_ACTION_V1');
  assert.equal(action.symbol,'7203.T');
  assert.equal(action.side,'BUY');
  assert.equal(action.positionEffect,'OPEN');
  assert.equal(action.quantity,300);
  assert.equal(action.estimatedNotional,30060);
  assert.equal(action.cashOnly,true);
  assert.equal(action.marginAllowed,false);
  assert.equal(action.shortSellingAllowed,false);
  assert.equal(action.transmitted,false);
  assert.match(action.actionSha256,/^[a-f0-9]{64}$/);
  assert.equal(validateCashUpstreamAction(action),action);
});

test('rejects tampering and short semantics before locked pipeline',()=>{
  const action=cashUpstreamActionFromShadowIntent(shadow());
  assert.throws(()=>validateCashUpstreamAction({...action,quantity:100}),/HASH_MISMATCH/);
  assert.throws(()=>cashUpstreamActionFromShadowIntent(shadow('SELL','ENTRY')),/CASH_LONG_ENTRY_BUY_ONLY/);
});
