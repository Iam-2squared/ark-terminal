import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const file='research/no12-prebuy-causal-runtime-20261011/NO11_2026_RSS_PRICE_ONLY_OBSERVED_AGGREGATE_20261014.json';
const d=JSON.parse(fs.readFileSync(file,'utf8'));
const total=(rows,key)=>rows.reduce((n,r)=>n+r[key],0);

test('RSS 2026 physical price-only 8 session x 10 clock aggregate',()=>{
  assert.equal(d.byClock.length,10);
  assert.equal(d.byDay.length,8);
  assert.equal(d.independentInputFileSha256,'380616e9c2d05eb481b5ed160e35b92365822d770e23f9ed80d7295ac883c5e4');
  const expected={
    anchors:d.summary.anchors,
    fullFutureObserved:d.summary.fullyObservedFutureWindow,
    up2Observed:d.summary.up2.observed,
    up3Observed:d.summary.up3.observed,
    up5Observed:d.summary.up5.observed,
    down2Observed:d.summary.down2.observed,
    down3Observed:d.summary.down3.observed,
    down5Observed:d.summary.down5.observed
  };
  for(const [key,n] of Object.entries(expected)){
    assert.equal(total(d.byDay,key),n,key);
    assert.equal(total(d.byClock,key),n,key);
  }
  assert.equal(d.summary.anchors,59712);
  assert.equal(d.summary.fullyObservedFutureWindow,17251);
});

test('Never turn unknown post-decision future into known negative labels',()=>{
  const n=d.summary.anchors;
  for(const side of ['up','down']){
    let prevHits=Infinity,prevUnknown=0;
    for(const level of [2,3,5]){
      const row=d.summary[side+level];
      assert.equal(row.observed+row.confirmedNoTouchInProxy+row.unknown,n);
      assert.ok(row.observed<=prevHits);
      assert.ok(row.unknown>=prevUnknown);
      assert.ok(row.unknown<=n-d.summary.fullyObservedFutureWindow);
      prevHits=row.observed;prevUnknown=row.unknown;
    }
  }
  for(const field of ['productionReady','orderTransmission','comparisonWithFrozenSelector','firstEntryExecuted','state9Executed','h235PredictionExecuted','frozenOriginalChanged','mainMerge'])
    assert.equal(d.flags[field],false,field);
  assert.equal(d.flags.new2026SupervisedTrainingExamples,0);
});
