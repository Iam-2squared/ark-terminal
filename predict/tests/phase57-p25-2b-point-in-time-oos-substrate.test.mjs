import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildP252PointInTimeUniverseAtDecision,
  buildP252PointInTimeUniverseTimeline,
  PHASE57_P25_2B_POLICY,
  PHASE57_P25_2B_SAFETY,
} from '../daytrade/phase57-p25-2b-point-in-time-oos-substrate.js';

function entry(i,{scannedAt='2026-08-18T00:00:00.000Z'}={}){
  const sector=`S${i%20}`;
  return {
    symbol:`${String(1000+i).padStart(4,'0')}.T`,
    sector,
    market:i%3===0?'グロース':i%3===1?'スタンダード':'プライム',
    currentPrice:500+(i%300),
    volume:10000+i*100,
    volumeRatio:0.8+(i%25)/10,
    dailyChangePercent:(i%17)-8,
    atrPercent:1+(i%11)/10,
    discoveryScore:20+(i%75),
    technicalScore:25+(i%70),
    confidence:50+(i%50),
    qualityScore:60+(i%41),
    scannedAt,
    status:'analyzed',
  };
}

function snapshot(generatedAt,count=120){
  return {meta:{generatedAt},entries:Array.from({length:count},(_,i)=>entry(i,{scannedAt:generatedAt}))};
}

test('uses only the latest snapshot available at or before the frozen decision',()=>{
  const before=snapshot('2026-08-18T01:00:00.000Z');
  const future=snapshot('2026-08-18T01:10:00.000Z');
  future.entries=future.entries.map((row,i)=>({...row,volume:i===0?999999999:row.volume}));
  const result=buildP252PointInTimeUniverseAtDecision({
    sessionDate:'2026-08-18',
    decisionTimestamp:'2026-08-18T01:05:00.000Z',
    snapshots:[future,before],
    minimumEligibleCrossSection:50,
  });
  assert.equal(result.ready,true);
  assert.equal(result.sourceSnapshotGeneratedAt,'2026-08-18T01:00:00.000Z');
  assert.equal(result.methodology.laterSnapshotBackfill,false);
});

test('fails closed when only future snapshots exist',()=>{
  const result=buildP252PointInTimeUniverseAtDecision({
    sessionDate:'2026-08-18',
    decisionTimestamp:'2026-08-18T01:05:00.000Z',
    snapshots:[snapshot('2026-08-18T01:06:00.000Z')],
    minimumEligibleCrossSection:50,
  });
  assert.equal(result.ready,false);
  assert.equal(result.reason,'NO_SNAPSHOT_AT_OR_BEFORE_DECISION');
});

test('blocks stale or thin point-in-time cross-sections instead of backfilling later data',()=>{
  const old=snapshot('2026-08-18T00:00:00.000Z',80);
  const result=buildP252PointInTimeUniverseAtDecision({
    sessionDate:'2026-08-18',
    decisionTimestamp:'2026-08-18T02:00:00.000Z',
    snapshots:[old],
    minimumEligibleCrossSection:70,
    maxRowAgeMs:30*60*1000,
  });
  assert.equal(result.ready,false);
  assert.equal(result.reason,'INSUFFICIENT_POINT_IN_TIME_CROSS_SECTION');
  assert.equal(result.eligibleCount,0);
});

test('dynamic 30, 40 and 50 are nested prefixes of one frozen cross-sectional rank',()=>{
  const result=buildP252PointInTimeUniverseAtDecision({
    sessionDate:'2026-08-18',
    decisionTimestamp:'2026-08-18T01:05:00.000Z',
    snapshots:[snapshot('2026-08-18T01:00:00.000Z',120)],
    minimumEligibleCrossSection:50,
    maxRowAgeMs:10*60*1000,
  });
  assert.equal(result.ready,true);
  assert.equal(result.variants.DYNAMIC_30.length,30);
  assert.equal(result.variants.DYNAMIC_40.length,40);
  assert.equal(result.variants.DYNAMIC_50.length,50);
  assert.deepEqual(result.variants.DYNAMIC_30,result.variants.DYNAMIC_40.slice(0,30));
  assert.deepEqual(result.variants.DYNAMIC_40,result.variants.DYNAMIC_50.slice(0,40));
  const sectors=result.rankAudit.day50.reduce((map,row)=>map.set(row.sector,(map.get(row.sector)??0)+1),new Map());
  assert.ok(Math.max(...sectors.values())<=PHASE57_P25_2B_POLICY.maxPerSector);
});

