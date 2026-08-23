import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

function row(){return {signal:{signalId:'2026-08-24|2026-08-24T00:05:00.000Z|7203.T',evidenceDate:'2026-08-24',sourceTimestamp:'2026-08-24T00:05:00.000Z',symbol:'7203.T',direction:'UP',universeVariant:'PRECOMMITTED_FROZEN_LEDGER',modelVersion:'frozen-p25',lineageHeadSha256:'abc123'},referencePrice:2500,referenceTimestamp:'2026-08-24T00:05:00.000Z'};}

test('daily research Paper runner writes cumulative non-executable state and skips duplicate session',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'p25-paper-'));
  const exportFile=path.join(dir,'export.json');
  const out1=path.join(dir,'state1.json');
  const out2=path.join(dir,'state2.json');
  fs.writeFileSync(exportFile,JSON.stringify({mode:'research_offline_only',executable:false,lineageManifestHeadSha256:'abc123',sessions:[{sessionDate:'2026-08-24',input:{rows:[row()]}}]}));
  const first=spawnSync(process.execPath,['scripts/run_p25_research_paper_daily.mjs','--paper-export',exportFile,'--output',out1],{encoding:'utf8'});
  assert.equal(first.status,0,first.stderr);
  const state1=JSON.parse(fs.readFileSync(out1,'utf8'));
  assert.equal(state1.mode,'research_offline_only');
  assert.equal(state1.executable,false);
  assert.equal(state1.completedSessionCount,1);
  assert.equal(state1.ledger.sessions.length,1);
  for(const value of Object.values(state1.safety))assert.equal(value,false);
  const second=spawnSync(process.execPath,['scripts/run_p25_research_paper_daily.mjs','--paper-export',exportFile,'--state',out1,'--output',out2],{encoding:'utf8'});
  assert.equal(second.status,0,second.stderr);
  const state2=JSON.parse(fs.readFileSync(out2,'utf8'));
  assert.equal(state2.completedSessionCount,1);
  assert.equal(state2.ledger.sessions.length,1);
});
