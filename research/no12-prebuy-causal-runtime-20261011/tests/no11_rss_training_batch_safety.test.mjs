import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const script=path.resolve('research/no12-prebuy-causal-runtime-20261011/windows/Capture-No11RssTrainingBatchReadOnly.ps1');
const bytes=fs.readFileSync(script);
const text=bytes.toString('utf8');

test('No11 batch source: UTF8 BOM and bounded parameters',()=>{
 assert.deepEqual([...bytes.subarray(0,3)],[239,187,191]);
 assert.match(text,/ValidateRange\(1,20\)/);
 assert.match(text,/ValidateRange\(20,3000\)/);
 assert.match(text,/existing\+\$BatchSize -gt 50/);
});

test('No11 batch source: no broker order or saved workbook modification',()=>{
 assert.doesNotMatch(text,/Rss(?:StockOrder|CancelOrder|ModifyOrder)\s*\(|RegisterXLL|\.SaveAs\s*\(|\.Save\s*\(|productionReady\s*=\s*\$true|orderTransmission\s*=\s*\$true/i);
 assert.match(text,/\$book=\$excel\.Workbooks\.Add\(\)/);
 assert.match(text,/\$book\.Close\(\$false\)/);
 assert.match(text,/SpecialCells\(-4123\)/);
 assert.match(text,/NO11_BATCH_ONLY_TWO_ORIGINAL_WORKBOOKS_REQUIRED/);
 assert.match(text,/NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST/);
 assert.match(text,/Get-Process EXCEL -ErrorAction SilentlyContinue \| Where-Object/);
 assert.match(text,/MainWindowTitle -like 'Ark_No11_\*'/);
 assert.match(text,/MainWindowHandle -ne \[IntPtr\]::Zero/);
 assert.match(text,/\$arkNamed\.Count -eq 1/);
 assert.match(text,/\$arkNamed\.Count -eq 0 -and \$visible\.Count -eq 1/);
 assert.match(text,/if\(\$processes\.Count -ne 1\)\{throw 'NO11_BATCH_EXCEL_IDENTITY_NOT_UNIQUE'\}/);
 assert.doesNotMatch(text,/\$processes=@\(Get-Process EXCEL -ErrorAction Stop\)/);
});

test('No11 batch source: immutable receipts and no model promotion',()=>{
 assert.match(text,/FileMode\]::CreateNew/);
 assert.match(text,/SOURCE_UNAVAILABLE/);
 assert.match(text,/modelTrainingReady=\$false/);
 assert.match(text,/actualHistoricalKnownAtCertified=\$false/);
 assert.match(text,/NO11_BATCH_NO_USABLE_SYMBOL_IN_WAVE/);
});

test('No11 batch Windows PowerShell parse and synthetic formula/OHLCV checks, no Excel', {skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',script,'-OfflineSelfTest'],{encoding:'utf8',timeout:30000});
 assert.equal(r.status,0,String(r.stderr||r.error||r.stdout));
 assert.match(r.stdout,/NO11_TRAINING_BATCH_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/NO11_LIVE_DATA_ACCESSED=False/);
 assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
});
