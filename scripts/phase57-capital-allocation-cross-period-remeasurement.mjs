import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {replayFirstEnter} from './phase57-capital-allocation-v3-phase-a.mjs';
import {loadInputs} from './phase57-capital-allocation-v3-phase-b.mjs';
import {buildIntegratedInputs,budgetAttribution} from './phase57-capital-allocation-budget-envelope-ablation.mjs';
import {PHASE_B_POLICY,PHASE_B_SAFETY,simulatePhaseB,runBar5Adapter,executionAttribution,phaseBHashes} from './lib/phase57-capital-allocation-v3-phase-b.mjs';

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const digest=b=>createHash('sha256').update(b).digest('hex');
const round=(x,d=6)=>Number.isFinite(x)?Number(x.toFixed(d)):x;
const sum=xs=>xs.reduce((a,b)=>a+b,0);
const args=argv=>{const x={};for(let i=0;i<argv.length;i+=2){assert.ok(argv[i]?.startsWith('--')&&argv[i+1]!==undefined,'arguments require --key value pairs');x[argv[i].slice(2)]=argv[i+1];}for(const k of ['features-dir','model','block-a','block-b','bar5-pinned-report','old20-features-dir','old20-trades','old20-report','output-dir'])assert.ok(x[k],`MISSING_ARG:${k}`);return x;};
const direction=x=>x==='LONG'||x===1?1:-1;
const directionalReturnPct=(d,entry,exit)=>direction(d)*(Number(exit)/Number(entry)-1)*100;
const blockDates={A:['2026-06-18','2026-07-30'],B:['2026-07-31','2026-08-12'],OLD20:['2026-08-13','2026-09-09']};
const inRange=(date,[first,last])=>date>=first&&date<=last;
const compactArm=arm=>{const {curve,closedTrades,decisions,ledgerTrace,...summary}=arm;return summary;};
const safetyFalse=x=>Object.values(x).every(v=>v===false);

function subsetBase(base,id,range){
  const trades=base.eligible.filter(x=>inRange(x.sessionDate,range));
  const ids=new Set(trades.map(x=>x.eventId));
  const opportunities=base.paired.filter(x=>ids.has(x.eventId));
  const marks=base.input.marks.filter(x=>inRange(x.sessionDate,range));
  const dates=base.input.featureDates.filter(x=>inRange(x,range));
  return {id,role:id==='A'?'REPLAYABLE_DEVELOPMENT_BLOCK_A':'REPLAYABLE_DEVELOPMENT_BLOCK_B',range,dates,trades,opportunities,marks,barCloseAt:base.barCloseAt,allFirstEnterCount:opportunities.length,missingOutcomePathCount:0,parity:base.parity[id==='A'?'blockA':'blockB']};
}

function old20DecisionRows(trade,input){
  const rows=input.barsBySession.get(trade.sessionDate)?.get(trade.symbol)??[];
  return rows.filter(x=>Date.parse(x.availableAt)>Date.parse(trade.entryTimestamp)).sort((a,b)=>String(a.availableAt).localeCompare(String(b.availableAt))).map((bar,i)=>({baseScore:{state:{elapsedBars:i+1}},currentReturnPct:directionalReturnPct(trade.direction,trade.entryPrice,bar.close),timestamp:bar.availableAt}));
}

