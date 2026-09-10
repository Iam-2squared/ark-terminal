import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {stateful,labels,mean,median} from './lib/phase57-entry-development-measure.mjs';
import {CONTRACT} from './lib/phase57-minimal-stateful-entry.mjs';
import {buildP252PinnedHistoricalSessions,PHASE57_P25_2K_POLICY} from '../predict/daytrade/phase57-p25-2k-pinned-history-bridge.js';
import {buildP25DataDrivenExitAnalogPool} from '../predict/daytrade/phase57-p25-data-driven-exit.js';
import {simulateP25ExitV3DualGate,P25_EXIT_V3_DUAL_GATE_POLICY_SHA256} from '../predict/daytrade/phase57-p25-exit-v3-dual-gate.js';
import {simulateP25ExitV4,P25_EXIT_V4_POLICY_SHA256} from '../predict/daytrade/phase57-p25-exit-v4-structural-risk.js';

const hash=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const cfg=read(process.env.DIAGNOSTIC_CONFIG??'predict/research/phase57-exit-v4-20session-diagnostic-v1.json');
const input=process.env.INPUT_DIR??'artifacts/diagnostic-input';
const candidatePath=process.env.CANDIDATE_MODEL??'artifacts/input/candidate/candidate-model.json';
const snapshotPath=process.env.ANALOG_SNAPSHOT;
const out=process.env.OUTPUT_DIR??'artifacts/phase57-exit-v4-20session-measurement';
assert(snapshotPath&&fs.existsSync(snapshotPath),'ANALOG_SNAPSHOT_REQUIRED');
assert.equal(cfg.sessions.length,20);assert.equal(cfg.minimumCausalNeighbors,30);
fs.mkdirSync(out,{recursive:true});
const candidateBytes=fs.readFileSync(candidatePath);assert.equal(hash(candidateBytes),cfg.lockedUpstream.candidateModelSha256,'CANDIDATE_SHA_MISMATCH');
const model=JSON.parse(candidateBytes);assert.equal(model.threshold,0.6);assert.equal(model.selectorModelDigest,CONTRACT.selectorModelDigest);assert.equal(model.selectorFreezeSHA,CONTRACT.selectorFreezeSHA);
for(const v of Object.values(cfg.safety))assert.equal(v,false,'SAFETY_FLAG_CHANGED');

const snapshotBytes=fs.readFileSync(snapshotPath);assert.equal(hash(snapshotBytes),PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,'ANALOG_SNAPSHOT_SHA_MISMATCH');
const history=buildP252PinnedHistoricalSessions({snapshot:JSON.parse(snapshotBytes),snapshotSha256:hash(snapshotBytes)});
const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:history.sessions});
assert(analogPool.length>=30,'ANALOG_POOL_TOO_SMALL');
const analogLatest=[...new Set(analogPool.map(r=>r.sessionDate))].sort().at(-1);
assert(analogLatest<cfg.sessions[0].sessionDate,'ANALOG_NOT_CAUSAL_FOR_DIAGNOSTIC');

const events=[],barsBySessionSymbol=new Map();
for(const {sessionDate} of cfg.sessions){
  const mf=path.join(input,`${sessionDate}.manifest.json`),ff=path.join(input,`${sessionDate}.features.json.gz`),bf=path.join(input,`${sessionDate}.bars.json.gz`);
  assert(fs.existsSync(mf)&&fs.existsSync(ff)&&fs.existsSync(bf),`MISSING_SESSION_BUNDLE:${sessionDate}`);
  const m=read(mf);assert.equal(m.sessionDate,sessionDate);assert.equal(m.labelsGenerated,false);assert.equal(m.outcomeMeasured,false);
  const bundle=JSON.parse(gunzipSync(fs.readFileSync(ff)));assert.equal(bundle.sessionDate,sessionDate);
  for(const e of bundle.events)events.push(e);
  const barEntries=JSON.parse(gunzipSync(fs.readFileSync(bf)));
  for(const e of barEntries)barsBySessionSymbol.set(`${sessionDate}|${e.symbol}`,e.bars);
}
assert.equal(new Set(events.map(e=>e.eventId)).size,events.length,'DUPLICATE_EVENT');
const decisionInputs=events.map(({eventId,symbolSessionId,stateBefore,directionFeatures})=>({eventId,symbolSessionId,stateBefore,directionFeatures}));
const decision=stateful(decisionInputs,model,0.6);
const byId=new Map(events.map(e=>[e.eventId,e]));
const entered=decision.ledger.filter(x=>x.status==='ENTER').map(x=>({...byId.get(x.eventId),direction:x.direction,longProbability:x.longProbability,shortProbability:x.shortProbability}));

