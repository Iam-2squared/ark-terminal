import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source=fs.readFileSync(new URL('../daytrade/phase57-p25-data-driven-exit-multisession.js',import.meta.url),'utf8');

test('formal paired evaluator filters frozen membership to DYNAMIC_50 before simulation',()=>{
  const filterIndex=source.indexOf("includes('DYNAMIC_50')");
  const simulateIndex=source.indexOf('simulateP25DataDrivenExit');
  assert.ok(filterIndex>=0);
  assert.ok(source.indexOf('simulateP25DataDrivenExit',simulateIndex+1)>filterIndex);
});
