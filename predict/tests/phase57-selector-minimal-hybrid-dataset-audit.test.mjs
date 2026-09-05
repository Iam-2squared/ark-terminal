import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';

import {
  auditPhase57MinimalHybridDataset,
  requirePhase57MinimalHybridDatasetAdmission,
} from '../daytrade/phase57-selector-minimal-hybrid-dataset-audit.js';

const SAFETY=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
});

function tradingDates(count){
  const dates=[];let cursor=Date.UTC(2025,0,6);
  while(dates.length<count){const day=new Date(cursor).getUTCDay();if(day!==0&&day!==6)dates.push(new Date(cursor).toISOString().slice(0,10));cursor+=86_400_000;}
  return dates;
}

function fiveMinuteStarts(sessionDate){
  const starts=[];
  for(const [hour,minute,count] of [[9,0,30],[12,30,36]]){
    const start=Date.parse(`${sessionDate}T${String(hour).padStart(2,'0')}:${String(minute).padStart(2,'0')}:00+09:00`);
    for(let index=0;index<count;index+=1)starts.push(start+index*5*60_000);
  }
  return starts;
}

function datasetFixture(){
  const dates=tradingDates(120);
  const bars=dates.flatMap((date,sessionIndex)=>fiveMinuteStarts(date).map((timestamp,index)=>{
    const open=100+sessionIndex*0.01+index*0.001,close=open+0.02;
    return {
      timestamp:new Date(timestamp).toISOString(),availableAt:new Date(timestamp+5*60_000).toISOString(),sessionDate:date,
      open,high:close+0.01,low:open-0.01,close,volume:1000+index,turnover:(1000+index)*close,
    };
  }));
  return {
    manifest:{
      datasetId:'PHASE57_MINIMAL_HYBRID_FRESH_FIXTURE',parentDatasetIds:[],rawSourceSha256:'a'.repeat(64),
      sourceProvider:'AUTHORIZED_FIXTURE_PROVIDER',sourceEndpoint:'OFFLINE_FIXTURE',acquisitionMethod:'IMMUTABLE_IMPORT',
      acquiredAt:'2025-07-01T00:00:00.000Z',reconstructionMethod:'EXACT_POINT_IN_TIME_FIXTURE',
      evidenceClassification:'EXACT_POINT_IN_TIME',providerEntitlementVerified:true,
      previouslyUsedForSelectorOutcomeInspection:false,intervalMinutes:5,barTimestampMeaning:'BAR_OPEN',
      availableAtRule:'BAR_OPEN_PLUS_INTERVAL',noTradeMinutePolicy:'MISSING_NEVER_FABRICATE',
      missingMicrostructurePolicy:'UNKNOWN_WITH_AVAILABILITY_MASK',microstructureZeroFilled:false,
      completeCrossSectionAtomic:true,universeStatus:'POINT_IN_TIME',strongHistoricalClaimAllowed:true,
      survivorshipLimitation:'NONE_IN_FIXTURE',corporateActionHandling:'EXPLICIT_POINT_IN_TIME_EVENT_TABLE',
      volumeSemantics:'OBSERVED_SHARES_PER_5M_BAR',turnoverSemantics:'OBSERVED_YEN_PER_5M_BAR',
      targetLabelPolicy:'SAME_SESSION_AFTER_CUTOFF_ONLY',validationReleased:false,untouchedOosReleased:false,
      safety:SAFETY,
    },
    sessions:dates.map(date=>({
      sessionDate:date,crossSectionAtomic:true,memberSymbols:['1001.T'],
      decisionCutoffs:[new Date(Date.parse(`${date}T09:15:00+09:00`)).toISOString()],
    })),
    symbols:[{symbol:'1001.T',sector:'TEST',market:'PRIME',bars}],
  };
}

test('readiness evidence is frozen at DATASET_NOT_READY without training or release',()=>{
  const url=new URL('../research/phase57-selector-minimal-hybrid-dataset-readiness-2026-09-05.json',import.meta.url);
  const bytes=fs.readFileSync(url);
  const report=JSON.parse(bytes);
  const expected=fs.readFileSync(new URL('../research/phase57-selector-minimal-hybrid-dataset-readiness-2026-09-05.sha256',import.meta.url),'utf8').trim().split(/\s+/)[0];
  assert.equal(createHash('sha256').update(bytes).digest('hex'),expected);
  assert.equal(report.status,'DATASET_NOT_READY');
  assert.equal(report.dataAcquired,false);
  assert.equal(report.datasetAdmitted,false);
  assert.equal(report.modelFittingPerformed,false);
  assert.equal(report.validationReleased,false);
  assert.equal(report.untouchedOosReleased,false);
  for(const [key,value] of Object.entries(report.safety))assert.equal(value,false,key);
});

test('complete 120-session fixture emits an auditable Development-only admission',()=>{
  const report=auditPhase57MinimalHybridDataset(datasetFixture());
  assert.equal(report.status,'MINIMAL_HYBRID_DATASET_ADMITTED_DEVELOPMENT_ONLY');
  assert.equal(report.counts.sessionCount,120);
  assert.equal(report.counts.totalBars,7920);
  assert.equal(report.counts.totalCrossSections,7920);
  assert.equal(report.counts.missingBars,0);
  assert.equal(report.counts.duplicateBars,0);
  assert.equal(report.counts.timestampConflicts,0);
  assert.equal(report.counts.lunchViolations,0);
  assert.equal(report.counts.futureAvailabilityViolations,0);
  assert.equal(report.release.developmentReleased,true);
  assert.equal(report.release.validationReleased,false);
  assert.equal(report.release.untouchedOosReleased,false);
  assert.equal(report.training.modelFittingPerformed,false);
  assert.equal(requirePhase57MinimalHybridDatasetAdmission(datasetFixture()).reportSha256,report.reportSha256);
});

test('availability violations, duplicates, and consumed ancestry reject admission',()=>{
  const availability=datasetFixture();
  availability.symbols[0].bars[0].availableAt=availability.symbols[0].bars[0].timestamp;
  let report=auditPhase57MinimalHybridDataset(availability);
  assert.equal(report.status,'MINIMAL_HYBRID_DATASET_ADMISSION_REJECTED');
  assert.ok(report.blockers.includes('BAR_AVAILABILITY_SEMANTICS_VIOLATION'));

  const duplicate=datasetFixture();
  duplicate.symbols[0].bars.push({...duplicate.symbols[0].bars[0]});
  report=auditPhase57MinimalHybridDataset(duplicate);
  assert.ok(report.blockers.includes('DUPLICATE_BARS_PRESENT'));

  const ancestry=datasetFixture();
  ancestry.manifest.parentDatasetIds=['PHASE57_SELECTOR_YAHOO_5M_24626FD37F8633F4'];
  report=auditPhase57MinimalHybridDataset(ancestry);
  assert.equal(report.status,'MINIMAL_HYBRID_DATASET_ADMISSION_REJECTED');
  assert.ok(report.blockers.some(value=>value.includes('consumed dataset identity is forbidden')));
  assert.throws(()=>requirePhase57MinimalHybridDatasetAdmission(ancestry),/admission failed/);
});
