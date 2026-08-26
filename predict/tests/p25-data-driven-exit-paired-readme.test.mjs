import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('paired evaluator research boundary is documented',()=>{
  const text=fs.readFileSync(new URL('../daytrade/README-p25-data-driven-exit-paired.md',import.meta.url),'utf8');
  assert.match(text,/DYNAMIC_50/);
  assert.match(text,/research-only/i);
  assert.match(text,/outcomes are not used to fit or tune/i);
});
