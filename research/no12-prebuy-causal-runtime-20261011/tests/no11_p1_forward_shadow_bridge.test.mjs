import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const tests=path.dirname(fileURLToPath(import.meta.url));
const tool=path.resolve(tests,'../tools/no11_p1_forward_shadow.py');
test('P1 forward shadow reuses frozen inference, not fit or broker execution',()=>{
 const source=fs.readFileSync(tool,'utf8');
 assert.match(source,/original\.FrozenP1Fold\(5,/);
 assert.match(source,/score_named_batch/);
 assert.match(source,/StateFeatureStream/);
 assert.match(source,/FIRST_ENTRY_CANDIDATE/);
 assert.match(source,/BEGIN IMMEDIATE/);
 assert.match(source,/LATEST_SAVED_TRAINING_END_NO_PERFORMANCE_SEARCH/);
 assert.doesNotMatch(source,/\.fit\s*\(|RssStockOrder|RssCancelOrder/);
});
test('P1 F5/Q70 original public binding, durable Watch and first-entry safety',()=>{
 const executable=process.platform==='win32'?'python':'python3';
 const child=spawnSync(executable,['-m','unittest','discover','-s',tests,'-p','test_no11_p1_forward_shadow.py','-v'],
  {encoding:'utf8',timeout:60000,windowsHide:true});
 assert.equal(child.status,0,(child.stderr??'')+'\n'+(child.stdout??''));
 assert.match(child.stderr,/Ran 21 tests/);
 assert.match(child.stderr,/OK/);
 assert.doesNotMatch(child.stderr,/Full repository source not mounted/);
});
