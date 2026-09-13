import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {buildIntegratedInputs} from './phase57-capital-allocation-budget-envelope-ablation.mjs';
import {simulatePhaseB,executionAttribution,PHASE_B_SAFETY} from './lib/phase57-capital-allocation-v3-phase-b.mjs';
import {prepareValidationReadiness} from './phase57-capital-allocation-validation-runner.mjs';

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const digest=b=>createHash('sha256').update(b).digest('hex');
const args=argv=>{const x={};for(let i=0;i<argv.length;i+=2){if(!argv[i]?.startsWith('--')||argv[i+1]===undefined)throw Error('arguments require --key value pairs');x[argv[i].slice(2)]=argv[i+1];}for(const k of ['features-dir','model','block-a','block-b','bar5-pinned-report','output-dir'])if(!x[k])throw Error(`MISSING_ARG:${k}`);return x;};
const round=(x,d=6)=>Number.isFinite(x)?Number(x.toFixed(d)):x;
const writeJson=(dir,name,value)=>{const bytes=Buffer.from(JSON.stringify(value,null,2)+'\n');fs.writeFileSync(path.join(dir,name),bytes);fs.writeFileSync(path.join(dir,`${name}.sha256`),`${digest(bytes)}  ${name}\n`);};
const compact=arm=>{const {curve,closedTrades,decisions,ledgerTrace,dailyEquity,...summary}=arm;return {...summary,dailyEquity};};
const peak=(rows,value)=>[...rows].sort((a,b)=>value(b)-value(a)||a.timestamp.localeCompare(b.timestamp))[0];
const traceSummary=t=>({timestamp:t.timestamp,currentRealizedEquityJpy:t.currentRealizedEquityJpy,currentEquityJpy:t.currentEquityJpy,currentCashJpy:t.currentCashJpy,availableCashJpy:t.availableCashJpy,lockedShortCollateralJpy:t.lockedShortCollateralJpy,lockedLongCapitalJpy:t.lockedLongCapitalJpy,longNotionalJpy:t.longNotionalJpy,shortNotionalJpy:t.shortNotionalJpy,grossExposureJpy:t.grossExposureJpy,signedNetExposureJpy:t.signedNetExposureJpy,absoluteNetExposureJpy:t.absoluteNetExposureJpy,unrealizedPnlJpy:t.unrealizedPnlJpy,positionCount:t.positionCount,exitCashReleasedJpy:t.exitCashReleasedJpy,entryCashConsumedJpy:t.entryCashConsumedJpy,feesJpy:t.feesJpy,buyingPowerBeforeJpy:t.buyingPowerBeforeJpy,buyingPowerAfterJpy:t.buyingPowerAfterJpy,currentEquityBasis:t.currentEquityBasis,openPositions:t.openPositions,exits:t.exits,entries:t.entries,invariants:t.invariants});

