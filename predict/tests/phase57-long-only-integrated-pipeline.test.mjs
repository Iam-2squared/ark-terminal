import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import test from 'node:test';
import {assembleLongOnlyL0Rows,normalizeAndAggregateMinuteRows,createIntegratedResearchDataset} from '../long-only/phase57-long-only-integrated-dataset.js';
import {buildCausalL1Features,buildEvaluatorOnlyL1Label,evaluateEarlyWinnerDiscovery,assignCausalLiquidityBuckets} from '../long-only/phase57-long-only-l1-labels-features.js';
import {compareLongOnlyIntegratedSystems,COMPARISON_STAGES} from '../long-only/phase57-long-only-integrated-comparison.js';
import {acquireFormalL0Session,fetchJquantsPages} from '../long-only/phase57-long-only-jquants-client.js';
import {replayLongOnlyIntegratedStages} from '../long-only/phase57-long-only-replay-interface.js';
import {buildEvaluatorOnlyL2Targets,assertL2SelectionBoundary,L2_CANDIDATE_CONTRACT} from '../long-only/phase57-long-only-l2-candidate-contract.js';
import {loadFormalL0PartitionFromCache} from '../long-only/phase57-long-only-l0-cache.js';
import {buildL1DiscoveryReport} from '../long-only/phase57-long-only-l1-discovery-report.js';
import {buildL1CrossSectionDataset} from '../long-only/phase57-long-only-l1-cross-section.js';
import {buildFixedHorizonTargets,L2_HORIZON_CONTRACT} from '../long-only/phase57-long-only-l2-fixed-horizon.js';
import {L2_SELECTOR_CONTRACT,L2_FEATURE_FAMILIES,projectL2Features} from '../long-only/phase57-long-only-l2-selector-v1.js';

test('frozen split names exactly 205 unique outcome-unread historical sessions',()=>{
  const allocation=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
  const expected={DEVELOPMENT_A:25,DEVELOPMENT_B:15,DEVELOPMENT_C:20,DEVELOPMENT_D:20,VALIDATION:30,VALIDATION_REPLICATION:20,PRIMARY_OOS:30,CONTINGENCY_OOS:30,RESERVE:15};
  const all=[];for(const [partition,count] of Object.entries(expected)){assert.equal(allocation.partitions[partition].length,count);all.push(...allocation.partitions[partition]);}
  assert.equal(all.length,205);assert.equal(new Set(all).size,205);assert.deepEqual(all,[...all].sort());assert.equal(allocation.outcomesInspected,false);
});

test('daily plus dated master is sufficient for formal L0 and audits exclusions',()=>{
  const dailyRows=[
    {Date:'2024-01-03',Code:'11110',AdjC:100,AdjFactor:1,Vo:10,Va:1000},
    {Date:'2024-01-04',Code:'11110',AdjC:106,AdjFactor:1,Vo:20,Va:2100},
    {Date:'2024-01-04',Code:'99990',AdjC:10,AdjFactor:1,Vo:0,Va:0},
  ];
  const masterRows=[{Date:'2024-01-03',Code:'11110',Mkt:'0111',ProdCat:'011'},{Date:'2024-01-04',Code:'11110',Mkt:'0111',ProdCat:'011'}];
  const result=assembleLongOnlyL0Rows({dailyRows,masterRows});
  assert.equal(result.rows.length,1);assert.equal(result.rows[0].adjustedPreviousClose,100);assert.equal(result.rows[0].segment,'PRIME');assert.equal(result.audit.exclusionCounts.NOT_ELIGIBLE_PIT_COMMON_EQUITY,1);
  assert.equal(result.rows[0].adjustmentScale,1);
});

