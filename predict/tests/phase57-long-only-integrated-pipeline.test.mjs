import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {assembleLongOnlyL0Rows,normalizeAndAggregateMinuteRows,createIntegratedResearchDataset} from '../long-only/phase57-long-only-integrated-dataset.js';
import {buildCausalL1Features,buildEvaluatorOnlyL1Label,evaluateEarlyWinnerDiscovery} from '../long-only/phase57-long-only-l1-labels-features.js';
import {compareLongOnlyIntegratedSystems,COMPARISON_STAGES} from '../long-only/phase57-long-only-integrated-comparison.js';
import {acquireFormalL0Session,fetchJquantsPages} from '../long-only/phase57-long-only-jquants-client.js';
import {replayLongOnlyIntegratedStages} from '../long-only/phase57-long-only-replay-interface.js';

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
  const label=buildEvaluatorOnlyL1Label({sessionDate:'2024-01-04',symbol:'11110',decisionTimeJst:'09:30',bars5m:bars,previousAdjustedClose:100});
  assert.equal(feature.latestAvailableAtJst,'2024-01-04T09:30:00+09:00');assert.equal(feature.currentPrice,108);assert.equal(label.evaluatorOnly,true);assert.equal(label.futureBarCount,1);
  for(const forbidden of ['winner','remainingUpsidePct','futureMfePct','futureMaePct','finalReturnPct'])assert.equal(forbidden in feature,false);
  const k=`${feature.sessionDate}|${feature.symbol}|${feature.decisionTimeJst}`,summary=evaluateEarlyWinnerDiscovery({features:[feature],evaluatorOnlyLabels:[label],detectedKeys:[k]});
  assert.equal(summary.detectedWinnerCount,1);assert.equal(summary.earlyWinnerRecallPct,100);
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

const system=(sessions,cost,net,ddEnd)=>({evaluationSessions:sessions,costModelSha256:cost,initialCashJpy:100000,stages:Object.fromEntries(COMPARISON_STAGES.map(stage=>[stage,{trades:[{side:'LONG',accountType:'CASH_EQUITY',quantity:100,leverage:1,symbol:'11110',sector:'TECH',entryAt:'2024-01-04T09:30:00+09:00',exitAt:'2024-01-04T10:00:00+09:00',entryPrice:1000,exitPrice:1000+net/100,netPnlJpy:net}],equityCurve:[{equityJpy:100000,investedJpy:50000},{equityJpy:ddEnd,investedJpy:0}],opportunityCount:2,missedOpportunityCount:1}]))});

test('integrated harness enforces same window/cost and proves zero short or margin',()=>{
  const sessions=['2024-01-04'],cost='a'.repeat(64),baseline=system(sessions,cost,1000,101000),candidate=system(sessions,cost,2000,102000);
  const result=compareLongOnlyIntegratedSystems({evaluationSessions:sessions,costModelSha256:cost,baseline,candidate});
  assert.equal(result.pass,true);assert.equal(result.proof.candidateShortTrades,0);assert.equal(result.proof.cashLedgerAudit.cashNeverNegative,true);assert.equal(Object.keys(result.stages).length,4);
  const bad=structuredClone(candidate);bad.stages.FULL_INTEGRATED_PORTFOLIO.trades[0].side='SHORT';assert.throws(()=>compareLongOnlyIntegratedSystems({evaluationSessions:sessions,costModelSha256:cost,baseline,candidate:bad}),/SHORT/);
});

test('J-Quants pagination is reusable but formal acquisition fails before any network call when gate is blocked',async()=>{
  let calls=0;const pages=[{data:[1],pagination_key:'next'},{data:[2]}];
  const fetched=await fetchJquantsPages({endpoint:'/equities/bars/daily',query:{date:'2024-01-04'},apiKey:'fixture',fetchImpl:async()=>{const payload=pages[calls++];return {ok:true,status:200,text:async()=>JSON.stringify(payload)};}});
  assert.equal(fetched.pageCount,2);assert.equal(calls,2);
  calls=0;const plan=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
  await assert.rejects(()=>acquireFormalL0Session({plan,authorization:{},partition:'DEVELOPMENT_A',sessionDate:'2024-01-04',apiKey:'fixture',fetchImpl:async()=>{calls++;}}),/does not match/);assert.equal(calls,0);
});
