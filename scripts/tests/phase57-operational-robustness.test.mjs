import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createConnectionState,
  classifyFreshness,
  applyExternalCashFlow,
  reconcileState,
  constrainQuantity,
  createOperationalGate,
} from '../lib/phase57-operational-robustness.mjs';

test('connection state fails closed except HEALTHY',()=>{
  const c=createConnectionState();
  assert.equal(c.mustFailClosed(),true);
  c.transition('CONNECTING','START');
  c.transition('HEALTHY','SOURCE_READY');
  assert.equal(c.canEvaluate(),true);
  c.transition('STALE','HEARTBEAT_EXPIRED');
  assert.equal(c.mustFailClosed(),true);
  c.transition('UNKNOWN','STATE_NOT_CONFIRMED');
  c.transition('DISCONNECTED','SOURCE_LOST');
  c.transition('HALTED','STOP');
  assert.equal(c.state,'HALTED');
  assert.throws(()=>c.transition('HEALTHY'),/INVALID_CONNECTION_TRANSITION/);
});

test('freshness rejects future and stale timestamps',()=>{
  const observedAt='2026-08-13T09:05:10+09:00';
  assert.deepEqual(classifyFreshness({sourceTimestamp:'2026-08-13T09:05:00+09:00',observedAt,maxAgeMs:15000}),{status:'FRESH',ageMs:10000,decisionAllowed:true});
  assert.equal(classifyFreshness({sourceTimestamp:'2026-08-13T09:04:00+09:00',observedAt,maxAgeMs:15000}).status,'STALE');
  assert.equal(classifyFreshness({sourceTimestamp:'2026-08-13T09:06:00+09:00',observedAt,maxAgeMs:15000}).status,'FUTURE_TIMESTAMP');
});

test('external cash flow is separated from trading pnl',()=>{
  const base={cashJpy:1_000_000,equityJpy:1_200_000,tradingPnlJpy:200_000,externalCashFlowJpy:0};
  const afterDeposit=applyExternalCashFlow(base,{type:'DEPOSIT',amountJpy:100_000,id:'d1'});
  assert.equal(afterDeposit.cashJpy,1_100_000);
  assert.equal(afterDeposit.equityJpy,1_300_000);
  assert.equal(afterDeposit.tradingPnlJpy,200_000);
  assert.equal(afterDeposit.externalCashFlowJpy,100_000);
  const afterWithdrawal=applyExternalCashFlow(afterDeposit,{type:'WITHDRAWAL',amountJpy:250_000,id:'w1'});
  assert.equal(afterWithdrawal.cashJpy,850_000);
  assert.equal(afterWithdrawal.equityJpy,1_050_000);
  assert.equal(afterWithdrawal.tradingPnlJpy,200_000);
  assert.equal(afterWithdrawal.externalCashFlowJpy,-150_000);
  assert.throws(()=>applyExternalCashFlow({cashJpy:100,equityJpy:100},{type:'WITHDRAWAL',amountJpy:101}),/EXCEEDS_CASH/);
});

test('reconciliation locks decisions on position or balance mismatch',()=>{
  const expected={cashJpy:500_000,equityJpy:1_000_000,grossExposureJpy:500_000,absoluteNetExposureJpy:500_000,positions:[{symbol:'1111.T',direction:'LONG',quantity:100}]};
  assert.equal(reconcileState(expected,structuredClone(expected)).decisionAllowed,true);
  const wrong={...structuredClone(expected),positions:[{symbol:'1111.T',direction:'LONG',quantity:200}]};
  const r=reconcileState(expected,wrong);
  assert.equal(r.reconciled,false);
  assert.equal(r.nextState,'UNKNOWN');
  assert.ok(r.mismatches.some(x=>x.field==='quantity'));
});

test('quantity constraint is deterministic and lot-safe',()=>{
  const r=constrainQuantity({desiredQuantity:750,priceJpy:1200,lotSize:100,maxQuantity:600,maxNotionalJpy:500_000,availableCashJpy:1_000_000});
  assert.equal(r.desiredQuantity,700);
  assert.equal(r.finalQuantity,400);
  assert.equal(r.finalNotionalJpy,480_000);
  assert.equal(r.constrained,true);
  assert.deepEqual(r.reasons,['MAX_NOTIONAL']);
});

test('operational gate requires healthy connection and reconciliation',()=>{
  const g=createOperationalGate();
  assert.equal(g.decisionAllowed(),false);
  g.connection.transition('CONNECTING','START');
  g.connection.transition('HEALTHY','READY');
  assert.equal(g.decisionAllowed(),false);
  g.markReconciled(true);
  assert.equal(g.decisionAllowed(),true);
  g.connection.transition('STALE','STALE_DATA');
  assert.equal(g.decisionAllowed(),false);
});

test('failed reconciliation transitions healthy gate to UNKNOWN',()=>{
  const g=createOperationalGate({connectionState:'HEALTHY'});
  g.markReconciled(false);
  assert.equal(g.connection.state,'UNKNOWN');
  assert.equal(g.decisionAllowed(),false);
});
