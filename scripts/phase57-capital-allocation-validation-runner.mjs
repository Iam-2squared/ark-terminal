import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {simulatePhaseB,executionAttribution,PHASE_B_SAFETY} from './lib/phase57-capital-allocation-v3-phase-b.mjs';

const CONTRACT_PATH='predict/research/phase57-capital-allocation-validation-contract.json';
const FREEZE_PATH='predict/research/phase57-capital-allocation-integrated-candidate-freeze.json';
const SCHEMA_PATH='predict/research/phase57-capital-allocation-validation-output-schema.json';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const digest=b=>createHash('sha256').update(b).digest('hex');
const parseArgs=argv=>{const x={};for(let i=0;i<argv.length;i+=2){if(!argv[i]?.startsWith('--')||argv[i+1]===undefined)throw Error('arguments require --key value pairs');x[argv[i].slice(2)]=argv[i+1];}return x;};
const writeJson=(dir,name,value)=>{const bytes=Buffer.from(JSON.stringify(value,null,2)+'\n');fs.writeFileSync(path.join(dir,name),bytes);fs.writeFileSync(path.join(dir,`${name}.sha256`),`${digest(bytes)}  ${name}\n`);};
const compact=arm=>{const {curve,closedTrades,decisions,ledgerTrace,dailyEquity,...summary}=arm;return {...summary,dailyEquity,validationMetrics:{finalEquityJpy:arm.finalEquityJpy,returnPct:arm.netReturnPct,portfolioProfitFactor:arm.portfolioProfitFactor,maxDrawdownPct:arm.maxDrawdown.maxDrawdownPct,worstDay:arm.worstDay,accepted:arm.trade.accepted,belowLotSkip:arm.trade.rejectionCounts.TARGET_BUDGET_BELOW_100_SHARES??0,cashInsufficientSkip:arm.accounting.cashInsufficientSkips,averageCapitalUtilization:arm.capital.averageCapitalUtilization,maximumCapitalUtilization:arm.capital.maximumCapitalUtilization,averageGrossExposureJpy:arm.capital.averageGrossExposureJpy,maximumGrossExposureJpy:arm.capital.maximumGrossExposureJpy,averageAbsoluteNetExposureJpy:arm.capital.averageAbsoluteNetExposureJpy,maximumAbsoluteNetExposureJpy:arm.capital.maximumAbsoluteNetExposureJpy,longCapitalShare:arm.directionCapitalShare.long,shortCapitalShare:arm.directionCapitalShare.short,winRate:arm.trade.winRate,averageTradePnlJpy:arm.trade.averagePnlJpy,medianTradePnlJpy:arm.trade.medianPnlJpy,averageWinJpy:arm.trade.averageWinJpy,averageLossJpy:arm.trade.averageLossJpy,top1ProfitContribution:arm.profitContribution.top1,top3ProfitContribution:arm.profitContribution.top3}};};

