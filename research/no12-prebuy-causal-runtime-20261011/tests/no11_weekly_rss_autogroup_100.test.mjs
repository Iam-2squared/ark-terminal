import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const daily=fileURLToPath(new URL('../windows/Run-No11WeeklyCandidateRefreshReadOnly.ps1',import.meta.url));
const nightly=fileURLToPath(new URL('../windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1',import.meta.url));
const october=fileURLToPath(new URL('../windows/Run-No11Oct28CatchUpReadOnly.ps1',import.meta.url));
const catchup=fileURLToPath(new URL('../windows/Run-No11WeeklyCandidateCatchUpReadOnly.ps1',import.meta.url));
const read=p=>fs.readFileSync(p,'utf8');
const source=read(daily),parent=read(nightly);

test('future RSS daily workflow defaults to 100-symbol automatic workgroups',()=>{
 for(const token of [
  '[ValidateSet(50,100)][int]$GroupSize=100',
  '[ValidateRange(1,47)][int]$BatchSize=30',
  '[ValidateRange(5,60)][int]$WaitSeconds=25',
  'NextWaveEnd $offset $remaining.Count $GroupSize $physical',
  '$batch=@($remaining[$offset..($waveEnd-1)])',
  '$offset=$waveEnd',
  'NO11_DAILY_GROUP_COMPLETE=',
  'NEXT_WAVE_AUTO=True',
  'NO11_DAILY_PROGRESS=',
  'NO11_DAILY_RESUME_VERIFIED='
 ])assert.ok(source.includes(token),token);
 for(const token of [
  '[ValidateSet(50,100)][int]$RefreshGroupSize=100',
  '[ValidateRange(1,47)][int]$RefreshBatchSize=30',
  "'-GroupSize',[string]$RefreshGroupSize",
  "'-BatchSize',[string]$RefreshBatchSize",
  "'-WaitSeconds',[string]$RefreshWaitSeconds"
 ])assert.ok(parent.includes(token),token);
});
test('physical charts never exceed original RSS 50 limit and retain three free slots',()=>{
 for(const token of [
  'function SafePhysicalBatch',
  '$capacity=50-$originalCharts-3',
  'if($capacity -lt 1){throw',
  'return [Math]::Min($requested,$capacity)',
  'function NextWaveEnd',
  '$groupEnd=[int]([Math]::Floor($offset/$groupSize)+1)*$groupSize',
  'return [Math]::Min($remaining,[Math]::Min($offset+$physical,$groupEnd))',
  'NO11_DAILY_BATCH_POLICY=GROUP_',
  'LIMIT_50','RESERVE_3',
  'NO11_DAILY_AUTO_100_GROUP_OFFLINE_SELFTEST=PASS'
 ])assert.ok(source.includes(token),token);
 assert.doesNotMatch(source,/\$existing\+\$BatchSize -gt 50/);
});
test('partial/unavailable Yahoo or RSS data never fabricated and bounded empty-wave retry preserved',()=>{
 for(const token of [
  'NO11_DAILY_EMPTY_WAVE_RETRY=',
  '$emptyRetry -ge 2',
  'NO11_DAILY_ALL_EMPTY_WAVE_RETRY_AFTER_RECONNECT',
  '$physical=[Math]::Max(1,[int][Math]::Floor($physical/2))',
  'NO11_DAILY_BATCH_TUNE=PARTIAL_REDUCED_TO_',
  'NO11_DAILY_BATCH_TUNE=FULL_WAVES_RAISED_TO_',
  '$fullWaves -ge 2',
  'NO11_DAILY_NO_FULL_HISTORY_IN_WAVE_REVIEW_PARTIAL_REPORT',
  'NO11_WEEKLY_DAILY_REFRESH=COMPLETE_NOT_FULL_UNIVERSE',
  'ORDER_TRANSMISSION=False'
 ])assert.ok(source.includes(token),token);
 const failIndex=source.indexOf('if($usable -eq 0){throw');
 const saveIndex=source.indexOf('foreach($payload in $payloads){Save-Capture');
 assert.ok(failIndex>0 && failIndex<saveIndex,'no entirely empty RSS wave may be saved');
 for(const regex of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Stop-Process|taskkill|git\s+reset|git\s+checkout/,
  /orderTransmission\s*=\s*\$true/])
  assert.doesNotMatch(source,regex);
});
test('today Oct28 on-device catch-up scripts remain unchanged by tomorrow optimization',()=>{
 const one=read(october),two=read(catchup);
 assert.match(one,/\[ValidateRange\(1,20\)\]\[int\]\$BatchSize=20/);
 assert.match(two,/\[ValidateRange\(1,20\)\]\[int\]\$BatchSize=20/);
 assert.doesNotMatch(one,/GroupSize=100/);
 assert.doesNotMatch(two,/GroupSize=100/);
});
test('Windows PowerShell source executes both 50 and 100-group offline tests without Excel', {skip:process.platform!=='win32'},()=>{
 for(const g of [50,100]){
  const cmd=spawnSync('powershell.exe',
   ['-NoProfile','-ExecutionPolicy','Bypass','-File',daily,
    '-OfflineSelfTest','-GroupSize',String(g),'-BatchSize','30'],
   {encoding:'utf8',timeout:25000});
  assert.equal(cmd.status,0,(cmd.stdout||'')+'\n'+(cmd.stderr||''));
  assert.match(cmd.stdout,/NO11_DAILY_AUTO_100_GROUP_OFFLINE_SELFTEST=PASS/);
  assert.match(cmd.stdout,/NO11_DAILY_OFFLINE_SELFTEST=PASS/);
  assert.match(cmd.stdout,/ORDER_TRANSMISSION=False/);
 }
});
