import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildSwingS1ProspectiveUniverseRecord,
  PHASE56_SWING_S1_POLICY,
  PHASE56_SWING_S1_SAFETY,
} from '../swing/phase56-s1-jpx-prospective-universe.js';

function entries({count=3100,scannedAt='2026-08-18T22:00:00.000Z'}={}){
  return Array.from({length:count},(_,index)=>({
    symbol:`${1000+index}.T`,
    sector:`SECTOR_${index%100}`,
    market:index%3===0?'Prime':index%3===1?'Standard':'Growth',
    status:'analyzed',
    currentPrice:100+(index%500),
    volume:100000+(index*137)%900000,
    volumeRatio:0.5+(index%40)/10,
    dailyChangePercent:((index%21)-10)/2,
    atrPercent:1+(index%30)/10,
    discoveryScore:(index*17)%101,
    technicalScore:(index*29)%101,
    confidence:0.5+(index%50)/100,
    qualityScore:(index*13)%100,
    scannedAt,
  }));
}
function snapshot(overrides={}){
  return {
    meta:{
      generatedAt:'2026-08-18T23:15:00.000Z',
      refreshProgress:{cycleComplete:true},
      ...(overrides.meta??{}),
    },
    entries:overrides.entries??entries(),
  };
}

test('freezes nested Swing Dynamic30/40/50 from one pre-open point-in-time rank',()=>{
  const record=buildSwingS1ProspectiveUniverseRecord({snapshot:snapshot()});
  assert.equal(record.ready,true);
  assert.equal(record.sessionDate,'2026-08-19');
  assert.equal(record.variants.SWING_FIXED_5.length,5);
  assert.equal(record.variants.SWING_OLD_FIXED_30.length,30);
  assert.equal(record.variants.SWING_DYNAMIC_30.length,30);
  assert.equal(record.variants.SWING_DYNAMIC_40.length,40);
  assert.equal(record.variants.SWING_DYNAMIC_50.length,50);
  assert.deepEqual(record.variants.SWING_DYNAMIC_30,record.variants.SWING_DYNAMIC_40.slice(0,30));
  assert.deepEqual(record.variants.SWING_DYNAMIC_40,record.variants.SWING_DYNAMIC_50.slice(0,40));
  assert.equal(record.methodology.currentOuterOosDoesNotSelectUniverseSize,true);
  assert.equal(record.methodology.currentOuterOosDoesNotSelectHorizon,true);
  assert.equal(record.methodology.directionAgnosticOpportunityStrength,true);
});

test('Swing rank obeys the predeclared sector cap',()=>{
  const record=buildSwingS1ProspectiveUniverseRecord({snapshot:snapshot()});
  const counts=new Map();
  for(const row of record.rankAudit.swing50)counts.set(row.sector,(counts.get(row.sector)??0)+1);
  assert.ok([...counts.values()].every(n=>n<=PHASE56_SWING_S1_POLICY.maxPerSector));
});

test('future outcome poison fields cannot alter the frozen rank or source fingerprint',()=>{
  const baseEntries=entries();
  const poisoned=baseEntries.map((row,index)=>({...row,futureReturnPct:index%2?999:-999,outerOosScore:100000-index,winnerVariant:'POISON'}));
  const first=buildSwingS1ProspectiveUniverseRecord({snapshot:snapshot({entries:baseEntries})});
  const second=buildSwingS1ProspectiveUniverseRecord({snapshot:snapshot({entries:poisoned})});
  assert.equal(first.sourceSnapshotFingerprint,second.sourceSnapshotFingerprint);
  assert.deepEqual(first.variants,second.variants);
});

test('incomplete, stale, after-cutoff and duplicate snapshots fail closed',()=>{
  const incomplete=buildSwingS1ProspectiveUniverseRecord({snapshot:snapshot({meta:{refreshProgress:{cycleComplete:false}}})});
  assert.equal(incomplete.ready,false);
  assert.equal(incomplete.reason,'SCREENER_CYCLE_INCOMPLETE');

  const stale=buildSwingS1ProspectiveUniverseRecord({snapshot:snapshot({entries:entries({scannedAt:'2026-08-18T09:00:00.000Z'})})});
  assert.equal(stale.ready,false);
  assert.equal(stale.reason,'INSUFFICIENT_POINT_IN_TIME_CROSS_SECTION');

  const afterCutoff=buildSwingS1ProspectiveUniverseRecord({snapshot:snapshot({meta:{generatedAt:'2026-08-19T00:00:00.000Z',refreshProgress:{cycleComplete:true}}})});
  assert.equal(afterCutoff.ready,false);
  assert.equal(afterCutoff.reason,'CAPTURE_AFTER_PREOPEN_CUTOFF');

  const duplicateRows=entries();
  duplicateRows.push({...duplicateRows[0]});
  const duplicate=buildSwingS1ProspectiveUniverseRecord({snapshot:snapshot({entries:duplicateRows})});
  assert.equal(duplicate.ready,false);
  assert.equal(duplicate.reason,'DUPLICATE_SYMBOL_ROWS');
});

test('Swing S1 stays read-only and routine research needs no MARKETSPEED, board or Tick',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE56_SWING_S1_SAFETY[key],false,key);
  }
  assert.equal(PHASE56_SWING_S1_POLICY.dailyMarketSpeedRequired,false);
  assert.equal(PHASE56_SWING_S1_POLICY.boardOrTickUsed,false);
  assert.equal(PHASE56_SWING_S1_POLICY.microstructureUsed,false);
  assert.equal(PHASE56_SWING_S1_POLICY.currentOuterOosUniverseSizeSelectionAllowed,false);
  assert.equal(PHASE56_SWING_S1_POLICY.currentOuterOosHorizonSelectionAllowed,false);
});
