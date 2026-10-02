import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ark-home-equity-'));
const input=path.join(dir,'input.json');
const scorecard=path.join(dir,'scorecard.json');
const evaluation=path.join(dir,'evaluation.json');
const output=path.join(dir,'output.json');
const variants=['DYNAMIC_30','DYNAMIC_40','DYNAMIC_50'];

fs.writeFileSync(input,JSON.stringify({startingCapitalJpy:1000000,series:Object.fromEntries(variants.map(v=>[v,[{date:'2026-08-18',equityJpy:1000000,dailyReturnPct:0,resolvedEntries:0,source:'START'}]])),safety:{executionAllowed:false}},null,2));
fs.writeFileSync(scorecard,JSON.stringify({scorecard:{expectedSessionCount:5,blockedSessionCount:0,rows:variants.map(variant=>({variant,frozenEntries:5,resolvedEntries:5,unresolvedFrozenEntries:0,entriesPerTradingSession:1,afterCostNetPct:5,profitFactor:2,maxDrawdownPct:2,sessionEqualWeightAfterCostNetPct:1}))}},null,2));
const sessions=[
  {sessionDate:'2026-08-19',returnPct:1},
  {sessionDate:'2026-08-20',returnPct:-1},
  {sessionDate:'2026-08-21',returnPct:0},
  {sessionDate:'2026-08-24',returnPct:2},
  {sessionDate:'2026-08-25',returnPct:1},
];
fs.writeFileSync(evaluation,JSON.stringify({evaluation:{result:{evidence:{comparison:{results:Object.fromEntries(variants.map(variant=>[variant,{sessionEqualWeightPortfolio:{sessions}}]))}}}}},null,2));

const run=spawnSync(process.execPath,['scripts/update_home_paper_equity.mjs','--scorecard',scorecard,'--evaluation',evaluation,'--date','2026-08-25','--input',input,'--output',output],{encoding:'utf8'});
assert.equal(run.status,0,run.stderr||run.stdout);
const out=JSON.parse(fs.readFileSync(output,'utf8'));
for(const variant of variants){
  assert.equal(out.series[variant].length,6);
  assert.deepEqual(out.series[variant].slice(1).map(x=>x.date),sessions.map(x=>x.sessionDate));
  assert.deepEqual(out.series[variant].slice(1).map(x=>x.dailyReturnPct),sessions.map(x=>x.returnPct));
  assert.equal(out.series[variant].at(-1).equityJpy,1030096.98);
}
assert.equal(out.latestCumulative.evidenceDate,'2026-08-25');
console.log('Home paper equity multi-session rebuild test passed');
