import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTechnicalFusionFeatures } from '../chart/phase56-technical-fusion.js';

const indicators={
  currentPrice:120,
  movingAverages:{ma5:115,ma25:110,ma75:100,ma200:90,previousMa5:114,previousMa25:109},
  rsi:61,
  macd:{value:2,signal:1,histogram:1},
  adx:{value:31,plusDi:28,minusDi:14},
  atr:{percent:3.2},
  vwap:112,
  bollingerBands:{upper:125,middle:110,lower:95,percentB:.83},
  stochastic:{k:67,d:58},
  volume:{ratio:1.8},
  priceChangePercent:2.1,
};

test('P3 builds interaction-ready technical features from existing indicator schema',()=>{
  const r=buildTechnicalFusionFeatures({indicators,asOfSessionDate:'2026-08-08'});
  assert.equal(r.status,'TECHNICAL_FEATURES_READY');
  assert.equal(r.features.maStack,'BULL_STACK');
  assert.equal(r.interactions.trendVolume,'BULL_TREND_VOLUME_CONFIRM');
  assert.equal(r.interactions.vwapMomentum,'ABOVE_VWAP_POSITIVE_MACD');
  assert.equal(r.interactions.trendStrength,'UP_STRONG');
  assert.equal(r.reviewOnly,true);
});

test('P3 remains safe with partial indicator data',()=>{
  const r=buildTechnicalFusionFeatures({indicators:{currentPrice:100,rsi:50}});
  assert.equal(r.status,'PARTIAL_TECHNICAL_FEATURES');
  assert.equal(r.features.maStack,'UNKNOWN');
  assert.equal(r.interactions.trendVolume,'NONE');
});

test('P3 cannot write or promote',()=>{
  const r=buildTechnicalFusionFeatures({indicators});
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(r[key],false,key);
  assert.equal(r.safety.paperTradingAllowed,false);
  assert.equal(r.transmitted,false);
  assert.equal(r.humanApprovalRequired,true);
});
