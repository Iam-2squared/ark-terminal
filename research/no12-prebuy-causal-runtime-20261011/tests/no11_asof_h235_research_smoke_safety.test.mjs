import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const script=path.resolve('research/no12-prebuy-causal-runtime-20261011/windows/Run-No11AsOfH235ResearchSmokeReadOnly.ps1');
const buffer=fs.readFileSync(script);
const content=buffer.toString('utf8');

test('No11 research smoke runner: bounded only to private offline models',()=>{
 assert.deepEqual([...buffer.subarray(0,3)],[0xef,0xbb,0xbf]);
 assert.match(content,/OFFLINE_RESEARCH_ONLY/);
 assert.match(content,/SOURCE_HASH_INVALID/);
 assert.match(content,/MODEL/ig);
 assert.match(content,/NO11_ASOF_RESEARCH_SMOKE=PASS_DEVELOPMENT_ONLY/);
 assert.match(content,/modelFrom2026Data -ne \$false/);
 assert.match(content,/originalFrozenReplaced -ne \$false/);
 assert.match(content,/NO11_NATIVE_SELECTOR_AND_ENTRY_CONNECTED=False/);
 assert.match(content,/ORDER_TRANSMISSION=False/);
 assert.doesNotMatch(content,/RssStockOrder|RssCancelOrder|RssModifyOrder|SaveAs|Remove-Item|Stop-Process|New-Object -ComObject|Excel.Application/);
});
