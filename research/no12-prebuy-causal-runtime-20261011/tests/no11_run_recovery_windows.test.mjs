import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const launcher=path.join(base,'windows/Run-No11ReceivedSessionReadOnly.ps1');
test('same-run controller is the default launcher and explicit resume keeps argument boundaries',()=>{
 const ps=fs.readFileSync(launcher,'utf8');
 assert.match(ps,/no11_received_session_controller\.py/);
 assert.match(ps,/\[string\]\$ResumeRun/);
 assert.match(ps,/'--resume-run',\$resume/);
 assert.doesNotMatch(ps,/Stop-Process|taskkill|Remove-Item|RssStockOrder\s*\(|RssCancelOrder\s*\(/i);
 assert.ok([...ps].every(c=>c.charCodeAt(0)<128));
});
test('Windows launcher parses and self-checks new and resume arguments without Excel',{
 skip:process.platform!=='win32'
},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',launcher,'-OfflineSelfTest'],
  {encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
 assert.match(r.stdout,/NO11_BOOTSTRAP_RESUME_ARGUMENT_SELFTEST=PASS/);
 assert.match(r.stdout,/NO11_BOOTSTRAP_COLLECTOR_STARTED=False/);
});
test('resume and failure isolation do not introduce broker writes or model fitting',()=>{
 for(const name of ['no11_received_run_recovery.py','no11_received_session_controller.py','no11_received_failure_isolation.py']){
  const src=fs.readFileSync(path.join(base,'tools',name),'utf8');
  assert.doesNotMatch(src,/RssStockOrder\s*\(|RssCancelOrder\s*\(|\.kill\(|\.terminate\(|shell\s*=\s*True|\.fit\(/i);
  assert.doesNotMatch(src,/['"]orderTransmission['"]\s*:\s*True|['"]productionReady['"]\s*:\s*True/);
 }
 const iso=fs.readFileSync(path.join(base,'tools/no11_received_failure_isolation.py'),'utf8');
 assert.match(iso,/ENTRY_PIPELINE_HALT:/);
 assert.match(iso,/self\.portfolio\._event/);
 assert.match(iso,/self\._verify_held_prefix\(feed\)/);
});
