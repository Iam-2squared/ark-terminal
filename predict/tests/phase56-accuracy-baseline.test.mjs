import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateChartAccuracy, PHASE56_BASELINE_SAFETY } from '../chart/phase56-accuracy-baseline.js';

function trendBars(n=180){
  return Array.from({length:n},(_,i)=>{
    const base=100+i*0.35+Math.sin(i/3)*0.4;
    return {time:i,open:base-0.2,high:base+0.8,low:base-0.8,close:base,volume:1000+i*5,vwap:base-0.1};
  });
}

test('produces horizon metrics from chart signals',()=>{
  const r=evaluateChartAccuracy({candles:trendBars(),lookback:40,horizons:[1,3,5],minimumSignals:5});
  assert.ok(['BASELINE_READY','INSUFFICIENT_SIGNALS'].includes(r.status));
  assert.equal(r.byHorizon.length,3);
  assert.equal(r.executionAllowed,false);
  assert.equal(r.recommendationAllowed,false);
});

test('fails closed with too little data',()=>{
  const r=evaluateChartAccuracy({candles:trendBars(30),lookback:40,minimumSignals:5});
  assert.equal(r.status,'INSUFFICIENT_SIGNALS');
});

test('baseline safety stays read only',()=>{
  assert.equal(PHASE56_BASELINE_SAFETY.brokerWriteAllowed,false);
  assert.equal(PHASE56_BASELINE_SAFETY.rssOrderFunctionAllowed,false);
  assert.equal(PHASE56_BASELINE_SAFETY.liveTradingAllowed,false);
});
