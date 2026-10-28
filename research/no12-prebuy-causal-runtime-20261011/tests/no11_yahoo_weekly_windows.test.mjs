import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const script=fileURLToPath(new URL('../windows/Run-No11YahooWeeklySeedReadOnly.ps1',import.meta.url));
test('Windows offline Yahoo weekly helper has no Excel or Yahoo connection', {skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',script,
  '-OfflineSelfTest'],{encoding:'utf8',timeout:30000});
 assert.equal(r.status,0,(r.stdout||'')+'\n'+(r.stderr||''));
 assert.match(r.stdout,/NO11_YAHOO_WEEKLY_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/NO11_YAHOO_WEEKLY_YFINANCE_FETCHED=False/);
 assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
});
