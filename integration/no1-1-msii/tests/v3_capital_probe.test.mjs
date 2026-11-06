import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {inspectV3CandidateCapital} from '../tools/no11_v3_capital_probe.mjs';
import {LOCKED_FLAGS,digest} from '../runtime/locked_intent.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');

function fixture(){
  const now=new Date().toISOString();
  const snapshot={schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',
    capturedAt:now,captureCompletedAt:now,source:'MARKETSPEED_II_RSS',mode:'READ_ONLY',
    captureMethod:'ISOLATED_BULK_CANDIDATE_NOT_PRODUCTION',
    positions:[{symbol:'408A',quantity:180,marketValue:300000}],orders:[],executions:[],
    buyingPower:700000,safety:{...LOCKED_FLAGS}};
  const health={schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',
    readOnly:true,addinLoaded:true,workbookPersisted:true,rssErrors:0,
    observationBasis:'FINAL_STATUS_RE_READ_NOT_MARKET_SOURCE_TIMESTAMP',
    actualFeedTimestampCertified:false,healthCapturedAt:now,
    feeds:Object.fromEntries(Object.entries({capacity:'完了',orders:'配信中',
      executions:'配信中',positions:'配信中'}).map(([key,state])=>[key,{state,observedAt:now}]))};
  const core={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',frozen:true,capturedAt:now,
    source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
    externalPositions:[{symbol:'408A.T',quantity:180}],arkManagedPositions:[]};
  return {snapshot,health,ownership:{...core,baselineSha256:digest(core)},now:new Date(now)};
}
test('V3 Capital preview delegates to the real gate, never trades',()=>{
  const z=inspectV3CandidateCapital(fixture());
  assert.equal(z.status,'READ_ONLY_CAPITAL_PREVIEW');
  assert.deepEqual(z.blockers,[]);
  assert.equal(z.productionReady,false);
  assert.equal(z.orderTransmission,false);
  assert.equal(z.actualBrokerDeliveryTimestampCertified,false);
});
test('stale RSS observation, outdated snapshot, and unverified state fail closed',()=>{
  const a=fixture();
  a.health.feeds.capacity.observedAt=new Date(Date.parse(a.snapshot.captureCompletedAt)-31000).toISOString();
  assert.equal(inspectV3CandidateCapital(a).status,'BLOCKED');
  const b=fixture(); b.now=new Date(Date.parse(b.snapshot.captureCompletedAt)+31000);
  assert.equal(inspectV3CandidateCapital(b).status,'BLOCKED');
  const c=fixture(); c.health.actualFeedTimestampCertified=true;
  assert.deepEqual(inspectV3CandidateCapital(c).blockers,['V3_OBSERVATION_CONTRACT_INVALID']);
});
test('ownership tampering, missing/changed broker position, pending order fail closed',()=>{
  const a=fixture();a.ownership.baselineSha256='a'.repeat(64);
  assert.equal(inspectV3CandidateCapital(a).status,'BLOCKED');
  const b=fixture();b.snapshot.positions[0].quantity=100;
  assert.equal(inspectV3CandidateCapital(b).status,'BLOCKED');
  const c=fixture();c.snapshot.orders.push({orderNumber:'test'});
  assert.equal(inspectV3CandidateCapital(c).status,'BLOCKED');
});
test('safety flags, source certificate semantics, and snapshot source are strict',()=>{
  const a=fixture();a.snapshot.safety.executionAllowed=true;
  assert.equal(inspectV3CandidateCapital(a).status,'BLOCKED');
  const b=fixture();b.snapshot.captureMethod='FORGED';
  assert.equal(inspectV3CandidateCapital(b).status,'BLOCKED');
  const c=fixture();c.health.observationBasis='BROKER_PROOF';
  assert.equal(inspectV3CandidateCapital(c).status,'BLOCKED');
});
test('probe shell reads only, checks immutable Freeze and hash and leaves official path alone',()=>{
  const s=fs.readFileSync(path.join(root,'windows/Test-No11V3CapitalReadOnly.ps1'),'utf8');
  assert.match(s,/8B396BF22724ABBCA4BCEB7B93862AE46D40ACBDFE95B385F492E960E9F08DA3/);
  assert.match(s,/10c94c92c4bd2a59a22744667fd0210252602df4/);
  assert.match(s,/Local\\ArkTerminal_No11_RSS_ReadOnly/);
  assert.match(s,/NO11_V3_CAPITAL_DIAGNOSTIC_PASS=/);
  assert.doesNotMatch(s,/\.Save(?:As)?\s*\(/i);
  assert.doesNotMatch(s,/\.Formula\s*=/i);
  assert.doesNotMatch(s,/RssStockOrder\s*\(/i);
  assert.doesNotMatch(s,/private-safety-ledger\.json/i);
  const j=fs.readFileSync(path.join(root,'tools/no11_v3_capital_probe.mjs'),'utf8');
  assert.doesNotMatch(j,/writeFile|renameSync|unlink|rmSync|mkdirSync/);
  assert.match(j,/no11_desktop_cash_preview\.mjs/);
});

test('Windows V3 Capital probe executes byte-verified Downloads candidate, not smudged Git worktree',()=>{
  const s=fs.readFileSync(path.join(root,'windows/Test-No11V3CapitalReadOnly.ps1'),'utf8');
  assert.match(s,/Downloads\\Ark-No11-CaptureReadOnly-v3-CANDIDATE\.ps1/);
  assert.match(s,/\$v3=\$V3File/);
  assert.match(s,/Get-FileHash -LiteralPath \$v3 -Algorithm SHA256/);
  assert.match(s,/V3_CANDIDATE_HASH_MISMATCH/);
  assert.match(s,/NO11_V3_PINNED_DOWNLOAD_SOURCE_VERIFIED=True/);
  assert.match(s,/NO11_V3_CAPITAL_DIAGNOSTIC_PASS=/);
  assert.doesNotMatch(s,/(?:Set-Content|Add-Content|Out-File|WriteAllBytes|WriteAllText|\.Save(?:As)?\()/i);
});
