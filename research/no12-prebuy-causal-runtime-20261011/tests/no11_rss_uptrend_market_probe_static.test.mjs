import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const script=path.resolve(path.dirname(fileURLToPath(import.meta.url)),
  '../windows/Probe-No11ObservedPassRssMarketReadOnly.ps1');
const source=fs.readFileSync(script,'utf8');

test('temporary RSS quotation probe is neither broker order nor a workbook saver',()=>{
 assert.match(source,/NO11_QWATCH_MARKET_SESSION_ONLY/);
 assert.match(source,/NO11_QWATCH_RSS_QUOTE_CAP_EXCEEDED/);
 assert.match(source,/NO11_QWATCH_EXISTING_MARKET_LIMIT/);
 assert.match(source,/NO11_QWATCH_STALE_OR_UNCERTIFIED_MASK/);
 assert.match(source,/originalSelectorNativeConnected=false/);
 assert.match(source,/quoteFresh30Seconds/);
 assert.match(source,/\.Close\(\$false\)/);
 assert.match(source,/ORDER_TRANSMISSION=False/);
 assert.doesNotMatch(source,/RssStockOrder\s*\(|RssCancelOrder\s*\(|\.SaveAs\s*\(|\.Save\s*\(|productionReady=\$true/);
});
test('RSS quote-only probe source is ASCII Windows PowerShell 5.1 safe',()=>{
 assert.match(source,/RunDir/);
 assert.equal([...source].every(ch=>ch.charCodeAt(0)<=127),true);
});
test('Windows offline parser and fixed quote formula selfcheck',()=>{
 if(process.platform!=='win32')return;
 const r=spawnSync('powershell.exe',
   ['-NoProfile','-ExecutionPolicy','Bypass','-File',script,'-OfflineSelfTest'],
   {encoding:'utf8',timeout:25000,windowsHide:true});
 assert.equal(r.status,0,r.stderr+'\n'+r.stdout);
 assert.match(r.stdout,/NO11_QWATCH_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
});