test('Formal L0 cache loader verifies immutable pages and preserves every Development A session with causal warmup',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'phase57-l0-cache-')),base=path.join(root,'phase57-long-only','raw','jquants-v2');
  const writeSession=(sessionDate,kind,rows,manifestName='l0-manifest.json')=>{
    const dir=path.join(base,sessionDate);fs.mkdirSync(dir,{recursive:true});
    const responseText=JSON.stringify({data:rows}),responseSha256=createHash('sha256').update(responseText).digest('hex');
    const pages=[{page:1,responseSha256,responseText,payload:{data:rows}}],aggregateSha256=createHash('sha256').update(JSON.stringify([responseSha256])).digest('hex');
    fs.writeFileSync(path.join(dir,`${kind}-pages.json`),JSON.stringify(pages));
    const manifestPath=path.join(dir,manifestName),existing=fs.existsSync(manifestPath)?JSON.parse(fs.readFileSync(manifestPath,'utf8')):{};
    fs.writeFileSync(manifestPath,JSON.stringify({...existing,sessionDate,partition:'DEVELOPMENT_A',evaluationPartition:manifestName.includes('warmup')?false:undefined,manifestSha256:'a'.repeat(64),[kind]:{pageCount:1,aggregateSha256}}));
  };
  writeSession('2024-09-09','daily',[{Date:'2024-09-09',Code:'11110',AdjC:100}],'l0-warmup-manifest.json');
  writeSession('2024-09-10','daily',[{Date:'2024-09-10',Code:'11110',AdjC:106,AdjFactor:1,Vo:10,Va:1060}]);
  writeSession('2024-09-10','master',[{Date:'2024-09-10',Code:'11110',Mkt:'0111',ProdCat:'011'}]);
  const result=loadFormalL0PartitionFromCache({cacheRoot:root,partition:'DEVELOPMENT_A',plan:{l0Contract:{causalWarmup:{sessionDate:'2024-09-09'}}},allocation:{partitions:{DEVELOPMENT_A:['2024-09-10']}}});
  assert.equal(result.rows.length,1);assert.equal(result.rows[0].adjustedPreviousClose,100);assert.equal(result.admissionAudit.warmupDailyRows,1);
  fs.rmSync(root,{recursive:true,force:true});
});

const minuteRows=[
  {Date:'2024-01-04',Code:'11110',Time:'09:00',O:100,H:101,L:99,C:100,Vo:100,Va:10000},
  {Date:'2024-01-04',Code:'11110',Time:'09:02',O:100,H:103,L:100,C:102,Vo:200,Va:20400},
  {Date:'2024-01-04',Code:'11110',Time:'09:05',O:102,H:104,L:101,C:103,Vo:150,Va:15450},
  {Date:'2024-01-04',Code:'11110',Time:'09:10',O:103,H:106,L:102,C:105,Vo:200,Va:21000},
  {Date:'2024-01-04',Code:'11110',Time:'09:15',O:105,H:107,L:104,C:106,Vo:100,Va:10600},
  {Date:'2024-01-04',Code:'11110',Time:'09:20',O:106,H:108,L:105,C:107,Vo:100,Va:10700},
  {Date:'2024-01-04',Code:'11110',Time:'09:25',O:107,H:109,L:106,C:108,Vo:100,Va:10800},
  {Date:'2024-01-04',Code:'11110',Time:'09:30',O:108,H:111,L:107,C:110,Vo:200,Va:22000},
  {Date:'2024-01-04',Code:'11110',Time:'11:30',O:110,H:110,L:110,C:110,Vo:1,Va:110},
];

test('sparse minute rows aggregate causally and terminal auction is separate',()=>{
  const result=normalizeAndAggregateMinuteRows(minuteRows);
  assert.equal(result.bars.length,7);assert.equal(result.bars[0].observedMinutes,2);assert.equal(result.bars[0].availableAtJst,'2024-01-04T09:05:00+09:00');assert.equal(result.terminalAuctions.length,1);
});

