import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {inspectNo11Rss1mHistorical as inspect,
 archiveNo11Rss1mHistorical as archive} from '../tools/no11_rss_1m_history_archive.mjs';
import {RSS_CHART_COLUMNS} from '../runtime/msii_rss_chart_observation.mjs';
const capturedAt='2026-10-12T19:47:00+09:00';
const now=new Date('2026-10-12T19:47:05+09:00');
const row=(day,clock)=>({
 '銘柄名称':'PUBLIC','市場名称':'東証','足種':'1M','日付':day,'時刻':clock,
 '始値':100,'高値':101,'安値':99,'終値':100,'出来高':200
});
const fixture=()=>({
 schemaId:'ARK_NO12_MSII_RSS_CHART_1M_OBSERVATION_V1',
 sourceFunction:'RssChart',period:'1M',evidenceMode:'OBSERVED_READ_ONLY',
 symbol:'7203.T',columns:[...RSS_CHART_COLUMNS],
 capturedAt,privateAccountDataIncluded:false,
 rows:[row('2026/10/09','09:00'),row('2026/10/09','09:01'),
       row('2026/10/08','15:29')]
});
test('JPX holiday afterhours archive accepts historical rows without same-day bar',()=>{
 const r=inspect({snapshot:fixture(),now});
 assert.equal(r.observedSessions,2);
 assert.equal(r.acceptedClosedRows,3);
 assert.equal(r.earliestDay,'2026-10-08');
 assert.equal(r.latestDay,'2026-10-09');
 assert.equal(r.modelTrainingReady,false);
 assert.equal(r.productionReady,false);
 assert.equal(r.orderTransmission,false);
});
test('local historical 1M receipts are immutable and strip unexpected private fields',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'no11-archive-'));
 try{
  const file=path.join(root,'one-minute-candidate-'+'f'.repeat(32)+'.json');
  const s=fixture();s.accountSecret='DO_NOT_PERSIST';
  fs.writeFileSync(file,JSON.stringify(s));
  const r=archive({privateRoot:root,candidatePath:file,now});
  assert.equal(r.rows,3);
  const names=fs.readdirSync(root).filter(n=>n.startsWith('rss-1m-'));
  assert.equal(names.length,2);
  const obj=JSON.parse(fs.readFileSync(path.join(root,names.find(n=>n.endsWith('.json')&&!n.endsWith('.receipt.json'))),'utf8'));
  assert.equal(obj.modelTrainingReady,false);
  assert(!JSON.stringify(obj).includes('accountSecret'));
  assert(!JSON.stringify(obj).includes('DO_NOT_PERSIST'));
  assert.throws(()=>archive({privateRoot:root,candidatePath:file,now}),/EEXIST/);
 }finally{fs.rmSync(root,{recursive:true,force:true})}
});
test('holiday, duplicate, future and invalid OHLCV cannot be archived',()=>{
 const a=fixture();a.rows[0]['日付']='2026/10/12';
 assert.throws(()=>inspect({snapshot:a,now}),/NO11_1M_ARCHIVE_DAY_INVALID/);
 const b=fixture();b.rows.push({...b.rows[0]});
 assert.throws(()=>inspect({snapshot:b,now}),/NO11_1M_ARCHIVE_DUPLICATE_BAR/);
 const c=fixture();c.rows[0]['高値']=1;
 assert.throws(()=>inspect({snapshot:c,now}),/NO11_1M_ARCHIVE_OHLCV_INCONSISTENT/);
 const d=fixture();d.rows[0]['日付']='2026/10/13';
 assert.throws(()=>inspect({snapshot:d,now}),/NO11_1M_ARCHIVE_DAY_INVALID/);
});
test('stale source, unapproved symbol and unsafe source contract fail closed',()=>{
 const a=fixture();a.capturedAt='2026-10-13T19:47:00+09:00';
 assert.throws(()=>inspect({snapshot:a,now}),/NO11_1M_ARCHIVE_CAPTURE_STALE_OR_FUTURE/);
 const b=fixture();b.symbol='9999.T';
 assert.throws(()=>inspect({snapshot:b,now}),/NO11_1M_ARCHIVE_SOURCE_CONTRACT_INVALID/);
 const c=fixture();c.privateAccountDataIncluded=true;
 assert.throws(()=>inspect({snapshot:c,now}),/NO11_1M_ARCHIVE_SOURCE_CONTRACT_INVALID/);
});
test('Windows archive switch preserves unsaved one-workbook READ ONLY protections',()=>{
 const ps=fs.readFileSync(new URL('../windows/Probe-No12MarketRss1mReadOnly.ps1',import.meta.url),'utf8');
 assert.equal(ps.charCodeAt(0),0xFEFF);
 assert.match(ps,/\[switch\]\$ArchiveHistoricalOnly/);
 assert.match(ps,/no11_rss_1m_history_archive\.mjs/);
 assert.match(ps,/NO11_1M_ARCHIVE_STATUS=LOCAL_HISTORICAL_1M_OBSERVED_NOT_TRAINING_CERTIFIED/);
 assert.match(ps,/NO11_1M_ARCHIVE_ROWS=/);
 assert.match(ps,/NO11_MODEL_TRAINING_READY=False/);
 assert.match(ps,/\$book\.Close\(\$false\)/);
 assert.match(ps,/NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST/);
 assert.match(ps,/EXCEL_HAS_EXISTING_WORKBOOK_CLOSE_FIRST/);
 assert.match(ps,/ORDER_TRANSMISSION=False/);
 for(const p of [/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,
  /Workbooks\.Open\(/i,/SaveAs\(/i,/\.Save\(/i,
  /Invoke-WebRequest|Invoke-RestMethod|Start-BitsTransfer/i])
  assert.doesNotMatch(ps,p);
});
test('archiver does not contain Excel automation, networking or order calls',()=>{
 const src=fs.readFileSync(new URL('../tools/no11_rss_1m_history_archive.mjs',import.meta.url),'utf8');
 for(const p of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Excel.Application/,/\bfetch\s*\(/,/productionReady\s*:\s*true/,
  /orderTransmission\s*:\s*true/])assert.doesNotMatch(src,p);
});
