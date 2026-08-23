import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

function row(date='2026-08-24',symbol='7203.T'){return {signal:{signalId:`${date}|${date}T00:05:00.000Z|${symbol}`,evidenceDate:date,sourceTimestamp:`${date}T00:05:00.000Z`,symbol,direction:'UP',universeVariant:'PRECOMMITTED_FROZEN_LEDGER',modelVersion:'frozen-p25',lineageHeadSha256:'abc123'},referencePrice:2500,referenceTimestamp:`${date}T00:05:00.000Z`};}

function run(args){return spawnSync(process.execPath,['scripts/run_p25_research_paper_daily.mjs',...args],{encoding:'utf8'});}

test('daily research Paper runner writes cumulative non-executable state and skips duplicate session',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'p25-paper-'));
  const exportFile=path.join(dir,'export.json');
  const out1=path.join(dir,'state1.json');
  const out2=path.join(dir,'state2.json');
  fs.writeFileSync(exportFile,JSON.stringify({mode:'research_offline_only',executable:false,lineageManifestHeadSha256:'abc123',sessions:[{sessionDate:'2026-08-24',input:{rows:[row()]}}]}));
  const first=run(['--paper-export',exportFile,'--output',out1]);
  assert.equal(first.status,0,first.stderr);
  const state1=JSON.parse(fs.readFileSync(out1,'utf8'));
  assert.equal(state1.mode,'research_offline_only');
  assert.equal(state1.executable,false);
  assert.equal(state1.completedSessionCount,1);
  assert.equal(state1.ledger.sessions.length,1);
  assert.equal(state1.reports.length,1);
  for(const value of Object.values(state1.safety))assert.equal(value,false);
  const second=run(['--paper-export',exportFile,'--state',out1,'--output',out2]);
  assert.equal(second.status,0,second.stderr);
  const state2=JSON.parse(fs.readFileSync(out2,'utf8'));
  assert.equal(state2.completedSessionCount,1);
  assert.equal(state2.ledger.sessions.length,1);
  assert.equal(state2.reports.length,1);
});

test('daily research Paper runner preserves prior reports when appending a new session',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'p25-paper-cumulative-'));
  const firstExport=path.join(dir,'export1.json');
  const secondExport=path.join(dir,'export2.json');
  const state1File=path.join(dir,'state1.json');
  const state2File=path.join(dir,'state2.json');
  fs.writeFileSync(firstExport,JSON.stringify({mode:'research_offline_only',executable:false,lineageManifestHeadSha256:'abc123',sessions:[{sessionDate:'2026-08-24',input:{rows:[row('2026-08-24','7203.T')]}}]}));
  let result=run(['--paper-export',firstExport,'--output',state1File]);
  assert.equal(result.status,0,result.stderr);
  fs.writeFileSync(secondExport,JSON.stringify({mode:'research_offline_only',executable:false,lineageManifestHeadSha256:'abc123',sessions:[{sessionDate:'2026-08-25',input:{rows:[row('2026-08-25','6758.T')]}}]}));
  result=run(['--paper-export',secondExport,'--state',state1File,'--output',state2File]);
  assert.equal(result.status,0,result.stderr);
  const state2=JSON.parse(fs.readFileSync(state2File,'utf8'));
  assert.equal(state2.completedSessionCount,2);
  assert.equal(state2.ledger.sessions.length,2);
  assert.equal(state2.reports.length,2);
  assert.deepEqual(state2.reports.map(x=>x.sessionDate),['2026-08-24','2026-08-25']);
  assert.equal(state2.methodology.cumulativeReportsPreserved,true);
});