test('L1 decision features cannot see evaluator-only future path',()=>{
  const bars=normalizeAndAggregateMinuteRows(minuteRows).bars;
  const feature=buildCausalL1Features({sessionDate:'2024-01-04',symbol:'11110',decisionTimeJst:'09:30',bars5m:bars,previousAdjustedClose:100});
  const label=buildEvaluatorOnlyL1Label({sessionDate:'2024-01-04',symbol:'11110',decisionTimeJst:'09:30',bars5m:bars,previousAdjustedClose:100,decisionTimeAtr:feature.causalAtr});
  assert.equal(feature.latestAvailableAtJst,'2024-01-04T09:30:00+09:00');assert.equal(feature.currentPrice,108);assert.equal(label.evaluatorOnly,true);assert.equal(label.futureBarCount,1);
  for(const forbidden of ['winner','remainingUpsidePct','futureMfePct','futureMaePct','finalReturnPct'])assert.equal(forbidden in feature,false);
  assert.ok(Number.isFinite(label.futureMfeAtr));assert.ok(Number.isFinite(label.futureMaeAtr));
  const stratified=assignCausalLiquidityBuckets([{...feature,segment:'PRIME'}]);
  const k=`${feature.sessionDate}|${feature.symbol}|${feature.decisionTimeJst}`,summary=evaluateEarlyWinnerDiscovery({features:stratified,evaluatorOnlyLabels:[label],detectedKeys:[k]});
  assert.equal(summary.detectedWinnerCount,1);assert.equal(summary.earlyWinnerRecallPct,100);
  assert.equal(summary.byMarket.PRIME.n,1);assert.equal(summary.byLiquidity.HIGH.n,1);
  const targets=buildEvaluatorOnlyL2Targets(label);assert.equal(targets.evaluatorOnly,true);assert.ok(Number.isFinite(targets.riskAdjustedRemainingOpportunityPct));
  assert.equal(assertL2SelectionBoundary({partition:'DEVELOPMENT_C',targetCount:3,modelFamilyCount:2}),true);
  assert.throws(()=>assertL2SelectionBoundary({partition:'VALIDATION',targetCount:1,modelFamilyCount:1}),/Development C\/D/);
  assert.equal(L2_CANDIDATE_CONTRACT.validationMaySelectTarget,false);
  assert.throws(()=>buildCausalL1Features({sessionDate:'2024-01-04',symbol:'11110',decisionTimeJst:'09:30',bars5m:bars,previousAdjustedClose:100,corporateActionFlag:true}),/corporate-action/);
});

test('L1 de-adjusts prior close to the raw Minute price scale without changing winner return',()=>{
  const rawBars=normalizeAndAggregateMinuteRows(minuteRows.map(row=>({...row,O:row.O*10,H:row.H*10,L:row.L*10,C:row.C*10,Va:row.Va*10}))).bars;
  const built=buildL1CrossSectionDataset({partition:'DEVELOPMENT_A',dailyRows:[{sessionDate:'2024-01-04',symbol:'11110',segment:'PRIME',adjustedPreviousClose:100,adjustedClose:106,unadjustedClose:1060,adjustmentScale:.1,corporateActionFlag:false}],bars5m:rawBars});
  assert.equal(built.audit.nonUnitAdjustmentScaleRows,1);
  assert.ok(Math.abs(built.featureRows[0].currentReturnPct-8)<1e-9);
  assert.equal(built.evaluatorOnlyLabels[0].winner,true);
});

test('L2 fixed 30m and 60m targets mean exactly 6 and 12 future five-minute bars',()=>{
  const bars=Array.from({length:20},(_,i)=>({sessionDate:'2024-01-04',symbol:'11110',availableAtJst:`2024-01-04T${String(9+Math.floor((5*(i+1))/60)).padStart(2,'0')}:${String((5*(i+1))%60).padStart(2,'0')}:00+09:00`,open:100+i,high:101+i,low:99+i,close:100+i}));
  const feature={sessionDate:'2024-01-04',symbol:'11110',decisionTimeJst:'09:30',decisionAtJst:'2024-01-04T09:30:00+09:00'};
  const label={sessionDate:'2024-01-04',symbol:'11110',decisionTimeJst:'09:30',evaluatorOnly:true,winner:true,largeWinner:false,remainingUpsidePct:5,timeToWinnerMinutes:30};
  const [target]=buildFixedHorizonTargets({featureRows:[feature],bars5m:bars,evaluatorOnlyLabels:[label]});
  assert.equal(L2_HORIZON_CONTRACT.horizons.Y30_BPS,6);assert.equal(L2_HORIZON_CONTRACT.horizons.Y60_BPS,12);
  assert.equal(target.target30AvailableAtJst,'2024-01-04T10:00:00+09:00');
  assert.equal(target.target60AvailableAtJst,'2024-01-04T10:30:00+09:00');
  assert.ok(Math.abs(target.y30Bps-10000*(111/105-1))<1e-7);
});