function report(result){
  const f=x=>Number(x).toLocaleString(undefined,{maximumFractionDigits:6}),p=x=>`${(100*x).toFixed(4)}%`;
  const row=(label,t)=>`| ${label} | ${t.timestamp} | ¥${f(t.currentEquityJpy)} | ¥${f(t.currentCashJpy)} | ¥${f(t.lockedShortCollateralJpy)} | ¥${f(t.grossExposureJpy)} | ¥${f(t.signedNetExposureJpy)} | ${p(t.currentEquityBasis.grossRatio)} | ${p(t.currentEquityBasis.absoluteNetRatio)} | ${t.positionCount} |`;
  const day=result.peakEvents.worstDay.transactionTimestamps.map(t=>`| ${t.timestamp} | ¥${f(t.currentRealizedEquityJpy)} | ¥${f(t.currentEquityJpy)} | ¥${f(t.availableCashJpy)} | ¥${f(t.lockedShortCollateralJpy)} | ¥${f(t.longNotionalJpy)} | ¥${f(t.shortNotionalJpy)} | ¥${f(t.exitCashReleasedJpy)} | ¥${f(t.entryCashConsumedJpy)} | ¥${f(t.feesJpy)} | ${t.positionCount} |`).join('\n');
  return `# Phase57 Capital Allocation Ledger Audit and Candidate Freeze

Status: **DEVELOPMENT_PRIMARY_CANDIDATE_FROZEN / VALIDATION_READY**

## Ledger verdict

Ledger audit: **${result.ledgerAudit.status}**. Hidden leverage found: **${result.ledgerAudit.hiddenLeverageFound}**. Exposure is tested against current mark-to-market equity at every timestamp, not against the original JPY 1,000,000.

Under the inherited ledger contract, the cash-funded entry reference notional is itself the locked collateral; it is not a second additional charge. Required entry cash is reference notional plus the entry half-cost. SHORT sale proceeds are credited as JPY 0 and cannot increase buying power.

| Event | Timestamp | Current equity | Cash | Locked SHORT collateral | Gross | Signed net | Gross/equity | Abs net/equity | Positions |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
${row('MAX gross / max utilization',result.peakEvents.maxGross.trace)}
${row('MAX abs net',result.peakEvents.maxAbsoluteNet.trace)}

MAX gross exceeds initial capital by JPY ${f(result.peakEvents.maxGross.initialCapitalExcessJpy)}, but remains JPY ${f(result.peakEvents.maxGross.currentEquityHeadroomJpy)} below current equity. MAX abs net exceeds initial capital by JPY ${f(result.peakEvents.maxAbsoluteNet.initialCapitalExcessJpy)}, but remains JPY ${f(result.peakEvents.maxAbsoluteNet.currentEquityHeadroomJpy)} below current equity.

## Worst day trace: ${result.peakEvents.worstDay.sessionDate}

Worst-day return ${result.peakEvents.worstDay.returnPct.toFixed(6)}%. The complete all-timestamp trace is in JSON; transaction timestamps are shown below.

| Timestamp | Realized equity | Current equity | Available cash | Locked SHORT | LONG notional | SHORT notional | EXIT released | ENTRY consumed | Fees | Positions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
${day||'| No transaction timestamp | - | - | - | - | - | - | - | - | - | - |'}

## Twelve invariant gate

All ${result.ledgerAudit.invariantNames.length} invariants pass across ${result.ledgerAudit.auditedEventCount} audited arm-timestamps. This includes nonnegative cash, non-reused SHORT proceeds, buying power excluding unrealized gains, full SHORT reference-notional collateral, EXIT-before-ENTRY, current-equity exposure limits, one round-trip cost, position/lot constraints, and realized-equity reconciliation.

## Development roles frozen

- MAX_5: PRIMARY_DEVELOPMENT_CANDIDATE
- MAX_10: LEGACY_BUDGET_BASELINE
- MAX_3: AGGRESSIVE_DEVELOPMENT_REFERENCE
- Integrated primary: Frozen Minimal Hybrid v1 x MSH-Entry v1 x V3_B_RISK x MAX_5 x EXIT_V5_DYNAMIC_RECLAIM_BAR_5

MAX_5 to MAX_3 adds ${result.diminishingMarginalEdge.additionalTradeCount} trades contributing only JPY ${f(result.diminishingMarginalEdge.additionalTradeContributionJpy)} directly (JPY ${f(result.diminishingMarginalEdge.averagePerAdditionalTradeJpy)} per trade). The previously inferred JPY ${f(result.diminishingMarginalEdge.crossBaselineNewTradeContributionDifferenceJpy)} is not the direct 14-trade effect: JPY ${f(result.diminishingMarginalEdge.sharedPreviouslyAddedTradeSizeEffectJpy)} comes from larger quantities on 21 trades already accepted by MAX_5. This corrected decomposition is recorded as diminishing marginal edge, not a new selection threshold.

## Validation preparation

Validation runner and output schema are ready but locked. No fresh/OOS source was opened or measured. A separate hash-bound authorization contract is required before execution.

This is not OOS PASS, VALIDATION PASS, FINAL PASS or Production Ready. Main merge, Ready conversion, auto-merge, execution and paper/live orders remain prohibited.
`;
}

