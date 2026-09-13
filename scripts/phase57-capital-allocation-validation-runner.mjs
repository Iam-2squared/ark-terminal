import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {simulatePhaseB,executionAttribution,PHASE_B_SAFETY} from './lib/phase57-capital-allocation-v3-phase-b.mjs';
import {budgetAttribution} from './phase57-capital-allocation-budget-envelope-ablation.mjs';

const CONTRACT_PATH='predict/research/phase57-capital-allocation-validation-contract.json';
const FREEZE_PATH='predict/research/phase57-capital-allocation-integrated-candidate-freeze.json';
const PRECOMMIT_PATH='predict/research/phase57-capital-allocation-future-integrated-oos-precommit.json';
const SCHEMA_PATH='predict/research/phase57-capital-allocation-validation-output-schema.json';
const START_DATE='2026-10-22';
const REQUIRED_SESSION_COUNT=20;
const ELIGIBILITY_RULE_ID='FIRST_20_CHRONOLOGICALLY_ELIGIBLE_SESSIONS_FROM_2026_10_22_V1';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const digest=b=>createHash('sha256').update(b).digest('hex');
const parseArgs=argv=>{const x={};for(let i=0;i<argv.length;i+=2){if(!argv[i]?.startsWith('--')||argv[i+1]===undefined)throw Error('arguments require --key value pairs');x[argv[i].slice(2)]=argv[i+1];}return x;};
const writeJson=(dir,name,value)=>{const bytes=Buffer.from(JSON.stringify(value,null,2)+'\n');fs.writeFileSync(path.join(dir,name),bytes);fs.writeFileSync(path.join(dir,`${name}.sha256`),`${digest(bytes)}  ${name}\n`);};

