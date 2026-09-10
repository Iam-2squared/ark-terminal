import fs from 'node:fs';
import path from 'node:path';
import {
  STAGE3_PINS,STAGE3_SAFETY,sha256,validateStage3DevAIntegrity,
} from './lib/phase57-stage3-dev-a-integrity.mjs';

const root=path.resolve(import.meta.dirname,'..');
const out=process.env.OUTPUT_PATH??path.join(root,'predict/research/phase57-exit-v4-stage3-dev-a-integrity-block-v1.json');
const paths={
  allocationContractSha256:'predict/research/phase57-exit-v4-stage2-data-allocation-contract-v1.json',
  allocationManifestSha256:'predict/research/phase57-exit-v4-stage2-allocation-manifest-v1.json',
  sessionMetadataInventorySha256:'predict/research/phase57-exit-v4-stage2-session-metadata-inventory-v1.json',
  tier2ContractSha256:'predict/research/phase57-exit-v4-tier2-reconstruction-contract-v1.json',
};
const bytes=Object.fromEntries(Object.entries(paths).map(([key,name])=>[key,fs.readFileSync(path.join(root,name))]));
const digests=Object.fromEntries(Object.entries(bytes).map(([key,value])=>[key,sha256(value)]));
for(const [key,value] of Object.entries(digests))if(value!==STAGE3_PINS[key])throw new Error(`FROZEN_FILE_DIGEST_MISMATCH:${key}`);
const manifest=JSON.parse(bytes.allocationManifestSha256);
const handoff=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-exit-v4-stage2-dev-a-handoff-v1.json'),'utf8'));
const preflight=validateStage3DevAIntegrity({manifest,handoff,fileDigests:digests});
const payload={
  schemaVersion:1,
  auditId:'PHASE57_EXIT_V4_STAGE3_DEV_A_INTEGRITY_PREFLIGHT_V1',
  asOfJst:'2026-09-10',
  status:'BLOCKED_BEFORE_DEV_A_OUTCOME_ACCESS',
  classification:{substrate:'TIER2_RECONSTRUCTED_REPLAY',researchUse:'DEVELOPMENT_ONLY',temporality:'NON_PROSPECTIVE'},
  authorization:{devAOutcomeAccessAuthorized:true,devASessions:70,authorizationUsed:false,reason:'PRE_OUTCOME_CAUSAL_INTEGRITY_BLOCK'},
  preflight,
  frozenPins:STAGE3_PINS,
  measurement:{attemptedSessions:0,eligibleMeasuredSessions:0,blockedSessions:70,firstEnterEvents:null,fixed:null,exitV3:null,exitV4:null,pairedDeltas:null,performanceClaimAllowed:false},
  accessLedger:{devAOutcomeSessions:0,devB:0,validation:0,historicalHoldout:0,untouchedOos:0,futureReserve:0,protected180To282:0,freshValidationOrOos:0,exitOutcomes:0,futureLabels:0,exitInvocations:0},
  decision:'Do not fetch DEV-A outcome paths or report Fixed/v3/v4 performance: frozen v3/v4 analog evidence is chronologically later than every DEV-A session, so a causal paired policy measurement cannot be formed.',
  requiredRepair:'Freeze a result-blind analog source wholly available before 2024-09-10, or separately re-contract/reallocate an evaluation window after the frozen analog history. Either path requires explicit methodology review and a new authorization.',
  safety:STAGE3_SAFETY,
};
fs.mkdirSync(path.dirname(out),{recursive:true});
fs.writeFileSync(out,JSON.stringify(payload,null,2)+'\n');
fs.writeFileSync(out.replace(/\.json$/,'.sha256'),`${sha256(fs.readFileSync(out))}  ${path.basename(out)}\n`);
console.log(JSON.stringify({status:payload.status,gate:preflight.gate,blocker:preflight.blocker,devAOutcomeSessions:0,exitOutcomes:0,safety:payload.safety},null,2));

