import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const dir=fileURLToPath(new URL('../windows/Install-No11PrivateNativeModels.ps1',import.meta.url));
const cli=fileURLToPath(new URL('../tools/no11_native_model_audit.mjs',import.meta.url));
const contents=fs.readFileSync(dir,'utf8');
test('private model one-time importer is package-SHA-pinned, private-path only, idempotent',()=>{
 for(const key of ['990A0AADDDDDA36DEC4C2E7D77BEC291C306E57265B2D1879AC1447B1A0BDC80',
   'Get-FileHash -LiteralPath $ArchivePath','private-native-models','private-native-staging-',
   'Expand-Archive -LiteralPath $ArchivePath','Move-Item -LiteralPath $stage',
   'NATIVE_EXISTING_MODEL_SOURCE_INVALID','NATIVE_INSTALLED_MODEL_SOURCE_INVALID']){
   assert.ok(contents.includes(key),key);
 }
 assert.equal((contents.match(/& \$node \$auditor '--model-root'/g)||[]).length,3);
});
test('original private importer cannot transmit, mutate Excel or reset Safety',()=>{
 for(const re of [/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,/Excel.Application/,
  /\.Formula\s*=/,/explicitSafetyReset\s*\(/,/killSwitchLatched\s*=\s*false/]){
  assert.doesNotMatch(contents,re);
 }
 assert.match(contents,/ORDER_TRANSMISSION=False/);
 assert.match(contents,/NO11_PRODUCTION_READY=False/);
});
test('CLI refuses missing original models without claiming model verification',()=>{
 const empty=fs.mkdtempSync(path.join(os.tmpdir(),'no11-model-cli-'));
 try{
  const r=spawnSync(process.execPath,[cli,'--model-root',path.join(empty,'not-there')],{
   encoding:'utf8',env:{...process.env,LOCALAPPDATA:empty},timeout:3000});
  assert.equal(r.status,2);
  assert.match(r.stdout,/NO11_NATIVE_MODELS_MISSING=24/);
  assert.match(r.stdout,/NO11_NATIVE_DECISION_EMITTED=False/);
  assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
 }finally{fs.rmSync(empty,{recursive:true,force:true})}
});
