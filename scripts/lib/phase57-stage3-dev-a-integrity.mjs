import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {P25_EXIT_V2_STATE_CONDITIONED_POLICY} from '../../predict/daytrade/phase57-p25-exit-v2-state-conditioned.js';
import {P25_EXIT_V3_DUAL_GATE_POLICY_SHA256} from '../../predict/daytrade/phase57-p25-exit-v3-dual-gate.js';
import {P25_EXIT_V4_POLICY_SHA256} from '../../predict/daytrade/phase57-p25-exit-v4-structural-risk.js';
import {PHASE57_P25_2K_POLICY} from '../../predict/daytrade/phase57-p25-2k-pinned-history-bridge.js';

export const STAGE3_FALSE_FLAGS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed',
  'productionUpdateAllowed','transmitted',
]);

export const STAGE3_SAFETY=Object.freeze(Object.fromEntries(STAGE3_FALSE_FLAGS.map(key=>[key,false])));

export const STAGE3_PINS=Object.freeze({
  tier2ContractSha256:'2aa9fd80596c0f71f2359fb132288a15d563e3fab8e22ecbac54fda308a54a70',
  allocationContractSha256:'7e2792dfe35998716535bbbe0c9347adf87c9d6179f004b405bf0afd7240faec',
  allocationManifestSha256:'316d65a051ef62a0917446a910eabd9c46f2b577486fb5ead5743c446075a276',
  sessionMetadataInventorySha256:'127bc15586301936fcb5806486b2d3f03f9a51790d5e1b051fa918815a019e82',
  devASessionsSha256:'8fc50ffaff4aa7107b5e1a904237c3ea4dba00dd4a27255c94839627363a9909',
  exitV3PolicySha256:P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,
  exitV4PolicySha256:P25_EXIT_V4_POLICY_SHA256,
  analogSnapshotSha256:PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,
});

export const sha256=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');

export function earliestPossibleAnalogTimestamp(){
  const end=Date.parse(PHASE57_P25_2K_POLICY.canonicalDataEndIso);
  assert(Number.isFinite(end));
  return new Date(end-PHASE57_P25_2K_POLICY.canonicalWindowDays*86400000).toISOString();
}

export function validateStage3DevAIntegrity({manifest,handoff,fileDigests={}}={}){
  assert.equal(manifest?.schemaId,'PHASE57_EXIT_V4_STAGE2_ALLOCATION_MANIFEST_V1');
  assert.equal(handoff?.handoffId,'PHASE57_EXIT_V4_STAGE2_DEV_A_HANDOFF_V1');
  for(const [key,expected] of Object.entries({
    allocationContractSha256:handoff.allocationContractDigest,
    allocationManifestSha256:handoff.allocationManifestDigest,
    sessionMetadataInventorySha256:handoff.sessionMetadataInventoryDigest,
  }))assert.equal(expected,STAGE3_PINS[key],`HANDOFF_PIN_MISMATCH:${key}`);
  for(const [key,actual] of Object.entries(fileDigests))assert.equal(actual,STAGE3_PINS[key],`FILE_DIGEST_MISMATCH:${key}`);

  const devA=manifest.sessions.filter(row=>row.allocationClass==='DEV_A_LOCKED');
  const dates=devA.map(row=>row.sessionDate);
  assert.equal(devA.length,70,'DEV_A_EXACT_COUNT_REQUIRED');
  assert.deepEqual(dates,handoff.devASessions,'DEV_A_HANDOFF_LIST_MISMATCH');
  assert.equal(sha256(dates.join('\n')+'\n'),STAGE3_PINS.devASessionsSha256,'DEV_A_LIST_DIGEST_MISMATCH');
  assert(devA.every(row=>row.eligibilityStatus==='ELIGIBLE'),'DEV_A_INELIGIBLE_SESSION');
  assert(devA.every(row=>row.exposureStatus==='METADATA_ONLY_OUTCOME_UNTOUCHED'),'DEV_A_PREOPEN_EXPOSURE_MISMATCH');

  const earliestAnalog=earliestPossibleAnalogTimestamp();
  const earliestAnalogDate=earliestAnalog.slice(0,10);
  const incompatible=dates.filter(date=>date<earliestAnalogDate);
  assert.equal(incompatible.length,70,'EXPECTED_ALL_DEV_A_BEFORE_ANALOG_WINDOW');
  assert.equal(P25_EXIT_V2_STATE_CONDITIONED_POLICY.minNeighbors,30);

  return Object.freeze({
    ready:false,
    gate:'DEV_A_MEASUREMENT_INTEGRITY_BLOCKED',
    blocker:'FROZEN_EXIT_ANALOG_POOL_POSTDATES_ALL_DEV_A_SESSIONS',
    devASessionCount:dates.length,
    devAFirst:dates[0],
    devALast:dates.at(-1),
    earliestPossibleAnalogTimestamp:earliestAnalog,
    causalAnalogUpperBoundPerDevASession:0,
    minimumRequiredNeighbors:P25_EXIT_V2_STATE_CONDITIONED_POLICY.minNeighbors,
    pitViolationsIfLaterAnalogsForced:'MATERIAL_NONZERO_ALL_MANAGED_DECISIONS',
    safeTreatment:'STOP_BEFORE_MARKET_OUTCOME_ACCESS',
  });
}

export function assertNoNonDevAAccess(sessionDates,manifest){
  const allowed=new Set(manifest.sessions.filter(row=>row.allocationClass==='DEV_A_LOCKED').map(row=>row.sessionDate));
  for(const date of sessionDates)assert(allowed.has(date),`NON_DEV_A_ACCESS_DENIED:${date}`);
  return true;
}

