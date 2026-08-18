import assert from 'node:assert/strict';
import test from 'node:test';
import {
  summarizeP252TradeFrequencyVariant,
  PHASE57_P25_2_VARIANTS,
  PHASE57_P25_2_POLICY,
  PHASE57_P25_2_SAFETY,
} from '../daytrade/phase57-p25-2-trade-frequency-evaluator.js';

function trade({
  symbol='1001.T',sector='Tech',sessionDate='2026-08-03',entryTimestamp='2026-08-03T00:30:00.000Z',
  net=0.2,aligned=net,hit=true,timeBucket='09:00-09:59',regime='BULL',entryAccepted=true,
}={}){
  return {entryAccepted,symbol,sector,sessionDate,entryTimestamp,netReturnPct:net,alignedReturnPct:aligned,hit,timeBucket,regime};
}

test('P25.2 universe-size sensitivity set is fully precommitted and cannot use outer OOS to select N',()=>{
  assert.deepEqual(PHASE57_P25_2_VARIANTS.map(x=>x.id),['FIXED_5','OLD_FIXED_30','DYNAMIC_30','DYNAMIC_40','DYNAMIC_50']);
  assert.equal(PHASE57_P25_2_POLICY.entryThresholdRelaxationAllowed,false);
  assert.equal(PHASE57_P25_2_POLICY.outerOosUniverseSizeSelectionAllowed,false);
  assert.equal(PHASE57_P25_2_POLICY.postHocWinnerFilteringAllowed,false);
  assert.equal(PHASE57_P25_2_POLICY.currentOosThresholdSearchAllowed,false);
});

test('trade-frequency KPI reports observed sessions to the 400th valid frozen entry without threshold relaxation',()=>{
  const sessions=['2026-08-03','2026-08-04','2026-08-05','2026-08-06'];
  const rows=[];
  let id=0;
  for(const [sessionIndex,count] of [100,100,100,120].entries()){
    for(let i=0;i<count;i+=1){
      id+=1;
      rows.push(trade({
        symbol:`${1000+(id%50)}.T`,
        sector:`S${id%8}`,
        sessionDate:sessions[sessionIndex],
        entryTimestamp:`${sessions[sessionIndex]}T${String(1+Math.floor(i/60)).padStart(2,'0')}:${String(i%60).padStart(2,'0')}:00.000Z`,
        net:id%3===0?-0.1:0.2,
      }));
    }
  }
  const result=summarizeP252TradeFrequencyVariant({variant:'DYNAMIC_50',trades:rows,evaluatedSessions:sessions,eligibleDecisionCount:840});
  assert.equal(result.validFrozenEntries,420);
  assert.equal(result.tradeFrequency.observedDays,4);
  assert.equal(result.tradeFrequency.entriesPerTradingSession,105);
  assert.equal(result.tradeFrequency.paceEstimatedDays,3.81);
  assert.equal(result.coverage,0.5);
  assert.equal(result.methodology.entryThresholdRelaxed,false);
});

test('same-time audit conservatively clusters co-signals and measures pairwise aligned-return correlation',()=>{
  const rows=[];
  const samples=[
    ['2026-08-03','2026-08-03T00:30:00.000Z',1,2],
    ['2026-08-04','2026-08-04T00:30:00.000Z',2,4],
    ['2026-08-05','2026-08-05T00:30:00.000Z',3,6],
  ];
  for(const [sessionDate,entryTimestamp,a,b] of samples){
    rows.push(trade({symbol:'1001.T',sector:'Tech',sessionDate,entryTimestamp,net:a,aligned:a}));
    rows.push(trade({symbol:'1002.T',sector:'Bank',sessionDate,entryTimestamp,net:b,aligned:b}));
  }
  const result=summarizeP252TradeFrequencyVariant({variant:'DYNAMIC_30',trades:rows,evaluatedSessions:samples.map(x=>x[0])});
  assert.equal(result.sameTimeCorrelation.clusterCount,3);
  assert.equal(result.sameTimeCorrelation.largestClusterSize,2);
  assert.equal(result.sameTimeCorrelation.multiSignalEntryShare,1);
  assert.equal(result.sameTimeCorrelation.conservativeEffectiveIndependentEntries,3);
  assert.equal(result.sameTimeCorrelation.conservativeIndependenceRatio,0.5);
  assert.equal(result.sameTimeCorrelation.pairCount,1);
  assert.equal(result.sameTimeCorrelation.pairwise[0].correlation,1);
  assert.equal(result.sameTimeCorrelation.weightedMeanAbsCorrelation,1);
});

test('session-equal-weight portfolio prevents same-day co-signals from being compounded as independent sequential trades',()=>{
  const rows=[
    trade({symbol:'1001.T',sessionDate:'2026-08-03',entryTimestamp:'2026-08-03T00:30:00.000Z',net:10}),
    trade({symbol:'1002.T',sessionDate:'2026-08-03',entryTimestamp:'2026-08-03T00:30:00.000Z',net:-10}),
    trade({symbol:'1003.T',sessionDate:'2026-08-04',entryTimestamp:'2026-08-04T00:30:00.000Z',net:10}),
  ];
  const result=summarizeP252TradeFrequencyVariant({variant:'OLD_FIXED_30',trades:rows,evaluatedSessions:['2026-08-03','2026-08-04']});
  assert.equal(result.afterCostNetPct,8.9);
  assert.equal(result.sessionEqualWeightPortfolio.afterCostNetPct,10);
  assert.equal(result.sessionEqualWeightPortfolio.sessions[0].returnPct,0);
  assert.equal(result.sessionEqualWeightPortfolio.sessions[1].returnPct,10);
});

test('invalid or non-frozen rows cannot inflate valid Entry frequency',()=>{
  const rows=[
    trade(),
    trade({symbol:'',entryTimestamp:'2026-08-03T00:35:00.000Z'}),
    trade({entryAccepted:false,entryTimestamp:'2026-08-03T00:40:00.000Z'}),
  ];
  const result=summarizeP252TradeFrequencyVariant({variant:'FIXED_5',trades:rows,evaluatedSessions:['2026-08-03']});
  assert.equal(result.inputRows,3);
  assert.equal(result.validFrozenEntries,1);
  assert.equal(result.tradeFrequency.entriesPerTradingSession,1);
});

test('all execution, broker, Excel, RSS order, trading, promotion, production and fresh-holdout surfaces remain disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE57_P25_2_SAFETY[key],false,key);
  }
});