function main(){
  const a=args(process.argv.slice(2)),x=buildIntegratedInputs(a),make=(divisor,exit)=>simulatePhaseB({opportunities:x.paired,trades:x.eligible,allocationId:'V3_B_RISK',exitId:exit,barCloseAt:x.barCloseAt,marks:x.input.marks,maxPositions:10,budgetDivisor:divisor,lotSize:100,armId:`V3_B_RISK__${exit}__MAX_${divisor}`});
  const max10v4=make(10,'FROZEN_EXIT_V4'),max10v5=make(10,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'),max5v4=make(5,'FROZEN_EXIT_V4'),max5v5=make(5,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'),max3v4=make(3,'FROZEN_EXIT_V4'),max3v5=make(3,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5');
  assert.deepEqual([max5v4.finalEquityJpy,max5v4.netReturnPct,max5v4.portfolioProfitFactor,max5v4.maxDrawdown.maxDrawdownPct,max5v4.trade.accepted],[1212126.265,21.212626,3.900744,4.273109,49]);
  assert.deepEqual([max3v4.finalEquityJpy,max3v4.netReturnPct,max3v4.portfolioProfitFactor,max3v4.maxDrawdown.maxDrawdownPct,max3v4.trade.accepted],[1344231.6,34.42316,2.739732,6.379147,63]);
  assert.deepEqual([max5v5.finalEquityJpy,max5v5.netReturnPct,max5v5.trade.accepted],[1214425.715,21.442571,49]);
  const allAudited=[max10v4,max10v5,max5v4,max5v5,max3v4,max3v5];for(const arm of allAudited)assert.equal(arm.ledgerAudit.status,'LEDGER_INVARIANTS_PASS');
  const maxGross=peak(max3v4.ledgerTrace,t=>t.grossExposureJpy),maxAbs=peak(max3v4.ledgerTrace,t=>t.absoluteNetExposureJpy),maxUtil=peak(max3v4.ledgerTrace,t=>t.currentEquityBasis.grossRatio);assert.equal(maxGross.timestamp,'2026-08-07T04:25:00.000Z');assert.equal(maxAbs.timestamp,'2026-08-06T05:05:00.000Z');assert.equal(maxUtil.timestamp,maxGross.timestamp);assert.equal(maxGross.grossExposureJpy,1213950);assert.equal(maxAbs.absoluteNetExposureJpy,1115700);
  const worstDate=max3v4.worstDay.sessionDate;assert.equal(worstDate,'2026-07-24');const worstAll=max3v4.ledgerTrace.filter(t=>t.sessionDate===worstDate),worstTransactions=worstAll.filter(t=>t.exits.length||t.entries.length);assert.ok(worstAll.length>0);
  const marginal=executionAttribution(max5v4,max3v4,{label:'MAX_5_TO_MAX_3_DIMINISHING_MARGINAL_EDGE',leftName:max5v4.armId,rightName:max3v4.armId});assert.equal(marginal.rightOnlyTrades.count,14);assert.equal(marginal.leftOnlyTrades.count,0);
  const baseIds=new Set(max10v4.closedTrades.map(t=>t.eventId)),fiveById=new Map(max5v4.closedTrades.map(t=>[t.eventId,t])),threeById=new Map(max3v4.closedTrades.map(t=>[t.eventId,t])),sharedPreviouslyAdded=[...fiveById.keys()].filter(id=>!baseIds.has(id)&&threeById.has(id)),sharedPreviouslyAddedSizeEffect=sharedPreviouslyAdded.reduce((s,id)=>s+threeById.get(id).realizedPnlJpy-fiveById.get(id).realizedPnlJpy,0),crossBaselineNewTradeContributionDifference=81112.225-65641.95;assert.equal(sharedPreviouslyAdded.length,21);assert.ok(Math.abs(crossBaselineNewTradeContributionDifference-(sharedPreviouslyAddedSizeEffect+marginal.rightOnlyTrades.contributionToDeltaJpy))<1e-3);
  const freezeBytes=fs.readFileSync('predict/research/phase57-capital-allocation-integrated-candidate-freeze.json'),validation=prepareValidationReadiness();
  const invariantNames=max3v4.ledgerAudit.checks,auditedEventCount=allAudited.reduce((s,arm)=>s+arm.ledgerAudit.eventCount,0);
  const result={schemaVersion:1,schemaId:'PHASE57_CAPITAL_ALLOCATION_LEDGER_AUDIT_FREEZE_V1',status:'DEVELOPMENT_PRIMARY_CANDIDATE_FROZEN_VALIDATION_READY',evidenceRole:'EXPOSED_DEVELOPMENT_AUDIT_ONLY',ledgerAudit:{status:'LEDGER_AUDIT_PASS_NO_HIDDEN_LEVERAGE',hiddenLeverageFound:false,comparisonBasis:'CURRENT_MARK_TO_MARKET_EQUITY',auditedArmCount:allAudited.length,auditedEventCount,invariantNames,violationCount:0,max5AccountingParity:'PASS'},peakEvents:{maxGross:{trace:traceSummary(maxGross),initialCapitalExcessJpy:round(maxGross.grossExposureJpy-1000000),currentEquityHeadroomJpy:round(maxGross.currentEquityJpy-maxGross.grossExposureJpy)},maxAbsoluteNet:{trace:traceSummary(maxAbs),initialCapitalExcessJpy:round(maxAbs.absoluteNetExposureJpy-1000000),currentEquityHeadroomJpy:round(maxAbs.currentEquityJpy-maxAbs.absoluteNetExposureJpy)},maxUtilization:{trace:traceSummary(maxUtil)},worstDay:{sessionDate:worstDate,returnPct:max3v4.worstDay.returnPct,allTimestampCount:worstAll.length,allTimestamps:worstAll.map(traceSummary),transactionTimestamps:worstTransactions.map(traceSummary)}},developmentParity:{MAX_5_V4:compact(max5v4),MAX_3_V4:compact(max3v4),MAX_5_V5:compact(max5v5)},diminishingMarginalEdge:{comparison:'MAX_5_TO_MAX_3_V4',additionalTradeCount:marginal.rightOnlyTrades.count,additionalTradeContributionJpy:marginal.rightOnlyTrades.contributionToDeltaJpy,averagePerAdditionalTradeJpy:round(marginal.rightOnlyTrades.contributionToDeltaJpy/marginal.rightOnlyTrades.count),commonTradeSizeEffectJpy:marginal.commonTrades.deltaJpy,sharedPreviouslyAddedTradeCount:sharedPreviouslyAdded.length,sharedPreviouslyAddedTradeSizeEffectJpy:round(sharedPreviouslyAddedSizeEffect),crossBaselineNewTradeContributionDifferenceJpy:round(crossBaselineNewTradeContributionDifference),attributionCorrection:'THE_15470_275_CROSS_BASELINE_DIFFERENCE_INCLUDES_15433_3_SIZE_EFFECT_ON_21_MAX5_ACCEPTED_TRADES_AND_ONLY_36_975_DIRECT_PNL_FROM_14_NEW_TRADES',totalPnlDeltaJpy:marginal.totalDeltaJpy,recomposed:marginal.recomposed},freeze:{status:'DEVELOPMENT_PRIMARY_CANDIDATE_FROZEN',sha256:digest(freezeBytes),roles:{MAX_5:'PRIMARY_DEVELOPMENT_CANDIDATE',MAX_10:'LEGACY_BUDGET_BASELINE',MAX_3:'AGGRESSIVE_DEVELOPMENT_REFERENCE'},integratedCandidate:'FROZEN_MINIMAL_HYBRID_V1__MSH_ENTRY_V1__V3_B_RISK__MAX_5__EXIT_V5_DYNAMIC_RECLAIM_BAR_5'},validationReadiness:validation,claims:{oosOpened:false,validationMeasured:false,oosPass:false,validationPass:false,finalPass:false,productionReady:false},safety:PHASE_B_SAFETY};
  const review={schemaVersion:1,schemaId:'PHASE57_CAPITAL_ALLOCATION_LEDGER_AUDIT_REVIEW_PACKET_V1',status:'REVIEW_PACKET_PREPARED_NOT_REVIEWED',questions:['Do all cash, collateral, cost and realized-equity traces reconcile?','Are gross and absolute-net comparisons correctly based on current equity?','Is locked SHORT collateral correctly interpreted as entry reference notional under this research contract?','Is the no-hidden-leverage verdict supported?','Is MAX_5 freeze separated from Validation/OOS claims?'],result,safety:PHASE_B_SAFETY};
  fs.mkdirSync(a['output-dir'],{recursive:true});writeJson(a['output-dir'],'ledger-audit-freeze-result.json',result);writeJson(a['output-dir'],'ledger-audit-review-packet.json',review);const md=Buffer.from(report(result));fs.writeFileSync(path.join(a['output-dir'],'ledger-audit-freeze-report.md'),md);fs.writeFileSync(path.join(a['output-dir'],'ledger-audit-freeze-report.md.sha256'),`${digest(md)}  ledger-audit-freeze-report.md\n`);writeJson(a['output-dir'],'validation-runner-readiness.json',validation);
  if(a['committed-output-dir']){fs.mkdirSync(a['committed-output-dir'],{recursive:true});for(const name of ['ledger-audit-freeze-result.json','ledger-audit-review-packet.json','ledger-audit-freeze-report.md','validation-runner-readiness.json'])for(const suffix of ['', '.sha256'])fs.copyFileSync(path.join(a['output-dir'],`${name}${suffix}`),path.join(a['committed-output-dir'],`${name}${suffix}`));}
  console.log(JSON.stringify({status:result.status,ledgerAudit:result.ledgerAudit.status,maxGross:{timestamp:maxGross.timestamp,gross:maxGross.grossExposureJpy,currentEquity:maxGross.currentEquityJpy,ratio:maxGross.currentEquityBasis.grossRatio},maxAbsNet:{timestamp:maxAbs.timestamp,absNet:maxAbs.absoluteNetExposureJpy,currentEquity:maxAbs.currentEquityJpy,ratio:maxAbs.currentEquityBasis.absoluteNetRatio},worstDay:{sessionDate:worstDate,returnPct:max3v4.worstDay.returnPct},marginal:result.diminishingMarginalEdge,validation:validation.status}));
}

if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1]))main();