test('L2 feature contract is causal, compact by family, and excludes outcome fields',()=>{
  const feature={sessionDate:'2024-01-04',symbol:'11110',decisionTimeJst:'09:30',currentPrice:105,currentReturnPct:5,momentum30Pct:4,vwapDistancePct:2,vwapSlope15Pct:1,cumulativeTurnover:1e8,volumeAccelerationRatio:1.2,trendEfficiency:.8,rangeExpansionPct:6,gapPct:1,decisionVolatilityPct:.4,causalAtr:1,segment:'PRIME',liquidityBucket:'HIGH',marketBreadthPositivePct:55,sectorBreadthPositivePct:60};
  assert.equal(Object.keys(L2_FEATURE_FAMILIES).length,8);assert.equal(L2_SELECTOR_CONTRACT.candidates.length,3);
  assert.doesNotThrow(()=>projectL2Features(feature));
  assert.throws(()=>projectL2Features({...feature,futureMfePct:4}),/outcome/);
});

test('L1 discovery report compares winners with full-cross-section negative controls',()=>{
  const base={sessionDate:'2024-09-10',decisionTimeJst:'10:00',segment:'PRIME',liquidityBucket:'HIGH',gapBucket:'NON_GAP',currentReturnPct:1.5,momentum5Pct:1,momentum15Pct:1,marketBreadthPositivePct:50,sectorBreadthPositivePct:50};
  const featureRows=[{...base,symbol:'1000'},{...base,symbol:'2000',currentReturnPct:0.1}];
  const evaluatorOnlyLabels=[{sessionDate:'2024-09-10',symbol:'1000',decisionTimeJst:'10:00',evaluatorOnly:true,winner:true,largeWinner:false,finalClass:'FINAL_GTE5',remainingUpsidePct:4,futureMfePct:4,futureMaePct:-1,futureMfeAtr:2,futureMaeAtr:-.5,timeToWinnerMinutes:60,lateDetection:false,limitUpTouched:false},{sessionDate:'2024-09-10',symbol:'2000',decisionTimeJst:'10:00',evaluatorOnly:true,winner:false,largeWinner:false,finalClass:'NON_WINNER',remainingUpsidePct:1,futureMfePct:1,futureMaePct:-2,futureMfeAtr:.5,futureMaeAtr:-1,timeToWinnerMinutes:null,lateDetection:false,limitUpTouched:false}];
  const report=buildL1DiscoveryReport({featureRows,evaluatorOnlyLabels});
  assert.equal(report.winnerCurrentReturnBuckets['1_TO_2'].symbols,1);
  assert.equal(report.winnerUniverse.finalGte5SymbolSessions,1);
  assert.equal(report.comparisonCohorts.highVolumeNonWinner.symbols,1);
  assert.equal(report.sessionStability['2024-09-10'].observations,2);
  assert.equal(report.causalFeatureDiagnostics['10:00'].topNByCausalFeature.currentReturnPct.winnerRecallPct,100);
  assert.equal(report.contract.outcomesNeverReturnedToDecisionPipeline,true);
});

test('one immutable dataset identity is reused by selector entry exit allocation and portfolio',()=>{
  const dataset=createIntegratedResearchDataset({partition:'DEVELOPMENT_A',sourceManifest:{sourceSha256:'a'.repeat(64)},dailyRows:[],masterRows:[],minuteRows});
  for(const consumer of ['SELECTOR','ENTRY','EXIT','ALLOCATION','PORTFOLIO'])assert.equal(dataset.consumers[consumer].datasetId,dataset.datasetId);
  assert.equal(dataset.safety.executionAllowed,false);assert.equal(dataset.safety.paperTradingAllowed,false);
});

