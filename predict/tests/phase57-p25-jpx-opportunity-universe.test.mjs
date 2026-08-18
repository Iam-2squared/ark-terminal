import assert from 'node:assert/strict';
import test from 'node:test';
import {selectJpxOpportunityUniverse,PHASE57_P25_SAFETY} from '../daytrade/phase57-p25-jpx-opportunity-universe.js';

function row(symbol,{sector='A',price=1000,volume=100000,volumeRatio=1,change=0,atr=2,discovery=50,technical=50,confidence=50,quality=80,scannedAt='2026-08-18T00:00:00.000Z',status='analyzed'}={}){
  return {symbol,sector,market:'プライム',currentPrice:price,volume,volumeRatio,dailyChangePercent:change,atrPercent:atr,discoveryScore:discovery,technicalScore:technical,confidence,qualityScore:quality,scannedAt,status};
}

test('day head prioritizes liquid active names without directional outcome labels',()=>{
  const entries=[
    row('1001.T',{volume:500000,volumeRatio:3.2,change:-5.0,atr:4.0,discovery:35,technical:35}),
    row('1002.T',{volume:120000,volumeRatio:1.3,change:1.0,atr:2.0,discovery:75,technical:75}),
    row('1003.T',{volume:80000,volumeRatio:0.9,change:0.2,atr:1.2,discovery:55,technical:55}),
  ];
  const result=selectJpxOpportunityUniverse({entries,dayCount:1,swingCount:1,maxCombinedCount:2,maxPerSector:3});
  assert.equal(result.day[0].symbol,'1001.T');
  assert.equal(result.day[0].absoluteChangePct,5);
  assert.equal(result.methodology.directionAgnosticOpportunityStrength,true);
});

test('swing head prioritizes persistent technical conviction and confidence',()=>{
  const entries=[
    row('2001.T',{discovery:92,technical:88,confidence:86,quality:95,volumeRatio:1.8,volume:250000}),
    row('2002.T',{discovery:55,technical:57,confidence:52,quality:80,volumeRatio:4.0,volume:900000,change:7,atr:6}),
    row('2003.T',{discovery:48,technical:49,confidence:50,quality:80,volumeRatio:1.0,volume:100000}),
  ];
  const result=selectJpxOpportunityUniverse({entries,dayCount:1,swingCount:1,maxCombinedCount:2,maxPerSector:3});
  assert.equal(result.swing[0].symbol,'2001.T');
});

test('sector cap prevents one sector from occupying the full research universe',()=>{
  const entries=[
    row('3001.T',{sector:'Tech',volume:900000,volumeRatio:5,change:6,atr:5,discovery:90,technical:90}),
    row('3002.T',{sector:'Tech',volume:800000,volumeRatio:4,change:5,atr:4,discovery:85,technical:85}),
    row('3003.T',{sector:'Tech',volume:700000,volumeRatio:3,change:4,atr:3,discovery:80,technical:80}),
    row('3004.T',{sector:'Bank',volume:400000,volumeRatio:2,change:2,atr:2,discovery:75,technical:75}),
  ];
  const result=selectJpxOpportunityUniverse({entries,dayCount:3,swingCount:3,maxCombinedCount:4,maxPerSector:2});
  assert.ok(result.day.filter(x=>x.sector==='Tech').length<=2);
  assert.ok(result.swing.filter(x=>x.sector==='Tech').length<=2);
});

test('point-in-time guard rejects future and stale screener rows',()=>{
  const entries=[
    row('4001.T',{scannedAt:'2026-08-18T01:00:00.000Z'}),
    row('4002.T',{scannedAt:'2026-08-18T03:00:01.000Z'}),
    row('4003.T',{scannedAt:'2026-08-17T00:00:00.000Z'}),
  ];
  const result=selectJpxOpportunityUniverse({entries,dayCount:3,swingCount:3,maxCombinedCount:3,maxPerSector:3,asOf:'2026-08-18T03:00:00.000Z',maxAgeMs:6*60*60*1000});
  assert.deepEqual(result.combined.map(x=>x.symbol),['4001.T']);
  assert.equal(result.methodology.pointInTimeFreshnessGuard,true);
});

test('future outcomes and trade results cannot change selection',()=>{
  const base=[
    row('5001.T',{sector:'A',volume:500000,volumeRatio:3,change:4,discovery:80,technical:75}),
    row('5002.T',{sector:'B',volume:300000,volumeRatio:2,change:2,discovery:70,technical:65}),
    row('5003.T',{sector:'C',volume:100000,volumeRatio:1,change:1,discovery:60,technical:55}),
  ];
  const poisoned=base.map((x,i)=>({...x,futureReturnPct:i===2?999:-999,tradeWin:i===2,outerOosProfitFactor:i===2?99:0}));
  const a=selectJpxOpportunityUniverse({entries:base,dayCount:2,swingCount:2,maxCombinedCount:3,maxPerSector:2});
  const b=selectJpxOpportunityUniverse({entries:poisoned,dayCount:2,swingCount:2,maxCombinedCount:3,maxPerSector:2});
  assert.deepEqual(a.day,b.day);
  assert.deepEqual(a.swing,b.swing);
  assert.deepEqual(a.combined,b.combined);
  assert.equal(a.methodology.usesFutureOutcome,false);
  assert.equal(a.methodology.usesTradeResult,false);
  assert.equal(a.methodology.usesOuterOosPerformance,false);
});

test('all execution and promotion surfaces remain disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE57_P25_SAFETY[key],false,key);
  }
});
