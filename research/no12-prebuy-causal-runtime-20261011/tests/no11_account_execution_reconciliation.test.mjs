import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {LOCKED_FLAGS} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {reconcileAccountExecutions as reconcile} from '../tools/no11_account_execution_reconciliation.mjs';
import {observe,ENVELOPE} from '../tools/no11_account_observation.mjs';
const day='2026-10-26',at=s=>`${day}T09:30:${String(s).padStart(2,'0')}+09:00`;
function snap(second=10){return {schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',source:'MARKETSPEED_II_RSS',mode:'READ_ONLY',safety:{...LOCKED_FLAGS},capturedAt:at(second-2),captureCompletedAt:at(second),orders:[],executions:[],positions:[],buyingPower:1000000}}
function order(q=100,side='BUY',id='123'){return {orderNumber:id,symbol:'7203',account:'特定',side:side==='BUY'?'買付':'売付',trade:'現物',quantity:q,filledQty:q,status:'約定'}}
function execution(q=100,price=100.1,side='BUY'){return {symbol:'7203',account:'特定',side:side==='BUY'?'買付':'売付',quantity:q,price,executionDate:'2026/10/26 09:30:04'}}
const pos=q=>({symbol:'7203',account:'特定',quantity:q});
const run=(snapshot,previous=null)=>reconcile({snapshot,sessionDate:day,previous});
function filled(second=10){const s=snap(second);s.orders=[order()];s.executions=[execution()];s.positions=[pos(100)];return s}
function envelope(s,seq=1){const rss={capacity:'完了',orders:'配信中',executions:'配信中',positions:'配信中'};return {
 schemaId:ENVELOPE,runId:'a'.repeat(32),sequence:seq,status:'OBSERVED',readOnly:true,productionReady:false,orderTransmission:false,
 snapshot:{...s,rssStatus:rss},health:{schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',readOnly:true,addinLoaded:true,workbookPersisted:true,rssErrors:0,actualFeedTimestampCertified:false,
 healthCapturedAt:s.captureCompletedAt,feeds:Object.fromEntries(Object.entries(rss).map(([k,state])=>[k,{state,observedAt:s.captureCompletedAt}]))}}}

test('empty snapshot records a baseline but never certifies spendable cash or actual fills',()=>{
 const r=run(snap());assert.deepEqual(r.report.blockers,[]);assert.equal(r.report.positionConservationCompared,false);
 for(const k of ['buyingPowerIsCash','feesAndTaxesReconciled','spendableCashReconciled','realAccountLedgerUpdated','realFillsAppliedToShadow','executionAllowed','orderTransmission','productionReady'])assert.equal(r.report[k],false,k);
 assert.equal(r.report.observedGrossCashFlowJpy,'0');
});
test('observed decimal price times quantity is exact gross consideration not a fee-adjusted balance',()=>{
 const r=run(filled());assert.equal(r.report.observedGrossBuyConsiderationJpy,'10010');assert.equal(r.report.observedGrossCashFlowJpy,'-10010');
 assert.equal(r.report.groups[0].quantityMatched,true);assert.equal(r.report.groups[0].individualOrderPriceAttributed,false);
});
test('identical execution rows preserve multiplicity rather than silently deduplicating partial fills',()=>{
 const s=filled();s.orders=[order(200)];s.positions=[pos(200)];s.executions.push({...s.executions[0]});
 const r=run(s);assert.equal(r.report.groups[0].executionQuantity,200);assert.equal(r.report.observedGrossBuyConsiderationJpy,'20020');
 assert.equal(Object.values(r.state.seenExecutionRows)[0],2);assert.deepEqual(r.report.blockers,[]);
});
test('two same-symbol orders do not become a fabricated execution-price to order-number mapping',()=>{
 const s=filled();s.orders.push(order(100,'BUY','456'));s.executions=[execution(200)];s.positions=[pos(200)];
 const r=run(s);assert.equal(r.report.groups[0].filledOrderCount,2);assert.equal(r.report.individualOrderPriceAttributed,false);
 assert.equal(r.report.groups[0].grossConsiderationJpy,'20020');
});
test('separate account classes cannot be netted together to hide a quantity mismatch',()=>{
 const s=filled();s.executions[0].account='一般';const r=run(s);
 assert.equal(r.report.groups.length,2);assert.ok(r.report.blockers.includes('ORDER_EXECUTION_QUANTITY_MISMATCH'));
});
test('BUY and SELL quantities cannot cancel each other in the order-execution comparison',()=>{
 const s=filled();s.executions[0].side='売付';const r=run(s);
 assert.equal(r.report.groups.length,2);assert.ok(r.report.blockers.includes('ORDER_EXECUTION_QUANTITY_MISMATCH'));
});
test('BUY receipt explains only the corresponding observed position increase',()=>{
 const first=run(snap()),second=run(filled(15),first.state);
 assert.equal(second.report.positionConservationCompared,true);assert.deepEqual(second.report.blockers,[]);
 assert.equal(second.report.positionChecks[0].expectedQuantity,100);assert.equal(second.report.positionChecks[0].observedQuantity,100);
});
test('SELL receipt explains a partial reduction but never asserts the remaining position is closed',()=>{
 const s=snap();s.positions=[pos(200)];const first=run(s),next=snap(15);
 next.orders=[order(100,'SELL')];next.executions=[execution(100,101,'SELL')];next.positions=[pos(100)];
 const r=run(next,first.state);assert.deepEqual(r.report.blockers,[]);assert.equal(r.report.positionChecks[0].expectedQuantity,100);
 assert.equal(r.report.observedGrossSellConsiderationJpy,'10100');
});
test('BUY and SELL round trip reconciles zero remaining quantity and separately reports gross flow',()=>{
 const first=run(snap()),s=snap(15);s.orders=[order(),order(100,'SELL','456')];s.executions=[execution(),execution(100,110.1,'SELL')];
 const r=run(s,first.state);assert.deepEqual(r.report.blockers,[]);assert.equal(r.report.positionChecks[0].expectedQuantity,0);
 assert.equal(r.report.observedGrossCashFlowJpy,'1000');assert.equal(r.report.spendableCashReconciled,false);
});
test('an unexplained position increase is blocked, not imported as an Ark BUY',()=>{
 const first=run(snap()),next=snap(15);next.positions=[pos(100)];const r=run(next,first.state);
 assert.ok(r.report.blockers.includes('POSITION_EXECUTION_QUANTITY_MISMATCH'));assert.equal(r.report.realAccountLedgerUpdated,false);
});
test('filled order without its execution receipt is not assigned an invented price',()=>{
 const s=snap();s.orders=[order()];s.positions=[pos(100)];const r=run(s);
 assert.ok(r.report.blockers.includes('ORDER_EXECUTION_QUANTITY_MISMATCH'));assert.equal(r.report.observedGrossBuyConsiderationJpy,'0');
});
test('execution received before the position list catches up blocks until the lists agree',()=>{
 const baseline=run(snap()),late=filled(15);late.positions=[];const a=run(late,baseline.state);
 assert.ok(a.report.blockers.includes('POSITION_EXECUTION_QUANTITY_MISMATCH'));
 const b=run(filled(20),a.state);assert.deepEqual(b.report.blockers,[]);
});
test('already present executions form the baseline and are not applied a second time',()=>{
 const a=run(filled()),b=run(filled(15),a.state);assert.deepEqual(b.report.blockers,[]);
 assert.equal(b.report.positionChecks[0].expectedQuantity,100);
});
test('partial cancellation still requires the observed executed quantity and keeps its gross cost',()=>{
 const s=filled();s.orders[0].quantity=200;s.orders[0].status='取消済（出来有）';
 const r=run(s);assert.equal(r.report.groups[0].orderFilledQuantity,100);assert.equal(r.report.observedGrossBuyConsiderationJpy,'10010');
});
test('unfilled pending order has no execution-derived money or position',()=>{
 const s=snap();s.orders=[{...order(200),filledQty:0,status:'執行中'}];const r=run(s);
 assert.equal(r.report.observedGrossCashFlowJpy,'0');assert.equal(r.report.groups[0].executionQuantity,0);
});
test('execution row disappearance remains unresolved after restart and reappearance',()=>{
 const a=run(filled()),empty=snap(15);empty.positions=[pos(100)];const b=run(empty,JSON.parse(JSON.stringify(a.state)));
 assert.ok(b.report.blockers.includes('EXECUTION_ROWS_REMOVED_OR_REVISED'));
 const c=run(filled(20),JSON.parse(JSON.stringify(b.state)));assert.ok(c.report.blockers.includes('EXECUTION_ROWS_REMOVED_OR_REVISED'));
});
test('a reduction in identical row multiplicity is not hidden by a deduplicated set',()=>{
 const s=filled();s.orders=[order(200)];s.positions=[pos(200)];s.executions.push({...s.executions[0]});const a=run(s);
 const b=run(filled(15),a.state);assert.ok(b.report.blockers.includes('EXECUTION_ROWS_REMOVED_OR_REVISED'));
});
test('execution price correction is reported as revised source rather than silently applied twice',()=>{
 const a=run(filled()),s=filled(15);s.executions[0].price=101.1;
 const r=run(s,a.state);assert.ok(r.report.blockers.includes('EXECUTION_ROWS_REMOVED_OR_REVISED'));
});
test('row reordering preserves the multiset and does not look like a correction',()=>{
 const s=filled();s.orders=[order(200)];s.positions=[pos(200)];s.executions.push(execution(100,101.1));
 const a=run(s),n=structuredClone(s);n.captureCompletedAt=at(15);n.executions.reverse();
 const b=run(n,a.state);assert.deepEqual(b.report.blockers,[]);assert.deepEqual(b.state.seenExecutionRows,a.state.seenExecutionRows);
});
test('same snapshot replay is exactly idempotent and leaves original objects untouched',()=>{
 const s=filled(),copy=structuredClone(s),a=run(s),prior=structuredClone(a.state),b=run(s,a.state);
 assert.deepEqual(a.state,b.state);assert.deepEqual(s,copy);assert.deepEqual(a.state,prior);
});
test('changed retained baseline and wrong-session state are rejected',()=>{
 const a=run(filled());a.state.baselinePositions['["7203.T","特定"]']=1000;
 assert.throws(()=>run(filled(15),a.state),/STATE_HASH/);
 const b=run(filled());b.state.sessionDate='2026-10-23';assert.throws(()=>run(filled(15),b.state),/STATE/);
});
test('missing execution time stays unknown and never gets capture time substituted',()=>{
 const s=filled();delete s.executions[0].executionDate;const r=run(s);
 assert.equal(r.report.missingExecutionTimes,1);assert.ok(r.report.blockers.includes('EXECUTION_TIME_UNAVAILABLE'));
 assert.equal(s.executions[0].executionDate,undefined);
});
test('prior-day and future execution timestamps are rejected',()=>{
 for(const stamp of ['2026/10/23 09:30:04','2026/10/26 09:31:00','2026/10/26 24:30:00']){
 const s=filled();s.executions[0].executionDate=stamp;assert.throws(()=>run(s),/EXECUTION_TIME/);}
});
test('nonfinite, negative, overprecision and boolean prices do not become money',()=>{
 for(const price of [NaN,Infinity,-1,0,true,'100.1234567']){const s=filled();s.executions[0].price=price;assert.throws(()=>run(s),/PRICE/);}
});
test('duplicate broker numbers and duplicate position-account rows are rejected',()=>{
 const s=filled();s.orders.push({...s.orders[0]});assert.throws(()=>run(s),/DUPLICATE_ORDER/);
 const p=filled();p.positions.push({...p.positions[0]});assert.throws(()=>run(p),/POSITION/);
});
test('source time cannot move backwards on a restored ledger',()=>{
 const a=run(filled(15));assert.throws(()=>run(filled(10),a.state),/SOURCE_CLOCK_REVERSED/);
});
test('actual observer calls the reconciler and blocks mismatches without mutating real or synthetic cash',()=>{
 const e=envelope(filled());e.snapshot.executions=[];
 const r=observe({envelope:e,sessionDate:day,throughJst:at(12)});
 assert.equal(r.report.newShadowEntriesAllowed,false);assert.ok(r.report.blockers.includes('ORDER_EXECUTION_QUANTITY_MISMATCH'));
 assert.equal(r.report.realCashUsedForFunding,false);assert.equal(r.report.realFillsAppliedToShadow,false);assert.equal(e.snapshot.buyingPower,1000000);
});
test('legacy observer state acquires only a current baseline without claiming historical reconciliation',()=>{
 const e=envelope(snap()),a=observe({envelope:e,sessionDate:day,throughJst:at(12)});
 const {stateSha256,executionConsistency,...legacy}=a.state;
 const old={...legacy,stateSha256:createHash('sha256').update(JSON.stringify(legacy)).digest('hex')};
 const b=observe({envelope:envelope(filled(15),2),sessionDate:day,throughJst:at(16),previous:old});
 assert.equal(b.report.executionReconciliation.positionConservationCompared,false);
 assert.equal(b.report.arkOrderAttributionAvailable,false);
});
test('live execution permission cannot be introduced through a source snapshot',()=>{
 const s=filled();s.safety.brokerWriteAllowed=true;assert.throws(()=>run(s),/READONLY_SNAPSHOT/);
});
