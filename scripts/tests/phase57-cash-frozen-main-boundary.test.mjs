import assert from 'node:assert/strict';
import test from 'node:test';
import {adaptFrozenMainTraceToCashActions} from '../lib/phase57-cash-frozen-main-boundary.mjs';

const base=()=>({
  timestamp:'2026-09-03T00:35:00.000Z',
  entries:[],exits:[],openPositions:[],
});

test('maps accepted Frozen Main LONG entry without changing upstream sizing',()=>{
  const trace=base();
  trace.entries=[{eventId:'E1',symbol:'7203.T',direction:'LONG',quantity:300,entryNotionalJpy:300000,requiredCashJpy:300150}];
  const out=adaptFrozenMainTraceToCashActions(trace);
  assert.equal(out.status,'READY');
  assert.equal(out.actions.length,1);
  assert.deepEqual({symbol:out.actions[0].symbol,side:out.actions[0].side,positionEffect:out.actions[0].positionEffect,quantity:out.actions[0].quantity},
    {symbol:'7203.T',side:'BUY',positionEffect:'OPEN',quantity:300});
  assert.equal(out.actions[0].estimatedNotional,300000);
  assert.equal(out.actions[0].requiredCashJpy,300150);
  assert.equal(out.actions[0].allocation,'V3_B_RISK');
  assert.equal(out.actions[0].capacity,'MAX_3');
  assert.equal(out.marginAllowed,false);
  assert.equal(out.shortSellingAllowed,false);
  assert.equal(out.safety.transmitted,false);
});

test('blocks the entire bridge when Frozen Main accepted a SHORT entry',()=>{
  const trace=base();
  trace.entries=[{eventId:'S1',symbol:'7203.T',direction:'SHORT',quantity:100,entryNotionalJpy:100000,requiredCashJpy:100050}];
  const out=adaptFrozenMainTraceToCashActions(trace);
  assert.equal(out.status,'BLOCKED');
  assert.ok(out.blockers.includes('SHORT_ENTRY_ACCEPTED_UPSTREAM'));
  assert.equal(out.actions.length,0);
});

test('blocks when any upstream short position already exists, even if new entry is LONG',()=>{
  const trace=base();
  trace.openPositions=[{eventId:'S0',symbol:'6758.T',direction:'SHORT',quantity:100}];
  trace.entries=[{eventId:'L1',symbol:'7203.T',direction:'LONG',quantity:100,entryNotionalJpy:100000,requiredCashJpy:100050}];
  const out=adaptFrozenMainTraceToCashActions(trace);
  assert.equal(out.status,'BLOCKED');
  assert.ok(out.blockers.includes('SHORT_POSITION_PRESENT_UPSTREAM'));
  assert.equal(out.actions.length,0);
});

test('preserves exit-before-entry event ordering and requires reconciliation between multiple actions',()=>{
  const trace=base();
  trace.exits=[{eventId:'E0',symbol:'6758.T',direction:'LONG',quantity:100,referenceNotionalJpy:120000}];
  trace.entries=[{eventId:'E1',symbol:'7203.T',direction:'LONG',quantity:100,entryNotionalJpy:300000,requiredCashJpy:300150}];
  const out=adaptFrozenMainTraceToCashActions(trace);
  assert.equal(out.status,'READY');
  assert.equal(out.actions[0].side,'SELL');
  assert.equal(out.actions[0].positionEffect,'CLOSE');
  assert.equal(out.actions[1].side,'BUY');
  assert.equal(out.actions[1].positionEffect,'OPEN');
  assert.equal(out.requiresSequentialAccountReconciliation,true);
});

test('returns NO_ACTION for a clean idle Frozen Main trace',()=>{
  const out=adaptFrozenMainTraceToCashActions(base());
  assert.equal(out.status,'NO_ACTION');
  assert.equal(out.actions.length,0);
  assert.equal(out.requiresSequentialAccountReconciliation,false);
});
