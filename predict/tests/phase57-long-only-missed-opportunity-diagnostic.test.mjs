import test from 'node:test';
import assert from 'node:assert/strict';
import {addDiagnosticPercentiles,buildDiagnosticCohorts,diagnoseMissedOpportunities,MISSED_OPPORTUNITY_DIAGNOSTIC_CONTRACT} from '../long-only/phase57-long-only-missed-opportunity-diagnostic.js';

const ranked=[];
for(const date of ['2024-01-01','2024-01-02'])for(const time of ['09:30','10:00'])for(let rank=1;rank<=150;rank++){
  const emerging=rank>=101&&rank%2===0,y30Bps=emerging?250:rank<=20?120:0;
  ranked.push({
    rank,score:151-rank,groupSize:150,scorePercentile:100*(151-rank)/150,
    feature:{sessionDate:date,symbol:`S${rank}`,decisionTimeJst:time,currentReturnPct:rank<=20?3:0.5,momentum5Pct:rank<=20?2:0.1,momentum15Pct:rank<=20?3:0.2,momentum30Pct:rank<=20?5:0.3,momentumAccelerationPct:emerging?2:0,vwapSlope15Pct:emerging?2:0,vwapDistancePct:emerging?1:0,cumulativeVolume:emerging?1_000_000:100_000,volumeAccelerationRatio:emerging?3:1,rangeExpansionPct:2,trendEfficiency:0.5,pullbackDepthPct:-1,decisionVolatilityPct:emerging?3:1,marketBreadthPositivePct:50,sectorBreadthPositivePct:emerging?80:50,gapPct:0,vwapReclaim5m:emerging,segment:'PRIME',liquidityBucket:'MID',gapBucket:'NON_GAP'},
    target:{sessionDate:date,symbol:`S${rank}`,decisionTimeJst:time,y30Bps,futureMfe30Pct:y30Bps/100+0.5,futureMae30Pct:-0.5,timeToMfe30Minutes:20},
  });
}

test('diagnostic contract preserves six 5m bars and sealed fixed-score scope',()=>{
  assert.equal(MISSED_OPPORTUNITY_DIAGNOSTIC_CONTRACT.horizonBars,6);
  assert.equal(MISSED_OPPORTUNITY_DIAGNOSTIC_CONTRACT.retrainingAllowed,false);
  assert.equal(MISSED_OPPORTUNITY_DIAGNOSTIC_CONTRACT.validationAllowed,false);
});

test('cohorts separate top20, rank101 missed opportunities, and matched ordinary controls',()=>{
  const decorated=addDiagnosticPercentiles(ranked),cohorts=buildDiagnosticCohorts(decorated);
  assert.equal(cohorts.RIDGE_TOP20.length,80);
  assert.equal(cohorts.MISSED_200_RANK101_PLUS.length,100);
  assert.ok(cohorts.ORDINARY_MATCHED_CONTROL.length>0);
  assert.ok(cohorts.MISSED_200_RANK101_PLUS.every(row=>row.rank>=101&&row.target.y30Bps>=200));
});

test('full diagnostic reports feature effects, archetypes, MFE mismatch, volatility, and formal old-selector availability',()=>{
  const oldRows=ranked.filter(row=>row.rank>=101&&row.rank%2===0).map(row=>({...row.feature,selectorRank:row.rank-100,selectorScore:200-row.rank}));
  const report=diagnoseMissedOpportunities({ranked,oldSelectors:{V3:{status:'AVAILABLE',rows:oldRows},V1:{status:'UNAVAILABLE',reason:'NO_FORMAL_RANK'}}});
  assert.ok(report.featureContrast.effects.MISSED200_VS_CONTROL.relativeVolumePercentile.standardizedMeanDifference>0);
  assert.ok(report.archetypes.GE_200_BPS.overlapping.VWAP_RECLAIM.count>0);
  assert.ok(report.endpointVsMfe.missed200.timeToMfeMinutes.n>0);
  assert.equal(report.oldSelectorComplementarity.V3.missed200.recallPct,100);
  assert.equal(report.oldSelectorComplementarity.V1.status,'UNAVAILABLE');
});