export function verifyOld20Bar5Parity(trades,barCloseAt){
  const counts={};let net=0;
  for(const trade of trades){
    const actual=runBar5Adapter(trade,{barCloseAt});
    const rows=(trade.management?.v4??[]).slice(0,5).map(x=>({elapsedBars:Number(x.baseScore.state.elapsedBars),currentReturnPct:Number(x.currentReturnPct),timestamp:x.timestamp}));
    const first=Number.isFinite(Number(trade?.entryQuality?.h1?.gross))
      ?Number(trade.entryQuality.h1.gross)/100
      :rows.find(x=>x.elapsedBars===1)?.currentReturnPct;
    assert.ok(Number.isFinite(first),`Old20 first completed-bar return ${trade.eventId}`);
    let expected=trade.v4,classification='FIRST_BAR_NON_ADVERSE_V4';
    if(first<0){
      if(rows.find(x=>x.elapsedBars>1&&x.currentReturnPct>=0))classification='RECOVERED_TO_V4';
      else {const bar5=rows.find(x=>x.elapsedBars===5);if(bar5){const price=barCloseAt(trade.symbol,bar5.timestamp);expected={...trade.v4,exitTimestamp:bar5.timestamp,exitPrice:price,netReturnPct:directionalReturnPct(trade.direction,trade.entryPrice,price)-PHASE_B_POLICY.roundTripCostPct};classification='DEFENSIVE_EXIT_BAR_5';}else classification='HORIZON_FALLBACK_V4';}
    }
    assert.equal(actual.classification,classification,`Old20 bar5 classification ${trade.eventId}`);
    assert.equal(actual.exitTimestamp,expected.exitTimestamp,`Old20 bar5 timestamp ${trade.eventId}`);
    assert.ok(Math.abs(actual.netReturnPct-expected.netReturnPct)<1e-10,`Old20 bar5 net ${trade.eventId}`);
    counts[classification]=(counts[classification]??0)+1;net+=actual.netReturnPct;
  }
  return {status:'OLD20_DIRECT_BAR5_PATH_PARITY_PASS',n:trades.length,netReturnPctPoints:round(net,12),stateCounts:counts,futureBarsAfterBar5Read:false,costAppliedExactlyOnce:true};
}

function buildOld20(a,model){
  const input=loadInputs(a['old20-features-dir'],{expectedSessionCount:20});
  assert.deepEqual(input.featureDates,[
    '2026-08-13','2026-08-14','2026-08-17','2026-08-18','2026-08-19','2026-08-20','2026-08-21','2026-08-24','2026-08-25','2026-08-26','2026-08-27','2026-08-28','2026-08-31','2026-09-01','2026-09-02','2026-09-03','2026-09-04','2026-09-07','2026-09-08','2026-09-09']);
  const sourceReport=read(a['old20-report']),rawTrades=read(a['old20-trades']);
  assert.equal(sourceReport.sessionCount,20);assert.equal(sourceReport.entryQuality.firstEnter,36);assert.equal(sourceReport.entryQuality.pairedFirstEnter,35);
  assert.equal(sourceReport.causal.minimumRequiredNeighbors,30);assert.ok(sourceReport.causal.minimumObservedNeighborCount>=30);assert.equal(sourceReport.causal.insufficientFallbacks,0);assert.equal(sourceReport.causal.pitViolations,0);
  assert.equal(rawTrades.length,35);assert.equal(new Set(rawTrades.map(x=>x.eventId)).size,35);
  const allOpps=replayFirstEnter(input.events,model,input.barsBySession),byOpp=new Map(allOpps.map(x=>[x.eventId,x])),byEvent=new Map(input.events.map(x=>[x.eventId,x]));
  assert.equal(allOpps.length,36,'Old20 frozen MSH First ENTER parity');
  const trades=rawTrades.map(t=>{const e=byEvent.get(t.eventId),o=byOpp.get(t.eventId);assert.ok(e&&o,`Old20 MSH join ${t.eventId}`);assert.equal(o.direction,direction(t.direction));assert.ok(Math.abs(Number(e.priceReference)-Number(t.entryPrice))<1e-9);const gross=directionalReturnPct(t.direction,t.entryPrice,t.v4.exitPrice);assert.ok(Math.abs(gross-PHASE_B_POLICY.roundTripCostPct-t.v4.netReturnPct)<1e-8,`Old20 v4 cost parity ${t.eventId}`);return {...t,entryPrice:Number(e.priceReference),causalEligible:true,management:{v4:old20DecisionRows(t,input)}};}).sort((x,y)=>x.entryTimestamp.localeCompare(y.entryTimestamp)||x.symbol.localeCompare(y.symbol));
  const ids=new Set(trades.map(x=>x.eventId)),opportunities=allOpps.filter(x=>ids.has(x.eventId)).map(o=>{
    const e=byEvent.get(o.eventId);assert.ok(Number(e?.priceReference)>0,`Old20 entry price ${o.eventId}`);
    return {...o,entryPrice:Number(e.priceReference)};
  });assert.equal(opportunities.length,35);
  const barCloseAt=(symbol,timestamp)=>input.closeLookup.get(`${timestamp.slice(0,10)}|${symbol}|${timestamp}`);
  const parity=verifyOld20Bar5Parity(trades,barCloseAt);
  return {id:'OLD20',role:'REPLAYABLE_EXPOSED_DIAGNOSTIC',range:blockDates.OLD20,dates:input.featureDates,trades,opportunities,marks:input.marks,barCloseAt,allFirstEnterCount:36,missingOutcomePathCount:1,parity,sourceReport};
}

