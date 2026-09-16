import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {FREEZE,SAFETY,hash,digest,verifyFreeze,iso} from './lib/phase57-offline-parity.mjs';
import {OfflineSession,exportSession} from './lib/phase57-offline-session.mjs';
import {diagnoseSnapshots} from './lib/phase57-offline-semantics.mjs';
import {createOfflineShadowLedger} from './lib/phase57-offline-shadow-ledger.mjs';
import {simulatePhaseB} from './lib/phase57-capital-allocation-v3-phase-b.mjs';
import {compareDay,cumulativeDays,STAGES} from './lib/phase57-parity-report.mjs';

// Synthetic software smoke test, not a market selection, order or paper session.
const [output]=process.argv.slice(2);assert.equal(process.argv.length,3,'USE NEW_OUTPUT_DIRECTORY');
verifyFreeze(process.cwd());fs.mkdirSync(output,{recursive:false});
const date='2026-08-13',t=n=>iso(Date.parse(date+'T00:00:00Z')+n*300000);
const opportunity={eventId:'synthetic-transport',symbol:'0000.T',sessionDate:date,decisionTimestamp:t(1),direction:-1,entryPrice:100,mshScore:.8,recentRealizedVolatility:.01,outcomeUsed:false,exitUsed:false};
const trades=[{eventId:opportunity.eventId,symbol:opportunity.symbol,direction:-1,causalEligible:true,v4:{exitTimestamp:t(2),exitPrice:99,exitReason:'SYNTHETIC_V4_FEED',barsHeld:1}}];
const marks=[{symbol:'0000.T',timestamp:t(1),sessionDate:date,close:100},{symbol:'0000.T',timestamp:t(2),sessionDate:date,close:99}];
const inputs=marks.map((m,i)=>({sessionDate:date,timestamp:m.timestamp,marks:[m],entries:i?[]:[opportunity],exitDecisions:i?[{eventId:opportunity.eventId,...trades[0].v4}]:[]}));
const reference=simulatePhaseB({opportunities:[opportunity],trades,marks,allocationId:'V3_B_RISK',exitId:'FROZEN_EXIT_V4',budgetDivisor:3});
const makeReducer=()=>{const ledger=createOfflineShadowLedger();return input=>{
  ledger.step(input);const state=ledger.snapshot();
  return {raw:[input],normalized:input.marks,decisions:state.decisions.filter(x=>x.timestamp===input.timestamp||x.decisionTimestamp===input.timestamp),ledger:[state.ledgerTrace.at(-1)],health:[{timestamp:input.timestamp,status:'READY_OFFLINE_FIXTURE',realCapture:false}],reference:[reference.ledgerTrace.find(x=>x.timestamp===input.timestamp)]};
};};
const workbook=digest(fs.readFileSync('tools/templates/ArkParityOffline.xlsx'));
const implementationFiles=['scripts/phase57-offline-local-gate.mjs','scripts/lib/phase57-offline-session.mjs','scripts/lib/phase57-offline-shadow-ledger.mjs','scripts/lib/phase57-offline-semantics.mjs','scripts/lib/phase57-parity-report.mjs'];
const implementationSha256=hash(implementationFiles.map(file=>({file,sha256:digest(fs.readFileSync(file))})));
const identity={sessionDate:date,sourceClass:'SYNTHETIC_TRANSPORT_TEST',freezeSha256:FREEZE,repoHead:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),implementationSha256,workbookSha256:workbook,sourceIdentity:hash(inputs)};
const directory=path.join(output,'session');let session=new OfflineSession(directory,identity,makeReducer);
try{session.commit('capture-1',inputs[0]);}finally{session.close();}
session=new OfflineSession(directory,identity,makeReducer);
let result,dailyReport;
try{
  assert.equal(session.commit('capture-1',inputs[0]).duplicate,true);
  result=session.commit('capture-2',inputs[1]);
  assert.deepEqual(result.output.ledger[0],reference.ledgerTrace.at(-1));
  const records=fs.readFileSync(path.join(directory,'session.jsonl'),'utf8').trim().split('\n').map(JSON.parse).filter(x=>x.kind==='COMMIT');
  const adapt=x=>({...x,id:x.timestamp,equityJpy:x.currentEquityJpy,realizedPnlJpy:x.currentRealizedEquityJpy-1000000});
  const left={sessionDate:date,sourceClass:'SYNTHETIC_TRANSPORT_TEST',freezeSha256:FREEZE,...Object.fromEntries(STAGES.map(x=>[x,[]])),LEDGER:records.flatMap(x=>x.payload.output.ledger).map(adapt)};
  const right={...left,LEDGER:reference.ledgerTrace.map(adapt)};
  dailyReport={...compareDay(left,right),smoke:{status:'SYNTHETIC_RESTART_AND_LEDGER_PARITY_PASS',committedInputs:2,duplicateSuppressed:1,ledgerInvariants:reference.ledgerAudit,entryModelMeasured:false,selectorMeasured:false,v4Feed:'SYNTHETIC_CURRENT_DECISION'}};
  session.seal(dailyReport);
}finally{session.close();}
const manifest=exportSession(path.join(directory,'session.jsonl'),path.join(output,'daily'));
fs.writeFileSync(path.join(output,'cumulative.json'),JSON.stringify(cumulativeDays([dailyReport]),null,2)+'\n',{flag:'wx'});
fs.writeFileSync(path.join(output,'daily-report.md'),'# Offline software smoke test\n\nSynthetic inputs only; not a market session.\n\n| Stage | Exact | Compared |\n| --- | ---: | ---: |\n'+dailyReport.stages.map(x=>`| ${x.stage} | ${x.exact} | ${x.denominator} |`).join('\n')+'\n\nEmpty stages are NOT MEASURED. Real Excel/MSII remains untested.\n',{flag:'wx'});
const snapshots=['09:00:00','09:04:00','11:30:00','12:30:00','15:30:00'].map((time,i)=>({captureId:'source-'+i,symbol:'0000.T',sourceDate:date,sourceTime:i===1?'09:00:00':time,captureAt:iso(Date.parse(date+'T'+time+'+09:00')),open:100,high:102,low:99,close:i===1?101:100,volume:100+i,marketTimestamp:iso(Date.parse(date+'T'+time+'+09:00')),connected:true,workbookHealthy:true,rssError:null}));
const semantics=diagnoseSnapshots(snapshots);
for(const [name,value]of Object.entries({'source-semantics-input':snapshots,'source-semantics-report':semantics,'gate-summary':{status:'OFFLINE_LOCAL_GATE_PASS',manifestHash:hash(manifest),semanticsHash:hash(semantics),actualWindowsTested:process.platform==='win32',actualExcelTested:false,actualMsiiTested:false,reservedDataOpened:false,safety:SAFETY}}))fs.writeFileSync(path.join(output,name+'.json'),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
console.log('OFFLINE_LOCAL_GATE_PASS: '+output);
