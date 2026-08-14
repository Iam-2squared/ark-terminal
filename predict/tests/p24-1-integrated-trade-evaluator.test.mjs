import test from 'node:test';
import assert from 'node:assert/strict';
import {P24_1_SAFETY,evaluateIntegratedTradeResearch} from '../daytrade/phase57-p24-integrated-trade-evaluator.js';

const bar=(timestamp,open,high,low,close,volume=1000)=>({timestamp,open,high,low,close,volume});
const context=[
  bar('2026-08-10T00:00:00.000Z',100,100.4,99.8,100.2),
  bar('2026-08-10T00:05:00.000Z',100.2,100.8,100.1,100.7),
  bar('2026-08-10T00:10:00.000Z',100.7,101.3,100.6,101.2),
  bar('2026-08-10T00:15:00.000Z',101.2,101.9,101.1,101.8),
];

test('P24.1 remains fail-closed',()=>{
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'])assert.equal(P24_1_SAFETY[k],false,k);
  assert.equal(P24_1_SAFETY.freshHoldoutConsumed,false);
});

test('P24.1 evaluates accepted entries only and returns portfolio metrics',()=>{
  const rows=[
    {entryAccepted:true,entryBand:'Q4_HIGH',symbol:'TEST.T',sessionDate:'2026-08-10',signalDirection:'LONG',entryPrice:101.8,contextBars:context,futureBars:[
      bar('2026-08-10T00:20:00.000Z',101.8,102.4,101.6,102.2),
      bar('2026-08-10T00:25:00.000Z',102.2,102.8,102.0,102.6),
      bar('2026-08-10T00:30:00.000Z',102.6,102.9,102.2,102.5),
    ]},
    {entryAccepted:false,entryBand:'Q3',symbol:'SKIP.T',sessionDate:'2026-08-10',signalDirection:'LONG',entryPrice:100,contextBars:context,futureBars:[bar('2026-08-10T00:20:00.000Z',100,101,99,100.5)]},
  ];
  const r=evaluateIntegratedTradeResearch(rows,{tradeManagement:{roundTripCostPct:0.05}});
  assert.equal(r.summary.acceptedEntryCount,1);
  assert.equal(r.summary.n,1);
  assert.equal(r.summary.coverage,1);
  assert.equal(r.outcomes[0].entryBand,'Q4_HIGH');
  assert.ok(Number.isFinite(r.summary.netReturnPct));
  assert.ok(Number.isFinite(r.summary.maxDrawdownPct));
  assert.equal(r.freshHoldoutConsumed,false);
});