test('future outcomes and outer-OOS fields cannot affect rank or safe fingerprint',()=>{
  const base=snapshot('2026-08-18T01:00:00.000Z',120);
  const poisoned={meta:{...base.meta},entries:base.entries.map((row,i)=>({
    ...row,
    futureReturnPct:i===119?9999:-9999,
    realizedPnl:i===119?1e9:-1e9,
    tradeWin:i===119,
    outerOosProfitFactor:i===119?99:0,
  }))};
  const args={sessionDate:'2026-08-18',decisionTimestamp:'2026-08-18T01:05:00.000Z',minimumEligibleCrossSection:50,maxRowAgeMs:10*60*1000};
  const a=buildP252PointInTimeUniverseAtDecision({...args,snapshots:[base]});
  const b=buildP252PointInTimeUniverseAtDecision({...args,snapshots:[poisoned]});
  assert.equal(a.sourceSnapshotFingerprint,b.sourceSnapshotFingerprint);
  assert.deepEqual(a.variants.DYNAMIC_30,b.variants.DYNAMIC_30);
  assert.deepEqual(a.variants.DYNAMIC_40,b.variants.DYNAMIC_40);
  assert.deepEqual(a.variants.DYNAMIC_50,b.variants.DYNAMIC_50);
  assert.equal(a.methodology.usesFutureOutcome,false);
  assert.equal(a.methodology.usesOuterOosPerformance,false);
});

test('duplicate symbols in one snapshot block the decision',()=>{
  const s=snapshot('2026-08-18T01:00:00.000Z',120);
  s.entries.push({...s.entries[0],volume:s.entries[0].volume+1});
  const result=buildP252PointInTimeUniverseAtDecision({
    sessionDate:'2026-08-18',decisionTimestamp:'2026-08-18T01:05:00.000Z',snapshots:[s],minimumEligibleCrossSection:50,
  });
  assert.equal(result.ready,false);
  assert.equal(result.reason,'DUPLICATE_SYMBOL_ROWS');
});

test('conflicting snapshots at an identical generatedAt are rejected',()=>{
  const a=snapshot('2026-08-18T01:00:00.000Z',120);
  const b=snapshot('2026-08-18T01:00:00.000Z',120);
  b.entries[0]={...b.entries[0],volume:b.entries[0].volume+123};
  const result=buildP252PointInTimeUniverseAtDecision({
    sessionDate:'2026-08-18',decisionTimestamp:'2026-08-18T01:05:00.000Z',snapshots:[a,b],minimumEligibleCrossSection:50,
  });
  assert.equal(result.ready,false);
  assert.equal(result.reason,'CONFLICTING_SNAPSHOTS_AT_SAME_TIMESTAMP');
});

test('timeline preserves blocked decisions instead of silently deleting bad coverage',()=>{
  const timeline=buildP252PointInTimeUniverseTimeline({
    decisionPoints:[
      {sessionDate:'2026-08-18',decisionTimestamp:'2026-08-18T01:05:00.000Z'},
      {sessionDate:'2026-08-18',decisionTimestamp:'2026-08-18T02:05:00.000Z'},
    ],
    snapshots:[snapshot('2026-08-18T01:00:00.000Z',120)],
    minimumEligibleCrossSection:50,
    maxSnapshotAgeMs:30*60*1000,
  });
  assert.equal(timeline.decisionCount,2);
  assert.equal(timeline.readyCount,1);
  assert.equal(timeline.blockedCount,1);
  assert.equal(timeline.timeline[1].reason,'SNAPSHOT_TOO_OLD');
  assert.equal(timeline.methodology.blockedDecisionsPreserved,true);
});

test('all execution, write, paper/live, promotion and holdout surfaces remain disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE57_P25_2B_SAFETY[key],false,key);
  }
});
