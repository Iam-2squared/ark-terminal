import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {diagnoseCaptures,diagnoseFolder} from '../tools/no11_saved_chart_diagnostics.mjs';
const day='2026-10-26',symbol='7203.T';
const time=(minute,second=8)=>`${day}T09:${String(minute).padStart(2,'0')}:${String(second).padStart(2,'0')}.000+09:00`;
const bar=(minute,seen)=>({Date:day,Code:symbol,Time:`09:${String(minute).padStart(2,'0')}`,O:100,H:100,L:100,C:100,Vo:100,knownAtJst:time(seen,9)});
function capture(minute,rows){
 const volume=1000+(minute-31)*100;
 return {schemaId:'ARK_NO11_RSS_CHART50_1M_CAPTURE_V1',sessionDate:day,chartPlanSha256:'a'.repeat(64),
  selectedSymbols:[symbol],source:'RssChart_1M_AND_RssMarket_CUMULATIVE_READONLY',
  marketObservedAtJst:time(minute),observedEndJst:time(minute,10),
  chartRows:rows,marketObservations:[{symbol,marketDate:day,cumulativeVolumeRaw:String(volume),
   cumulativeTurnoverRaw:String(volume*100),vendorVolumeWeightedAverage:'100'}],
  shadowOnly:true,productionReady:false,orderTransmission:false};
}
const valid=()=>[capture(31,[bar(30,31)]),capture(32,[bar(30,32),bar(31,32)])];
test('new appended bar and valid cumulative bracket produce proxy without exposing prices or symbols',()=>{
 const r=diagnoseCaptures(valid());
 assert.equal(r.frames[1].addedBarKeys,1);assert.equal(r.frames[1].changedMarketRows,1);
 assert.equal(r.approximateMinuteVaRows,1);assert.equal(r.newBarKeysObserved,true);
 assert.equal(r.frames[1].latestChartBarTime,'09:31');
 assert.equal(r.frames[1].cumulativeValidation.VENDOR_RATIO_CONSISTENT_NOT_MINUTE_VA,1);
 assert.equal(JSON.stringify(r).includes(symbol),false);
 assert.equal(r.productionReady,false);assert.equal(r.orderTransmission,false);assert.equal(r.shadowTested,false);
});
test('four static chart frames are not called a live feed success even if counters change',()=>{
 const r=diagnoseCaptures([31,32,33,34].map(n=>capture(n,[bar(30,n)])));
 assert.equal(r.newBarKeysObserved,false);assert.equal(r.marketValuesChanged,true);
 assert.equal(r.approximateMinuteVaRows,0);assert.equal(r.status,'NO_USABLE_PROXY_ROWS');
 assert.deepEqual(r.frames.slice(1).map(f=>f.addedBarKeys),[0,0,0]);
});
test('missing cumulative source and VWAP ratio mismatch are reported separately',()=>{
 const input=valid();input[0].marketObservations[0].marketDate=null;
 input[1].marketObservations[0].cumulativeTurnoverRaw='1';
 const r=diagnoseCaptures(input);
 assert.equal(r.frames[0].cumulativeValidation.SOURCE_INCOMPLETE,1);
 assert.equal(r.frames[1].cumulativeValidation.TURNOVER_VWAP_RATIO_MISMATCH,1);
 assert.equal(r.approximateMinuteVaRows,0);
});
test('time and volume guards remain active in diagnostic import',()=>{
 const input=valid();input[1].chartRows[1].Vo=200;
 const r=diagnoseCaptures(input);
 assert.equal(r.approximateMinuteVaRows,0);
 assert.equal(r.skippedBars.BLOCKED_CHART_VOLUME_AND_CUMULATIVE_DELTA_MISMATCH,1);
 const late=valid();late[1].chartRows[1].knownAtJst=time(35);
 assert.throws(()=>diagnoseCaptures(late),/CAUSALITY/);
});
test('modified earlier chart rows are still invalidated rather than silently overwritten',()=>{
 const input=valid();input[1].chartRows[0].Vo=200;
 const r=diagnoseCaptures(input);assert.equal(r.invalidatedRevisedChartRows,1);
});
test('requires a bounded set of frames and rejects duplicate timestamps',()=>{
 assert.throws(()=>diagnoseCaptures([]),/TWO_TO_TEN/);
 assert.throws(()=>diagnoseCaptures(Array(11).fill(valid()[0])),/TWO_TO_TEN/);
 assert.throws(()=>diagnoseCaptures([valid()[0],valid()[0]]),/SNAPSHOT_CLOCK/);
});
test('saved input bytes are checked against their hashes and files are never changed',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'no11-frame-diagnostic-'));
 try{
  const files=valid().map(c=>{const b=Buffer.from(JSON.stringify(c)+'\n');
   const file=path.join(root,'snapshot-'+createHash('sha256').update(b).digest('hex')+'.json');fs.writeFileSync(file,b);return file;});
  const before=files.map(f=>fs.readFileSync(f,'utf8'));
  const r=diagnoseFolder(root);assert.equal(r.snapshotHashesVerified,true);assert.equal(r.approximateMinuteVaRows,1);
  assert.deepEqual(files.map(f=>fs.readFileSync(f,'utf8')),before);
  fs.appendFileSync(files[0],' ');assert.throws(()=>diagnoseFolder(root),/HASH/);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
