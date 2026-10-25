import test from 'node:test';
import assert from 'node:assert/strict';
import {featureAudit,futureLabelAudit,auditEntryFeasibilityEvent} from '../long-only/phase57-long-only-entry-preimplementation-feasibility.js';

const sessionDate='2024-09-17';
const at=hhmm=>`${sessionDate}T${hhmm}:00+09:00`;
const bar=(hhmm,close=100,volume=100)=>({timestamp:at(hhmm),availableAt:new Date(Date.parse(at(hhmm))+300000).toISOString(),
  open:close,high:close+1,low:close-1,close,volume});
const morning=['09:00','09:05','09:10','09:15','09:20','09:25'].map((time,index)=>bar(time,100+index));

test('09:30 keeps exact canonical Momentum3, pullback6 and relativeVolume5 intrinsically scoreable',()=>{
  const result=featureAudit({bars:morning,decisionTimestamp:at('09:30'),sessionDate,rank:1,firstSelectionTimestamp:at('09:30'),priorSelectionCount:0});
  assert.equal(result.directionalMomentum3Pct.status,'AVAILABLE');
  assert.ok(Math.abs(result.directionalMomentum3Pct.value-100*(105/102-1))<1e-12);
  assert.equal(result.directionalPullback6Pct.status,'AVAILABLE');
  assert.equal(result.relativeVolume5.status,'AVAILABLE');
  assert.equal(result.directionalMomentumAccelerationPct.status,'BLOCKED_BY_HISTORY');
  assert.equal(result.directionalReturnFromOpenPct.status,'AVAILABLE');
  assert.equal(result.directionalVwapDistancePct.status,'AVAILABLE');
});

test('feature prerequisites fail closed without filling missing session or grid bars',()=>{
  const noOpen=morning.slice(1),gridGap=morning.filter(row=>!row.timestamp.includes('09:15'));
  assert.equal(featureAudit({bars:noOpen,decisionTimestamp:at('09:30'),sessionDate,rank:1,firstSelectionTimestamp:at('09:30'),priorSelectionCount:0}).directionalReturnFromOpenPct.status,'BLOCKED_BY_SESSION_OPEN');
  assert.equal(featureAudit({bars:gridGap,decisionTimestamp:at('09:30'),sessionDate,rank:1,firstSelectionTimestamp:at('09:30'),priorSelectionCount:0}).directionalMomentum3Pct.status,'BLOCKED_BY_GRID');
});

test('strict wall-clock ordinal label uses six future bars and separates HIGH from CLOSE',()=>{
  const future=['10:00','10:05','10:10','10:15','10:20','10:25'].map((time,index)=>{
    const row=bar(time,100+index/10);row.high=index===2?103.2:101;return row;
  });
  const result=futureLabelAudit({bars:future,minutes:[],auctions:[{minute:900}],decisionTimestamp:at('10:00'),sessionDate,decisionPrice:100});
  assert.equal(result.labelable,true);assert.equal(result.ordinalClass,3);assert.equal(result.closeOrdinalClass,0);
});

test('lunch and session end are unavailable rather than converted to market minutes',()=>{
  assert.equal(futureLabelAudit({bars:[],minutes:[],auctions:[{minute:900}],decisionTimestamp:at('11:30'),sessionDate,decisionPrice:100}).reason,'LUNCH_BREAK');
  assert.equal(futureLabelAudit({bars:[],minutes:[],auctions:[{minute:900}],decisionTimestamp:at('15:00'),sessionDate,decisionPrice:100}).reason,'SESSION_END');
});

test('complete event audit remains LONG-only and does not score a model',()=>{
  const future=['10:00','10:05','10:10','10:15','10:20','10:25'].map(time=>bar(time));
  const result=auditEntryFeasibilityEvent({event:{selectorEventId:'e',sessionDate,symbol:'7203',decisionTimestamp:at('10:00'),decisionPrice:100,
    decisionPriceAgeMinutes:0,decisionPriceSource:'LATEST_ACCEPTED_MINUTE_CLOSE',ridgeRank:1,ridgeScore:2,direction:'LONG'},
    bars:[...morning,...future],minutes:[],auctions:[{minute:900}],firstSelectionTimestamp:at('10:00'),priorSelectionCount:0});
  assert.equal(result.direction,'LONG');assert.equal(result.shortScoreEvaluated,false);assert.equal('probability' in result,false);
});
