import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';
import {auditPrivateOriginalFirstEntryClocks as audit} from '../tools/audit_no11_first_entry_clock_private.mjs';
function fixture(gzip=true){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'no11-intent-timing-'));
 const file=path.join(dir,'FIRST_ENTRY_Q70.jsonl'+(gzip?'.gz':''));
 const data=[
  {session:'2026-10-13',family:'P1',policy:'Q70',symbol:'1234.T',fill_price:5302,
   selector_minute:565,first_intent:{intent_minute:570},fill_minute:570,
   intent_to_fill_active_delay:0,selector_to_entry_active_delay:5},
  {session:'2026-10-13',family:'P1',policy:'Q70',symbol:'5678.T',fill_price:1357,
   selector_minute:565,first_intent:{intent_minute:570},fill_minute:572,
   intent_to_fill_active_delay:2,selector_to_entry_active_delay:7},
  {session:'2026-10-13',family:'P1',policy:'Q70',symbol:'5555.T',
   selector_minute:565,first_intent:null,fill_minute:null},
  {session:'2026-10-13',family:'P0',policy:'Q70',symbol:'4321.T',
   selector_minute:565,first_intent:{intent_minute:570},fill_minute:570}
 ];
 const json=Buffer.from(data.map(x=>JSON.stringify(x)).join('\n')+'\n');
 fs.writeFileSync(file,gzip?zlib.gzipSync(json):json);
 return {file,dispose:()=>fs.rmSync(dir,{recursive:true,force:true})};
}
test('locally count original scheduled clock parity without emitting any private symbol or price',async()=>{
 const f=fixture();try{
  const r=await audit({localInputPath:f.file,family:'P1',policy:'Q70'});
  assert.equal(r.total,2);assert.equal(r.selectedRecords,3);
  assert.equal(r.noFirstIntentRecords,1);assert.equal(r.ignoredOtherPolicyRecords,1);
  assert.equal(r.deterministicScheduleMatch,1);assert.equal(r.scheduleMismatch,1);
  assert.equal(r.privateRowsExported,false);assert.equal(r.modelScoreComputed,false);
  assert.equal(r.productionReady,false);
  const encoded=JSON.stringify(r);
  for(const sensitive of ['1234.T','5678.T','5302','1357',f.file])
   assert.equal(encoded.includes(sensitive),false);
 }finally{f.dispose()}
});
test('plain local JSONL works; missing or bogus file paths fail closed',async()=>{
 const f=fixture(false);try{
  const r=await audit({localInputPath:f.file});assert.equal(r.total,2);
  await assert.rejects(audit({localInputPath:'/not/found.jsonl'}));
  await assert.rejects(audit({localInputPath:f.file,family:'UNKNOWN'}),/NO11_LOCAL_AUDIT_ARGUMENT_INVALID/);
 }finally{f.dispose()}
});
test('neither private CLI nor evaluator exposes RSS orders/network calls',()=>{
 const script=fs.readFileSync(new URL('../tools/audit_no11_first_entry_clock_private.mjs',import.meta.url),'utf8');
 for(const re of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/https?:\/\//,/\bfetch\s*\(/,/\bgit\s+push\b/i])
  assert.doesNotMatch(script,re);
});