const dirRet=(a,b,d)=>(Number(b)/Number(a)-1)*100*(d==='LONG'?1:-1);
const jstHm=iso=>new Date(Date.parse(iso)+32400000).toISOString().slice(11,16);
const regular=b=>{const hm=jstHm(b.timestamp);return (hm>='09:00'&&hm<'11:30')||(hm>='12:30'&&hm<'15:30');};
const converted=b=>({timestamp:b.availableAt??new Date(Date.parse(b.timestamp)+300000).toISOString(),open:b.open,high:b.high,low:b.low,close:b.close,volume:b.volume});
const tradeRows=[];
for(const e of entered){
  const bars=(barsBySessionSymbol.get(`${e.sessionDate}|${e.symbol}`)??[]).filter(regular).sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));
  const entryTime=Date.parse(e.decisionTimestamp),entryPrice=Number(e.priceReference);assert(Number.isFinite(entryPrice)&&entryPrice>0,'INVALID_ENTRY_PRICE');
  const context=bars.filter(b=>Date.parse(b.availableAt)<=entryTime).map(converted);
  const future=bars.filter(b=>Date.parse(b.availableAt)>entryTime).map(converted);
  if(!future.length)continue;
  const row={entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,sessionDate:e.sessionDate,direction:e.direction,signalDirection:e.direction,entryPrice,contextBars:context,futureBars:future};
  const v3=simulateP25ExitV3DualGate({row,analogPool,roundTripCostPct:cfg.roundTripCostPct});
  const v4=simulateP25ExitV4({row,analogPool,roundTripCostPct:cfg.roundTripCostPct});
  const fixedFuture=future.slice(0,12),fixedExit=fixedFuture.at(-1)??future.at(-1),sessionEnd=future.at(-1);
  const fixedGross=dirRet(entryPrice,fixedExit.close,e.direction),sessionGross=dirRet(entryPrice,sessionEnd.close,e.direction);
  const evLabels=labels(e,bars),first=evLabels[1]?.[e.direction]??null,l3=evLabels[3]?.[e.direction]??null,l6=evLabels[6]?.[e.direction]??null;
  const adverse=Boolean(first&&first.mae>0),recovered6=Boolean(adverse&&l6&&l6.mfe>0);
  const minNeighbor=Math.min(...[...v3.managementDecisions,...v4.managementDecisions].map(x=>Number(x.baseScore?.neighborCount??0)).filter(Number.isFinite));
  const fallbacks=[...v3.managementDecisions,...v4.managementDecisions].filter(x=>String(x.baseScore?.reason??'').includes('INSUFFICIENT')).length;
  tradeRows.push({eventId:e.eventId,sessionDate:e.sessionDate,symbol:e.symbol,direction:e.direction,entryTimestamp:e.decisionTimestamp,entryPrice,hybridRank:e.hybridRank??null,hybridScore:e.hybridScore??null,longProbability:e.longProbability,shortProbability:e.shortProbability,entryQuality:{h1:first,h3:l3,h6:l6,immediateAdverse:adverse,recoveredBy6:recovered6},fixed12:{exitTimestamp:fixedExit.timestamp,barsHeld:fixedFuture.length,grossReturnPct:fixedGross,netReturnPct:fixedGross-cfg.roundTripCostPct},sessionEnd:{exitTimestamp:sessionEnd.timestamp,barsHeld:future.length,grossReturnPct:sessionGross,netReturnPct:sessionGross-cfg.roundTripCostPct},v3:{...v3,managementDecisions:undefined},v4:{...v4,managementDecisions:undefined},causal:{minimumObservedNeighborCount:Number.isFinite(minNeighbor)?minNeighbor:null,insufficientFallbackCount:fallbacks}});
}

