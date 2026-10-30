import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {ENVELOPE,observe} from '../tools/no11_account_observation.mjs';
import {LOCKED_FLAGS} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
const day='2026-10-26';
const at=s=>`${day}T09:30:${String(s).padStart(2,'0')}+09:00`;
export function fixture(seq=1,end=10){
 const rss={capacity:'完了',orders:'配信中',executions:'配信中',positions:'配信中'};
 return {schemaId:ENVELOPE,runId:'a'.repeat(32),sequence:seq,status:'OBSERVED',readOnly:true,productionReady:false,orderTransmission:false,
 snapshot:{schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',source:'MARKETSPEED_II_RSS',mode:'READ_ONLY',capturedAt:at(end-2),captureCompletedAt:at(end),rssStatus:rss,
 safety:{...LOCKED_FLAGS},positions:[],orders:[],executions:[],buyingPower:1000000},
 health:{schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',readOnly:true,addinLoaded:true,workbookPersisted:true,rssErrors:0,
 actualFeedTimestampCertified:false,healthCapturedAt:at(end),feeds:Object.fromEntries(Object.entries(rss).map(([k,state])=>[k,{state,observedAt:at(end)}]))}};
}
const order=(filled=0,status='執行中')=>({orderNumber:'123',symbol:'7203',account:'特定',side:'買',trade:'現物',quantity:200,filledQty:filled,status});
const run=(e,previous=null,throughJst=at(12))=>observe({envelope:e,sessionDate:day,throughJst,previous});
test('verified empty account is observable but never real execution authority',()=>{
 const r=run(fixture());assert.equal(r.report.newShadowEntriesAllowed,true);assert.deepEqual(r.report.excludedSymbols,[]);
 assert.equal(r.report.realCashUsedForFunding,false);assert.equal(r.report.orderTransmission,false);
});
test('personal holdings and executed personal symbols remain excluded',()=>{
 const e=fixture();e.snapshot.positions=[{symbol:'7203',account:'特定',quantity:100}];
 e.snapshot.executions=[{symbol:'6501',account:'一般',side:'売',quantity:100,price:1000}];
 const r=run(e);assert.deepEqual(r.report.excludedSymbols,['6501.T','7203.T']);
 const next=run(fixture(2,15),r.state,at(16));assert.deepEqual(next.report.excludedSymbols,r.report.excludedSymbols);
});
test('partial and unknown real orders block new shadow entries',()=>{
 for(const status of ['執行中','UNKNOWN','受付中']){const e=fixture();e.snapshot.orders=[order(100,status)];
 const r=run(e);assert.equal(r.report.newShadowEntriesAllowed,false);assert.equal(r.report.realFillsAppliedToShadow,false);}
});
test('real order disappearance is unresolved, not inferred cancellation',()=>{
 const e=fixture();e.snapshot.orders=[order()];const a=run(e);
 const b=run(fixture(2,15),a.state,at(16));assert.ok(b.report.blockers.includes('ORDER_DISAPPEARED_UNRESOLVED'));
 assert.equal(b.report.disappearedOrders,1);assert.equal(b.report.newShadowEntriesAllowed,false);
});
test('fill progression is observed once and reversals remain latched',()=>{
 let e=fixture();e.snapshot.orders=[order()];const a=run(e);
 e=fixture(2,15);e.snapshot.orders=[order(100)];const b=run(e,a.state,at(16));assert.equal(b.report.fillIncreasedOrders,1);
 e=fixture(3,18);e.snapshot.orders=[order(0)];const c=run(e,b.state,at(19));assert.ok(c.report.blockers.includes('CUMULATIVE_FILL_REVERSED'));
 e=fixture(4,20);e.snapshot.orders=[order(200,'約定')];const d=run(e,c.state,at(21));assert.equal(d.report.newShadowEntriesAllowed,false);
});
test('complete fill status requires complete cumulative quantity',()=>{
 const e=fixture();e.snapshot.orders=[order(100,'約定')];assert.throws(()=>run(e),/FALSE_COMPLETE_FILL/);
});
test('same capture is idempotent and changed sequence content fails',()=>{
 const e=fixture(),a=run(e),b=run(e,a.state);assert.deepEqual(a.state,b.state);
 e.snapshot.buyingPower=1;assert.throws(()=>run(e,a.state),/SAME_TIME_CHANGED/);
});
test('snapshot and health are not relabelled with fresh processing time',()=>{
 assert.throws(()=>run(fixture(),null,at(41)),/STALE_OR_FUTURE_SOURCE/);
 const e=fixture();e.health.feeds.positions.observedAt=at(2);assert.throws(()=>run(e),/STATUS_CLOCK_INVALID/);
 assert.throws(()=>run(fixture(),null,at(9)),/STALE_OR_FUTURE_SOURCE/);
});
test('changed state and source order identity cannot silently pass',()=>{
 const e=fixture();e.snapshot.orders=[order()];const a=run(e);
 const next=fixture(2,15);next.snapshot.orders=[{...order(),side:'売'}];const b=run(next,a.state,at(16));
 assert.ok(b.report.blockers.includes('ORDER_IDENTITY_CHANGED'));
 a.state.sequence=999;assert.throws(()=>run(next,a.state,at(16)),/STATE_CHANGED/);
});
test('missing account, duplicate ids and malformed quantities fail closed',()=>{
 for(const update of [{account:''},{quantity:0},{filledQty:-1},{filledQty:201},{quantity:'200'}]){
 const e=fixture();e.snapshot.orders=[{...order(),...update}];assert.throws(()=>run(e));}
 const e=fixture();e.snapshot.orders=[order(),order()];assert.throws(()=>run(e),/ORDER_ID_INVALID/);
});
test('observer never writes existing books or submits orders',()=>{
 const file=new URL('../windows/Observe-No11AccountReadOnly.ps1',import.meta.url);const source=fs.readFileSync(file,'utf8');
 assert.ok(source.startsWith('\ufeff'));assert.match(source,/f8be4d704ebad539762471ba62476c32b02a65b1/);
 assert.match(source,/FullName/);assert.match(source,/ACCOUNT_BOOK_NOT_UNIQUE/);
 assert.doesNotMatch(source,/\.Save\s*\(|\.Quit\s*\(|\.Formula\s*=|\.Value2\s*=|\.Workbooks\.(?:Add|Open)\s*\(/i);
});
test('Windows pinned source assembly parses without Excel or accounts',{skip:process.platform!=='win32'},()=>{
 const p=fileURLToPath(new URL('../windows/Observe-No11AccountReadOnly.ps1',import.meta.url));
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',p,'-OfflineSelfTest'],{encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,r.stdout+'\n'+r.stderr);assert.match(r.stdout,/NO11_ACCOUNT_CAPTURE_OFFLINE_SELFTEST=PASS/);
});
