import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {auditNo11State9InputBoundary as audit} from '../runtime/no11_state9_rss_input_boundary.mjs';
const time=(m)=>'2026-10-13T14:'+String(m).padStart(2,'0')+':00+09:00';
const row=m=>({label:time(m),open:100,high:101,low:99,close:100,volume:100});
test('market RSS OHLCV never silently becomes Frozen State9 input',()=>{
 const obj={
  schemaId:'ARK_NO11_RSS_CHART_DUAL_EVIDENCE_V1',
  symbol:'7203.T',sourceFunction:'RssChart',evidenceMode:'OBSERVED_READ_ONLY',
  privateAccountDataIncluded:false,excelOrderEnabled:false,
  labelSemanticsCertified:false,brokerArrivalCertified:false,
  originalNativeState9Certified:false,productionReady:false,orderTransmission:false,
  capturedAt:time(20),
  periods:{
   '1M':{observedAt:time(18),requestedBars:300,validRows:5,rows:[0,1,2,3,4].map(row)},
   '5M':{observedAt:time(19),requestedBars:100,validRows:1,rows:[row(0)]}
  }
 };
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'no11-state9-boundary-'));
 try{
  const file=path.join(dir,'chart-evidence-'+'a'.repeat(32)+'.json');
  fs.writeFileSync(file,JSON.stringify(obj));
  const r=audit({file,now:new Date(time(21))});
  assert.equal(r.observedParity.matched,1);
  assert.equal(r.nativeState9Connected,false);
  assert.equal(r.productionReady,false);
  assert(r.blockers.includes('EXACT_NORMALIZED_DECIMAL_OHLC_ADAPTER_NOT_CERTIFIED'));
  assert(r.blockers.includes('SINGLE_SYMBOL_NOT_MARKETWIDE_SELECTOR'));
 }finally{fs.rmSync(dir,{recursive:true,force:true})}
});
