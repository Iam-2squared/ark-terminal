import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const file=fileURLToPath(new URL('../tools/no11_nov02_bootstrap_bridge_readonly.py',import.meta.url));
const source=fs.readFileSync(file,'utf8');
const python=process.platform==='win32'?'python':'python3';
const run=(args)=>spawnSync(python,['-B',file,...args],{encoding:'utf8',timeout:30000});

test('Nov2 source-only bridge reads 24 original shortlisted symbols, never creates trading approval',()=>{
 for(const token of [
  'NO11_NOV02_BOOTSTRAP_STATIC_24=VERIFIED',
  'NO11_NOV02_BOOTSTRAP_LIVE_CONFIG=NOT_CREATED',
  'NO11_NOV02_BOOTSTRAP_EXTERNAL_LIVE_GATES=STILL_REQUIRED',
  '"sourceMode": "VERIFIED_STATIC_INPUTS_ONLY_NO_DATED_MASTER"',
  '"executableBootstrapCreated": False',
  '"tradePermissionChanged": False',
  '"productionReady": False',
  '"orderTransmission": False',
  'broker_service.settings',
  'bootstrap.validate_scope',
  'EXISTING_EXTERNAL_REVIEW_NOT_INFERRED_BY_ADAPTER',
  'ACTUAL_SESSION_DATE_REQUIRED',
  'PREVIOUS_CONTEXT_NOT_BOUND_TO_REAL_MASTER',
  'AUTO_SECURITIES_ACCOUNT_CASH_ONLY'
 ])assert.ok(source.includes(token),token);
 for(const dangerous of [
  /RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/\bStop-Process\b/,
  /["']orderTransmission["']\s*:\s*True/,
  /corporateActionsCleared[^\n]{0,12}True/,
  /\bopenpyxl\b/,/\bExcel\.Application\b/
 ])assert.doesNotMatch(source,dangerous);
});
test('Nov2 bridge offline selftest is true offline without Excel',()=>{
 const p=run(['--offline-selftest']);
 assert.equal(p.status,0,p.stdout+'\n'+p.stderr);
 assert.match(p.stdout,/NO11_NOV02_BOOTSTRAP_BRIDGE_OFFLINE_SELFTEST=PASS_NO_EXCEL_NO_ORDERS/);
 assert.match(p.stdout,/ORDER_TRANSMISSION=False/);
});
test('Nov2 bridge refuses to create any config without real evidence',()=>{
 const p=run(['--finalize']);
 assert.notEqual(p.status,0);
 assert.match(p.stderr,/NO11_NOV02_BOOTSTRAP_COMMON_PARAMETERS_REQUIRED/);
 assert.match(p.stdout,/ORDER_TRANSMISSION=False/);
});
