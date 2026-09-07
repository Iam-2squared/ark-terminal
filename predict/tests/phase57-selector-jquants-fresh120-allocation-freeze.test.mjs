import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';

const jsonUrl=new URL('../research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url);
const shaUrl=new URL('../research/phase57-selector-jquants-fresh120-allocation.sha256',import.meta.url);

test('J-Quants Fresh-120 allocation is immutable and OOS remains sealed',()=>{
  const bytes=fs.readFileSync(jsonUrl);
  const expected=fs.readFileSync(shaUrl,'utf8').trim().split(/\s+/)[0];
  assert.equal(createHash('sha256').update(bytes).digest('hex'),expected);
  const value=JSON.parse(bytes);
  assert.equal(value.status,'FRESH_120_ALLOCATION_FROZEN');
  assert.equal(value.development.length,72);
  assert.equal(value.purgeDevelopmentValidation.length,1);
  assert.equal(value.validation.length,24);
  assert.equal(value.purgeValidationOos.length,1);
  assert.equal(value.untouchedOos.length,24);
  assert.equal(new Set([...value.development,...value.purgeDevelopmentValidation,...value.validation,...value.purgeValidationOos,...value.untouchedOos]).size,122);
  assert.equal(value.release.developmentReleased,false);
  assert.equal(value.release.validationReleased,false);
  assert.equal(value.release.untouchedOosReleased,false);
  assert.equal(value.guards.splitMutableAfterFreeze,false);
  assert.equal(value.guards.oosOutcomePayloadRequested,false);
  assert.equal(value.reserve.sessionCount,282);
  assert.ok(Object.values(value.safety).every(item=>item===false));
});