const armMetrics=name=>{const rs=tradeRows.map(r=>r[name]).filter(Boolean),nets=rs.map(x=>x.netReturnPct),wins=nets.filter(x=>x>0),loss=nets.filter(x=>x<0),ordered=tradeRows.map(r=>r[name]?.netReturnPct).filter(Number.isFinite);let eq=0,peak=0,maxDd=0;for(const x of ordered){eq+=x;peak=Math.max(peak,eq);maxDd=Math.min(maxDd,eq-peak);}return {n:rs.length,netReturnPct:nets.reduce((s,x)=>s+x,0),profitFactor:loss.length?wins.reduce((s,x)=>s+x,0)/Math.abs(loss.reduce((s,x)=>s+x,0)):null,winRate:mean(nets.map(x=>Number(x>0))),averageTradePct:mean(nets),medianTradePct:median(nets),maxDrawdownPct:maxDd,meanMfePct:mean(rs.map(x=>x.mfePct).filter(Number.isFinite)),meanMaePct:mean(rs.map(x=>x.maePct).filter(Number.isFinite)),meanCaptureRatio:mean(rs.map(x=>x.captureRatio).filter(Number.isFinite)),meanGivebackPct:mean(rs.map(x=>x.givebackPct).filter(Number.isFinite)),meanHoldingBars:mean(rs.map(x=>x.barsHeld).filter(Number.isFinite))};};
const fixedMetrics=armMetrics('fixed12'),sessionMetrics=armMetrics('sessionEnd'),v3Metrics=armMetrics('v3'),v4Metrics=armMetrics('v4');
const q=h=>tradeRows.map(r=>r.entryQuality[`h${h}`]).filter(Boolean);
const symbols=Object.entries(tradeRows.reduce((m,r)=>(m[r.symbol]=(m[r.symbol]??0)+1,m),{})).sort((a,b)=>b[1]-a[1]);
const share=n=>tradeRows.length?symbols.slice(0,n).reduce((s,x)=>s+x[1],0)/tradeRows.length:null;
const immediate=tradeRows.filter(r=>r.entryQuality.immediateAdverse),recovered=immediate.filter(r=>r.entryQuality.recoveredBy6);
const entryQuality={firstEnter:tradeRows.length,uniqueSymbols:symbols.length,LONG:tradeRows.filter(r=>r.direction==='LONG').length,SHORT:tradeRows.filter(r=>r.direction==='SHORT').length,top1SymbolShare:share(1),top3SymbolShare:share(3),top5SymbolShare:share(5),topSymbols:symbols.slice(0,10),horizons:Object.fromEntries([1,3,6].map(h=>{const xs=q(h);return [h,{n:xs.length,meanGrossBps:mean(xs.map(x=>x.gross)),meanNetBps:mean(xs.map(x=>x.net)),medianNetBps:median(xs.map(x=>x.net)),positiveNetRate:mean(xs.map(x=>Number(x.net>0))),meanMfeBps:mean(xs.map(x=>x.mfe)),meanMaeBps:mean(xs.map(x=>x.mae)),meanTimeToMfeMinutes:mean(xs.map(x=>x.timeToMfe))}];})),immediateAdverseRate:tradeRows.length?immediate.length/tradeRows.length:null,recoveryBy6AmongImmediateAdverse:immediate.length?recovered.length/immediate.length:null};
const causal={analogPoolCount:analogPool.length,analogLatestSessionDate:analogLatest,minimumRequiredNeighbors:cfg.minimumCausalNeighbors,minimumObservedNeighborCount:Math.min(...tradeRows.map(r=>r.causal.minimumObservedNeighborCount).filter(Number.isFinite)),insufficientFallbacks:tradeRows.reduce((s,r)=>s+r.causal.insufficientFallbackCount,0)};
const classify=()=>{const h3=entryQuality.horizons[3],entryGood=Number(h3?.meanNetBps)>0&&Number(h3?.positiveNetRate)>=0.5;const v34Weak=entryGood&&v3Metrics.averageTradePct<fixedMetrics.averageTradePct&&v4Metrics.averageTradePct<fixedMetrics.averageTradePct;return entryGood?(v34Weak?'20SESSION_DIAGNOSTIC_COMPLETE_ENTRY_GOOD_EXIT_V34_WEAK':'20SESSION_DIAGNOSTIC_COMPLETE_ENTRY_GOOD_EXIT_V34_USABLE'):'20SESSION_DIAGNOSTIC_COMPLETE_ENTRY_WEAK';};
const report={schemaVersion:1,status:classify(),role:cfg.role,sessions:cfg.sessions.map(x=>x.sessionDate),sessionCount:cfg.sessions.length,entryQuality,arms:{fixed12:fixedMetrics,sessionEnd:sessionMetrics,v3:v3Metrics,v4:v4Metrics},pairedDelta:{v3MinusFixedAvgPct:v3Metrics.averageTradePct-fixedMetrics.averageTradePct,v4MinusFixedAvgPct:v4Metrics.averageTradePct-fixedMetrics.averageTradePct,v4MinusV3AvgPct:v4Metrics.averageTradePct-v3Metrics.averageTradePct},causal,policy:{v3:P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,v4:P25_EXIT_V4_POLICY_SHA256,analogSnapshot:PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,candidate:cfg.lockedUpstream.candidateModelSha256},access:{diagnosticOutcomeSessions:cfg.sessions.length,protectedExternal:0,freshExternalOutsideDiagnostic:0,automaticExpansion:0},safety:cfg.safety};
assert(causal.minimumObservedNeighborCount>=cfg.minimumCausalNeighbors||tradeRows.length===0,'CAUSAL_NEIGHBOR_GATE_FAILED');
fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');
fs.writeFileSync(path.join(out,'trades.json'),JSON.stringify(tradeRows,null,2)+'\n');
fs.writeFileSync(path.join(out,'report.json.sha256'),`${hash(fs.readFileSync(path.join(out,'report.json')))}  report.json\n`);
console.log('PHASE57_20SESSION_RESULT='+JSON.stringify(report));
