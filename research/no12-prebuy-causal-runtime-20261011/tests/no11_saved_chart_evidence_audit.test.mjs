import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {inspectNo11SavedChartEvidence as inspect,
 readNo11SavedChartEvidence as read} from '../runtime/no11_saved_chart_evidence_audit.mjs';
const row=(label,price=100)=>({label,open:price,high:price+2,low:price-1,close:price+1,volume:100});
const fixture=()=>({
 schemaId:'ARK_NO11_RSS_CHART_DUAL_EVIDENCE_V1',symbol:'7203.T',
 sourceFunction:'RssChart',evidenceMode:'OBSERVED_READ_ONLY',
 privateAccountDataIncluded:false,excelOrderEnabled:false,
 labelSemanticsCertified:false,brokerArrivalCertified:false,
 originalNativeState9Certified:false,productionReady:false,orderTransmission:false,
 capturedAt:'2026-10-13T14:11:35+09:00',
 periods:{
  '1M':{observedAt:'2026-10-13T14:11:25+09:00',requestedBars:300,
   validRows:2,rows:[row('2026-10-13T14:09:00+09:00'),row('2026-10-13T14:11:00+09:00')]},
  '5M':{observedAt:'2026-10-13T14:11:30+09:00',requestedBars:100,
   validRows:2,rows:[row('2026-10-13T14:00:00+09:00'),row('2026-10-13T14:10:00+09:00')]}
 }
});
const now=new Date('2026-10-13T14:11:36+09:00');
test('observed 1M and 5M audit only, excludes potentially unclosed bars',()=>{
 const r=inspect({evidence:fixture(),now});
 assert.equal(r.periods['1M'].observedRows,2);
 assert.equal(r.periods['1M'].conservativelyClosedRows,1);
 assert.equal(r.periods['1M'].notConservativelyClosedRows,1);
 assert.equal(r.periods['5M'].conservativelyClosedRows,1);
 assert.equal(r.periods['5M'].notConservativelyClosedRows,1);
 assert.equal(r.frozenState9Connected,false);
 assert.equal(r.productionReady,false);
 assert.equal(r.orderTransmission,false);
});
test('rejects duplicate, bad OHLCV, future label, false certification',()=>{
 const a=fixture();a.periods['1M'].rows[1].label=a.periods['1M'].rows[0].label;
 assert.throws(()=>inspect({evidence:a,now}),/DUPLICATE/);
 const b=fixture();b.periods['5M'].rows[0].high=1;
 assert.throws(()=>inspect({evidence:b,now}),/OHLCV_INCONSISTENT/);
 const c=fixture();c.periods['1M'].rows[1].label='2026-10-13T14:12:00+09:00';
 assert.throws(()=>inspect({evidence:c,now}),/FUTURE_OR_DUPLICATE/);
 const d=fixture();d.originalNativeState9Certified=true;
 assert.throws(()=>inspect({evidence:d,now}),/CONTRACT_INVALID/);
});
test('rejects false counts, bad market time, future capture',()=>{
 const a=fixture();a.periods['1M'].validRows=1;
 assert.throws(()=>inspect({evidence:a,now}),/ROW_COUNT_INVALID/);
 const b=fixture();b.periods['1M'].rows[0].label='2026-10-13T12:00:00+09:00';
 assert.throws(()=>inspect({evidence:b,now}),/MARKET_LABEL_INVALID/);
 const c=fixture();c.capturedAt='2026-10-13T14:15:00+09:00';
 assert.throws(()=>inspect({evidence:c,now}),/CAPTURE_IN_FUTURE/);
});
test('reads private immutable chart snapshot with local hash only',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'no11-chart-evidence-'));
 try{
  const file=path.join(root,'chart-evidence-'+'a'.repeat(32)+'.json');
  fs.writeFileSync(file,JSON.stringify(fixture()));
  const r=read({file,now});
  assert.match(r.localFileSha256,/^[a-f0-9]{64}$/);
  assert.equal(r.vendorBarLabelSemanticsCertified,false);
  assert.equal(r.completeBarAvailabilityCertified,false);
  assert.equal(r.marketwideSelectorDataAvailable,false);
 }finally{fs.rmSync(root,{recursive:true,force:true})}
});
test('PowerShell archive is opt-in and does not touch saved workbooks or orders',()=>{
 const s=fs.readFileSync(new URL('../windows/Probe-No11SavedExcelChartInputsReadOnly.ps1',import.meta.url),'utf8');
 assert.equal(s.charCodeAt(0),0xFEFF);
 assert.match(s,/\[switch\]\$SaveEvidence/);
 assert.match(s,/FileMode\]::CreateNew/);
 assert.match(s,/chart-evidence-/);
 assert.match(s,/NO11_CHART_EVIDENCE_SHA256=/);
 assert.match(s,/\$book\.Close\(\$false\)/);
 for(const p of [/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,
  /Workbooks\.Open\(/i,/SaveAs\(/i,/\.Save\(/i,
  /Invoke-WebRequest|Invoke-RestMethod/i])
  assert.doesNotMatch(s,p);
});
