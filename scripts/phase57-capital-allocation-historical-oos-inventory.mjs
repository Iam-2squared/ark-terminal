import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const INVENTORY_PATH='predict/research/phase57-capital-allocation-historical-oos-inventory-v1.json';
const FREEZE_PATH='predict/research/phase57-capital-allocation-integrated-candidate-freeze.json';
const VALIDATION_PATH='predict/research/phase57-capital-allocation-validation-contract.json';
const PHASE_B_PATH='predict/research/phase57-capital-allocation-v3-phase-b-evidence/phase-b-result.json';
const ENTRY_DEVELOPMENT_PATH='predict/research/phase57-entry-development-allocation-v1.json';
const ENTRY_HOLDOUT_PATH='predict/research/phase57-entry-historical-holdout29-source-parity-precommit.json';
const ENTRY_FRESH_PATH='predict/research/phase57-minimal-stateful-entry-fresh-allocation.json';
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const readBytes=p=>fs.readFileSync(p);
const read=p=>JSON.parse(readBytes(p));
const allFalse=x=>Object.values(x).every(v=>v===false);
const parseArgs=argv=>{const out={};for(let i=0;i<argv.length;i+=2){assert.ok(argv[i]?.startsWith('--')&&argv[i+1]!==undefined,'arguments require --key value pairs');out[argv[i].slice(2)]=argv[i+1];}return out;};
const write=(dir,name,bytes)=>{fs.writeFileSync(path.join(dir,name),bytes);fs.writeFileSync(path.join(dir,`${name}.sha256`),`${digest(bytes)}  ${name}\n`);};

export function auditHistoricalOosInventory(){
  const inventoryBytes=readBytes(INVENTORY_PATH),inventory=JSON.parse(inventoryBytes),freezeBytes=readBytes(FREEZE_PATH),freeze=JSON.parse(freezeBytes),validationBytes=readBytes(VALIDATION_PATH),validation=JSON.parse(validationBytes),phaseB=read(PHASE_B_PATH),entryDevelopment=read(ENTRY_DEVELOPMENT_PATH),entryHoldout=read(ENTRY_HOLDOUT_PATH),entryFresh=read(ENTRY_FRESH_PATH);
  assert.equal(inventory.status,'NO_TRULY_UNUSED_CAUSAL_ELIGIBLE_HISTORICAL_BLOCK');
  assert.equal(inventory.sourcePins.capital.candidateFreezeSha256,digest(freezeBytes));
  assert.equal(inventory.sourcePins.capital.validationContractSha256,digest(validationBytes));
  assert.equal(inventory.sourcePins.entry.developmentAllocationSha256,digest(readBytes(ENTRY_DEVELOPMENT_PATH)));
  assert.equal(inventory.sourcePins.entry.historicalHoldoutSha256,digest(readBytes(ENTRY_HOLDOUT_PATH)));
  assert.equal(freeze.status,'DEVELOPMENT_PRIMARY_CANDIDATE_FROZEN');
  assert.equal(freeze.candidate.budgetEnvelope,'MAX_5');
  assert.equal(freeze.candidate.exit,'EXIT_V5_DYNAMIC_RECLAIM_BAR_5');
  assert.equal(validation.status,'VALIDATION_READY_NOT_OPENED');
  assert.equal(validation.validationOpened,false);
  assert.equal(validation.runnerExecutionUnlocked,false);
  assert.equal(inventory.jquantsHistoricalInventory.firstSessionWithRequiredCausalCoverage,'2026-06-19');
  assert.deepEqual(phaseB.input.sessions.slice(0,1),['2026-06-18']);
  assert.deepEqual(phaseB.input.sessions.slice(-1),['2026-08-12']);
  assert.equal(phaseB.input.sessions.length,38);
  assert.equal(entryDevelopment.sessionCount,58);
  assert.equal(entryDevelopment.sessions[0].sessionDate,'2025-10-09');
  assert.equal(entryDevelopment.sessions.at(-1).sessionDate,'2026-01-07');
  assert.equal(entryHoldout.count,29);
  assert.equal(entryHoldout.sessions[0],'2025-08-27');
  assert.equal(entryHoldout.sessions.at(-1),'2025-10-08');
  assert.deepEqual(entryFresh.FRESH_ENTRY_VALIDATION.slice(0,2),['2026-09-10','2026-09-11']);
  assert.equal(entryFresh.PROSPECTIVE.notBefore,'2026-10-22');
  assert.equal(inventory.candidateSearch.trulyUnusedCausalEligibleHistoricalSessionCount,0);
  assert.deepEqual(inventory.candidateSearch.trulyUnusedCausalEligibleHistoricalSessions,[]);
  assert.equal(inventory.candidateSearch.historicalOosBlockPreFrozen,false);
  assert.equal(inventory.candidateSearch.validationUnlockCreated,false);
  assert.equal(inventory.candidateSearch.validationRunnerExecuted,false);
  assert.equal(inventory.candidateSearch.fourArmPerformanceMeasured,false);
  assert.ok(allFalse(inventory.claims));
  assert.ok(allFalse(inventory.safety));
  assert.ok(allFalse(freeze.safety));
  assert.ok(allFalse(validation.safety));
  return {
    schemaVersion:1,
    schemaId:'PHASE57_CAPITAL_ALLOCATION_HISTORICAL_OOS_INVENTORY_AUDIT_V1',
    status:inventory.status,
    asOfJst:inventory.asOfJst,
    inventorySha256:digest(inventoryBytes),
    candidateFreezeSha256:digest(freezeBytes),
    validationContractSha256:digest(validationBytes),
    discoveredMarketSessions:inventory.jquantsHistoricalInventory.discoveredMarketSessions,
    firstCausalEligibleDate:inventory.jquantsHistoricalInventory.firstSessionWithRequiredCausalCoverage,
    trulyUnusedCausalEligibleHistoricalSessionCount:0,
    historicalOosOpened:false,
    validationUnlockCreated:false,
    validationRunnerExecuted:false,
    fourArmPerformanceMeasured:false,
    nextCleanOpportunity:inventory.nextCleanOpportunity,
    frozenCandidateUnchanged:inventory.frozenCandidateUnchanged,
    claims:inventory.claims,
    safety:inventory.safety
  };
}

