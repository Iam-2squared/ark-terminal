import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
test('public standalone executable validates full synthetic buy/sell/no-new-buy day with no brokerage',()=>{
 const script=new URL('../tools/no12_offline_demo.mjs',import.meta.url);
 const run=spawnSync(process.execPath,[script.pathname],{
   encoding:'utf8',env:{...process.env},timeout:5000
 });
 assert.equal(run.status,0,run.stderr);
 for(const line of ['NO12_SYNTHETIC_FULL_LIFECYCLE_PASS=True',
   'NO12_SYNTHETIC_PERSONAL_EXCLUDED=True',
   'NO12_SYNTHETIC_SELL_FILL_HALTS_NEW_BUY=True',
   'NO12_ORIGINAL_NO11_R0_REPRODUCED=False',
   'NO12_NATIVE_STRATEGY_CERTIFIED=False','NO12_LIVE_ORDER_ENABLED=False']){
     assert(run.stdout.includes(line),line);
 }
 const src=fs.readFileSync(script,'utf8');
 for(const re of [/RssStockOrder\s*\(/,/fetch\s*\(/,/axios|Excel.Application|node:net|node:http/i])
   assert.doesNotMatch(src,re);
});
