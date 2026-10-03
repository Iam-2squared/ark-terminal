import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertV2PreFitContract,V2_COMPARISON_CONTRACT,V2_DEVELOPMENT} from '../long-only/phase57-long-only-v2-contract.js';

const read=file=>JSON.parse(fs.readFileSync(new URL(file,import.meta.url),'utf8'));
test('Candidate v2 contract is fixed before acquisition and disjoint from prior Minute research',()=>{
  const allocation=read('../long-only/phase57-long-only-session-allocation-v3.json');
  const l1=read('../long-only/phase57-long-only-l1-discovery-sessions.json');
  const l2=read('../long-only/phase57-long-only-l2-development-sessions.json');
  assert.equal(assertV2PreFitContract({allocation,l1Contract:l1,l2Contract:l2}),true);
  assert.equal(V2_DEVELOPMENT.sessions.length,20);
  assert.equal(V2_DEVELOPMENT.requestHardCeiling,300);
  assert.equal(V2_COMPARISON_CONTRACT.familyCount,1);
  assert.equal(V2_COMPARISON_CONTRACT.hyperparameterCandidates.length,4);
  assert.deepEqual(V2_COMPARISON_CONTRACT.target,{name:'Y30_ENDPOINT_EXPECTED_RETURN_BPS',horizonBars:6,barMinutes:5,semantics:'SIX_CLOSED_5M_BARS_EQUALS_30_TRADING_MINUTES'});
});
