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

import {summarizeManagementReadiness,combineManagementReadiness,managementIntegrity} from './lib/phase57-exit-v4-20session-runtime.mjs';

const hash=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const cfg=read(process.env.DIAGNOSTIC_CONFIG??'predict/research/phase57-exit-v4-20session-diagnostic-v1.json');
const input=process.env.INPUT_DIR??'artifacts/diagnostic-input';
const candidatePath=process.env.CANDIDATE_MODEL??'artifacts/input/candidate/candidate-model.json';
const snapshotPath=process.env.ANALOG_SNAPSHOT;
const out=process.env.OUTPUT_DIR??'artifacts/phase57-exit-v4-20session-measurement';
assert(snapshotPath&&fs.existsSync(snapshotPath),'ANALOG_SNAPSHOT_REQUIRED');
assert.equal(cfg.sessions.length,Number(cfg.expectedSessionCount??20));assert.equal(cfg.minimumCausalNeighbors,30);
fs.mkdirSync(out,{recursive:true});
const candidateBytes=fs.readFileSync(candidatePath);assert.equal(hash(candidateBytes),cfg.lockedUpstream.candidateModelSha256,'CANDIDATE_SHA_MISMATCH');
const model=JSON.parse(candidateBytes);assert.equal(model.threshold,0.6);assert.equal(model.selectorModelDigest,CONTRACT.selectorModelDigest);assert.equal(model.selectorFreezeSHA,CONTRACT.selectorFreezeSHA);
for(const v of Object.values(cfg.safety))assert.equal(v,false,'SAFETY_FLAG_CHANGED');

const snapshotBytes=fs.readFileSync(snapshotPath);assert.equal(hash(snapshotBytes),PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,'ANALOG_SNAPSHOT_SHA_MISMATCH');
const history=buildP252PinnedHistoricalSessions({snapshot:JSON.parse(snapshotBytes),snapshotSha256:hash(snapshotBytes)});
const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:history.sessions});
assert(analogPool.length>=30,'ANALOG_POOL_TOO_SMALL');
const analogLatest=[...new Set(analogPool.map(r=>r.sessionDate))].sort().at(-1);
if(cfg.causalAnalogMode!=='PER_EVENT_STRICT_PRE_SESSION_AND_FULLY_REALIZED')assert(analogLatest<cfg.sessions[0].sessionDate,'ANALOG_NOT_CAUSAL_FOR_DIAGNOSTIC');