test('replay adapters receive one dataset and enforce cash-only entry intents',async()=>{
  const dataset=createIntegratedResearchDataset({partition:'DEVELOPMENT_A',sourceManifest:{sourceSha256:'a'.repeat(64)},minuteRows});
  const result=await replayLongOnlyIntegratedStages({dataset,components:{selector:async view=>[{symbol:'11110',datasetId:view.datasetId}],entry:async({candidates})=>candidates.map(x=>({side:'LONG',accountType:'CASH_EQUITY',quantity:100,price:1000,availableCashJpy:100000,symbol:x.symbol})),exit:async({intents})=>intents.map(x=>({...x,netPnlJpy:100})),allocation:async({trades})=>({tradeCount:trades.length})}});
  assert.equal(result.proof.singleRawDatasetReused,true);assert.equal(result.stages.FULL_INTEGRATED_PORTFOLIO.portfolio.tradeCount,1);
});

const system=(sessions,cost,net,ddEnd)=>({evaluationSessions:sessions,costModelSha256:cost,initialCashJpy:100000,stages:Object.fromEntries(COMPARISON_STAGES.map(stage=>[stage,{trades:[{side:'LONG',accountType:'CASH_EQUITY',quantity:100,leverage:1,symbol:'11110',sector:'TECH',sessionDate:'2024-01-04',regime:'RISK_ON',mfeCapturePct:60,maePct:-0.5,entryAt:'2024-01-04T09:30:00+09:00',exitAt:'2024-01-04T10:00:00+09:00',entryPrice:1000,exitPrice:1000+net/100,netPnlJpy:net}],equityCurve:[{equityJpy:100000,investedJpy:50000},{equityJpy:ddEnd,investedJpy:0}],opportunityCount:2,missedOpportunityCount:1}]))});

test('integrated harness enforces same window/cost and proves zero short or margin',()=>{
  const sessions=['2024-01-04'],cost='a'.repeat(64),baseline=system(sessions,cost,1000,101000),candidate=system(sessions,cost,2000,102000);
  const result=compareLongOnlyIntegratedSystems({evaluationSessions:sessions,costModelSha256:cost,baseline,candidate});
  assert.equal(result.pass,true);assert.equal(result.proof.candidateShortTrades,0);assert.equal(result.proof.cashLedgerAudit.cashNeverNegative,true);assert.equal(Object.keys(result.stages).length,4);
  assert.equal(result.stages.FULL_INTEGRATED_PORTFOLIO.candidate.meanMfeCapturePct,60);assert.equal(result.stages.FULL_INTEGRATED_PORTFOLIO.candidate.sessionStability.profitableGroupPct,100);
  const bad=structuredClone(candidate);bad.stages.FULL_INTEGRATED_PORTFOLIO.trades[0].side='SHORT';assert.throws(()=>compareLongOnlyIntegratedSystems({evaluationSessions:sessions,costModelSha256:cost,baseline,candidate:bad}),/SHORT/);
});

test('J-Quants pagination is reusable but formal acquisition fails before any network call when gate is blocked',async()=>{
  let calls=0;const pages=[{data:[1],pagination_key:'next'},{data:[2]}];
  const fetched=await fetchJquantsPages({endpoint:'/equities/bars/daily',query:{date:'2024-01-04'},apiKey:'fixture',fetchImpl:async()=>{const payload=pages[calls++];return {ok:true,status:200,text:async()=>JSON.stringify(payload)};}});
  assert.equal(fetched.pageCount,2);assert.equal(calls,2);
  calls=0;const plan=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
  await assert.rejects(()=>acquireFormalL0Session({plan,authorization:{},partition:'DEVELOPMENT_A',sessionDate:'2024-01-04',apiKey:'fixture',fetchImpl:async()=>{calls++;}}),/does not match/);assert.equal(calls,0);
});

test('approved physical provider-request budget cannot be exceeded by pagination',async()=>{
  let calls=0;const requestBudget={remaining:1,consumed:0};
  await assert.rejects(()=>fetchJquantsPages({endpoint:'/equities/bars/daily',query:{date:'2024-01-04'},apiKey:'fixture',requestBudget,fetchImpl:async()=>{calls++;return {ok:true,status:200,text:async()=>JSON.stringify({data:[1],pagination_key:'next'})};}}),/budget exhausted/);
  assert.equal(calls,1);assert.deepEqual(requestBudget,{remaining:0,consumed:1});
});
