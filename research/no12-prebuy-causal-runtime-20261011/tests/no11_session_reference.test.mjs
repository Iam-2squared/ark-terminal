import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const file=new URL('../windows/Capture-No11SessionReferenceReadOnly.ps1',import.meta.url);
const wrapper=new URL('../windows/Prepare-No11ReceivedInputsReadOnly.ps1',import.meta.url);
test('reference source is official RssMarket fields and no order or saved book changes',()=>{
 const src=fs.readFileSync(file,'utf8');assert.ok(src.startsWith('\ufeff'));
 for(const field of ['前日終値','前日日付','当日基準値','市場部名称','単位株数'])assert.ok(src.includes(field));
 assert.match(src,/\$symbols\.Count -le 50/);assert.match(src,/MARKET_CAPACITY_EXCEEDED/);
 assert.match(src,/corporateActionReviewPerformed=\$false/);
 assert.match(src,/\$book\.Close\(\$false\)/);
 assert.doesNotMatch(src,/RssStockOrder\s*\(|RssCancelOrder\s*\(|\.SaveAs\s*\(|\.Save\s*\(|\.Quit\s*\(|Stop-Process/);
});
test('input preparation delegates to original scope previous converter and same-run launcher',()=>{
 const src=fs.readFileSync(wrapper,'utf8');
 for(const name of ['no11_export_chart50_prescreen.mjs','no11_previous_archive_context.py','no11_prepare_received_inputs.py','Run-No11ReceivedSessionReadOnly.ps1'])assert.ok(src.includes(name));
 // The orchestration moved into a testable function, with explicit Options.
 // Preserve the actual opt-in and same-day gates, not the former local names.
 assert.match(src,/if\(-not \$Options\.StartShadow\)\{\$launch\+=@\('-PreflightOnly'\)\}/);
 assert.match(src,/\$session=\[string\]\$config\.sessionDate/);
 assert.match(src,/if\(\(\(-not \$Options\.CheckOnly\) -and \$session -cne \$today\) -or \$session -clt \$today\)/);
 assert.match(src,/if\(\$Options\.CheckOnly\)\{[\s\S]*?return\s*\}/);
 assert.doesNotMatch(src,/RssStockOrder\s*\(|RssCancelOrder\s*\(|\.Formula\s*=|Stop-Process|pip install/);
});
test('Windows session-reference formula parser without Excel',{skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',fileURLToPath(file),'-OfflineSelfTest'],{encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,r.stdout+'\n'+r.stderr);assert.match(r.stdout,/NO11_REFERENCE_OFFLINE_SELFTEST=PASS/);
});
test('Windows input-preparation entrypoint offline check without data or models',{skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',fileURLToPath(wrapper),'-OfflineSelfTest'],{encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,r.stdout+'\n'+r.stderr);assert.match(r.stdout,/NO11_INPUTS_WINDOWS_OFFLINE_SELFTEST=PASS/);
});
