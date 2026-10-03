import assert from 'node:assert/strict';
import test from 'node:test';
import {buildL1CrossSectionDataset} from '../long-only/phase57-long-only-l1-cross-section.js';
import {projectLongSelectorFeatures,runLongSelectorDevelopment,selectLongCandidates,LONG_SELECTOR_DEVELOPMENT_CONTRACT} from '../long-only/phase57-long-only-selector-development.js';

const feature=(partition,index)=>({
  partition,sessionDate:partition==='DEVELOPMENT_C'?'2026-01-05':'2026-02-02',symbol:String(10000+index),segment:index%3===0?'PRIME':index%3===1?'STANDARD':'GROWTH',decisionTimeJst:'10:00',decisionAtJst:'2026-01-05T10:00:00+09:00',
  currentPrice:100+index,currentReturnPct:index/10,momentum5Pct:index/20,momentum15Pct:index/15,momentum30Pct:index/12,momentumAccelerationPct:index/100,cumulativeVolume:1000+index*10,cumulativeTurnover:100000+index*10000,
  vwap:99,vwapDistancePct:index/50,sessionHighUpdate:index%2===0,rangeExpansionPct:2+index/100,trendEfficiency:0.5+index/1000,reversalCount:index%4,causalAtr:1+index/100,observedBars:12,
  latestAvailableAtJst:'2026-01-05T10:00:00+09:00',marketBreadthPositivePct:60,sectorBreadthPositivePct:55,sector:'TEST',marketBreadthN:40,sectorBreadthN:40,liquidityBucket:'MID',liquidityCrossSectionN:40,
});
const label=(row,index)=>({sessionDate:row.sessionDate,symbol:row.symbol,decisionTimeJst:row.decisionTimeJst,evaluatorOnly:true,finalReturnPct:index/5,winner:index>=25,remainingUpsidePct:index/8,futureMfePct:index/8,futureMaePct:-index/50,continuationToClosePct:index/10-1,lateDetection:false});
const dataset=partition=>{const featureRows=Array.from({length:40},(_,i)=>feature(partition,i)),evaluatorOnlyLabels=featureRows.map(label);return {partition,featureRows,evaluatorOnlyLabels};};

test('L2 development fits only C, selects only on D and freezes one refit artifact',()=>{
  const result=runLongSelectorDevelopment({developmentC:dataset('DEVELOPMENT_C'),developmentD:dataset('DEVELOPMENT_D')});
  assert.match(result.freezeSha256,/^[a-f0-9]{64}$/);assert.match(result.finalArtifact.artifactSha256,/^[a-f0-9]{64}$/);
  assert.equal(result.allCandidates.length,3);assert.equal(result.validationOutcomesUsed,false);assert.equal(result.oosOutcomesUsed,false);
  assert.equal(LONG_SELECTOR_DEVELOPMENT_CONTRACT.featureSets,1);assert.equal(LONG_SELECTOR_DEVELOPMENT_CONTRACT.thresholdSearch,false);
  const selected=selectLongCandidates({featureRows:dataset('DEVELOPMENT_D').featureRows,artifact:result.finalArtifact});assert.equal(selected.length,10);assert.equal(selected.filter(x=>x.selectorRank===1).length,1);
});

test('selector feature projection rejects evaluator outcomes',()=>{
  assert.throws(()=>projectLongSelectorFeatures({...feature('DEVELOPMENT_C',1),futureMfePct:5}),/outcome field/);
  assert.throws(()=>runLongSelectorDevelopment({developmentC:dataset('DEVELOPMENT_A'),developmentD:dataset('DEVELOPMENT_D')}),/Development C/);
});

test('L1 cross-section refuses sealed partitions before reading outcomes',()=>{
  assert.throws(()=>buildL1CrossSectionDataset({partition:'VALIDATION'}),/Development-only/);
});