export function renderHistoricalOosInventoryReport(inventory,audit){
  const rows=inventory.classification.map(x=>`| ${x.id} | ${x.window.join(' to ')} | ${x.sessions??'n/a'} | ${x.classification} | ${x.primaryExclusion} |`).join('\n');
  return `# Phase57 Integrated Historical OOS Inventory\n\nStatus: **${audit.status}**\n\nNo new J-Quants market payload, future label, realized outcome, or performance result was opened during this inventory. The four-arm runner was not unlocked because the precondition for a clean Historical OOS block failed.\n\n## Inventory\n\n| Segment | Window | Sessions | Classification | Primary exclusion |\n| --- | --- | ---: | --- | --- |\n${rows}\n\n## Causal conclusion\n\nThe frozen v4/v5 analog pool begins at ${inventory.jquantsHistoricalInventory.earliestFrozenAnalogTimestamp}; the first session with the required ${inventory.jquantsHistoricalInventory.minimumCausalAnalogCount} causal analogs is ${inventory.jquantsHistoricalInventory.firstSessionWithRequiredCausalCoverage}. Older outcome-unopened sessions cannot be evaluated by sending later 2026 analogs backward. Every causal-valid Historical session through 2026-09-09 has already been exposed by Block A, Block B, or diagnostic20.\n\nThe first EXIT-causal unseen date is 2026-09-10, but the existing Entry contract reserves 2026-09-10 through 2026-10-21. The first currently unassigned opportunity is **${inventory.nextCleanOpportunity.firstDateUnderCurrentCrossResearchReservations}**, and it is future/prospective rather than an available Historical OOS block. It still requires a separate outcome-blind precommit before that session.\n\n## Result\n\n- Historical OOS block pre-frozen: false\n- Validation unlock created: false\n- Four-arm performance measured: false\n- Frozen MAX_5 primary / MAX_10 baseline / MAX_3 aggressive reference / MAX_5 v4 comparator roles: unchanged\n- OOS PASS / Validation PASS / Final PASS / Production Ready: all false\n\nThis is a clear no-data result, not a performance failure. Development remains closed and no exposed period is relabelled OOS.\n`;
}

function main(){
  const args=parseArgs(process.argv.slice(2));
  assert.ok(args['output-dir'],'MISSING_ARG:output-dir');
  fs.mkdirSync(args['output-dir'],{recursive:true});
  const inventory=read(INVENTORY_PATH),audit=auditHistoricalOosInventory(),resultBytes=Buffer.from(JSON.stringify(audit,null,2)+'\n'),reportBytes=Buffer.from(renderHistoricalOosInventoryReport(inventory,audit));
  write(args['output-dir'],'historical-oos-inventory-audit.json',resultBytes);
  write(args['output-dir'],'historical-oos-inventory-report.md',reportBytes);
  console.log(JSON.stringify({status:audit.status,historicalOosOpened:false,fourArmPerformanceMeasured:false,nextCleanOpportunity:audit.nextCleanOpportunity.firstDateUnderCurrentCrossResearchReservations}));
}

if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1]))main();
