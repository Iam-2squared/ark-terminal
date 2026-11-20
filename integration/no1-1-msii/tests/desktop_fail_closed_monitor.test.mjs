import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {faultStatus} from '../tools/no11_fault_cli.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const source=fs.readFileSync(path.resolve(here,'../windows/Start-No11DesktopReadOnly.ps1'),'utf8');
const launcher=fs.readFileSync(path.resolve(here,'../windows/Start-No11DesktopUi.ps1'),'utf8');

test('desktop capture is exclusive and fails closed without Excel writes',()=>{
  assert.match(source,/Local\\ArkTerminal_No11_RSS_ReadOnly/);
  assert.match(source,/WaitOne\(0\)/);
  assert.match(source,/CAPITAL_OR_OWNERSHIP_GATE_BLOCKED/);
  assert.match(source,/READ_ONLY_CAPTURE_FAILED/);
  assert.match(source,/\$faultCli 'latch' '--ledger' \$ledger/);
  assert.doesNotMatch(source,/\.\s*(?:Save|SaveAs|RegisterXLL)\s*\(/i);
  assert.doesNotMatch(source,/\bRssStockOrder\s*\(/i);
  assert.match(launcher,/--max-model-age-seconds','30'/);
});

test('read-only gate failures persist on disk and never enable orders',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ark-no11-ro-fault-'));
  const ledger=path.join(dir,'safety.json');
  try {
    assert.equal(faultStatus({mode:'status',ledger}).killSwitchLatched,true);
    const latched=faultStatus({mode:'latch',ledger,reason:'CAPITAL_OR_OWNERSHIP_GATE_BLOCKED'});
    assert.equal(latched.killSwitchLatched,true);
    assert(latched.faults.includes('CAPITAL_OR_OWNERSHIP_GATE_BLOCKED'));
    const restored=faultStatus({mode:'status',ledger});
    assert(restored.faults.includes('CAPITAL_OR_OWNERSHIP_GATE_BLOCKED'));
    assert.equal(restored.executionAllowed,false);
    assert.equal(restored.transmitted,false);
  } finally { fs.rmSync(dir,{recursive:true,force:true}); }
});
