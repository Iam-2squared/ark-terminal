import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {buildIntegratedInputs} from './phase57-capital-allocation-budget-envelope-ablation.mjs';
import {replayFirstEnter} from './phase57-capital-allocation-v3-phase-a.mjs';
import {runBar5Adapter,simulatePhaseB} from './lib/phase57-capital-allocation-v3-phase-b.mjs';
import {createOfflineShadowLedger} from './lib/phase57-offline-shadow-ledger.mjs';
import {OfflineEntry,Bar5Manager,normalizeBar,CausalBars,exposedDate,verifyFreeze,hash,digest,FREEZE,SAFETY,EvidenceLog,iso} from './lib/phase57-offline-parity.mjs';

function inventory(root){const out=[];for(const d of fs.readdirSync(root,{withFileTypes:true})){assert.ok(!d.isSymbolicLink(),'SYMLINK_SOURCE_FORBIDDEN');const p=path.join(root,d.name);if(d.isDirectory())out.push(...inventory(p));else if(/\.(features|bars)\.json\.gz$|\.manifest\.json$/.test(d.name)){exposedDate(d.name.slice(0,10));out.push({path:p,sha256:digest(fs.readFileSync(p))});}}return out;}
export function historicalParity(root){
  verifyFreeze(process.cwd());
  // Inventory checks dates BEFORE reading compressed data. This runner has no network/COM dependency.
  const sources=inventory(path.join(root,'features'));
  assert.equal(hash(sources.map(({path:p,sha256})=>({name:path.relative(root,p).replaceAll('\\','/'),sha256}))), '6561c1561e7f3bd29289a1b32a1dc46984eafdf5988a568d30e904acb6d638e5','USED_INPUT_BUNDLE_IDENTITY');
  for(const [name,sha] of Object.entries({'block-a/trades.json':'4dd18c66586706aebc19775c718d0fca2fb1ac569d40e8746f85aae502a44a70','block-b/trades.json':'b28bf1931a2fc3332b0c83306523b0d0838d9776b3fc66cb8587b305170ac521','dev-final/report.json':'e2d2844c951d3271128ffadfce4bc2e1c66b2742f5bd0738357d9338accc82c5'}))assert.equal(digest(fs.readFileSync(path.join(root,'artifacts',name))),sha,'USED_EXIT_FIXTURE_IDENTITY');
  const x=buildIntegratedInputs({'features-dir':path.join(root,'features'),model:path.join(root,'features/10084158820/candidate-model.json'),'block-a':path.join(root,'artifacts/block-a/trades.json'),'block-b':path.join(root,'artifacts/block-b/trades.json'),'bar5-pinned-report':path.join(root,'artifacts/dev-final/report.json')});
  for(const e of x.input.events)exposedDate(e.sessionDate);
  const stream=new OfflineEntry(x.modelBytes),reconstructed=[],observations=[];let pairCount=0,barCount=0;
  const normalizedBySession=new Map();
  for(const [date,symbols] of x.input.barsBySession){const normalized=new Map();for(const [symbol,bars] of symbols){const cache=new CausalBars();for(const b of bars){const local=iso(Date.parse(b.timestamp)+32400000);const raw={symbol,sourceDate:date,sourceTime:local.slice(11,19),captureAt:b.availableAt,availableAt:b.availableAt,finalized:true,open:b.open,high:b.high,low:b.low,close:b.close,volume:b.volume};cache.add(normalizeBar(raw,{label:'START',decisionTimestamp:b.availableAt}));barCount++;}normalized.set(symbol,cache.prefix(symbol,date+'T15:30:00+09:00'));}normalizedBySession.set(date,normalized);}
  for(const e of x.input.events){if(e.featureStatus!=='READY')continue;const bars=normalizedBySession.get(e.sessionDate).get(e.symbol);const r=stream.decide(e,bars);for(let i=0;i<2;i++){assert.deepEqual(JSON.parse(JSON.stringify(r.event.directionFeatures[i])),e.directionFeatures[i],`FEATURE_PARITY:${e.eventId}`);pairCount++;}if(r.opportunity)reconstructed.push(r.opportunity);observations.push({id:e.eventId,pair:r.pair,action:r.action});}
  const referenceOpps=replayFirstEnter(x.input.events,JSON.parse(x.modelBytes),x.input.barsBySession);
  assert.deepEqual(JSON.parse(JSON.stringify(reconstructed)),referenceOpps,'FIRST_ENTER_SCORE_RISK_PARITY');
  const exits=[],steps=[];
  for(const t of x.eligible){
    const manager=new Bar5Manager({eventId:t.eventId,symbol:t.symbol,direction:t.direction==='LONG'?1:-1,entryPrice:t.entryPrice,entryTimestamp:t.entryTimestamp,usedPathIdentity:t.sessionDate<='2026-07-30'?'4dd18c66586706aebc19775c718d0fca2fb1ac569d40e8746f85aae502a44a70':'b28bf1931a2fc3332b0c83306523b0d0838d9776b3fc66cb8587b305170ac521'});
    const rows=(t.management?.v4??t.v4.managementDecisions??[]).map(d=>({timestamp:d.timestamp,n:Number(d.baseScore?.state?.elapsedBars??d.holdingBars)})).sort((a,b)=>a.n-b.n);
    let decision=null;
    for(const row of rows){assert.equal(row.n,manager.n+1,'MANAGEMENT_GRID_GAP');const isExit=Date.parse(row.timestamp)===Date.parse(t.v4.exitTimestamp);const v4={action:isExit?'EXIT':'HOLD',timestamp:row.timestamp,...(isExit?{exitPrice:Number(t.v4.exitPrice),exitReason:t.v4.exitReason}:{})};const result=manager.step({timestamp:row.timestamp,close:x.barCloseAt(t.symbol,row.timestamp),v4});steps.push(result);if(result.decision){decision=result.decision;break;}}
    assert.ok(decision,`EXIT_NOT_REACHED:${t.eventId}`);const expected=runBar5Adapter(t,{barCloseAt:x.barCloseAt});
    for(const k of ['exitTimestamp','exitPrice','exitReason','classification'])assert.deepEqual(decision[k],expected[k],`BAR5_STEP_PARITY:${t.eventId}:${k}`);
    exits.push(decision);
  }
  const reference=simulatePhaseB({opportunities:x.paired,trades:x.eligible,allocationId:'V3_B_RISK',exitId:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5',barCloseAt:x.barCloseAt,marks:x.input.marks,budgetDivisor:3});
  const events=new Map(),at=(timestamp,sessionDate)=>{if(!events.has(timestamp))events.set(timestamp,{timestamp,sessionDate,marks:[],entries:[],exitDecisions:[]});return events.get(timestamp);};
  for(const m of x.input.marks)at(m.timestamp,m.sessionDate).marks.push(m);
  for(const e of x.paired)at(e.decisionTimestamp,e.sessionDate).entries.push(e);
  for(const e of exits)at(e.exitTimestamp,e.exitTimestamp.slice(0,10)).exitDecisions.push(e);
  const ledger=createOfflineShadowLedger();for(const e of [...events.values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)))ledger.step(e);
  const actual=ledger.snapshot();assert.deepEqual(actual.ledgerTrace,reference.ledgerTrace,'ALL_12_INVARIANTS_AND_TRACE_PARITY');assert.deepEqual(actual.decisions,reference.decisions,'QUANTITY_CASH_REJECTION_PARITY');assert.deepEqual(actual.closedTrades,reference.closedTrades,'CLOSED_TRADE_PNL_PARITY');assert.deepEqual(actual.curve,reference.curve,'MTM_DRAWDOWN_INPUT_PARITY');
  return {summary:{status:'USED_FIXTURE_DOWNSTREAM_PARITY_PASS',scope:'A+B_DEVELOPMENT_NOT_REALTIME_NOT_OOS',sourceHead:'84b296102b85ab2909385a8f3ee7ef336c9b6129',freezeSha256:FREEZE,sourceBundleHash:hash(sources.map(({path:p,sha256})=>({name:path.relative(root,p),sha256}))),sessions:x.input.featureDates,normalizedBars:barCount,directionFeatureRows:pairCount,firstEnter:referenceOpps.length,eligibleExits:exits.length,bar5Steps:steps.length,savedPathGridGapSteps:steps.filter(x=>x.gridGap).length,savedPathGapTradeCount:new Set(steps.filter(x=>x.gridGap).map(x=>x.eventId)).size,barClock:"FROZEN_SAVED_PATH_ORDINAL_NOT_STRICT_REALTIME_GRID",ledgerEvents:actual.curve.length,ledgerInvariants:reference.ledgerAudit,accepted:actual.closedTrades.length,finalEquityJpy:reference.finalEquityJpy,entryEvidenceHash:hash(observations),exitEvidenceHash:hash(steps),ledgerEvidenceHash:hash(actual),selectorParity:'NOT_MEASURED_REFERENCE_SELECTION_LINEAGE',v4LogicParity:'NOT_MEASURED_SAVED_CURRENT_DECISION_FEED',realSourceTimingParity:'NOT_MEASURED',reservedDataOpened:false,safety:SAFETY},detail:{observations,steps,ledger:actual}};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const args=process.argv.slice(2);assert.equal(args.length,4,'USE --used-fixtures DIR --output NEW_DIR');assert.equal(args[0],'--used-fixtures');assert.equal(args[2],'--output');const result=historicalParity(path.resolve(args[1]));fs.mkdirSync(args[3],{recursive:false});
  const log=new EvidenceLog(path.join(args[3],'historical-evidence.jsonl'));try{log.append('USED_FIXTURE_PARITY',result.detail);log.append('SUMMARY',result.summary);}finally{log.close();}
  fs.writeFileSync(path.join(args[3],'summary.json'),JSON.stringify(result.summary,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result.summary));
}
