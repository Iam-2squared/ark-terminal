import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {publishNo12ObservedChart} from '../tools/no12_private_chart_publish.mjs';
import {NO12_CHART_SCHEMA,RSS_CHART_COLUMNS} from '../runtime/msii_rss_chart_observation.mjs';
import {recordNo12MarketFirstSeen as record,inspectNo12MarketFirstSeen as inspect} from '../runtime/market_first_seen_journal.mjs';
function fixture(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'no12-first-seen-'));
 const candidatePath=path.join(root,'chart-candidate-'+'e'.repeat(32)+'.json');
 const row=(t,p)=>({'銘柄名称':'TEST','市場名称':'東証','足種':'5M',
  '日付':'2026/10/13','時刻':t,'始値':p,'高値':p+2,
  '安値':p-2,'終値':p,'出来高':1000});
 const snap={schemaId:NO12_CHART_SCHEMA,sourceFunction:'RssChart',period:'5M',
  evidenceMode:'OBSERVED_READ_ONLY',symbol:'7203.T',
  columns:[...RSS_CHART_COLUMNS],capturedAt:'2026-10-13T09:36:10+09:00',
  rows:[row('09:25',1000),row('09:30',1001),row('09:35',1002)]};
 function capture(t,mutate=()=>{}){
  snap.capturedAt=t;mutate(snap);
  fs.writeFileSync(candidatePath,JSON.stringify(snap));
  const now=new Date(Date.parse(t)+1000);
  const result=publishNo12ObservedChart({privateRoot:root,candidatePath,now});
  assert.equal(result.status,'LOCAL_MARKET_OBSERVATION_RECORDED_NOT_CERTIFIED');
  return now;
 }
 return {root,snap,capture,row,dispose:()=>fs.rmSync(root,{recursive:true,force:true})};
}
test('first observation stores only the latest actually closed current bar',()=>{
 const f=fixture();try{
  const x=record({privateRoot:f.root,now:f.capture('2026-10-13T09:36:10+09:00')});
  assert.equal(x.status,'LOCAL_FIRST_SEEN_RECORDED');
  assert.equal(x.eventCount,1);
  assert.equal(x.continuity,'FIRST_OBSERVATION');
  const state=JSON.parse(fs.readFileSync(path.join(f.root,'first-seen-7203-T.json'),'utf8'));
  assert.equal(state.rows.length,1);
  assert.equal(state.rows[0].entry.bar.at,'2026-10-13T09:30:00+09:00');
  assert.equal(state.rows[0].entry.firstSeenAt,'2026-10-13T09:36:10+09:00');
  assert.equal(state.rows[0].entry.brokerArrivalCertified,false);
  assert.equal(inspect({privateRoot:f.root,symbol:'7203.T'}).eventCount,1);
 }finally{f.dispose()}
});
test('second capture of the identical candle is idempotent',()=>{
 const f=fixture();try{
  record({privateRoot:f.root,now:f.capture('2026-10-13T09:36:10+09:00')});
  const got=record({privateRoot:f.root,now:f.capture('2026-10-13T09:36:20+09:00')});
  assert.equal(got.status,'IDEMPOTENT_OBSERVATION');
  assert.equal(got.eventCount,1);
 }finally{f.dispose()}
});
test('the next observed bar is appended without claiming broker timestamp',()=>{
 const f=fixture();try{
  record({privateRoot:f.root,now:f.capture('2026-10-13T09:36:10+09:00')});
  const got=record({privateRoot:f.root,now:f.capture('2026-10-13T09:41:10+09:00')});
  assert.equal(got.status,'LOCAL_FIRST_SEEN_RECORDED');
  assert.equal(got.eventCount,2);
  assert.equal(got.continuity,'CONTIGUOUS');
  const info=inspect({privateRoot:f.root,symbol:'7203.T'});
  assert.equal(info.brokerArrivalCertified,false);
  assert.equal(info.productionReady,false);
 }finally{f.dispose()}
});
test('a bar that changed after first observation blocks new capture',()=>{
 const f=fixture();try{
  record({privateRoot:f.root,now:f.capture('2026-10-13T09:36:10+09:00')});
  const now=f.capture('2026-10-13T09:36:20+09:00',s=>s.rows[1]['終値']=1002);
  assert.throws(()=>record({privateRoot:f.root,now}),/FIRST_SEEN_REVISED_BAR_BLOCKED/);
  assert.equal(inspect({privateRoot:f.root,symbol:'7203.T'}).eventCount,1);
 }finally{f.dispose()}
});
test('missed successive samples do not imply 5m continuity',()=>{
 const f=fixture();try{
  record({privateRoot:f.root,now:f.capture('2026-10-13T09:36:10+09:00')});
  const now=f.capture('2026-10-13T09:46:10+09:00',s=>{
   s.rows.push(f.row('09:40',1003));
  });
  const got=record({privateRoot:f.root,now});
  assert.equal(got.continuity,'GAP_OR_CLOCK_MISMATCH');
  assert.equal(got.productionReady,false);
 }finally{f.dispose()}
});
test('a previously saved receipt becomes stale and cannot authorize a new observation',()=>{
 const f=fixture();try{
  f.capture('2026-10-13T09:36:10+09:00');
  assert.throws(()=>record({privateRoot:f.root,now:new Date('2026-10-13T09:37:00+09:00')}),
   /NO12_LOCAL_MARKET_RECEIPT_STALE/);
 }finally{f.dispose()}
});
test('semantic alteration of a saved journal breaks its hash and prevents append',()=>{
 const f=fixture();try{
  record({privateRoot:f.root,now:f.capture('2026-10-13T09:36:10+09:00')});
  const file=path.join(f.root,'first-seen-7203-T.json');
  const saved=JSON.parse(fs.readFileSync(file,'utf8'));
  saved.rows[0].entry.bar.close++;
  fs.writeFileSync(file,JSON.stringify(saved));
  assert.throws(()=>inspect({privateRoot:f.root,symbol:'7203.T'}),
   /FIRST_SEEN_JOURNAL_HASH_INVALID/);
  assert.throws(()=>record({privateRoot:f.root,now:f.capture('2026-10-13T09:41:10+09:00')}),
   /FIRST_SEEN_JOURNAL_HASH_INVALID/);
 }finally{f.dispose()}
});
test('a stale lock cannot be silently deleted by a new writer',()=>{
 const f=fixture();try{
  const now=f.capture('2026-10-13T09:36:10+09:00');
  const lock=path.join(f.root,'first-seen-7203-T.json.lock');
  fs.mkdirSync(lock);
  assert.throws(()=>record({privateRoot:f.root,now}),/FIRST_SEEN_LOCKED_OR_UNRECOVERED/);
  assert.equal(fs.existsSync(lock),true);
 }finally{f.dispose()}
});
test('modified market receipt is blocked even when an older journal exists',()=>{
 const f=fixture();try{
  record({privateRoot:f.root,now:f.capture('2026-10-13T09:36:10+09:00')});
  fs.appendFileSync(path.join(f.root,'market-readonly-observed.json'),' ');
  assert.throws(()=>record({privateRoot:f.root,now:new Date('2026-10-13T09:36:11+09:00')}),
   /LOCAL_MARKET_RECEIPT_MISMATCH/);
  assert.equal(inspect({privateRoot:f.root,symbol:'7203.T'}).eventCount,1);
 }finally{f.dispose()}
});
test('this first-seen module contains no live order or Excel calls',()=>{
 const src=fs.readFileSync(new URL('../runtime/market_first_seen_journal.mjs',import.meta.url),'utf8');
 for(const forbidden of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/Excel.Application/,
  /\bfetch\s*\(/,/productionReady\s*:\s*true/,/orderTransmission\s*:\s*true/])
  assert.doesNotMatch(src,forbidden);
});
