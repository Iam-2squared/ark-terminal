import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildP252ProspectivePreopenUniverseRecord,
  PHASE57_P25_2C_POLICY,
  PHASE57_P25_2C_SAFETY,
} from '../daytrade/phase57-p25-2c-prospective-preopen-universe-capture.js';

function row(i,scannedAt){
  return {
    symbol:`${1000+i}.T`,
    sector:`S${i%40}`,
    market:i%3===0?'プライム':i%3===1?'スタンダード':'グロース',
    currentPrice:500+(i%700),
    volume:10000+i*25,
    volumeRatio:0.8+(i%30)/10,
    dailyChangePercent:(i%21)-10,
    atrPercent:1+(i%13)/10,
    discoveryScore:20+(i%76),
    technicalScore:25+(i%71),
    confidence:50+(i%50),
    qualityScore:60+(i%41),
    scannedAt,
    status:'analyzed',
  };
}

function snapshot({generatedAt='2026-08-18T23:15:00.000Z',scannedAt=generatedAt,cycleComplete=true,count=3100}={}){
  return {
    meta:{generatedAt,refreshProgress:{cycleComplete}},
    entries:Array.from({length:count},(_,i)=>row(i,scannedAt)),
  };
}

test('freezes one prospective pre-open JPX universe only after a completed fresh cycle',()=>{
  const result=buildP252ProspectivePreopenUniverseRecord({snapshot:snapshot({})});
  assert.equal(result.ready,true);
  assert.equal(result.status,'PROSPECTIVE_PREOPEN_UNIVERSE_FROZEN');
  assert.equal(result.sessionDate,'2026-08-19');
  assert.equal(result.captureHmJst,'08:15');
  assert.equal(result.variants.DYNAMIC_30.length,30);
  assert.equal(result.variants.DYNAMIC_40.length,40);
  assert.equal(result.variants.DYNAMIC_50.length,50);
  assert.deepEqual(result.variants.DYNAMIC_30,result.variants.DYNAMIC_40.slice(0,30));
  assert.deepEqual(result.variants.DYNAMIC_40,result.variants.DYNAMIC_50.slice(0,40));
  assert.ok(result.eligibleCount>=PHASE57_P25_2C_POLICY.minimumEligibleCrossSection);
});

test('fails closed when the dedicated overnight screener cycle is incomplete',()=>{
  const result=buildP252ProspectivePreopenUniverseRecord({snapshot:snapshot({cycleComplete:false})});
  assert.equal(result.ready,false);
  assert.equal(result.reason,'SCREENER_CYCLE_INCOMPLETE');
});

test('fails closed when capture completes after the frozen pre-open cutoff',()=>{
  const result=buildP252ProspectivePreopenUniverseRecord({snapshot:snapshot({generatedAt:'2026-08-19T00:00:00.000Z',scannedAt:'2026-08-19T00:00:00.000Z'})});
  assert.equal(result.ready,false);
  assert.equal(result.reason,'CAPTURE_AFTER_PREOPEN_CUTOFF');
});

test('fails closed when a completed snapshot is too stale to represent the current session',()=>{
  const result=buildP252ProspectivePreopenUniverseRecord({snapshot:snapshot({scannedAt:'2026-08-18T08:00:00.000Z'})});
  assert.equal(result.ready,false);
  assert.equal(result.reason,'PIT_INSUFFICIENT_POINT_IN_TIME_CROSS_SECTION');
  assert.equal(result.detail.eligibleCount,0);
});

test('all broker, execution, paper/live, promotion and holdout surfaces stay disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE57_P25_2C_SAFETY[key],false,key);
  }
});
