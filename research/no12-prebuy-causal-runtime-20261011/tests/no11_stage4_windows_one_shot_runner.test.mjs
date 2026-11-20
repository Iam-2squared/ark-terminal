import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const ROOT=path.resolve('.');
const runner='research/no12-prebuy-causal-runtime-20261011/windows/Run-No11Stage4Full244AndP1SourceGateReadOnly.ps1';
const py='research/no12-prebuy-causal-runtime-20261011/tools/no11_2026_rc2_sparse_missing_research.py';
const js='research/no12-prebuy-causal-runtime-20261011/tools/no11_2026_first_entry_p1_source_gate.mjs';
const read=s=>fs.readFileSync(path.join(ROOT,s),'utf8');

test('Stage 4 one-shot Windows script pins original 40 receipt plus original 244 technical RC2 and P1 source only',()=>{
 const source=read(runner);
 assert.match(source,/d30f81c94b3f5313dcd1c2543cc393bca4c095c3e73e22336994c9b686b405ca/);
 assert.match(source,/--max-replayed','244'/);
 assert.match(source,/--export-asof/);
 assert.match(source,/--state9-report/);
 assert.match(source,/NO11_STAGE4_FULL_244_RESEARCH_RESULT_INVALID/);
 assert.match(source,/NO11_ORIGINAL_FIRST_ENTRY_SCORE_ROWS=0/);
 assert.match(source,/NO11_PRODUCTION_READY=False/);
 assert.match(source,/ORDER_TRANSMISSION=False/);
 for(const forbidden of [
  /RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Excel\.Application/,/Set-ExecutionPolicy/,/Invoke-WebRequest/,
  /Invoke-RestMethod/,/Start-Job/,/productionReady\s*:\s*true/i
 ])assert.doesNotMatch(source,forbidden);
});

test('Stage 4 script hash pins correspond to the currently checked-out working files',()=>{
 const source=read(runner);
 for(const [p,expected] of [
  [py,'50a3a659127ce5f4d82c6dc56a99931664a36907'],
  [js,'afaf67050a971bd1cf920c001bf6fa8cf8e54e1c']
 ]){
  const result=spawnSync('git',['-C',ROOT,'hash-object','--path='+p,p],{
    encoding:'utf8',timeout:15000
  });
  assert.equal(result.status,0,String(result.stderr||result.error));
  assert.equal(result.stdout.trim(),expected,'Git blob pin: '+p);
  assert.ok(source.includes(expected));
 }
});

test('Stage 4 Windows script is self-testing without saved private RSS or broker',()=>{
 if(process.platform!=='win32')return;
 const result=spawnSync('powershell.exe',[
  '-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
  '-File',path.join(ROOT,runner),'-OfflineSelfTest'
 ],{encoding:'utf8',timeout:20000});
 assert.equal(result.status,0,String(result.stderr||result.error||result.stdout));
 assert.match(result.stdout,/NO11_STAGE4_WINDOWS_RUNNER_OFFLINE_SELFTEST=PASS/);
 assert.match(result.stdout,/ORDER_TRANSMISSION=False/);
});
