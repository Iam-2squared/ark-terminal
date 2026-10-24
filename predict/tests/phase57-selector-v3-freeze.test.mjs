import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import {createHash} from 'node:crypto';

test('Selector V3.0 preregistration bytes match the committed freeze digest',()=>{
  const spec=fs.readFileSync(new URL('../research/phase57-selector-v3-freeze.json',import.meta.url));
  const expected=fs.readFileSync(new URL('../research/phase57-selector-v3-freeze.sha256',import.meta.url),'utf8').trim().split(/\s+/)[0];
  assert.equal(createHash('sha256').update(spec).digest('hex'),expected);
  const parsed=JSON.parse(spec);
  assert.equal(parsed.status,'PRE_REGISTERED_FROZEN_BEFORE_LARGE_SCALE_HISTORICAL_OUTCOMES');
  assert.equal(parsed.freezeDiscipline.largeScaleHistoricalOutcomesSeenBeforeFreeze,false);
});

