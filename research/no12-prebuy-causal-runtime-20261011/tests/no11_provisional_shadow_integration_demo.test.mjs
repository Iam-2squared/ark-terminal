import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const source=new URL('../tools/no11_provisional_shadow_integration_demo.mjs',import.meta.url);
test('No11 user-approved provisional H235 synthetic integration demo runs all stages without broker',()=>{
 const out=spawnSync(process.execPath,[fileURLToPath(source)],{
  encoding:'utf8',timeout:15000
 });
 assert.equal(out.status,0,out.stderr||String(out.error));
 const required=[
  'NO11_PROVISIONAL_2025_H235_DEVELOPMENT_LEARNING=COMPLETE_RESEARCH_ONLY',
  'NO11_INTEGRATION_SYNTHETIC_SOURCE_ASOF=PASS',
  'NO11_INTEGRATION_SYNTHETIC_ENTRY_TO_CASH=PASS',
  'NO11_INTEGRATION_SYNTHETIC_STATE9_SHARP_DROP_TO_EXIT_INTENT=PASS',
  'NO11_INTEGRATION_SYNTHETIC_SELL_FILL_AND_DAY_LATCH=PASS',
  'NO11_INTEGRATION_ORIGINAL_FROZEN_SELECTOR_EXECUTED=False',
  'NO11_INTEGRATION_ORIGINAL_FROZEN_H235_EXECUTED=False',
  'NO11_INTEGRATION_ORIGINAL_CAPITAL_V5_PYTHON_SYNTHETIC=PASS',
  'NO11_INTEGRATION_FROZEN_CAPITAL_LIVE_SAB_EXECUTED=False',
  'NO11_INTEGRATION_NATIVE_E2E_CERTIFIED=False',
  'NO11_PRODUCTION_READY=False',
  'ORDER_TRANSMISSION=False'
 ];
 for(const line of required)assert.ok(out.stdout.includes(line),'missing '+line);
 const contents=fs.readFileSync(source,'utf8');
 for(const deny of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
   /Excel.Application/,/\bfetch\s*\(/,/node:net/,/node:http/,
   /orderTransmission\s*:\s*true/,/productionReady\s*:\s*true/]){
   assert.doesNotMatch(contents,deny);
 }
});
