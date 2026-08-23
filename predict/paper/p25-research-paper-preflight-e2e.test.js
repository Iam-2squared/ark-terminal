import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

function row(date='2026-08-24',symbol='7203.T',referencePrice=2500){
  return {
    signal:{
      signalId:`${date}|${date}T00:05:00.000Z|${symbol}`,
      evidenceDate:date,
      sourceTimestamp:`${date}T00:05:00.000Z`,
      symbol,
      direction:'UP',
      universeVariant:'PRECOMMITTED_FROZEN_LEDGER',
      modelVersion:'frozen-p25',
      lineageHeadSha256:'preflight-lineage'
    },
    referencePrice,
    referenceTimestamp:`${date}T00:05:00.000Z`
  };
}

function run(args){
  return spawnSync(process.execPath,args,{encoding:'utf8'});
}

test('preflight traverses export-equivalent input -> 10bps replay -> cumulative state -> scoreboard offline only',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'p25-preflight-'));
  const exportFile=path.join(dir,'paper-export.json');
  const stateFile=path.join(dir,'state.json');
  const boardFile=path.join(dir,'scoreboard.json');
  fs.writeFileSync(exportFile,JSON.stringify({
    mode:'research_offline_only',
    executable:false,
    lineageManifestHeadSha256:'preflight-lineage',
    sessions:[{sessionDate:'2026-08-24',input:{rows:[row()]}}]
  }));

  const replay=run([
    'scripts/run_p25_research_paper_daily.mjs',
    '--paper-export',exportFile,
    '--output',stateFile,
    '--quantity','100',
    '--commission-per-fill','0',
    '--slippage-bps','10'
  ]);
  assert.equal(replay.status,0,replay.stderr);
  const state=JSON.parse(fs.readFileSync(stateFile,'utf8'));
  assert.equal(state.mode,'research_offline_only');
  assert.equal(state.executable,false);
  assert.equal(state.assumptions.slippageBps,10);
  assert.equal(state.assumptions.commissionPerFill,0);
  assert.equal(state.completedSessionCount,1);
  assert.equal(state.ledger.sessions.length,1);
  assert.equal(state.reports.length,1);
  for(const value of Object.values(state.safety))assert.equal(value,false);

  const board=run([
    'scripts/build_p25_research_paper_scoreboard.mjs',
    '--state',stateFile,
    '--output',boardFile
  ]);
  assert.equal(board.status,0,board.stderr);
  const score=JSON.parse(fs.readFileSync(boardFile,'utf8'));
  assert.equal(score.mode,'research_offline_only');
  assert.equal(score.executable,false);
  assert.equal(score.costPolicy.slippageBps,10);
  assert.equal(score.costPolicy.commissionPerFill,0);
  assert.equal(score.completedSessionCount,1);
  assert.equal(score.methodology.performanceConclusionAllowed,false);
  assert.equal(score.methodology.noDynamicNSelectionFromScoreboard,true);
});

test('preflight rejects a state whose cost assumptions drift from the predeclared baseline',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'p25-preflight-cost-'));
  const stateFile=path.join(dir,'state.json');
  const boardFile=path.join(dir,'scoreboard.json');
  fs.writeFileSync(stateFile,JSON.stringify({
    mode:'research_offline_only',
    executable:false,
    assumptions:{commissionPerFill:0,slippageBps:5},
    reports:[],
    ledger:{initialCash:1_000_000,sessions:[]}
  }));
  const board=run(['scripts/build_p25_research_paper_scoreboard.mjs','--state',stateFile,'--output',boardFile]);
  assert.notEqual(board.status,0);
  assert.match(board.stderr,/slippage does not match predeclared cost policy/);
});
