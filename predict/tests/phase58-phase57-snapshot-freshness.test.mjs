import test from 'node:test';
import assert from 'node:assert/strict';
import {validateFrozenPhase57Snapshot} from '../scalping/phase58-phase57-snapshot-contract.js';

function snapshot(context={}){
  return {
    direction:1,
    confidence:.56,
    setup:'VOLATILITY',
    context,
    asOf:'2026-08-18T00:30:00.000Z',
    modelId:'phase57-p21-prospective-rf-h24',
    artifactSha256:'a'.repeat(64),
    frozen:true,
    futureOutcomeUsed:false,
    thresholdSearchAfterCapture:false,
    entryRetunedAfterCapture:false,
  };
}

test('completed 5m source-bar close is the freshness boundary, not its opening timestamp',()=>{
  const out=validateFrozenPhase57Snapshot(snapshot({
    sourceBarTimestamp:'2026-08-18T00:30:00.000Z',
    sourceBarDurationMinutes:5,
    sourceBarCloseAt:'2026-08-18T00:35:00.000Z',
  }),{captureAsOf:'2026-08-18T00:36:32.169Z',maxAgeMs:300000});
  assert.equal(out.complete,true);
  assert.equal(out.freshness.freshnessAsOf,'2026-08-18T00:35:00.000Z');
  assert.equal(out.freshness.sourceBarCloseMetadataUsed,true);
});

test('legacy snapshot without source-bar close metadata keeps strict asOf freshness behavior',()=>{
  const out=validateFrozenPhase57Snapshot(snapshot(),{
    captureAsOf:'2026-08-18T00:36:32.169Z',
    maxAgeMs:300000,
  });
  assert.equal(out.complete,false);
  assert.ok(out.blockers.includes('STALE_PHASE57_SNAPSHOT'));
});

test('source-bar close metadata fails closed when it does not equal asOf plus declared duration',()=>{
  const out=validateFrozenPhase57Snapshot(snapshot({
    sourceBarDurationMinutes:5,
    sourceBarCloseAt:'2026-08-18T00:36:00.000Z',
  }),{captureAsOf:'2026-08-18T00:36:32.169Z',maxAgeMs:300000});
  assert.equal(out.complete,false);
  assert.ok(out.blockers.includes('PHASE57_SOURCE_BAR_CLOSE_MISMATCH'));
});
