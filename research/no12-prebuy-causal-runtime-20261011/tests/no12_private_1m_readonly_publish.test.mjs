import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {publishNo12PrivateOneMinute as publish,
 verifyNo12PrivateOneMinute as verify} from '../tools/no12_private_1m_readonly_publish.mjs';
import {NO12_ONE_MINUTE_SCHEMA} from '../runtime/rss_1m_history_observation.mjs';
import {RSS_CHART_COLUMNS} from '../runtime/msii_rss_chart_observation.mjs';
const days=['2026/10/05','2026/10/06','2026/10/07','2026/10/08','2026/10/09'];
const hm=m=>String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0');
const row=(day,m)=>({'銘柄名称':'SAMPLE','市場名称':'東証','足種':'1M',
 '日付':day,'時刻':hm(m),'始値':1000,'高値':1001,'安値':999,'終値':1000,'出来高':100,
 secretAccountNumber:'MUST_NOT_PERSIST'});
function fixture(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'no12-1m-private-'));
 const candidatePath=path.join(root,'one-minute-candidate-'+'f'.repeat(32)+'.json');
 const rows=[];
 for(const day of days)for(const [a,b] of [[540,690],[750,930]])
   for(let m=a;m<b;m++)rows.push(row(day,m));
 rows.push(row('2026/10/13',554),row('2026/10/13',555));
 const snapshot={schemaId:NO12_ONE_MINUTE_SCHEMA,
  sourceFunction:'RssChart',period:'1M',evidenceMode:'OBSERVED_READ_ONLY',
  symbol:'7203.T',columns:[...RSS_CHART_COLUMNS],
  capturedAt:'2026-10-13T09:16:10+09:00',
  privateAccountDataIncluded:false,rows};
 const write=()=>fs.writeFileSync(candidatePath,JSON.stringify(snapshot));
 write();
 return {root,candidatePath,snapshot,write,
  now:new Date('2026-10-13T09:16:11+09:00'),
  clean:()=>fs.rmSync(root,{recursive:true,force:true})};
}
test('1M 1650 historical bars and current completed bar publish local-only',()=>{
 const f=fixture();try{
  const r=publish(f);
  assert.equal(r.status,'LOCAL_1M_MARKET_RECEIPT_NOT_LIVE_CERTIFIED');
  assert.equal(r.historyStatus,'BACKFILL_1M_PREVIOUS_SESSIONS_AVAILABLE');
  assert.equal(r.historyBars,1650);
  assert.equal(r.rows,1652);
  assert.equal(r.orderTransmission,false);
  const v=verify({privateRoot:f.root,now:f.now});
  assert.equal(v.rows,1652);
  const raw=fs.readFileSync(path.join(f.root,'market-1m-readonly-observed.json'),'utf8');
  assert(!raw.includes('secretAccountNumber'));
  assert(!raw.includes('MUST_NOT_PERSIST'));
  const obj=JSON.parse(raw);
  assert.equal(obj.originalState9Certified,false);
  assert.equal(obj.brokerActualArrivalCertified,false);
 }finally{f.clean()}
});
test('historical missing 1M bar remains incomplete and never silently filled',()=>{
 const f=fixture();try{
  f.snapshot.rows=f.snapshot.rows.filter(r=>!(r['日付']==='2026/10/09'&&r['時刻']==='09:00'));
  f.write();
  const r=publish(f);
  assert.equal(r.historyStatus,'HISTORY_SOURCE_INCOMPLETE');
  assert.equal(r.historyBars,1649);
 }finally{f.clean()}
});
test('tampered receipt and expired capture fail closed',()=>{
 const f=fixture();try{
  publish(f);
  const p=path.join(f.root,'market-1m-readonly-observed.json');
  fs.appendFileSync(p,' ');
  assert.throws(()=>verify({privateRoot:f.root,now:f.now}),/NO12_1M_PRIVATE_RECEIPT_TAMPERED/);
  publish(f);
  assert.throws(()=>verify({privateRoot:f.root,
    now:new Date('2026-10-13T09:17:00+09:00')}),/NO12_1M_PRIVATE_RECEIPT_STALE/);
 }finally{f.clean()}
});
test('wrong candidate path, stale source and future data cannot publish',()=>{
 const f=fixture();try{
  assert.throws(()=>publish({...f,candidatePath:path.join(f.root,'other.json')}),
    /NO12_1M_PRIVATE_CANDIDATE_INVALID/);
  assert.throws(()=>publish({...f,now:new Date('2026-10-13T09:17:00+09:00')}),
    /NO12_1M_SOURCE_CLOCK_STALE_OR_FUTURE/);
  f.snapshot.rows.push(row('2026/10/14',540));f.write();
  assert.throws(()=>publish(f),/NO12_1M_FUTURE_DAY_BAR/);
 }finally{f.clean()}
});
test('publisher cannot send orders, change Excel or connect to broker',()=>{
 const source=fs.readFileSync(new URL('../tools/no12_private_1m_readonly_publish.mjs',import.meta.url),'utf8');
 for(const re of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/\bfetch\s*\(/,
  /Excel.Application/,/productionReady\s*:\s*true/,/orderTransmission\s*:\s*true/])
  assert.doesNotMatch(source,re);
});
