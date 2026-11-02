import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const file=fileURLToPath(new URL('../tools/no11_nov02_finish_reviewed_inputs_readonly.py',import.meta.url));
const src=fs.readFileSync(file,'utf8');
test('Nov2 master completion delegates to pinned existing RSS/evidence validator',()=>{
 for(const required of [
  "import no11_prepare_received_inputs as original",
  "import no11_previous_archive_context as archive",
  "original.prepare(",
  "selectedCount'] == 24",
  "masterRows'] == 24",
  "stagedPreviousSymbols'] == 24",
  "NO11_NOV02_BROKER_LIVE_CONFIG=NOT_CREATED",
  "INDEPENDENT_EXTERNAL_REVIEW_REQUIRED",
  "EXTERNAL_REVIEW_MISSING_24",
  "OBSERVED_24_RSS_REFERENCE_REQUIRED",
  "NO11_NOV02_FINISH_OFFLINE_SELFTEST=PASS_MISSING_REVIEW_BLOCKED",
  "'orderTransmission':False",
  "'productionReady':False"
 ])assert.ok(src.includes(required),required);
 for(const forbidden of [
  /\bRssStockOrder\s*\(/,/\bRssCancelOrder\s*\(/,
  /approvedForSession\s*=\s*True/,/automaticOrderAuthorization\s*=\s*True/,
  /commonEquity\s*=\s*True/,/corporateActionsCleared\s*=\s*True/,
  /priceBasisVerified\s*=\s*True/,/brokerExecutionConfig\s*=\s*['"]LIVE/
 ])assert.doesNotMatch(src,forbidden);
});
test('Nov2 master builder self-test fails closed for unavailable real review',()=>{
 const python=process.platform==='win32'?'python':'python3';
 const proc=spawnSync(python,['-B',file,'--offline-selftest'],
    {encoding:'utf8',timeout:30000});
 assert.equal(proc.status,0,proc.stdout+'\n'+proc.stderr);
 assert.match(proc.stdout,/NO11_NOV02_FINISH_OFFLINE_SELFTEST=PASS_MISSING_REVIEW_BLOCKED/);
 assert.match(proc.stdout,/ORDER_TRANSMISSION=False/);
});
test('Nov2 master builder refuses missing input rather than inventing dated master',()=>{
 const python=process.platform==='win32'?'python':'python3';
 const proc=spawnSync(python,['-B',file],{encoding:'utf8',timeout:30000});
 assert.notEqual(proc.status,0);
 assert.match(proc.stderr,/NO11_NOV02_FINISH_MISSING_REVIEW_DOCUMENTS_OR_RSS/);
 assert.match(proc.stdout,/ORDER_TRANSMISSION=False/);
});
