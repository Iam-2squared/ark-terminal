import test from 'node:test';
import assert from 'node:assert/strict';
import {fitL2Candidate} from '../long-only/phase57-long-only-l2-selector-v1.js';
import {rankFrozenScore,diagnoseCapacity,CAPACITY_TOP_NS} from '../long-only/phase57-long-only-selector-capacity-diagnostic.js';

const feature=(sessionDate,symbol,time,currentReturnPct)=>({sessionDate,symbol,decisionTimeJst:time,decisionAtJst:`${sessionDate}T${time}:00+09:00`,currentPrice:100,currentReturnPct,momentum30Pct:currentReturnPct,vwapDistancePct:currentReturnPct,vwapSlope15Pct:currentReturnPct,cumulativeTurnover:1000000,volumeAccelerationRatio:1,trendEfficiency:0.5,rangeExpansionPct:1,gapPct:0,decisionVolatilityPct:1,causalAtr:1,timeOfDayFraction:0,segment:'PRIME',liquidityBucket:'HIGH',gapBucket:'NON_GAP',marketBreadthPositivePct:50,sectorBreadthPositivePct:50});
const features=[],targets=[];for(const date of ['2024-01-01','2024-01-02'])for(const time of ['09:30','10:00'])for(let i=0;i<60;i++){const row=feature(date,`S${String(i).padStart(3,'0')}`,time,i);features.push(row);targets.push({sessionDate:date,symbol:row.symbol,decisionTimeJst:time,y30Bps:i*10,futureMfe30Pct:i/10,futureMae30Pct:-i/100,winner:i>=55});}
const artifact=fitL2Candidate({candidateId:'RIDGE_Y30',featureRows:features,targetRows:targets});

test('capacity diagnostic reuses one fixed score for all Top N policies',()=>{const ranked=rankFrozenScore({featureRows:features,targetRows:targets,artifact}),report=diagnoseCapacity(ranked);assert.deepEqual(CAPACITY_TOP_NS,[1,3,5,10,20,30,50]);assert.equal(report.capacityCurve.TOP_5.candidateCount,20);assert.equal(report.capacityCurve.TOP_50.candidateCount,200);assert.ok(report.capacityCurve.TOP_5.meanReturnBps>report.capacityCurve.TOP_50.meanReturnBps);assert.ok(report.capacityCurve.TOP_20.opportunities.GE_200_BPS.recallPct>report.capacityCurve.TOP_5.opportunities.GE_200_BPS.recallPct);assert.ok(report.scoreCalibration.spearman.global>0.99);});

test('missed opportunity and distribution diagnostics remain evaluator-only',()=>{const ranked=rankFrozenScore({featureRows:features,targetRows:targets,artifact}),report=diagnoseCapacity(ranked);assert.ok(report.missedOpportunity.GE_200_BPS.missedByTop5>0);assert.equal(report.distributionTop5.count,20);assert.ok(Number.isFinite(report.distributionTop5.kurtosis));assert.ok(report.stability.TOP_5.market.PRIME.candidateCount>0);});
