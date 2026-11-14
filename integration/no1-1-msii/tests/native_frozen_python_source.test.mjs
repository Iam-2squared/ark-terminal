import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const dir=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../frozen-native-code');
const gitBlob=bytes=>createHash('sha1').update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');
const source={
 'core_features.py':'685a7774ed96556b810aa23957d12fda8f9654ba',
 'preprocessing.py':'29119e9d9e5ca880159289728c9391e17f8427ca',
 'staircase.py':'6863b2dded50e4d0caa4e2d470619017fcf0b759'
};
test('frozen native math uses exact original public Git blobs, not recomputed new coefficients',()=>{
 for(const [name,expected] of Object.entries(source)){
  const raw=fs.readFileSync(path.join(dir,name));
  const text=Buffer.from(raw.toString('utf8').replace(/\r\n/g,'\n'));
  assert.equal(gitBlob(text),expected,name);
 }
});
test('original selftest imports pinned original preprocessing and staircase without broker access',()=>{
 const code=fs.readFileSync(path.resolve(dir,'../tools/no11_native_original_python_smoke.py'),'utf8');
 for(const phrase of ['ORIGINAL_NATIVE_MODEL_HASH_MISMATCH','--offline-self-test',
  '--private-model-smoke','predict_saved([case], artifact)','materialize(data)',
  'NO11_NATIVE_LIVE_DECISION_EMITTED=False','ORDER_TRANSMISSION=False'])
  assert.ok(code.includes(phrase),phrase);
 for(const re of [/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,/explicitSafetyReset\s*\(/i,/\brequests\./i,/\burllib\./i])
  assert.doesNotMatch(code,re);
});
