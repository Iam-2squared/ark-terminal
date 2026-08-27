import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {buildReadinessMeasurement,SAFETY} from '../../scripts/measure_p25_intraday_dynamic_universe_readiness.mjs';

function withCapture(session){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ark-intraday-readiness-'));
  fs.writeFileSync(path.join(dir,'capture.json'),JSON.stringify({sessions:[session]}));
  return dir;
}

test('bounded frozen capture blocks market-wide performance claims',()=>{
  const dir=withCapture({
    sessionDate:'2026-08-25',
    sessionBarsBySymbol:{'1001.T':[1,2,3],'1002.T':[1,2]},
    universeRecord:{sessionDate:'2026-08-25'},
  });
  const x=buildReadinessMeasurement({capturesDir:dir});
  assert.equal(x.status,'BLOCKED_MARKET_WIDE_POINT_IN_TIME_DATA_MISSING');
  assert.equal(x.summary.maxCapturedSymbols,2);
  assert.equal(x.summary.totalMarketWideSnapshots,0);
  assert.equal(x.summary.performanceMeasurementAllowed,false);
  assert.equal(x.interpretation.marketWide5mPerformanceComparable,false);
  assert.equal(x.interpretation.winnerSelectionAllowed,false);
});

test('point-in-time market-wide snapshots unlock causal measurement readiness only',()=>{
  const entries=Array.from({length:5},(_,i)=>({symbol:`${1000+i}.T`,currentPrice:1000,volume:1000,scannedAt:'2026-08-25T00:05:00.000Z'}));
  const dir=withCapture({
    sessionDate:'2026-08-25',
    sessionBarsBySymbol:{'1001.T':[1,2]},
    marketWideSnapshots:[{asOf:'2026-08-25T00:05:00.000Z',entries}],
  });
  const x=buildReadinessMeasurement({capturesDir:dir});
  assert.equal(x.status,'READY_FOR_MARKET_WIDE_INTRADAY_MEASUREMENT');
  assert.equal(x.summary.performanceMeasurementAllowed,true);
  assert.equal(x.interpretation.formalOos,false);
  assert.equal(x.interpretation.promotionEligible,false);
});

test('all execution surfaces remain disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(SAFETY[key],false,key);
  }
});
