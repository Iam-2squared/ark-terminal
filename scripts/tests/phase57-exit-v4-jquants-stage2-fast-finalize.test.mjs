import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';

const ROOT=path.resolve(import.meta.dirname,'../..');
const SCRIPT=path.join(ROOT,'scripts/phase57-exit-v4-jquants-stage2-fast-finalize.mjs');
const TIER2='2aa9fd80596c0f71f2359fb132288a15d563e3fab8e22ecbac54fda308a54a70';
const FALSE_FLAGS=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'];
const sha=text=>crypto.createHash('sha256').update(text).digest('hex');
const dates=(start,count)=>Array.from({length:count},(_,i)=>new Date(Date.parse(start)+i*86400000).toISOString().slice(0,10));

function fixture(){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ark-stage2-fast-'));
  const newRows=dates('2024-01-01',200).map(sessionDate=>({sessionDate,status:'ELIGIBLE',source:{provider:'J_QUANTS',artifactLineage:'synthetic-input-only-test',rawPersisted:false},counts:{normalizedMinuteRows:1,fiveMinuteBars:1,eligibleJpxSymbolCount:1},fingerprints:{minuteSha256:'a'.repeat(64),fiveMinuteSha256:'b'.repeat(64),memberSetSha256:'c'.repeat(64)},blockingReasons:[]}));
  const oldRows=dates('2023-01-01',179).map(sessionDate=>({sessionDate,normalizedMinuteRows:1,fiveMinuteBars:1,eligibleJpxSymbolCount:1,minuteSha256:'d'.repeat(64),fiveMinuteSha256:'e'.repeat(64),memberSetSha256:'f'.repeat(64)}));
  const fresh={status:'FAST_METADATA_INVENTORY_COMPLETE',range:{first:'2024-01-01',last:'2024-07-18'},discoveredSessionCount:200,sessions:newRows,blockingReasonCounts:{}};
  const freshPath=path.join(dir,'fresh.json'),v2Path=path.join(dir,'v2.json'),v21Path=path.join(dir,'v21.json'),out=path.join(dir,'out'),doc=path.join(dir,'report.md');
  fs.writeFileSync(freshPath,JSON.stringify(fresh));
  fs.writeFileSync(v2Path,JSON.stringify({auditBySession:oldRows.slice(0,120)}));
  fs.writeFileSync(v21Path,JSON.stringify({auditBySession:oldRows.slice(120)}));
  const run=spawnSync(process.execPath,[SCRIPT],{cwd:ROOT,encoding:'utf8',env:{...process.env,NEW_INVENTORY_PATH:freshPath,ADMISSION_V2_PATH:v2Path,ADMISSION_V21_PATH:v21Path,FINALIZE_OUT_DIR:out,FINALIZE_DOC_PATH:doc}});
  assert.equal(run.status,0,run.stderr||run.stdout);
  const read=name=>JSON.parse(fs.readFileSync(path.join(out,name),'utf8'));
  return {dir,out,manifest:read('phase57-exit-v4-stage2-allocation-manifest-v1.json'),contract:read('phase57-exit-v4-stage2-data-allocation-contract-v1.json'),handoff:read('phase57-exit-v4-stage2-dev-a-handoff-v1.json')};
}

test('freezes a deterministic chronological one-session-one-split allocation',()=>{
  const x=fixture();
  const allocated=x.manifest.sessions.filter(row=>row.eligibilityStatus==='ELIGIBLE');
  assert.equal(allocated.length,200);
  assert.equal(new Set(allocated.map(row=>row.sessionDate)).size,200);
  assert.deepEqual(allocated.map(row=>row.sessionDate),[...allocated.map(row=>row.sessionDate)].sort());
  assert.deepEqual(x.contract.allocation.sessionCounts,{devA:70,devB:15,validation:30,historicalHoldout:25,untouchedOos:30,futureReserve:30});
  assert.equal(x.contract.finalGate,'DATA_ALLOCATION_CAPACITY_CONSTRAINED_BUT_USABLE');
  assert.equal(x.contract.tier2Contract.sha256,TIER2);
  fs.rmSync(x.dir,{recursive:true,force:true});
});

test('keeps prior-exposure, Protected, Fresh, outcomes, labels, and Stage 3 locked',()=>{
  const x=fixture();
  const diagnostics=x.manifest.sessions.filter(row=>row.eligibilityStatus==='DIAGNOSTIC');
  assert.equal(diagnostics.length,179);
  assert.ok(diagnostics.every(row=>row.allocationClass==='DIAGNOSTIC_ONLY'));
  assert.equal(x.contract.protection.exposedAssignedOosOrReserve,0);
  assert.equal(x.contract.externalProtectionLedger,undefined);
  assert.equal(x.manifest.externalProtectionLedger.protected180To282.newAccess,0);
  assert.equal(x.manifest.externalProtectionLedger.freshValidationOrOos.newAccess,0);
  assert.deepEqual(x.contract.accessLedger,{newRawSessions:0,newSealedOutcomeSessions:0,protected180To282:0,freshValidationOrOos:0,exitOutcomes:0,futureLabels:0,exitInvocations:0});
  assert.equal(x.contract.developmentPolicy.developmentUnlocked,false);
  assert.equal(x.handoff.developmentUnlocked,false);
  for(const target of [x.manifest,x.contract,x.handoff])for(const flag of FALSE_FLAGS)assert.equal(target.safety[flag],false,flag);
  assert.doesNotMatch(JSON.stringify([x.manifest,x.contract,x.handoff]),/"(?:net|pf|winRate|mfe|mae|futureReturn|winner|loser)"\s*:/i);
  fs.rmSync(x.dir,{recursive:true,force:true});
});

test('writes exact SHA-256 sidecars for every frozen JSON artifact',()=>{
  const x=fixture();
  for(const name of fs.readdirSync(x.out).filter(name=>name.endsWith('.json'))){
    const text=fs.readFileSync(path.join(x.out,name),'utf8');
    const sidecar=fs.readFileSync(path.join(x.out,name.replace(/\.json$/,'.sha256')),'utf8').trim();
    assert.equal(sidecar,`${sha(text)}  ${name}`);
  }
  fs.rmSync(x.dir,{recursive:true,force:true});
});
