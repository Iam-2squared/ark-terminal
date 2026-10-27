import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {brokerExcelSessionKey} from '../tools/no11_broker_snapshot.mjs';
import {inspect} from '../tools/no11_account_connection_diagnostic_readonly.mjs';
import {LOCKED_FLAGS} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';

const DAY='2026-10-28';
const time=s=>DAY+'T09:01:'+String(s).padStart(2,'0')+'+09:00';
function account(amount){
 const excelSession={
  processId:233,startedAtUtc:'2026-10-28T00:00:00.0000000Z',
  accountWorkbookIdentity:'a'.repeat(64),orderIdWorkbookIdentity:'b'.repeat(64)
 };
 excelSession.sessionKey=brokerExcelSessionKey(excelSession);
 const raw={schemaId:'ARK_NO11_BROKER_OBSERVATION_V1',status:'OBSERVED',
  capturedAt:time(3),captureCompletedAt:time(10),readOnly:true,
  excelSession,idRows:[],orders:[],executions:[],positions:[],
  buyingPower:amount,cashScope:'ALL_CHANNELS_ALL_STATUSES_CASH_ONLY',
  completeTables:true,rowsTruncated:false,sameSnapshotVerified:true,
  verificationBasis:'DOUBLE_READ_EQUAL_NOT_ATOMIC_FEED',
  actualFeedTimestampCertified:false,buyingPowerFreshnessCertified:false,
  productionReady:false,orderTransmission:false};
 const snapshot={schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',
  mode:'READ_ONLY',source:'MARKETSPEED_II_RSS',safety:{...LOCKED_FLAGS},
  capturedAt:time(5),captureCompletedAt:time(7),
  orders:[],executions:[],positions:[],buyingPower:amount};
 return {schemaId:'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1',status:'OBSERVED',
  readOnly:true,productionReady:false,orderTransmission:false,
  snapshot,brokerObservation:raw};
}
test('observed buying power is dynamic, never hardcoded to planned deposit',()=>{
 for(const n of [0,837421,1000000,1423456]){
  const r=inspect(account(n),DAY,time(17));
  assert.equal(r.rssAvailableForCashStockJpy,String(n));
  assert.equal(r.dynamicalBudgetSource,'BROKER_ACCOUNT_OBSERVATION_ONLY_NO_FIXED_YEN');
  assert.equal(r.accountCashBalanceIdentified,false);
  assert.equal(r.bankBridgeMayBeIncluded,true);
  assert.equal(r.orderTransmission,false);
  assert.equal(r.openCashOrders,0);
  assert.equal(r.historicalRssOrderIds,0);
 }
});
test('cross-book disagreement, stale values or malformed account are rejected',()=>{
 const mismatch=account(500000);
 mismatch.snapshot.buyingPower=600000;
 assert.throws(()=>inspect(mismatch,DAY,time(17)),/ACCOUNT_SNAPSHOT_MISMATCH/);
 assert.throws(()=>inspect(account(200000),DAY,time(50)),/CAPTURE_CLOCK/);
 assert.throws(()=>inspect(account(200000),DAY,'2026-10-29T09:00:17+09:00'),/NO11_ACCOUNT_DIAG_SESSION_REQUIRED/);
 const invalid=account(1000000);
 invalid.brokerObservation.sameSnapshotVerified=false;
 assert.throws(()=>inspect(invalid,DAY,time(17)),/SOURCE_VERIFICATION/);
});
test('read-only diagnostic does not create cash ledger or transmit',()=>{
 const source=fs.readFileSync(new URL('../tools/no11_account_connection_diagnostic_readonly.mjs',import.meta.url),'utf8');
 for(const forbidden of [
  /RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /GetActiveObject\s*\(/,/Workbooks\.Add\s*\(/,/Workbooks\.Open\s*\(/,
  /writeFileSync\s*\(/,/allocatedCashJpy\s*:/,/orderTransmission\s*:\s*true/,
 ])assert.doesNotMatch(source,forbidden);
 assert.ok(source.includes('normalizeBrokerObservation'));
 assert.ok(source.includes('ORDER_TRANSMISSION=False'));
});