export function measureReplayBlock(block){
  const make=(divisor,exit,armId)=>simulatePhaseB({opportunities:block.opportunities,trades:block.trades,allocationId:'V3_B_RISK',exitId:exit,barCloseAt:block.barCloseAt,marks:block.marks,maxPositions:10,budgetDivisor:divisor,lotSize:100,armId});
  const arms={
    MAX_5_V5:make(5,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5','MAX_5_V5'),
    MAX_10_V5:make(10,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5','MAX_10_V5'),
    MAX_3_V5:make(3,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5','MAX_3_V5'),
    MAX_5_V4:make(5,'FROZEN_EXIT_V4','MAX_5_V4'),
  };
  for(const arm of Object.values(arms)){assert.equal(arm.ledgerAudit.status,'LEDGER_INVARIANTS_PASS');assert.equal(arm.ledgerAudit.violationCount,0);assert.equal(arm.initialCapitalJpy,1_000_000);}
  const max10To5=budgetAttribution(arms.MAX_10_V5,arms.MAX_5_V5),max5To3=budgetAttribution(arms.MAX_5_V5,arms.MAX_3_V5);
  const exitBase=executionAttribution(arms.MAX_5_V4,arms.MAX_5_V5,{label:'MAX_5_V4_TO_V5',leftName:'MAX_5_V4',rightName:'MAX_5_V5'});
  const L=new Map(arms.MAX_5_V4.closedTrades.map(x=>[x.eventId,x])),R=new Map(arms.MAX_5_V5.closedTrades.map(x=>[x.eventId,x]));
  const common=[...L.keys()].filter(x=>R.has(x));
  const changed=common.filter(x=>L.get(x).exitTimestamp!==R.get(x).exitTimestamp||Math.abs(L.get(x).realizedPnlJpy-R.get(x).realizedPnlJpy)>1e-6);
  const early=common.filter(x=>Date.parse(R.get(x).exitTimestamp)<Date.parse(L.get(x).exitTimestamp));
  const dayPnl={};for(const x of arms.MAX_5_V5.closedTrades)dayPnl[x.entryTimestamp.slice(0,10)]=(dayPnl[x.entryTimestamp.slice(0,10)]??0)+x.realizedPnlJpy;
  const positiveDays=Object.entries(dayPnl).filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]);const positiveDayPnl=sum(positiveDays.map(([,v])=>v));
  const exitAttribution={...exitBase,defensiveTradesAccepted:arms.MAX_5_V5.closedTrades.filter(x=>x.exitReason==='DEFENSIVE_EXIT_BAR_5').length,changedOutcomeCount:changed.length,changedOutcomeEventIds:changed.sort(),earlyCashReleaseCount:early.length,earlyCashReleaseEventIds:early.sort(),additionalEntriesCausedByRecycling:exitBase.earlierExitCapitalReleaseAdditionalTrades.count,additionalEntryPnlJpy:exitBase.earlierExitCapitalReleaseAdditionalTrades.pnlJpy};
  return {block:block.id,role:block.role,dateRange:block.range,sessionCount:block.dates.length,eligibleCount:block.trades.length,firstEnterCount:block.allFirstEnterCount,missingOutcomePathCount:block.missingOutcomePathCount,bar5Parity:block.parity,inputHashes:phaseBHashes({opportunities:block.opportunities,trades:block.trades,marks:block.marks}),arms,attribution:{MAX_10_TO_MAX_5:max10To5,MAX_5_TO_MAX_3:max5To3,MAX_5_V4_TO_V5:exitAttribution},dayConcentration:{topPositiveDay:positiveDays[0]?{sessionDate:positiveDays[0][0],pnlJpy:round(positiveDays[0][1]),shareOfPositiveDayProfit:round(positiveDays[0][1]/positiveDayPnl)}:null,top3PositiveDayShare:positiveDayPnl?round(sum(positiveDays.slice(0,3).map(([,v])=>v))/positiveDayPnl):null}};
}

function mergeBlocks(id,a,b){const tradeIds=new Set(),trades=[];for(const t of [...a.trades,...b.trades]){assert.ok(!tradeIds.has(t.eventId),`duplicate merged trade ${t.eventId}`);tradeIds.add(t.eventId);trades.push(t);}return {id,role:'DESCRIPTIVE_LEAVE_ONE_BLOCK_DIAGNOSTIC',range:[a.range[0],b.range[1]],dates:[...a.dates,...b.dates],trades,opportunities:[...a.opportunities,...b.opportunities],marks:[...a.marks,...b.marks].sort((x,y)=>x.timestamp.localeCompare(y.timestamp)||x.symbol.localeCompare(y.symbol)),barCloseAt:(symbol,timestamp)=>a.barCloseAt(symbol,timestamp)??b.barCloseAt(symbol,timestamp),allFirstEnterCount:a.allFirstEnterCount+b.allFirstEnterCount,missingOutcomePathCount:a.missingOutcomePathCount+b.missingOutcomePathCount,parity:{status:'COMPOSED_FROM_INDIVIDUALLY_VERIFIED_BLOCKS'}};}

function metricRow(block,arm){const x=block.arms[arm];return {block:block.block,sessions:block.sessionCount,arm,returnPct:x.netReturnPct,profitFactor:x.portfolioProfitFactor,maxDrawdownPct:x.maxDrawdown.maxDrawdownPct,worstDay:x.worstDay,accepted:x.trade.accepted,eligible:block.eligibleCount,averageUtilization:x.capital.averageCapitalUtilization,maximumUtilization:x.capital.maximumCapitalUtilization};}
function fullMetric(arm,eligible){return {initialEquityJpy:arm.initialCapitalJpy,finalEquityJpy:arm.finalEquityJpy,netPnlJpy:arm.netPnlJpy,returnPct:arm.netReturnPct,profitFactor:arm.portfolioProfitFactor,maxDrawdownPct:arm.maxDrawdown.maxDrawdownPct,worstDay:arm.worstDay,eligible,accepted:arm.trade.accepted,belowLotSkips:arm.trade.rejectionCounts.TARGET_BUDGET_BELOW_100_SHARES??0,cashSkips:arm.accounting.cashInsufficientSkips,positionLimitSkips:arm.accounting.positionLimitSkips,winRate:arm.trade.winRate,averageTradePnlJpy:arm.trade.averagePnlJpy,medianTradePnlJpy:arm.trade.medianPnlJpy,averageWinJpy:arm.trade.averageWinJpy,averageLossJpy:arm.trade.averageLossJpy,averageWinLossRatio:arm.trade.averageWinLossRatio,averageHoldingMinutes:arm.trade.averageHoldingMinutes,averageUtilization:arm.capital.averageCapitalUtilization,maximumUtilization:arm.capital.maximumCapitalUtilization,averageGrossExposureJpy:arm.capital.averageGrossExposureJpy,maximumGrossExposureJpy:arm.capital.maximumGrossExposureJpy,averageAbsoluteNetExposureJpy:arm.capital.averageAbsoluteNetExposureJpy,maximumAbsoluteNetExposureJpy:arm.capital.maximumAbsoluteNetExposureJpy,maximumConcurrentPositions:arm.capital.maximumConcurrentPositions,longCapitalShare:arm.directionCapitalShare.long,shortCapitalShare:arm.directionCapitalShare.short,top1ProfitContribution:arm.profitContribution.top1,top3ProfitContribution:arm.profitContribution.top3,top1CapitalConcentration:arm.symbolConcentration.topSymbol,top3CapitalConcentration:arm.symbolConcentration.top3Share,ledgerAudit:arm.ledgerAudit};}

function markdown(result){
  const p=x=>`${x.toFixed(6)}%`,f=x=>typeof x==='number'?x.toLocaleString():String(x??'-'),pc=x=>x===null?'-':`${(x*100).toFixed(2)}%`;
  const rows=result.requiredTable.map(x=>`| ${x.block} | ${x.sessions} | ${x.arm} | ${p(x.returnPct)} | ${f(x.profitFactor)} | ${p(x.maxDrawdownPct)} | ${x.worstDay?.sessionDate??'-'} ${x.worstDay?p(x.worstDay.returnPct):''} | ${x.accepted} | ${x.eligible} | ${pc(x.averageUtilization)} | ${pc(x.maximumUtilization)} |`).join('\n');
  const summary=result.summaryTable.map(x=>`| ${x.dataset} | ${x.role} | ${x.sessions} | ${p(x.max5ReturnPct)} | ${f(x.max5ProfitFactor)} | ${p(x.max5MaxDrawdownPct)} | ${p(x.max10ReturnPct)} | ${p(x.max3ReturnPct)} |`).join('\n');
  const attr=[];for(const b of result.blockOrder){for(const key of ['MAX_10_TO_MAX_5','MAX_5_TO_MAX_3']){const x=result.blocks[b].attribution[key];attr.push(`| ${b} | ${key} | ¥${f(x.totalDeltaJpy)} | ¥${f(x.positionSizeEffect.pnlDeltaJpy)} (${x.positionSizeEffect.commonTradeCount}) | ¥${f(x.newTradeEffect.pnlJpy)} (${x.newTradeEffect.count}) | ¥${f(x.cashRecyclingEffect.pnlJpy)} (${x.cashRecyclingEffect.count}) | ¥${f(x.otherExecutionSetEffect.pnlJpy)} (${x.otherExecutionSetEffect.count}) |`);}}
  const exits=result.blockOrder.map(b=>{const x=result.blocks[b],a=x.arms.MAX_5_V4,c=x.arms.MAX_5_V5,d=x.attribution.MAX_5_V4_TO_V5;return `| ${b} | ${p(a.returnPct)} | ${p(c.returnPct)} | ¥${f(d.totalDeltaJpy)} | ${d.defensiveTradesAccepted} | ${d.changedOutcomeCount} | ${d.earlyCashReleaseCount} | ${d.additionalEntriesCausedByRecycling} / ¥${f(d.additionalEntryPnlJpy)} |`;}).join('\n');
  return `# Phase57 Historical Re-measurement / Cross-Period Robustness\n\nStatus: **HISTORICAL_REMEASUREMENT_COMPLETE — USED/EXPOSED DATA, NOT OOS OR VALIDATION**\n\nThe frozen integrated system was replayed without parameter changes. No reserved 2026-09-10 through 2026-10-21 session was accessed.\n\n## Main comparison\n\n| Block | Sessions | Arm | Return | PF | MaxDD | Worst day | Accepted | Eligible | Avg util | Max util |\n| --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |\n${rows}\n\n## Cross-period summary\n\n| Dataset | Role | Sessions | MAX_5 v5 Return | PF | MaxDD | MAX_10 Return | MAX_3 Return |\n| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |\n${summary}\n\n## Budget attribution\n\n| Block | Comparison | Total | Common size | New trade | Cash recycling | Other set |\n| --- | --- | ---: | ---: | ---: | ---: | ---: |\n${attr.join('\n')}\n\n## Frozen EXIT comparison at MAX_5\n\n| Block | v4 Return | v5 Return | PnL delta | Defensive accepted | Changed outcomes | Earlier exits | Recycling additions |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n${exits}\n\n## Interpretation\n\n- Positive MAX_5 return in every replayable block: ${result.robustnessQuestions.positiveReturnEveryBlock}\n- PF above 1 in every replayable block: ${result.robustnessQuestions.profitFactorAboveOneEveryBlock}\n- MAX_5 return above MAX_10 in every block: ${result.robustnessQuestions.max5ReturnAboveMax10EveryBlock}\n- MAX_3 return above MAX_5 in every block: ${result.robustnessQuestions.max3ReturnAboveMax5EveryBlock}\n- SHORT capital share above 50% in every block: ${result.robustnessQuestions.shortHeavyEveryBlock}\n- v5 PnL above v4 in every block: ${result.robustnessQuestions.v5PositiveDeltaEveryBlock}\n\nExact arm metrics, symbol/day concentration, all attributions, ledger audits, and descriptive leave-one-block combinations are preserved in the JSON evidence. This diagnostic does not reopen Development, promote MAX_3, validate the candidate, or authorize execution.\n`;
}

function write(dir,name,value){const bytes=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value,null,2)+'\n');fs.writeFileSync(path.join(dir,name),bytes);fs.writeFileSync(path.join(dir,`${name}.sha256`),`${digest(bytes)}  ${name}\n`);}