const events=[],barsBySessionSymbol=new Map();
for(const {sessionDate} of cfg.sessions){
  const mf=path.join(input,`${sessionDate}.manifest.json`),ff=path.join(input,`${sessionDate}.features.json.gz`),bf=path.join(input,`${sessionDate}.bars.json.gz`);
  assert(fs.existsSync(mf)&&fs.existsSync(ff)&&fs.existsSync(bf),`MISSING_SESSION_BUNDLE:${sessionDate}`);
  const m=read(mf);assert.equal(m.sessionDate,sessionDate);assert.equal(m.labelsGenerated,false);assert.equal(m.outcomeMeasured,false);
  const featureBytes=gunzipSync(fs.readFileSync(ff));
  assert.equal(hash(featureBytes),m.featureSha256,'FEATURE_BUNDLE_SHA_MISMATCH');
  const bundle=JSON.parse(featureBytes);assert.equal(bundle.sessionDate,sessionDate);
  for(const e of bundle.events)events.push(e);
  const barBytes=gunzipSync(fs.readFileSync(bf));
  assert.equal(hash(barBytes),m.barsSha256,'BAR_BUNDLE_SHA_MISMATCH');
  const barEntries=JSON.parse(barBytes);
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
const pathOutcome=(entryPrice,path,direction,cost)=>{
  assert(path.length>0,'EMPTY_EXIT_PATH');
  const favorable=path.map(b=>dirRet(entryPrice,direction==='LONG'?b.high:b.low,direction));
  const adverse=path.map(b=>dirRet(entryPrice,direction==='LONG'?b.low:b.high,direction));
  const grossReturnPct=dirRet(entryPrice,path.at(-1).close,direction);
  const mfePct=Math.max(0,...favorable),maePct=Math.min(0,...adverse);
  return {exitTimestamp:path.at(-1).timestamp,exitPrice:path.at(-1).close,exitReason:'HORIZON_END',barsHeld:path.length,grossReturnPct,netReturnPct:grossReturnPct-cost,mfePct,maePct,givebackPct:Math.max(0,mfePct-grossReturnPct),captureRatio:mfePct>0?grossReturnPct/mfePct:null};
};
const tradeRows=[];
for(const e of entered){
  const bars=(barsBySessionSymbol.get(`${e.sessionDate}|${e.symbol}`)??[]).filter(regular).sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));
  const entryTime=Date.parse(e.decisionTimestamp),entryPrice=Number(e.priceReference);assert(Number.isFinite(entryPrice)&&entryPrice>0,'INVALID_ENTRY_PRICE');
  const context=bars.filter(b=>Date.parse(b.availableAt)<=entryTime).map(converted);
  const future=bars.filter(b=>Date.parse(b.availableAt)>entryTime).map(converted);
  if(!future.length)continue;
  const row={entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,sessionDate:e.sessionDate,direction:e.direction,signalDirection:e.direction,entryPrice,contextBars:context,futureBars:future};
  const evaluationAnalogPool=cfg.causalAnalogMode==='PER_EVENT_STRICT_PRE_SESSION_AND_FULLY_REALIZED'
    ? analogPool.filter(a=>a.sessionDate<e.sessionDate&&Date.parse(a.fullyRealizedAt)<entryTime)
    : analogPool;
  assert(evaluationAnalogPool.length>=cfg.minimumCausalNeighbors,'CAUSAL_ANALOG_POOL_TOO_SMALL');
  const v3=simulateP25ExitV3DualGate({row,analogPool:evaluationAnalogPool,roundTripCostPct:cfg.roundTripCostPct});
  const v4=simulateP25ExitV4({row,analogPool:evaluationAnalogPool,roundTripCostPct:cfg.roundTripCostPct});
  const fixedFuture=future.slice(0,12);
  const fixed12=pathOutcome(entryPrice,fixedFuture,e.direction,cfg.roundTripCostPct);
  const sessionEnd=pathOutcome(entryPrice,future,e.direction,cfg.roundTripCostPct);
  sessionEnd.exitReason='SESSION_END';
  const evLabels=labels(e,bars),first=evLabels[1]?.[e.direction]??null,l3=evLabels[3]?.[e.direction]??null,l6=evLabels[6]?.[e.direction]??null;
  const adverse=Boolean(first&&first.mae>0);
  const recoveredBy3Close=Boolean(adverse&&l3&&l3.gross>0),recoveredBy6Close=Boolean(adverse&&l6&&l6.gross>0);
  const recoveredBy3Touch=Boolean(adverse&&l3&&l3.mfe>0),recoveredBy6Touch=Boolean(adverse&&l6&&l6.mfe>0);
  const remainedLoserBy6=Boolean(adverse&&l6&&l6.gross<=0);
  const readiness=summarizeManagementReadiness([...v3.managementDecisions,...v4.managementDecisions],cfg.minimumCausalNeighbors);
  const minNeighbor=readiness.minimumScoredNeighbors, fallbackCount=readiness.insufficient;
  const sideFeature=(e.directionFeatures??[]).find(x=>(e.direction==='LONG'?1:-1)===Number(x.direction));
  const priorVolumes=context.slice(-5).map(x=>Number(x.volume)).filter(Number.isFinite);
  const priorMeanVolume=priorVolumes.length===5?mean(priorVolumes):null;
  const firstBarVolumeRatio=first&&priorMeanVolume>0?Number(future[0]?.volume)/priorMeanVolume:null;
  tradeRows.push({eventId:e.eventId,sessionDate:e.sessionDate,symbol:e.symbol,direction:e.direction,entryTimestamp:e.decisionTimestamp,entryPrice,hybridRank:e.hybridRank??null,hybridScore:e.hybridScore??null,longProbability:e.longProbability,shortProbability:e.shortProbability,entryFeatures:{directionalVwapDistancePct:sideFeature?.features?.directionalVwapDistancePct??null,relativeVolume5:sideFeature?.features?.relativeVolume5??null,hybridReciprocalRank:sideFeature?.features?.hybridReciprocalRank??(Number(e.hybridRank)>0?1/Number(e.hybridRank):null),firstBarVolumeRatio},entryQuality:{h1:first,h3:l3,h6:l6,immediateAdverse:adverse,recoveredBy3Close,recoveredBy6Close,recoveredBy3Touch,recoveredBy6Touch,remainedLoserBy6},fixed12,sessionEnd,v3:{...v3,managementDecisions:undefined},v4:{...v4,managementDecisions:undefined},management:{v3:v3.managementDecisions,v4:v4.managementDecisions},causal:{evaluationAnalogPoolCount:evaluationAnalogPool.length,minimumObservedNeighborCount:Number.isFinite(minNeighbor)?minNeighbor:null,insufficientFallbackCount:fallbackCount,readiness}});
}

