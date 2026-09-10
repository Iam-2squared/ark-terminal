import test from 'node:test';
import assert from 'node:assert/strict';
import {score,lastSevenCompletedCloses} from '../phase57-capital-allocation-v3-phase-a.mjs';

const keys=['directionalReturnFromOpenPct','directionalVwapDistancePct','directionalMomentum3Pct','directionalMomentumAccelerationPct','directionalPullback6Pct','relativeVolume5','minutesSinceFirstSelection','hybridReciprocalRank','priorSelectionCount','direction'];

test('phase A scorer uses frozen logistic normalization deterministically',()=>{
  const model={features:keys,weights:[1,0,0,0,0,0,0,0,0,0],means:Array(10).fill(0),scales:Array(10).fill(1),intercept:0};
  const features=Object.fromEntries(keys.map(k=>[k,0]));
  features.directionalReturnFromOpenPct=1;
  const p=score({features},model);
  assert.ok(Math.abs(p-0.7310585786300049)<1e-12);
});

test('risk extraction admits only bars available by decision time and takes exact last seven',()=>{
  const date='2026-09-01',symbol='1111.T',bars=[];
  for(let i=0;i<9;i++)bars.push({timestamp:`2026-09-01T00:${String(i*5).padStart(2,'0')}:00.000Z`,availableAt:`2026-09-01T00:${String((i+1)*5).padStart(2,'0')}:00.000Z`,close:100+i});
  const map=new Map([[date,new Map([[symbol,bars]])]]);
  const e={eventId:'x',sessionDate:date,symbol,decisionTimestamp:'2026-09-01T00:40:00.000Z'};
  assert.deepEqual(lastSevenCompletedCloses(map,e),[101,102,103,104,105,106,107]);
});
