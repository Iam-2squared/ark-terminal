import assert from 'node:assert/strict';
import test from 'node:test';
import {
  validatePhase57SelectorHistoricalDataset,
  splitPhase57SelectorHistoricalSessions,
  replayPhase57SelectorHistoricalDataset,
  calibratePhase57SelectorV3Threshold,
  evaluatePhase57SelectorHistoricalBenchmark,
} from '../daytrade/phase57-selector-v123-historical-benchmark.js';

const SAFETY=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
});

function isoDate(index){
  const start=Date.parse('2026-01-05T00:00:00.000Z');
  return new Date(start+index*24*60*60_000).toISOString().slice(0,10);
}

function barsForDay({sessionDate,base,step,volume}){
  const start=Date.parse(`${sessionDate}T00:00:00.000Z`);
  const bars=[];
  let previous=base;
  for(let index=0;index<18;index+=1){
    const wave=(index%4-1.5)*0.02;
    const open=previous;
    const close=open+step+wave;
    bars.push({
      timestamp:new Date(start+index*5*60_000).toISOString(),
      sessionDate,open,high:Math.max(open,close)+0.12,low:Math.min(open,close)-0.12,close,volume:volume+index*10,
    });
    previous=close;
  }
  return bars;
}

function dataset(){
  const symbols=Array.from({length:24},(_,index)=>({
    symbol:`${1000+index}.T`,sector:`SECTOR_${index%6}`,market:index%2?'PRIME':'STANDARD',
    bars:Array.from({length:31},(_,offset)=>{
      const day=offset-1;
      const sessionDate=isoDate(day);
      const base=20+index*30+day*0.1;
      const step=((index%7)-3)*0.05+(day%3-1)*0.01;
      return barsForDay({sessionDate,base,step,volume:50_000+index*8_000});
    }).flat(),
  }));
  const sessions=[];
  for(let day=0;day<30;day+=1){
    const sessionDate=isoDate(day);
    const start=Date.parse(`${sessionDate}T00:00:00.000Z`);
    sessions.push({
      sessionDate,
      decisionCutoffs:[3,6,9,12].map(count=>new Date(start+count*5*60_000).toISOString()),
      memberSymbols:symbols.map(item=>item.symbol),
    });
  }
  return {
    manifest:{
      schemaVersion:1,datasetId:'SYNTHETIC_SELECTOR_V123_30_SESSION',
      evidenceClassification:'SURVIVORSHIP_LIMITED_RECONSTRUCTION',
      universeStatus:'SURVIVORSHIP_LIMITED',
      claimsExactTradingViewReplay:false,
      intervalMinutes:5,barTimestampMeaning:'BAR_OPEN',
      source:'DETERMINISTIC_TEST_FIXTURE',safety:SAFETY,
    },
    symbols,sessions,
  };
}

test('dataset validator rejects exact-replay and survivorship mislabeling',()=>{
  const valid=dataset();
  assert.equal(validatePhase57SelectorHistoricalDataset(valid).sessionCount,30);
  const bad=structuredClone(valid);
  bad.manifest.evidenceClassification='LATER_FETCHED_HISTORICAL_RECONSTRUCTION';
  assert.throws(()=>validatePhase57SelectorHistoricalDataset(bad),/survivorship-limited input/);
  const falseExact=structuredClone(valid);
  falseExact.manifest.claimsExactTradingViewReplay=true;
  assert.throws(()=>validatePhase57SelectorHistoricalDataset(falseExact),/cannot claim exact/);
});

test('time split uses whole sessions and explicit purge sessions',()=>{
  const data=dataset();
  const split=splitPhase57SelectorHistoricalSessions(data.sessions);
  assert.equal(split.development.length,14);
  assert.equal(split.purgeDevelopmentValidation.length,1);
  assert.equal(split.validation.length,5);
  assert.equal(split.purgeValidationOos.length,1);
  assert.equal(split.untouchedOos.length,9);
  const flattened=[
    ...split.development,...split.purgeDevelopmentValidation,...split.validation,
    ...split.purgeValidationOos,...split.untouchedOos,
  ];
  assert.deepEqual(flattened,data.sessions.map(session=>session.sessionDate));
});

test('V1 V2 and frozen V3 replay the same symbol-timestamp market states',()=>{
  const data=dataset();
  const replay=replayPhase57SelectorHistoricalDataset(data);
  assert.equal(replay.records.length,30*4*24);
  assert.equal(replay.pointAudits.length,30*4);
  const first=replay.records[0];
  assert.equal(first.v1Selected,true);
  assert.equal(typeof first.v1Rank,'number');
  assert.equal(first.v3Eligible,true);
  assert.equal(first.targetStatus,'TARGET_READY');
  assert.equal(replay.methodology.sameReconstructedMarketState,true);
  assert.equal(replay.methodology.v1V2RealtimeExactReplayClaimed,false);
});

test('threshold calibration uses validation only and deterministic conservative ties',()=>{
  const rows=[];
  for(let point=0;point<20;point+=1){
    for(let rank=1;rank<=10;rank+=1){
      rows.push({
        featureCutoff:new Date(Date.parse('2026-03-01T00:00:00Z')+point*5*60_000).toISOString(),
        symbol:`${point}-${rank}`,sector:`S${rank}`,
        v3Rank:rank,v3Score:0.55,v3StructuralTradability:0.8,
        primaryCostAdjustedUtility:0.002,
      });
    }
  }
  const calibration=calibratePhase57SelectorV3Threshold(rows);
  assert.equal(calibration.selectedThreshold,0.55);
  assert.equal(calibration.outerOosUsed,false);
  assert.equal(calibration.candidates.find(row=>row.threshold===0.6).eligible,false);
});

test('outer OOS is sealed by default and released only explicitly',()=>{
  const data=dataset();
  const sealed=evaluatePhase57SelectorHistoricalBenchmark(data);
  assert.equal(sealed.outerOosConsumed,false);
  assert.equal(sealed.untouchedOos.status,'SEALED_UNTOUCHED_OOS');
  assert.equal(sealed.methodology.v1V2Changed,false);
  assert.equal(sealed.safety.executionAllowed,false);
  const released=evaluatePhase57SelectorHistoricalBenchmark(data,{releaseOuterOos:true});
  assert.equal(released.outerOosConsumed,true);
  assert.equal(released.untouchedOos.V1.selector,'V1');
  assert.equal(released.untouchedOos.V2.selector,'V2');
  assert.equal(released.untouchedOos.V3.selector,'V3');
});