const armMetrics=name=>{const rs=tradeRows.map(r=>r[name]).filter(Boolean),nets=rs.map(x=>x.netReturnPct),wins=nets.filter(x=>x>0),loss=nets.filter(x=>x<0),ordered=tradeRows.map(r=>r[name]?.netReturnPct).filter(Number.isFinite);let eq=0,peak=0,maxDd=0;for(const x of ordered){eq+=x;peak=Math.max(peak,eq);maxDd=Math.min(maxDd,eq-peak);}const reasons=Object.fromEntries([...new Set(rs.map(x=>x.exitReason))].sort().map(reason=>[reason,rs.filter(x=>x.exitReason===reason).length]));const paired=tradeRows.filter(r=>r[name]&&r.fixed12);return {n:rs.length,netReturnPct:nets.reduce((s,x)=>s+x,0),profitFactor:loss.length?wins.reduce((s,x)=>s+x,0)/Math.abs(loss.reduce((s,x)=>s+x,0)):null,winRate:mean(nets.map(x=>Number(x>0))),averageTradePct:mean(nets),medianTradePct:median(nets),maxDrawdownPct:maxDd,meanMfePct:mean(rs.map(x=>x.mfePct).filter(Number.isFinite)),meanMaePct:mean(rs.map(x=>x.maePct).filter(Number.isFinite)),meanCaptureRatio:mean(rs.map(x=>x.captureRatio).filter(Number.isFinite)),meanGivebackPct:mean(rs.map(x=>x.givebackPct).filter(Number.isFinite)),meanHoldingBars:mean(rs.map(x=>x.barsHeld).filter(Number.isFinite)),earlyVsFixedRate:mean(paired.map(r=>Number(r[name].barsHeld<r.fixed12.barsHeld))),lateVsFixedRate:mean(paired.map(r=>Number(r[name].barsHeld>r.fixed12.barsHeld))),meanAdditionalLossAvoidedPct:mean(paired.map(r=>Math.max(0,r[name].netReturnPct-r.fixed12.netReturnPct))),exitReasonDistribution:reasons};};
const fixedMetrics=armMetrics('fixed12'),sessionMetrics=armMetrics('sessionEnd'),v3Metrics=armMetrics('v3'),v4Metrics=armMetrics('v4');
const q=h=>tradeRows.map(r=>r.entryQuality[`h${h}`]).filter(Boolean);
const symbols=Object.entries(tradeRows.reduce((m,r)=>(m[r.symbol]=(m[r.symbol]??0)+1,m),{})).sort((a,b)=>b[1]-a[1]);
const share=n=>tradeRows.length?symbols.slice(0,n).reduce((s,x)=>s+x[1],0)/tradeRows.length:null;
const immediate=tradeRows.filter(r=>r.entryQuality.immediateAdverse);
const timeBucket=iso=>{const hm=jstHm(iso);if(hm<'10:00')return '09:00-09:55';if(hm<'11:30')return '10:00-11:25';if(hm<'14:00')return '12:30-13:55';return '14:00-15:25';};
const timeOfDayDistribution=Object.fromEntries(['09:00-09:55','10:00-11:25','12:30-13:55','14:00-15:25'].map(bucket=>[bucket,tradeRows.filter(r=>timeBucket(r.entryTimestamp)===bucket).length]));
const entryQuality={firstEnter:entered.length,pairedFirstEnter:tradeRows.length,missingOutcomePathEvents:entered.length-tradeRows.length,sessionsMeasured:new Set(tradeRows.map(r=>r.sessionDate)).size,firstEnterPerSession:entered.length/cfg.sessions.length,uniqueSymbols:symbols.length,LONG:tradeRows.filter(r=>r.direction==='LONG').length,SHORT:tradeRows.filter(r=>r.direction==='SHORT').length,longShortRatio:tradeRows.filter(r=>r.direction==='SHORT').length?tradeRows.filter(r=>r.direction==='LONG').length/tradeRows.filter(r=>r.direction==='SHORT').length:null,top1SymbolShare:share(1),top3SymbolShare:share(3),top5SymbolShare:share(5),topSymbols:symbols.slice(0,10),timeOfDayDistribution,horizons:Object.fromEntries([1,3,6].map(h=>{const xs=q(h);return [h,{n:xs.length,meanGrossBps:mean(xs.map(x=>x.gross)),medianGrossBps:median(xs.map(x=>x.gross)),meanNetBps:mean(xs.map(x=>x.net)),medianNetBps:median(xs.map(x=>x.net)),positiveGrossRate:mean(xs.map(x=>Number(x.gross>0))),positiveNetRate:mean(xs.map(x=>Number(x.net>0))),meanMfeBps:mean(xs.map(x=>x.mfe)),meanMaeBps:mean(xs.map(x=>x.mae)),meanTimeToMfeMinutes:mean(xs.map(x=>x.timeToMfe))}];})),immediateAdverseCount:immediate.length,immediateAdverseRate:tradeRows.length?immediate.length/tradeRows.length:null,recoveryBy3CloseAmongImmediateAdverse:immediate.length?mean(immediate.map(r=>Number(r.entryQuality.recoveredBy3Close))):null,recoveryBy6CloseAmongImmediateAdverse:immediate.length?mean(immediate.map(r=>Number(r.entryQuality.recoveredBy6Close))):null,recoveryBy3TouchAmongImmediateAdverse:immediate.length?mean(immediate.map(r=>Number(r.entryQuality.recoveredBy3Touch))):null,recoveryBy6TouchAmongImmediateAdverse:immediate.length?mean(immediate.map(r=>Number(r.entryQuality.recoveredBy6Touch))):null,remainedLoserBy6AmongImmediateAdverse:immediate.length?mean(immediate.map(r=>Number(r.entryQuality.remainedLoserBy6))):null};
const readiness=combineManagementReadiness(tradeRows.map(r=>r.causal.readiness));
const causal={readiness,analogPoolCount:analogPool.length,analogLatestSessionDate:analogLatest,minimumRequiredNeighbors:cfg.minimumCausalNeighbors,minimumObservedNeighborCount:readiness.minimumScoredNeighbors,insufficientFallbacks:tradeRows.reduce((s,r)=>s+r.causal.insufficientFallbackCount,0)};
const classify=()=>{const integrity=managementIntegrity(readiness,tradeRows.length);if(integrity!=='SCORING_READY')return `${cfg.schemaId==='PHASE57_EXIT_BLOCK_A_UNSEEN_VALIDATION_V1'?'BLOCK_A':'20SESSION_DIAGNOSTIC'}_${integrity}`;if(cfg.schemaId==='PHASE57_EXIT_BLOCK_A_UNSEEN_VALIDATION_V1')return 'BLOCK_A_BASE_MEASUREMENT_COMPLETE';const h3=entryQuality.horizons[3],entryGood=Number(h3?.meanNetBps)>0&&Number(h3?.positiveNetRate)>=0.5;const v34Weak=entryGood&&v3Metrics.averageTradePct<fixedMetrics.averageTradePct&&v4Metrics.averageTradePct<fixedMetrics.averageTradePct;return entryGood?(v34Weak?'20SESSION_DIAGNOSTIC_COMPLETE_ENTRY_GOOD_EXIT_V34_WEAK':'20SESSION_DIAGNOSTIC_COMPLETE_ENTRY_GOOD_EXIT_V34_USABLE'):'20SESSION_DIAGNOSTIC_COMPLETE_ENTRY_WEAK';};
const access=cfg.schemaId==='PHASE57_EXIT_BLOCK_A_UNSEEN_VALIDATION_V1'?{blockAUnseenOutcomeSessions:cfg.sessions.length,old20Reused:0,automaticExpansion:0}:{diagnosticOutcomeSessions:cfg.sessions.length,protectedExternal:0,freshExternalOutsideDiagnostic:0,automaticExpansion:0};
const report={schemaVersion:1,status:classify(),role:cfg.role,providerLineage:cfg.providerLineage??'JQUANTS_SESSION_LEVEL_NO_MIXING',sessions:cfg.sessions.map(x=>x.sessionDate),sessionCount:cfg.sessions.length,entryQuality,arms:{fixed12:fixedMetrics,sessionEnd:sessionMetrics,v3:v3Metrics,v4:v4Metrics},pairedDelta:{v3MinusFixedAvgPct:v3Metrics.averageTradePct-fixedMetrics.averageTradePct,v4MinusFixedAvgPct:v4Metrics.averageTradePct-fixedMetrics.averageTradePct,v4MinusV3AvgPct:v4Metrics.averageTradePct-v3Metrics.averageTradePct},causal:{...causal,causalAnalogMode:cfg.causalAnalogMode??'GLOBAL_PRE_SESSION',evaluationAnalogPoolCountRange:tradeRows.length?{min:Math.min(...tradeRows.map(r=>r.causal.evaluationAnalogPoolCount??analogPool.length)),max:Math.max(...tradeRows.map(r=>r.causal.evaluationAnalogPoolCount??analogPool.length))}:null,pitViolations:0},policy:{v3:P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,v4:P25_EXIT_V4_POLICY_SHA256,analogSnapshot:PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,candidate:cfg.lockedUpstream.candidateModelSha256},access,safety:cfg.safety};
// Persist a truthful blocked/capacity report; never treat warmup/neutral as neighbor failure.
if(managementIntegrity(readiness,tradeRows.length)==='INTEGRITY_BLOCKED')process.exitCode=20;
fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');
fs.writeFileSync(path.join(out,'trades.json'),JSON.stringify(tradeRows,null,2)+'\n');
fs.writeFileSync(path.join(out,'report.json.sha256'),`${hash(fs.readFileSync(path.join(out,'report.json')))}  report.json\n`);
console.log('PHASE57_20SESSION_RESULT='+JSON.stringify(report));
