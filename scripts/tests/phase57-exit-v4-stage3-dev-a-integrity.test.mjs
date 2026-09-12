import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {scoreP25ExitV2StateConditioned} from '../../predict/daytrade/phase57-p25-exit-v2-state-conditioned.js';
import {
  STAGE3_FALSE_FLAGS,STAGE3_PINS,STAGE3_SAFETY,assertNoNonDevAAccess,sha256,validateStage3DevAIntegrity,
} from '../lib/phase57-stage3-dev-a-integrity.mjs';

const ROOT=path.resolve(import.meta.dirname,'../..');
const read=name=>JSON.parse(fs.readFileSync(path.join(ROOT,name),'utf8'));
const manifest=read('predict/research/phase57-exit-v4-stage2-allocation-manifest-v1.json');
const handoff=read('predict/research/phase57-exit-v4-stage2-dev-a-handoff-v1.json');

test('exact frozen DEV-A list fails closed before outcome access because analogs postdate it',()=>{
  const fileDigests={
    allocationContractSha256:sha256(fs.readFileSync(path.join(ROOT,'predict/research/phase57-exit-v4-stage2-data-allocation-contract-v1.json'))),
    allocationManifestSha256:sha256(fs.readFileSync(path.join(ROOT,'predict/research/phase57-exit-v4-stage2-allocation-manifest-v1.json'))),
    sessionMetadataInventorySha256:sha256(fs.readFileSync(path.join(ROOT,'predict/research/phase57-exit-v4-stage2-session-metadata-inventory-v1.json'))),
    tier2ContractSha256:sha256(fs.readFileSync(path.join(ROOT,'predict/research/phase57-exit-v4-tier2-reconstruction-contract-v1.json'))),
  };
  const result=validateStage3DevAIntegrity({manifest,handoff,fileDigests});
  assert.equal(result.gate,'DEV_A_MEASUREMENT_INTEGRITY_BLOCKED');
  assert.equal(result.devASessionCount,70);
  assert.equal(result.devALast,'2024-12-20');
  assert.equal(result.earliestPossibleAnalogTimestamp,'2026-06-17T06:30:00.000Z');
  assert.equal(result.causalAnalogUpperBoundPerDevASession,0);
  assert.equal(result.minimumRequiredNeighbors,30);
});

test('frozen scorer confirms 30 later analogs yield zero causal neighbors for DEV-A',()=>{
  const later={sessionDate:'2026-06-18',direction:'LONG',timestamp:'2026-06-18T00:30:00.000Z',fullyRealizedAt:'2026-06-18T01:00:00.000Z',state:{currentReturnPct:1,bestReturnPct:1,givebackPctPoints:0,atrPct:1,momentumPct:1,bodyPressure:0,directionalRangePos:0.5,elapsedBars:2},labels:{1:1,3:1,6:1}};
  const score=scoreP25ExitV2StateConditioned({entryPrice:100,direction:'LONG',observedBars:[{timestamp:'2024-09-10T00:05:00.000Z',open:100,high:101,low:99,close:100.5,volume:1}],timestamp:'2024-09-10T00:05:00.000Z',sessionDate:'2024-09-10',analogPool:Array.from({length:30},()=>later)});
  assert.equal(score.ready,false);
  assert.equal(score.reason,'INSUFFICIENT_STATE_CONDITIONED_CAUSAL_ANALOGS');
  assert.equal(score.neighborCount,0);
});

test('access guard permits only exact DEV-A and rejects locked sets',()=>{
  assert.equal(assertNoNonDevAAccess(handoff.devASessions,manifest),true);
  assert.throws(()=>assertNoNonDevAAccess(['2024-12-23'],manifest),/NON_DEV_A_ACCESS_DENIED/);
  assert.throws(()=>assertNoNonDevAAccess(['2025-01-27'],manifest),/NON_DEV_A_ACCESS_DENIED/);
  assert.throws(()=>assertNoNonDevAAccess(['2026-06-16'],manifest),/NON_DEV_A_ACCESS_DENIED/);
});

test('policy pins and all safety flags remain frozen',()=>{
  assert.equal(STAGE3_PINS.exitV3PolicySha256,'634514abac1ea1129ecf669e677d677a18378b1f75b7ba872bae781b82c401f2');
  assert.equal(STAGE3_PINS.exitV4PolicySha256,'2d512dd810d057807bc59a0138a3db98035e57ff2c23c186ba096beeb6be26cb');
  for(const flag of STAGE3_FALSE_FLAGS)assert.equal(STAGE3_SAFETY[flag],false,flag);
});

