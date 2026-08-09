import test from 'node:test';
import assert from 'node:assert/strict';
import { enrichHistoricalIntradayBars, attachMultiFactorFeatures, PHASE57_P20_SAFETY } from './phase57-intraday-multifactor.js';

const bars=Array.from({length:40},(_,i)=>({timestamp:new Date(Date.UTC(2026,0,5,0,i*5)).toISOString(),open:100+i*0.05,high:100.3+i*0.05,low:99.8+i*0.05,close:100.1+i*0.05,volume:1000+i*25}));

test('enrichment uses only bars through current index',()=>{
  const first=enrichHistoricalIntradayBars(bars.slice(0,20));
  const second=enrichHistoricalIntradayBars(bars.slice(0,40));
  assert.deepEqual(first[19].multiFactor,second[19].multiFactor);
});

test('attaches technical/time factors without changing labels',()=>{
  const enriched=enrichHistoricalIntradayBars(bars);
  const row={featureCutoff:bars[25].timestamp,outcomeAt:bars[26].timestamp,label:1,features:{returnFromOpen:0.1}};
  const out=attachMultiFactorFeatures([row],enriched)[0];
  assert.equal(out.label,1);
  assert.ok(Number.isFinite(out.features.rsi14));
  assert.ok(Number.isFinite(out.features.vwapDistancePct));
  assert.ok(Number.isFinite(out.features.atrPct));
});

test('P20 safety remains research-only',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(PHASE57_P20_SAFETY[key],false);
});
