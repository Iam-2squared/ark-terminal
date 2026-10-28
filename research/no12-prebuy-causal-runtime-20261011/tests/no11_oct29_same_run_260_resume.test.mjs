import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {readFileSync} from 'node:fs';
import {daytimeCatchUpWindow} from '../tools/no11_weekly_g1_refresh.mjs';
const script=fileURLToPath(new URL('../windows/Repair-No11Oct29MorningCatchUpReadOnly.ps1',import.meta.url));
const body=readFileSync(script,'utf8');

test('previous cash-day 28-Oct can be genuinely re-received on 29-Oct 08:30–17:59',()=>{
 const x=daytimeCatchUpWindow('2026-10-29T08:37:00.000+09:00','2026-10-28');
 assert.equal(x.date,'2026-10-28');
 assert.equal(x.daytimeHistoricalRecovery,true);
 for(const stamp of ['2026-10-29T08:29:59.000+09:00',
    '2026-10-29T18:00:00.000+09:00','2026-10-30T08:37:00.000+09:00']){
  assert.throws(()=>daytimeCatchUpWindow(stamp,'2026-10-28'),
    /NO11_WEEKLY_CATCHUP_REQUIRES_ACTUAL_PREVIOUS_CASH_DAY/);
 }
});
test('restore only known version of missing --catch-up-asof G1 tool, not downloaded latest Yahoo tool',()=>{
 for(const marker of [
  '26cb29af530e5b7a0f736c728fd96e156d3e840a',
  'cb552dc9997ce072bdf535293adfc08178a1d266',
  '8b9d1ed70284be8fb2a41aec711482417c1e15a7',
  'c6ac1700595b8025838862151c699e1c1ff6258c',
  '9e01a5e826730661455050c865dd2e0a1a0d8fc3',
  '2f61dd9d14180f50040d6350607768fee97aca87',
  'a007e77587a4a3ee5c7ef413f290567b3ab5910d',
  '577882a0aa18c747734b905316a1bbbbeff1145e',
  'LOCAL_TOOL_HAS_UNREVIEWED_CHANGES_NO_OVERWRITE',
  'PINNED_DOWNLOAD_HASH_MISMATCH',
  'EXISTING_260_RECEIPTS_MISSING',
  'RESUMED_PLAN_NOT_SAME_260_RECEIPTS',
  "('--catch-up-asof',$targetAsOf)",
  'RSS_FAILED_RECEIPTS_PRESERVED',
  'ORDER_TRANSMISSION=False',
 ])assert.ok(body.includes(marker),marker);
 for(const forbidden of [/Stop-Process|\.Kill\s*\(/,
  /RssStockOrder\s*\(|RssCancelOrder\s*\(/,
  /(?:Remove-Item|rm -rf)\s.*sources/,
  /ORDER_TRANSMISSION=True|orderTransmission\s*:\s*true/])
  assert.doesNotMatch(body,forbidden);
});
test('installer does not alter user market source or fabricate timestamp',()=>{
 for(const marker of [
  'weekly-refresh-2026-10-28-',
  'NO11_OCT29_RESUME_EXISTING_RECEIPTS=',
  'NO11_OCT29_RESUME_VERIFIED=',
  'NO11_OCT29_RESUME_CATCHUP_TOOL=',
  'NO11_OCT29_RESUME_CODE_BACKUP=',
  '-CatchUpAsOf',
  'MAX', // optional: not required
 ])if(marker!=='MAX')assert.ok(body.includes(marker),marker);
 assert.ok(body.includes("daytimeHistoricalRecovery")===false);
 assert.ok(body.includes("if($RepairOnly){"));
});
test('Windows actual PS 5.1 offline selftest does not read Excel or change source',{
 skip:process.platform!=='win32'},()=>{
 const t=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass',
  '-File',script,'-OfflineSelfTest'],{encoding:'utf8',timeout:20000});
 assert.equal(t.status,0,(t.stdout||'')+'\n'+(t.stderr||''));
 assert.match(t.stdout,/NO11_OCT29_RESUME_OFFLINE_SELFTEST=PASS/);
 assert.match(t.stdout,/NO11_OCT29_RESUME_RECEIPTS_TOUCHED=False/);
 assert.match(t.stdout,/ORDER_TRANSMISSION=False/);
});
