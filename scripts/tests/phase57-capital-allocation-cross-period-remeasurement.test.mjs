import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {verifyOld20Bar5Parity} from '../phase57-capital-allocation-cross-period-remeasurement.mjs';

const evidencePath='predict/research/phase57-capital-allocation-cross-period-evidence/cross-period-remeasurement-result.json';

test('committed cross-period evidence preserves labels, parity, roles, safety and exact attribution',()=>{
  const result=JSON.parse(fs.readFileSync(evidencePath,'utf8'));
  assert.equal(result.status,'HISTORICAL_REMEASUREMENT_COMPLETE');
  assert.equal(result.classification,'CROSS_PERIOD_ROBUSTNESS_DIAGNOSTIC');
  assert.match(result.evidenceRole,/NOT_OOS_NOT_VALIDATION/);
  assert.equal(result.aPlusBReferenceParity,'PASS');
  assert.equal(result.blocks.OLD20.role,'REPLAYABLE_EXPOSED_DIAGNOSTIC');
  assert.equal(result.blocks.OLD20.sessionCount,20);
  assert.equal(result.blocks.OLD20.eligibleCount,35);
  assert.equal(result.blocks.OLD20.firstEnterCount,36);
  assert.equal(result.blocks.OLD20.missingOutcomePathCount,1);
  assert.equal(result.blocks.OLD20.bar5Parity.status,'OLD20_DIRECT_BAR5_PATH_PARITY_PASS');
  assert.equal(result.blocks['A+B'].arms.MAX_5_V5.finalEquityJpy,1214425.715);
  assert.equal(result.blocks['A+B'].arms.MAX_5_V5.returnPct,21.442571);
  assert.equal(result.blocks['A+B'].arms.MAX_5_V5.accepted,49);
  for(const block of result.blockOrder){
    for(const arm of Object.values(result.blocks[block].arms)){
      assert.equal(arm.ledgerAudit.status,'LEDGER_INVARIANTS_PASS');
      assert.equal(arm.ledgerAudit.violationCount,0);
    }
    for(const comparison of ['MAX_10_TO_MAX_5','MAX_5_TO_MAX_3']){
      const a=result.blocks[block].attribution[comparison];
      assert.equal(a.recomposition.matchesTotal,true);
      assert.ok(Math.abs(a.totalDeltaJpy-a.recomposition.pnlJpy)<1e-6);
    }
  }
  assert.ok(Object.values(result.safety).every(x=>x===false));
  assert.equal(result.interpretation.oosClaim,false);
  assert.equal(result.interpretation.validationClaim,false);
  assert.equal(result.interpretation.max3Promoted,false);
});

test('direct Old20 bar5 reference covers non-adverse, reclaim, exact bar5 and fallback without future reads',()=>{
  const mk=({id,first,returns,v4Net=1})=>({
    eventId:id,causalEligible:true,direction:'LONG',entryPrice:100,
    entryQuality:{h1:first===null?null:{gross:first*100}},
    v4:{exitTimestamp:`2026-08-13T06:00:00.000Z`,exitPrice:101,netReturnPct:v4Net,exitReason:'SESSION_END'},
    management:{v4:returns.map((currentReturnPct,i)=>({baseScore:{state:{elapsedBars:i+1}},currentReturnPct,timestamp:`2026-08-13T0${i+1}:00:00.000Z`}))},
  });
  const trades=[
    mk({id:'non-adverse',first:.1,returns:[.1,-1,-1,-1,-1]}),
    mk({id:'reclaim',first:-.1,returns:[-.1,-.2,0,-.2,-.3]}),
    mk({id:'bar5',first:-.1,returns:[-.1,-.2,-.3,-.4,-.5]}),
    mk({id:'fallback',first:null,returns:[-.1,-.2,-.3]}),
  ];
  const closes=new Map([['2026-08-13T05:00:00.000Z',99.5]]);
  const parity=verifyOld20Bar5Parity(trades,(_symbol,timestamp)=>closes.get(timestamp));
  assert.equal(parity.status,'OLD20_DIRECT_BAR5_PATH_PARITY_PASS');
  assert.deepEqual(parity.stateCounts,{FIRST_BAR_NON_ADVERSE_V4:1,RECOVERED_TO_V4:1,DEFENSIVE_EXIT_BAR_5:1,HORIZON_FALLBACK_V4:1});
  assert.equal(parity.futureBarsAfterBar5Read,false);
  assert.equal(parity.costAppliedExactlyOnce,true);
});
