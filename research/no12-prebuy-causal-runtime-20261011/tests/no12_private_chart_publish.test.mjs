import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {publishNo12ObservedChart as pub,verifyNo12ObservedChart as verify} from '../tools/no12_private_chart_publish.mjs';
import {NO12_CHART_SCHEMA,RSS_CHART_COLUMNS} from '../runtime/msii_rss_chart_observation.mjs';
function fixture(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'no12-market-private-'));
 const candidatePath=path.join(root,'chart-candidate-'+'a'.repeat(32)+'.json');
 const row=(clock,v)=>({'銘柄名称':'fixture','市場名称':'東証','足種':'5M',
   '日付':'2026/10/13','時刻':clock,'始値':v,'高値':v+2,'安値':v-2,
   '終値':v,'出来高':1000});
 const snap={schemaId:NO12_CHART_SCHEMA,sourceFunction:'RssChart',period:'5M',
  evidenceMode:'OBSERVED_READ_ONLY',symbol:'7203.T',
  columns:[...RSS_CHART_COLUMNS],capturedAt:'2026-10-13T09:36:10+09:00',
  rows:[row('09:25',1000),row('09:30',1001),row('09:35',1002)]};
 fs.writeFileSync(candidatePath,JSON.stringify(snap));
 return {root,candidatePath,now:new Date('2026-10-13T09:36:20+09:00'),
  cleanup:()=>fs.rmSync(root,{recursive:true,force:true})};
}
test('private local receipt persists only already closed bars, never unfinished or order authority',()=>{
 const f=fixture();try{
  const r=pub({...f,privateRoot:f.root});assert.equal(r.bars,2);
  const check=verify({privateRoot:f.root});
  assert.equal(check.status,'LOCAL_MARKET_RECEIPT_HASH_VALID');
  const value=JSON.parse(fs.readFileSync(path.join(f.root,'market-readonly-observed.json')));
  assert.equal(value.bars.length,2);
  assert.equal(value.productionReady,false);
  assert.equal(value.brokerArrivalCertified,false);
  assert.equal(value.orderTransmission,false);
 }finally{f.cleanup()}
});
test('partial write/tamper of saved observation breaks receipt',()=>{
 const f=fixture();try{
  pub({...f,privateRoot:f.root});
  const p=path.join(f.root,'market-readonly-observed.json');
  fs.appendFileSync(p,' ');
  assert.throws(()=>verify({privateRoot:f.root}),/LOCAL_MARKET_RECEIPT_MISMATCH/);
 }finally{f.cleanup()}
});
test('unsafe candidate path outside private root and absent session data block or remain unavailable',()=>{
 const f=fixture();try{
  assert.throws(()=>pub({...f,privateRoot:f.root,candidatePath:path.join(os.tmpdir(),'other.json')}),/PRIVATE_CHART_CANDIDATE_PATH_INVALID/);
  const raw=JSON.parse(fs.readFileSync(f.candidatePath,'utf8'));
  raw.rows=raw.rows.slice(-1);fs.writeFileSync(f.candidatePath,JSON.stringify(raw));
  const x=pub({...f,privateRoot:f.root});assert.equal(x.status,'NO_CURRENT_SESSION_COMPLETE_BAR');
  assert.equal(fs.existsSync(path.join(f.root,'market-readonly-receipt.json')),false);
 }finally{f.cleanup()}
});
test('private publisher never calls Excel order functions or network APIs',()=>{
 const script=fs.readFileSync(new URL('../tools/no12_private_chart_publish.mjs',import.meta.url),'utf8');
 for(const re of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/Excel.Application/i,/\bfetch\s*\(/])
 assert.doesNotMatch(script,re);
});

test('CLI refuses to report a saved market receipt if no current completed bar exists',()=>{
 const text=fs.readFileSync(new URL('../tools/no12_private_chart_publish.mjs',import.meta.url),'utf8');
 assert.match(text,/if\(out\.status!=='LOCAL_MARKET_OBSERVATION_RECORDED_NOT_CERTIFIED'\)/);
 assert.match(text,/NO12_CURRENT_SESSION_COMPLETED_BAR_REQUIRED/);
});
