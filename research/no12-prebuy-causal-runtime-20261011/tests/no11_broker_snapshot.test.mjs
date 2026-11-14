import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {normalizeBrokerObservation as normalize,brokerExcelSessionKey,normalizeRssDateTime,BROKER_OBSERVATION_SCHEMA,ORDER_ID_HEADERS,ORDER_HEADERS,EXECUTION_HEADERS} from '../tools/no11_broker_snapshot.mjs';
import {LOCKED_FLAGS} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
const day='2026-10-26',at=s=>`${day}T09:30:${String(s).padStart(2,'0')}+09:00`;
function fixture(){
 const excelSession={processId:123,startedAtUtc:'2026-10-25T23:00:00.0000000Z',accountWorkbookIdentity:'a'.repeat(64),orderIdWorkbookIdentity:'b'.repeat(64)};
 excelSession.sessionKey=brokerExcelSessionKey(excelSession);
 return {schemaId:BROKER_OBSERVATION_SCHEMA,status:'OBSERVED',capturedAt:at(5),captureCompletedAt:at(10),readOnly:true,excelSession,
  idRows:[{rssOrderId:77,functionName:'RssStockOrder',orderDate:day,orderTime:'09:30:00',orderNumber:'123',result:'発注済み(発注ID=77)'}],
  orders:[{orderNumber:'123',status:'約定',symbol:'7203',account:'特定',side:'買付',trade:'現物',executionCondition:'本日中',quantity:100,filledQty:100,market:'東証',orderReceivedAt:'2026/10/26 09:30:00',inputRoute:'MARKET SPEED',orderType:'通常注文'}],
  executions:[{executionDate:'2026/10/26 09:30:04',symbol:'7203',account:'特定',side:'買付',trade:'現物',market:'東証',quantity:100,price:1000.1}],
  positions:[{symbol:'7203',account:'特定',quantity:100}],buyingPower:100000,
  cashScope:'ALL_CHANNELS_ALL_STATUSES_CASH_ONLY',completeTables:true,rowsTruncated:false,
  sameSnapshotVerified:true,verificationBasis:'DOUBLE_READ_EQUAL_NOT_ATOMIC_FEED',actualFeedTimestampCertified:false,buyingPowerFreshnessCertified:false,productionReady:false,orderTransmission:false};
}
const run=(o,previous=null,accountSnapshot=null)=>normalize({brokerObservation:o,sessionDate:day,throughJst:at(20),previous,accountSnapshot});
function later(o){const n=structuredClone(o);n.capturedAt=at(11);n.captureCompletedAt=at(15);return n}
function account(o){return {schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',source:'MARKETSPEED_II_RSS',mode:'READ_ONLY',safety:{...LOCKED_FLAGS},capturedAt:at(6),captureCompletedAt:at(8),orders:structuredClone(o.orders),executions:structuredClone(o.executions),positions:structuredClone(o.positions),buyingPower:o.buyingPower}}

test('normalizes complete observed cash rows without granting attribution, fresh funds or sending',()=>{
 const f=fixture(),before=structuredClone(f),r=run(f);
 assert.equal(r.schemaId,'ARK_NO11_BROKER_SNAPSHOT_V1');assert.equal(r.status,'OBSERVED');assert.equal(r.idRows[0].rssOrderId,77);
 assert.equal(r.executions[0].executionDate,day+'T09:30:04+09:00');assert.equal(r.orders[0].orderReceivedAt,day+'T09:30:00+09:00');
 assert.equal(r.orders[0].inputRoute,'MARKET SPEED');assert.equal(r.executions[0].market,'東証');assert.equal(r.executions[0].trade,'現物');
 for(const k of ['brokerTimestampCertified','actualFeedTimestampCertified','buyingPowerFreshnessCertified','executionPriceAttributed','realAccountLedgerUpdated','productionReady','orderTransmission'])assert.equal(r[k],false,k);
 assert.deepEqual(f,before);assert.match(r.snapshotSha256,/^[a-f0-9]{64}$/);
});
test('existing account envelope common fields must agree within the supplemental capture range',()=>{
 const f=fixture(),a=account(f);assert.equal(run(f,null,a).accountSnapshotCompared,true);
 a.orders[0].filledQty=99;assert.throws(()=>run(f,null,a),/ACCOUNT_SNAPSHOT_MISMATCH/);
});
test('matching uses multiset counts and does not discard identical fill rows',()=>{
 const f=fixture();f.orders[0].quantity=200;f.orders[0].filledQty=200;f.positions[0].quantity=200;f.executions.push({...f.executions[0]});
 const a=account(f);assert.equal(run(f,null,a).executions.length,2);a.executions.pop();assert.throws(()=>run(f,null,a),/ACCOUNT_SNAPSHOT_MISMATCH/);
});
test('account snapshot before or after supplemental capture is rejected',()=>{
 const f=fixture(),a=account(f);a.capturedAt=at(1);assert.throws(()=>run(f,null,a),/ACCOUNT_CAPTURE_RANGE/);
});
test('an account snapshot cannot smuggle broker permission through a matching read-only projection',()=>{
 const f=fixture(),a=account(f);a.safety.brokerWriteAllowed=true;assert.throws(()=>run(f,null,a),/ACCOUNT_SAFETY/);
});
test('cross-book equality includes the cash trade and execution market',()=>{
 const f=fixture(),a=account(f);a.executions[0].trade='信用新規';assert.throws(()=>run(f,null,a),/ACCOUNT_SNAPSHOT_MISMATCH/);
 a.executions[0].trade='現物';a.executions[0].market='JNX';assert.throws(()=>run(f,null,a),/ACCOUNT_SNAPSHOT_MISMATCH/);
});
test('Excel restart requires rebinding even if RSS number and order contents are reused',()=>{
 const f=fixture(),first=run(f),n=later(f);n.excelSession.startedAtUtc='2026-10-26T00:30:11.0000000Z';n.excelSession.sessionKey=brokerExcelSessionKey(n.excelSession);
 const r=run(n,first);assert.equal(r.rebindRequired,true);assert.equal(r.status,'OBSERVED_REBIND_REQUIRED');assert.notEqual(r.sessionKey,first.sessionKey);
 assert.deepEqual(run(n,r),r,'duplicate first observation after Excel restart keeps its source fingerprint');
});
test('observer restart with unchanged Excel identity does not falsely reset the ID namespace',()=>{
 const f=fixture(),r=run(later(f),run(f));assert.equal(r.rebindRequired,false);assert.equal(r.sessionKey,run(f).sessionKey);
});
test('ID removal and immutable ID remapping in one Excel session are rejected',()=>{
 const f=fixture(),previous=run(f),missing=later(f);missing.idRows=[];assert.throws(()=>run(missing,previous),/RSS_ID_REMOVED/);
 const changed=later(f);changed.idRows[0].orderNumber='456';assert.throws(()=>run(changed,previous),/RSS_ID_REUSED_OR_CHANGED/);
});
test('an initially unassigned broker number can acquire its observed number once',()=>{
 const f=fixture();f.idRows[0].orderNumber=null;f.idRows[0].result='応答待ち';const first=run(f),n=later(f);n.idRows[0].orderNumber='123';n.idRows[0].result='発注済み(発注ID=77)';
 assert.equal(run(n,first).idRows[0].orderNumber,'123');
});
test('used IDs from prior days remain occupied until Excel exits',()=>{
 const f=fixture();f.idRows[0].orderDate='2026/10/23';assert.equal(run(f).idRows[0].orderDate,'2026-10-23');
});
test('same timestamp replay is idempotent; changed source at the same timestamp is rejected',()=>{
 const f=fixture(),a=run(f);assert.deepEqual(run(f,a),a);f.buyingPower++;assert.throws(()=>run(f,a),/SAME_TIME_CHANGED/);
});
test('same-time reread cannot silently change cross-book validation context',()=>{
 const f=fixture(),a=run(f);assert.throws(()=>run(f,a,account(f)),/SAME_TIME_CONTEXT_CHANGED/);
});
test('modified previous state cannot be used for continuity',()=>{
 const f=fixture(),p=structuredClone(run(f));p.idRows[0].orderNumber='456';assert.throws(()=>run(later(f),p),/PREVIOUS_HASH/);
});
test('duplicate RSS IDs and broker order numbers are never silently deduplicated',()=>{
 const f=fixture();f.idRows.push({...f.idRows[0]});assert.throws(()=>run(f),/DUPLICATE_RSS_ID/);
 const g=fixture();g.orders.push({...g.orders[0]});assert.throws(()=>run(g),/DUPLICATE_ORDER/);
});
test('source verification is exact; status cells and repeated reads cannot certify market arrival',()=>{
 for(const change of [{sameSnapshotVerified:false},{completeTables:false},{rowsTruncated:true},{actualFeedTimestampCertified:true},{buyingPowerFreshnessCertified:true},{cashScope:'FILTERED'},{verificationBasis:'ATOMIC'}]){
  assert.throws(()=>run(Object.assign(fixture(),change)),/SOURCE_VERIFICATION|TABLE_COMPLETENESS/);
 }
});
test('unavailable supplemental book cannot be normalized into observed evidence',()=>{
 const f=fixture();f.status='UNAVAILABLE';assert.throws(()=>run(f),/SOURCE_UNAVAILABLE/);
});
test('credit executions and non-cash orders do not enter the cash observer',()=>{
 const f=fixture();f.executions[0].trade='信用新規';assert.throws(()=>run(f),/EXECUTION_TRADE/);
 const g=fixture();g.orders[0].trade='信用新規';assert.throws(()=>run(g),/ORDER_FIELDS_INVALID/);
});
test('unsupported market is retained and explicitly prevents a normal observed status',()=>{
 const f=fixture();f.orders[0].market='名証';const r=run(f);assert.equal(r.status,'OBSERVED_UNSUPPORTED_MARKET');assert.deepEqual(r.unsupportedMarkets,['名証']);assert.equal(r.orderTransmission,false);
});
test('malformed IDs, numbers, missing provenance and contradictory order states are rejected',()=>{
 for(const x of [0,2147483648,1.5,'77',true]){const f=fixture();f.idRows[0].rssOrderId=x;assert.throws(()=>run(f),/RSS_ID/)}
 const f=fixture();delete f.orders[0].inputRoute;assert.throws(()=>run(f),/INPUT_ROUTE/);
 const g=fixture();g.orders[0].filledQty=99;assert.throws(()=>run(g),/FALSE_COMPLETE_FILL/);
 const h=fixture();h.executions[0].price=NaN;assert.throws(()=>run(h),/EXECUTION_PRICE/);
});
test('actual dates, session boundaries and future vendor times are validated',()=>{
 assert.throws(()=>normalizeRssDateTime('2026/02/30 09:30:00'),/DATETIME/);
 for(const value of ['2026/10/26 24:30:00','2026/10/26 09:30:21','2026/10/23 09:30:00']){const f=fixture();f.executions[0].executionDate=value;assert.throws(()=>run(f),/DATETIME|EXECUTION_SESSION/)}
 const f=fixture();f.excelSession.startedAtUtc='2026-10-26T01:00:00Z';f.excelSession.sessionKey=brokerExcelSessionKey(f.excelSession);assert.throws(()=>run(f),/EXCEL_START_FUTURE/);
});
test('freshness boundaries reject stale, future and overly long collections',()=>{
 for(const [start,end] of [['09:29:00','09:29:10'],['09:30:00','09:30:25'],['09:29:40','09:30:10']]){const f=fixture();f.capturedAt=day+'T'+start+'+09:00';f.captureCompletedAt=day+'T'+end+'+09:00';assert.throws(()=>run(f),/CAPTURE_CLOCK/)}
});
test('read-only Windows source preserves pinned original and fixes bulk execution datetime in the wrapper',()=>{
 const wrapper=fs.readFileSync(new URL('../windows/Observe-No11AccountReadOnly.ps1',import.meta.url),'utf8');
 assert.match(wrapper,/f8be4d704ebad539762471ba62476c32b02a65b1/);assert.match(wrapper,/\$body=PatchOnce \$body '\$date=Trim-Value/);
 assert.match(wrapper,/\$date=Convert-No11ExecutionDate \(Bulk-Value \$executionsBlock \$idx 0\)/);
 assert.match(wrapper,/\$value\.brokerObservation=\$observed\.brokerObservation/);
 const reader=fs.readFileSync(new URL('../windows/Read-No11BrokerSnapshot.ps1',import.meta.url),'utf8');
 for(const h of [...ORDER_ID_HEADERS,...ORDER_HEADERS,...EXECUTION_HEADERS])assert.ok(reader.includes("'"+h+"'"),h);
 assert.doesNotMatch(reader,/Workbooks\.(?:Add|Open)|\.Save(?:As)?\(|RssStockOrder\(|RssCancelOrder\(|\.Calculate\(/i);
 assert.ok(reader.includes('DOUBLE_READ_EQUAL_NOT_ATOMIC_FEED'));assert.ok(reader.includes('ACCOUNT_BROKER_TABLE_MISMATCH'));
});
const windows=process.platform==='win32',ps=windows?'powershell.exe':process.env.ARK_NO11_PWSH;
for(const [script,marker] of [['Read-No11BrokerSnapshot.ps1','NO11_BROKER_SNAPSHOT_OFFLINE_SELFTEST=PASS'],['New-No11BrokerReadOnlyWorkbook.ps1','NO11_BROKER_WORKBOOK_OFFLINE_SELFTEST=PASS'],['Observe-No11AccountReadOnly.ps1','NO11_ACCOUNT_CAPTURE_OFFLINE_SELFTEST=PASS']]){
 test('PowerShell offline collector/template verification: '+script,{skip:!ps},()=>{
  const file=fileURLToPath(new URL('../windows/'+script,import.meta.url));const child=spawnSync(ps,['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',file,'-OfflineSelfTest'],{encoding:'utf8',timeout:30000});
  assert.equal(child.status,0,child.stdout+'\n'+child.stderr);assert.ok(child.stdout.includes(marker));
 });
}