export const INTEGRATED_OOS_ARMS=Object.freeze({
  primary:Object.freeze({role:'PRIMARY_INTEGRATED_OOS_CANDIDATE',budgetDivisor:3,exitId:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'}),
  conservativeSub:Object.freeze({role:'CONSERVATIVE_INTEGRATED_SUB_CANDIDATE',budgetDivisor:5,exitId:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'}),
  legacyBaseline:Object.freeze({role:'LEGACY_BUDGET_BASELINE',budgetDivisor:10,exitId:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'}),
  exitComparator:Object.freeze({role:'PRIMARY_BUDGET_EXIT_COMPARATOR',budgetDivisor:3,exitId:'FROZEN_EXIT_V4'}),
});

function sourceDate(value){return String(value?.sessionDate??value?.decisionTimestamp??value?.entryTimestamp??value?.timestamp??'').slice(0,10);}
function assertSafetyFalse(safety){for(const [name,value] of Object.entries(PHASE_B_SAFETY)){assert.equal(value,false,`${name} must remain false`);assert.equal(safety?.[name],false,`${name} contract must remain false`);}}
function loadGovernance(){
  const contractBytes=fs.readFileSync(CONTRACT_PATH),freezeBytes=fs.readFileSync(FREEZE_PATH),precommitBytes=fs.readFileSync(PRECOMMIT_PATH),schemaBytes=fs.readFileSync(SCHEMA_PATH);
  return {contractBytes,freezeBytes,precommitBytes,schemaBytes,contract:JSON.parse(contractBytes),freeze:JSON.parse(freezeBytes),precommit:JSON.parse(precommitBytes),schema:JSON.parse(schemaBytes)};
}

function compact(arm,sourceIdentity){
  const {curve,closedTrades,decisions,ledgerTrace,...summary}=arm;
  const dates=sourceIdentity.sessionIds;
  return {...summary,validationMetrics:{
    dateRange:{start:dates[0],end:dates.at(-1)},eligibleSessionCount:dates.length,
    initialEquityJpy:arm.initialCapitalJpy,finalEquityJpy:arm.finalEquityJpy,netPnlJpy:arm.netPnlJpy,returnPct:arm.netReturnPct,
    portfolioProfitFactor:arm.portfolioProfitFactor,maxDrawdownPct:arm.maxDrawdown.maxDrawdownPct,worstDay:arm.worstDay,
    eligibleOpportunities:arm.trade.candidates,acceptedTrades:arm.trade.accepted,
    belowLotSkip:arm.trade.rejectionCounts.TARGET_BUDGET_BELOW_100_SHARES??0,
    cashInsufficientSkip:arm.accounting.cashInsufficientSkips,positionLimitSkip:arm.accounting.positionLimitSkips,
    winRate:arm.trade.winRate,averageTradePnlJpy:arm.trade.averagePnlJpy,medianTradePnlJpy:arm.trade.medianPnlJpy,
    averageWinJpy:arm.trade.averageWinJpy,averageLossJpy:arm.trade.averageLossJpy,averageWinLossRatio:arm.trade.averageWinLossRatio,
    averageHoldingMinutes:arm.trade.averageHoldingMinutes,
    averageCapitalUtilization:arm.capital.averageCapitalUtilization,maximumCapitalUtilization:arm.capital.maximumCapitalUtilization,
    averageGrossExposureJpy:arm.capital.averageGrossExposureJpy,maximumGrossExposureJpy:arm.capital.maximumGrossExposureJpy,
    averageAbsoluteNetExposureJpy:arm.capital.averageAbsoluteNetExposureJpy,maximumAbsoluteNetExposureJpy:arm.capital.maximumAbsoluteNetExposureJpy,
    maximumConcurrentPositions:arm.capital.maximumConcurrentPositions,longCapitalShare:arm.directionCapitalShare.long,shortCapitalShare:arm.directionCapitalShare.short,
    top1ProfitContribution:arm.profitContribution.top1,top3ProfitContribution:arm.profitContribution.top3,
    top1CapitalConcentration:arm.symbolConcentration.topSymbol,top3CapitalConcentration:arm.symbolConcentration.top3Share,
  }};
}

function assertFrozenGovernance(g){
  assert.equal(g.contract.status,'FUTURE_INTEGRATED_OOS_PRECOMMITTED_NOT_OPENED');
  assert.equal(g.contract.validationOpened,false);assert.equal(g.contract.runnerExecutionUnlocked,false);
  assert.equal(g.freeze.status,'DEVELOPMENT_MAIN_MAX_3_FROZEN');assert.equal(g.freeze.candidate.budgetEnvelope,'MAX_3');assert.equal(g.freeze.candidate.exit,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5');
  assert.equal(g.contract.integratedCandidateFreezeSha256,digest(g.freezeBytes),'contract candidate freeze hash mismatch');
  assert.equal(g.precommit.status,'FUTURE_INTEGRATED_OOS_PRECOMMITTED_OOS_NOT_OPENED');assert.equal(g.precommit.candidateFreezeSha256,digest(g.freezeBytes),'precommit candidate freeze hash mismatch');
  assert.equal(g.precommit.window.notBeforeSessionDate,START_DATE);assert.equal(g.precommit.window.targetEligibleMarketSessions,REQUIRED_SESSION_COUNT);assert.equal(g.precommit.eligibilityRule.id,ELIGIBILITY_RULE_ID);
  assert.equal(g.precommit.dataAccessAttestation.future2026_10_22PlusFetched,false);assert.equal(g.precommit.dataAccessAttestation.future2026_10_22PlusOpened,false);assert.equal(g.precommit.dataAccessAttestation.future2026_10_22PlusMeasured,false);assert.equal(g.precommit.dataAccessAttestation.reserved2026_09_10Through2026_10_21Consumed,false);assert.deepEqual(g.precommit.dataAccessAttestation.sessionIds,[]);assert.equal(g.precommit.dataAccessAttestation.inputBundleSha256,null);
  assert.equal(g.schema.$id,'PHASE57_CAPITAL_ALLOCATION_INTEGRATED_OOS_RESULT_V2');assertSafetyFalse(g.freeze.safety);assertSafetyFalse(g.precommit.safety);assertSafetyFalse(g.contract.safety);
}

export function prepareIntegratedOosReadiness(){
  const g=loadGovernance();assertFrozenGovernance(g);
  return {schemaVersion:2,schemaId:'PHASE57_CAPITAL_ALLOCATION_INTEGRATED_OOS_RUNNER_READINESS_V2',status:'FUTURE_INTEGRATED_OOS_PRECOMMITTED_OOS_NOT_OPENED',executionPerformed:false,futureOutcomeDataRead:false,reservedEntryBlockRead:false,candidateFreezeSha256:digest(g.freezeBytes),precommitSha256:digest(g.precommitBytes),contractSha256:digest(g.contractBytes),outputSchemaSha256:digest(g.schemaBytes),arms:INTEGRATED_OOS_ARMS,window:g.precommit.window,gate:{separateHashBoundUnlockRequired:true,inputBundleRequired:true,exactlyTwentyEligibleSessionsRequired:true,developmentOrExposedBundlesRejected:true},safety:PHASE_B_SAFETY};
}

function assertSourceIdentity(bundle){
  const source=bundle.sourceIdentity??{},ids=source.sessionIds??[],ledger=source.sessionEligibilityLedger??[];
  assert.ok(source.integratedOosSourceId,'integrated OOS source identity required');assert.equal(source.pointInTimeAttestation,true);assert.equal(source.unopenedBeforeAuthorizationAttestation,true);assert.equal(source.causalEligibilityAttestation,true);assert.equal(source.eligibilityRuleId,ELIGIBILITY_RULE_ID);
  assert.equal(ids.length,REQUIRED_SESSION_COUNT,'exactly 20 eligible sessions required');assert.equal(new Set(ids).size,REQUIRED_SESSION_COUNT,'session IDs must be unique');assert.deepEqual(ids,[...ids].sort(),'session IDs must be chronological');assert.ok(ids[0]>=START_DATE,'future integrated OOS starts 2026-10-22');assert.ok(ids.every(d=>d>'2026-10-21'),'reserved Entry block must not be consumed');
  assert.ok(Array.isArray(ledger)&&ledger.length>=REQUIRED_SESSION_COUNT,'session eligibility ledger required');const eligible=ledger.filter(x=>x.eligible===true).map(x=>x.sessionDate);assert.deepEqual(eligible,ids,'eligibility ledger must identify exactly the selected sessions');assert.ok(ledger.filter(x=>x.eligible===false).every(x=>x.reason&&x.sourceAvailabilityStatus),'excluded sessions require an objective reason and source status');
  const forbidden=/BLOCK_A|BLOCK_B|OLD20|DIAGNOSTIC20|DEVELOPMENT|EXPOSED/i;assert.equal(forbidden.test(String(source.integratedOosSourceId)),false,'Development/exposed bundle rejected');
  return source;
}

export function measureAuthorizedIntegratedOosBundle(bundle,{inputBundleSha256,unlock}={}){
  const g=loadGovernance();assertFrozenGovernance(g);const freezeSha=digest(g.freezeBytes),precommitSha=digest(g.precommitBytes),contractSha=digest(g.contractBytes);
  assert.equal(unlock?.status,'AUTHORIZED_INTEGRATED_OOS_OPEN','separate Integrated OOS unlock required');assert.equal(unlock?.candidateFreezeSha256,freezeSha,'candidate freeze hash mismatch');assert.equal(unlock?.precommitSha256,precommitSha,'precommit hash mismatch');assert.equal(unlock?.contractSha256,contractSha,'contract hash mismatch');assert.equal(unlock?.inputBundleSha256,inputBundleSha256,'authorized input bundle hash mismatch');
  assert.equal(bundle?.schemaId,'PHASE57_CAPITAL_ALLOCATION_INTEGRATED_OOS_MATERIALIZED_INPUT_V2');assert.equal(bundle?.evidenceRole,'UNTOUCHED_INTEGRATED_OOS');const source=assertSourceIdentity(bundle);
  assert.ok(Array.isArray(bundle.opportunities)&&Array.isArray(bundle.trades)&&Array.isArray(bundle.marks));assert.ok(bundle.opportunities.every(x=>x.outcomeUsed===false&&x.exitUsed===false&&!('v4' in x)&&!('futureBars' in x)),'allocator input must be point-in-time only');
  const allowed=new Set(source.sessionIds);for(const [label,rows] of [['opportunity',bundle.opportunities],['trade',bundle.trades],['mark',bundle.marks]])assert.ok(rows.every(x=>allowed.has(sourceDate(x))),`${label} outside precommitted session set`);
  const closeMap=new Map(Object.entries(bundle.barCloses??{})),barCloseAt=(symbol,timestamp)=>closeMap.get(`${symbol}|${timestamp}`);
  const make=spec=>simulatePhaseB({opportunities:bundle.opportunities,trades:bundle.trades,allocationId:'V3_B_RISK',exitId:spec.exitId,barCloseAt,marks:bundle.marks,initialCapital:1000000,maxPositions:10,budgetDivisor:spec.budgetDivisor,lotSize:100,armId:`V3_B_RISK__${spec.exitId}__MAX_${spec.budgetDivisor}`});
  const full=Object.fromEntries(Object.entries(INTEGRATED_OOS_ARMS).map(([name,spec])=>[name,make(spec)]));for(const arm of Object.values(full))assert.equal(arm.ledgerAudit.status,'LEDGER_INVARIANTS_PASS');
  const comparisons={max5ToMax3:budgetAttribution(full.conservativeSub,full.primary),max10ToMax3:budgetAttribution(full.legacyBaseline,full.primary),primaryV5VsV4:executionAttribution(full.exitComparator,full.primary,{label:'PRIMARY_BUDGET_EXIT_EFFECT',leftName:full.exitComparator.armId,rightName:full.primary.armId})};
  return {schemaVersion:2,schemaId:'PHASE57_CAPITAL_ALLOCATION_INTEGRATED_OOS_RESULT_V2',status:'INTEGRATED_OOS_MEASURED_NOT_ADJUDICATED',sourceIdentity:{...source,inputBundleSha256},candidateFreezeSha256:freezeSha,precommitSha256:precommitSha,contractSha256:contractSha,arms:Object.fromEntries(Object.entries(full).map(([name,arm])=>[name,compact(arm,source)])),comparisons,claims:{oosPass:false,validationPass:false,finalPass:false,productionReady:false,automaticRoleChangeAllowed:false,resultBasedRetuningAllowed:false},safety:PHASE_B_SAFETY};
}

// Compatibility names remain exported for callers while their semantics now use the v2 Integrated OOS contract.
export const VALIDATION_ARMS=INTEGRATED_OOS_ARMS;
export const prepareValidationReadiness=prepareIntegratedOosReadiness;
export const measureAuthorizedValidationBundle=measureAuthorizedIntegratedOosBundle;

function main(){
  const a=parseArgs(process.argv.slice(2)),mode=a.mode??'PREPARE_ONLY';assert.ok(a['output-dir'],'MISSING_ARG:output-dir');fs.mkdirSync(a['output-dir'],{recursive:true});
  if(mode==='PREPARE_ONLY'){const readiness=prepareIntegratedOosReadiness();writeJson(a['output-dir'],'integrated-oos-runner-readiness.json',readiness);console.log(JSON.stringify({status:readiness.status,executionPerformed:false,futureOutcomeDataRead:false,reservedEntryBlockRead:false}));return;}
  assert.equal(mode,'EXECUTE_AUTHORIZED_INTEGRATED_OOS','unknown Integrated OOS runner mode');for(const k of ['input-bundle','unlock-contract'])assert.ok(a[k],`MISSING_ARG:${k}`);
  const inputBytes=fs.readFileSync(a['input-bundle']),inputSha=digest(inputBytes),bundle=JSON.parse(inputBytes),unlock=read(a['unlock-contract']);const result=measureAuthorizedIntegratedOosBundle(bundle,{inputBundleSha256:inputSha,unlock});writeJson(a['output-dir'],'integrated-oos-result.json',result);console.log(JSON.stringify({status:result.status,source:result.sourceIdentity.integratedOosSourceId,arms:Object.keys(result.arms)}));
}

if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1]))main();