export const VALIDATION_ARMS=Object.freeze({
  primary:Object.freeze({role:'PRIMARY',budgetDivisor:5,exitId:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'}),
  legacyBaseline:Object.freeze({role:'LEGACY_BUDGET_BASELINE',budgetDivisor:10,exitId:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'}),
  aggressiveDevelopmentReference:Object.freeze({role:'AGGRESSIVE_DEVELOPMENT_REFERENCE_OPTIONAL',budgetDivisor:3,exitId:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5'}),
  exitComparator:Object.freeze({role:'EXIT_COMPARATOR',budgetDivisor:5,exitId:'FROZEN_EXIT_V4'}),
});

export function prepareValidationReadiness(){
  const contractBytes=fs.readFileSync(CONTRACT_PATH),freezeBytes=fs.readFileSync(FREEZE_PATH),schemaBytes=fs.readFileSync(SCHEMA_PATH),contract=JSON.parse(contractBytes),freeze=JSON.parse(freezeBytes),schema=JSON.parse(schemaBytes);
  assert.equal(contract.status,'VALIDATION_READY_NOT_OPENED');assert.equal(contract.validationOpened,false);assert.equal(contract.runnerExecutionUnlocked,false);
  assert.equal(freeze.status,'DEVELOPMENT_PRIMARY_CANDIDATE_FROZEN');assert.equal(freeze.candidate.budgetEnvelope,'MAX_5');assert.equal(freeze.candidate.exit,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5');
  assert.equal(schema.$id,'PHASE57_CAPITAL_ALLOCATION_VALIDATION_RESULT_V1');for(const v of Object.values(PHASE_B_SAFETY))assert.equal(v,false);
  return {schemaVersion:1,schemaId:'PHASE57_CAPITAL_ALLOCATION_VALIDATION_RUNNER_READINESS_V1',status:'VALIDATION_READY_NOT_OPENED',executionPerformed:false,protectedOrFreshDataRead:false,contractSha256:digest(contractBytes),candidateFreezeSha256:digest(freezeBytes),outputSchemaSha256:digest(schemaBytes),arms:VALIDATION_ARMS,gate:{separateUnlockRequired:true,inputBundleRequired:true,developmentBlockAOrBRejected:true},safety:PHASE_B_SAFETY};
}

export function measureAuthorizedValidationBundle(bundle,{inputBundleSha256,unlock}={}){
  const freezeBytes=fs.readFileSync(FREEZE_PATH),freezeSha256=digest(freezeBytes),contract=read(CONTRACT_PATH);
  assert.equal(unlock?.status,'AUTHORIZED_VALIDATION_OPEN','separate Validation unlock required');
  assert.equal(unlock?.candidateFreezeSha256,freezeSha256,'candidate freeze hash mismatch');
  assert.equal(unlock?.inputBundleSha256,inputBundleSha256,'authorized input bundle hash mismatch');
  assert.equal(bundle?.schemaId,'PHASE57_CAPITAL_ALLOCATION_VALIDATION_MATERIALIZED_INPUT_V1');
  assert.equal(bundle?.evidenceRole,'UNTOUCHED_VALIDATION');
  assert.equal(bundle?.sourceIdentity?.pointInTimeAttestation,true);
  assert.equal(bundle?.sourceIdentity?.unopenedBeforeAuthorizationAttestation,true);
  assert.ok(!String(bundle?.sourceIdentity?.validationSourceId??'').includes('BLOCK_A')&&!String(bundle?.sourceIdentity?.validationSourceId??'').includes('BLOCK_B'),'Development A/B bundle rejected');
  assert.ok(Array.isArray(bundle.opportunities)&&Array.isArray(bundle.trades)&&Array.isArray(bundle.marks));
  assert.ok(bundle.opportunities.every(x=>x.outcomeUsed===false&&x.exitUsed===false&&!('v4' in x)&&!('futureBars' in x)),'allocator input must be point-in-time only');
  const closeMap=new Map(Object.entries(bundle.barCloses??{})),barCloseAt=(symbol,timestamp)=>closeMap.get(`${symbol}|${timestamp}`);
  const make=spec=>simulatePhaseB({opportunities:bundle.opportunities,trades:bundle.trades,allocationId:'V3_B_RISK',exitId:spec.exitId,barCloseAt,marks:bundle.marks,initialCapital:1000000,maxPositions:10,budgetDivisor:spec.budgetDivisor,lotSize:100,armId:`V3_B_RISK__${spec.exitId}__MAX_${spec.budgetDivisor}`});
  const full={legacyBaseline:make(VALIDATION_ARMS.legacyBaseline),primary:make(VALIDATION_ARMS.primary),exitComparator:make(VALIDATION_ARMS.exitComparator)};
  if(bundle.includeAggressiveDevelopmentReference===true)full.aggressiveDevelopmentReference=make(VALIDATION_ARMS.aggressiveDevelopmentReference);
  const comparisons={primaryVsLegacyBudget:executionAttribution(full.legacyBaseline,full.primary,{label:'VALIDATION_BUDGET_EFFECT',leftName:full.legacyBaseline.armId,rightName:full.primary.armId}),primaryV5VsV4:executionAttribution(full.exitComparator,full.primary,{label:'VALIDATION_EXIT_EFFECT',leftName:full.exitComparator.armId,rightName:full.primary.armId})};
  return {schemaVersion:1,schemaId:'PHASE57_CAPITAL_ALLOCATION_VALIDATION_RESULT_V1',status:'VALIDATION_MEASURED_NOT_ADJUDICATED',sourceIdentity:{...bundle.sourceIdentity,inputBundleSha256},candidateFreezeSha256:freezeSha256,contractStatusAtPreparation:contract.status,arms:Object.fromEntries(Object.entries(full).map(([k,v])=>[k,compact(v)])),comparisons,claims:{validationPass:false,oosPass:false,finalPass:false,productionReady:false,resultBasedRetuningAllowed:false},safety:PHASE_B_SAFETY};
}

function main(){
  const a=parseArgs(process.argv.slice(2)),mode=a.mode??'PREPARE_ONLY';assert.ok(a['output-dir'],'MISSING_ARG:output-dir');fs.mkdirSync(a['output-dir'],{recursive:true});
  if(mode==='PREPARE_ONLY'){const readiness=prepareValidationReadiness();writeJson(a['output-dir'],'validation-runner-readiness.json',readiness);console.log(JSON.stringify({status:readiness.status,executionPerformed:false,protectedOrFreshDataRead:false}));return;}
  assert.equal(mode,'EXECUTE_AUTHORIZED_VALIDATION','unknown validation runner mode');for(const k of ['input-bundle','unlock-contract'])assert.ok(a[k],`MISSING_ARG:${k}`);
  const inputBytes=fs.readFileSync(a['input-bundle']),inputSha=digest(inputBytes),bundle=JSON.parse(inputBytes),unlock=read(a['unlock-contract']);const result=measureAuthorizedValidationBundle(bundle,{inputBundleSha256:inputSha,unlock});writeJson(a['output-dir'],'validation-result.json',result);console.log(JSON.stringify({status:result.status,source:result.sourceIdentity.validationSourceId,arms:Object.keys(result.arms)}));
}

if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1]))main();