export function runCrossPeriodRemeasurement(a){
  assert.ok(safetyFalse(PHASE_B_SAFETY));
  const base=buildIntegratedInputs(a),model=JSON.parse(base.modelBytes),A=subsetBase(base,'A',blockDates.A),B=subsetBase(base,'B',blockDates.B),OLD20=buildOld20(a,model),AB=mergeBlocks('A+B',A,B);
  AB.role='REPLAYABLE_DEVELOPMENT';AB.parity={status:'BAR5_PARITY_PASS',A:base.parity.blockA,B:base.parity.blockB};
  assert.equal(A.dates.length,30);assert.equal(B.dates.length,8);assert.equal(A.trades.length,51);assert.equal(B.trades.length,34);assert.equal(AB.trades.length,85);assert.equal(OLD20.trades.length,35);
  const raw={A:measureReplayBlock(A),B:measureReplayBlock(B),OLD20:measureReplayBlock(OLD20),'A+B':measureReplayBlock(AB)};
  const development=read('predict/research/phase57-capital-allocation-budget-envelope-evidence/budget-envelope-result.json');
  const parityPairs=[['MAX_5_V5','MAX_5_V5'],['MAX_10_V5','MAX_10'],['MAX_3_V5','MAX_3_V5'],['MAX_5_V4','MAX_5']];
  for(const [current,prior] of parityPairs){const x=raw['A+B'].arms[current],y=development.arms[prior];for(const key of ['finalEquityJpy','netPnlJpy','netReturnPct','portfolioProfitFactor'])assert.deepEqual(x[key],y[key],`A+B ${current} ${key} parity`);assert.deepEqual(x.maxDrawdown.maxDrawdownPct,y.maxDrawdown.maxDrawdownPct);assert.equal(x.trade.accepted,y.trade.accepted);}
  const blockOrder=['A','B','OLD20','A+B'],blocks=Object.fromEntries(blockOrder.map(id=>{const x=raw[id];return [id,{...x,arms:Object.fromEntries(Object.entries(x.arms).map(([k,v])=>[k,fullMetric(v,x.eligibleCount)]))}];}));
  const requiredTable=blockOrder.flatMap(id=>['MAX_5_V5','MAX_10_V5','MAX_3_V5','MAX_5_V4'].map(arm=>metricRow(raw[id],arm)));
  const summaryTable=blockOrder.map(id=>{const x=raw[id];return {dataset:id,role:x.role,sessions:x.sessionCount,max5ReturnPct:x.arms.MAX_5_V5.netReturnPct,max5ProfitFactor:x.arms.MAX_5_V5.portfolioProfitFactor,max5MaxDrawdownPct:x.arms.MAX_5_V5.maxDrawdown.maxDrawdownPct,max10ReturnPct:x.arms.MAX_10_V5.netReturnPct,max3ReturnPct:x.arms.MAX_3_V5.netReturnPct};});
  const independent=['A','B','OLD20'].map(id=>raw[id]),robustnessQuestions={positiveReturnEveryBlock:independent.every(x=>x.arms.MAX_5_V5.netReturnPct>0),profitFactorAboveOneEveryBlock:independent.every(x=>Number(x.arms.MAX_5_V5.portfolioProfitFactor)>1),drawdownToReturnByBlock:Object.fromEntries(independent.map(x=>[x.block,round(x.arms.MAX_5_V5.maxDrawdown.maxDrawdownPct/x.arms.MAX_5_V5.netReturnPct)])),max5ReturnAboveMax10EveryBlock:independent.every(x=>x.arms.MAX_5_V5.netReturnPct>x.arms.MAX_10_V5.netReturnPct),max5AcceptedAtLeastMax10EveryBlock:independent.every(x=>x.arms.MAX_5_V5.trade.accepted>=x.arms.MAX_10_V5.trade.accepted),shortHeavyEveryBlock:independent.every(x=>x.arms.MAX_5_V5.directionCapitalShare.short>.5),v5PositiveDeltaEveryBlock:independent.every(x=>x.attribution.MAX_5_V4_TO_V5.totalDeltaJpy>0),max3ReturnAboveMax5EveryBlock:independent.every(x=>x.arms.MAX_3_V5.netReturnPct>x.arms.MAX_5_V5.netReturnPct),max3RiskCostByBlock:Object.fromEntries(independent.map(x=>[x.block,{returnDeltaPctPoints:round(x.arms.MAX_3_V5.netReturnPct-x.arms.MAX_5_V5.netReturnPct),maxDrawdownDeltaPctPoints:round(x.arms.MAX_3_V5.maxDrawdown.maxDrawdownPct-x.arms.MAX_5_V5.maxDrawdown.maxDrawdownPct),maximumUtilizationDelta:round(x.arms.MAX_3_V5.capital.maximumCapitalUtilization-x.arms.MAX_5_V5.capital.maximumCapitalUtilization)}])),profitByBlock:Object.fromEntries(independent.map(x=>[x.block,x.arms.MAX_5_V5.netPnlJpy]))};
  const combos={};for(const block of [mergeBlocks('A+OLD20',A,OLD20),mergeBlocks('B+OLD20',B,OLD20)]){const arm=simulatePhaseB({opportunities:block.opportunities,trades:block.trades,allocationId:'V3_B_RISK',exitId:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5',barCloseAt:block.barCloseAt,marks:block.marks,maxPositions:10,budgetDivisor:5,lotSize:100,armId:'MAX_5_V5'});combos[block.id]={role:block.role,sessions:block.dates.length,dateRange:block.range,eligible:block.trades.length,MAX_5_V5:fullMetric(arm,block.trades.length)};}
  const inventory=[
    {block:'A',dateRange:blockDates.A,sessions:30,originalRole:'EXIT_BLOCK_A_AND_INTEGRATED_DEVELOPMENT',selectorExposure:'FROZEN_SELECTOR_ALREADY_SELECTED',entryExposure:'FROZEN_ENTRY_REPLAY_NOT_TUNED_ON_A',exitExposure:'USED_FOR_EXIT_V4_V5_DESIGN_AND_SELECTION',allocationExposure:'USED_FOR_MAX_5_SELECTION_AS_PART_OF_A+B',outcomesViewed:true,causalEligible:true,completeReplay:true,classification:'REPLAYABLE_DEVELOPMENT'},
    {block:'B',dateRange:blockDates.B,sessions:8,originalRole:'EXIT_BLOCK_B_AND_INTEGRATED_DEVELOPMENT',selectorExposure:'FROZEN_SELECTOR_ALREADY_SELECTED',entryExposure:'FROZEN_ENTRY_REPLAY_NOT_TUNED_ON_B',exitExposure:'USED_FOR_EXIT_V5_SELECTION',allocationExposure:'USED_FOR_MAX_5_SELECTION_AS_PART_OF_A+B',outcomesViewed:true,causalEligible:true,completeReplay:true,classification:'REPLAYABLE_DEVELOPMENT'},
    {block:'OLD20',dateRange:blockDates.OLD20,sessions:20,originalRole:'DEVELOPMENT_DIAGNOSTIC_ONLY_NON_PROSPECTIVE',selectorExposure:'FROZEN_SELECTOR_ALREADY_SELECTED',entryExposure:'OUTCOMES_VIEWED_FOR_ENTRY_QUALITY_DIAGNOSTIC',exitExposure:'OUTCOMES_VIEWED_FOR_V3_V4_DIAGNOSTIC_NOT_V5_SELECTION',allocationExposure:'NOT_USED_FOR_MAX_5_SELECTION',outcomesViewed:true,causalEligible:true,completeReplay:true,classification:'REPLAYABLE_EXPOSED_DIAGNOSTIC',note:'36 First ENTER; 35 have a complete intraday outcome path and are portfolio eligible.'},
    {block:'PRE_2026_06_19',dateRange:['2024-09-10','2026-06-18'],originalRole:'MIXED_USED_EXPOSED_PROTECTED_HISTORY',outcomesViewed:'MIXED',causalEligible:false,completeReplay:false,classification:'CAUSALLY_INELIGIBLE',reason:'Frozen EXIT requires 30 prior fully-realized analogs; future 2026 analogs are not backfilled.'},
    {block:'ENTRY_FRESH_RESERVE',dateRange:['2026-09-10','2026-10-21'],sessions:26,originalRole:'RESERVED_ENTRY_VALIDATION_PURGE_OOS',outcomesViewed:false,causalEligible:'NOT_ACCESSED',completeReplay:false,classification:'NOT_REPLAYABLE',reason:'Existing reservation contract; no access in this task.'}
  ];
  const result={schemaVersion:1,schemaId:'PHASE57_CAPITAL_ALLOCATION_CROSS_PERIOD_REMEASUREMENT_V1',status:'HISTORICAL_REMEASUREMENT_COMPLETE',classification:'CROSS_PERIOD_ROBUSTNESS_DIAGNOSTIC',evidenceRole:'USED_AND_EXPOSED_HISTORICAL_REPLAY_NOT_OOS_NOT_VALIDATION',frozenSystem:{selector:'FROZEN_MINIMAL_HYBRID_V1',entry:'MSH_ENTRY_V1_STRICT_GT_0_60_NO_REPEAT',allocation:'V3_B_RISK',risk:'7_COMPLETED_5M_CLOSES_6_LOG_RETURNS_POPULATION_SD',primaryBudget:'MAX_5',primaryExit:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5',initialCapitalJpy:1_000_000,lotSizeShares:100,maximumConcurrentPositions:10,eventOrder:PHASE_B_POLICY.eventOrder,roundTripCostPct:.05,candidateFreezeSha256:'0eda85ade4b16871229edb34f7c24e094c1398878277c0786b910d3fb53e26aa'},sourceProvenance:{model:{workflowRun:34292703804,artifactId:10084158820,modelSha256:'f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a'},blockA:{featureRun:34580109870,outcomeRun:34689621795,outcomeArtifactId:10297193220,outcomeArchiveSha256:'80f4ae315576abd4e13604f2b4271cbe1033ca6883221b65ae700bfff9422a62'},blockB:{workflowRun:34653714314,outcomeArtifactId:10286251638,outcomeArchiveSha256:'408efa60287e52c22890f2d558fce12d3135ab6997b2d10dedeea60874ec8521'},bar5DevelopmentFinal:{workflowRun:34691691199,artifactId:10297810131,archiveSha256:'179a9715d61a3152227393ab1fe08a81b0d05481872ebd46312d3bc5028f70ef'},old20:{featureRuns:[34494213877,34541503697],featureArtifactArchiveSha256:['2ab8d18aea65eb8ade779495ac7db99166cde7b2fdb2cea70d8574cf1bd772b3','abd95a5aa4b030d39e00648645357ca28f238e9ce90e05da8cd0e31adc59a218','6991573ed52545e2cf8e44252babf0b7f2bfc6ed7fd149a94ca2b651466e6248','d044f1e00794fc2f66a2501c9e7b233b1bf3033206e5390f966a30ebfe717ce1','7c1c0196169ed82581e641c4a216c12d53cf4c1422eeedea1f15e22e819939a9','bcce77a21ae5a222c283ff0d3932047fdcc86adc4a776b62ae58d6e8f2209a22','af0c0318779d40feb0e40aa3d1b25c7252050d5c5467e22842e9c9e38a10c964','56fc1ff0b094d0988a12f11bfbfc3faaef9e09b5aa0abe5d34abbd053c905180'],outcomeRun:34541503697,outcomeArtifactId:10178728601,outcomeArchiveSha256:'308738971814c2d6c54101e101153fbc64af64e29030b317f78fee1a5de0551e'}},inventory,blockOrder,requiredTable,summaryTable,blocks,leaveOneBlockDiagnostic:combos,robustnessQuestions,aPlusBReferenceParity:'PASS',interpretation:{retuningPerformed:false,winnerSelectionPerformed:false,max3Promoted:false,oosClaim:false,validationClaim:false,finalPass:false,productionReady:false},safety:PHASE_B_SAFETY};
  assert.ok(safetyFalse(result.safety));return {result,full:{...result,blocks:raw}};
}

function main(){const a=args(process.argv.slice(2)),{result,full}=runCrossPeriodRemeasurement(a);fs.mkdirSync(a['output-dir'],{recursive:true});write(a['output-dir'],'cross-period-remeasurement-result.json',result);write(a['output-dir'],'cross-period-remeasurement-full-evidence.json',full);write(a['output-dir'],'cross-period-remeasurement-report.md',Buffer.from(markdown(result)));if(a['committed-output-dir']){fs.mkdirSync(a['committed-output-dir'],{recursive:true});for(const name of ['cross-period-remeasurement-result.json','cross-period-remeasurement-report.md'])for(const suffix of ['', '.sha256'])fs.copyFileSync(path.join(a['output-dir'],`${name}${suffix}`),path.join(a['committed-output-dir'],`${name}${suffix}`));}console.log(JSON.stringify({status:result.status,classification:result.classification,summary:result.summaryTable,robustness:result.robustnessQuestions}));}
if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1]))main();
