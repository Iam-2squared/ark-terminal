import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {stateful,mean,median} from './lib/phase57-entry-development-measure.mjs';
import {CONTRACT} from './lib/phase57-minimal-stateful-entry.mjs';
import {runDynamicStateV1,DYNAMIC_STATE_V1} from './lib/phase57-exit-v5-dynamic-state.mjs';
import {buildP252PinnedHistoricalSessions,PHASE57_P25_2K_POLICY} from '../predict/daytrade/phase57-p25-2k-pinned-history-bridge.js';
import {buildP25DataDrivenExitAnalogPool} from '../predict/daytrade/phase57-p25-data-driven-exit.js';
import {simulateP25ExitV4,P25_EXIT_V4_POLICY_SHA256} from '../predict/daytrade/phase57-p25-exit-v4-structural-risk.js';

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const cfg=read(process.env.DIAGNOSTIC_CONFIG??'predict/research/phase57-exit-v5-block-c-unseen-v1.json');
const freeze=read(cfg.candidate.freezePath);
const input=process.env.INPUT_DIR??'artifacts/block-c-input';
const candidatePath=process.env.CANDIDATE_MODEL??'artifacts/input/candidate/candidate-model.json';
const snapshotPath=process.env.ANALOG_SNAPSHOT;
const out=process.env.OUTPUT_DIR??'artifacts/phase57-exit-v5-block-c';

assert.equal(cfg.schemaId,'PHASE57_EXIT_V5_BLOCK_C_UNSEEN_V1');
assert.equal(cfg.sessions.length,cfg.expectedSessionCount);
assert.equal(freeze.status,'FROZEN_FOR_NEXT_UNSEEN_VALIDATION_NOT_PROMOTED');
assert.equal(freeze.architecture,'CAUSAL_DYNAMIC_STATE_OVER_FROZEN_V4_CONTINUATION');
assert.equal(freeze.stateMachine.observationHorizonBars,6);
assert.equal(freeze.stateMachine.freeReturnThresholds,0);
assert.equal(DYNAMIC_STATE_V1.observationHorizonBars,6);
assert.equal(DYNAMIC_STATE_V1.adverseBoundaryPct,0);
assert.equal(DYNAMIC_STATE_V1.reclaimBoundaryPct,0);
for(const v of Object.values(cfg.safety))assert.equal(v,false,'SAFETY_FLAG_CHANGED');
assert(snapshotPath&&fs.existsSync(snapshotPath),'ANALOG_SNAPSHOT_REQUIRED');
fs.mkdirSync(out,{recursive:true});

const candidateBytes=fs.readFileSync(candidatePath);assert.equal(hash(candidateBytes),cfg.lockedUpstream.candidateModelSha256,'CANDIDATE_SHA_MISMATCH');
const model=JSON.parse(candidateBytes);assert.equal(model.threshold,0.6);assert.equal(model.selectorModelDigest,CONTRACT.selectorModelDigest);assert.equal(model.selectorFreezeSHA,CONTRACT.selectorFreezeSHA);
const snapshotBytes=fs.readFileSync(snapshotPath);assert.equal(hash(snapshotBytes),PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,'ANALOG_SNAPSHOT_SHA_MISMATCH');
const history=buildP252PinnedHistoricalSessions({snapshot:JSON.parse(snapshotBytes),snapshotSha256:hash(snapshotBytes)});
const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:history.sessions});
assert(analogPool.length>=cfg.minimumCausalNeighbors,'ANALOG_POOL_TOO_SMALL');

const events=[],barsBySessionSymbol=new Map();
for(const {sessionDate} of cfg.sessions){
  const mf=path.join(input,`${sessionDate}.manifest.json`),ff=path.join(input,`${sessionDate}.features.json.gz`),bf=path.join(input,`${sessionDate}.bars.json.gz`);
  assert(fs.existsSync(mf)&&fs.existsSync(ff)&&fs.existsSync(bf),`MISSING_SESSION_BUNDLE:${sessionDate}`);
  const m=read(mf);assert.equal(m.sessionDate,sessionDate);assert.equal(m.labelsGenerated,false);assert.equal(m.outcomeMeasured,false);
  const featureBytes=gunzipSync(fs.readFileSync(ff));assert.equal(hash(featureBytes),m.featureSha256,'FEATURE_BUNDLE_SHA_MISMATCH');
  const bundle=JSON.parse(featureBytes);for(const e of bundle.events)events.push(e);
  const barBytes=gunzipSync(fs.readFileSync(bf));assert.equal(hash(barBytes),m.barsSha256,'BAR_BUNDLE_SHA_MISMATCH');
  for(const e of JSON.parse(barBytes))barsBySessionSymbol.set(`${sessionDate}|${e.symbol}`,e.bars);
}
assert.equal(new Set(events.map(e=>e.eventId)).size,events.length,'DUPLICATE_EVENT');
const decisionInputs=events.map(({eventId,symbolSessionId,stateBefore,directionFeatures})=>({eventId,symbolSessionId,stateBefore,directionFeatures}));
const decision=stateful(decisionInputs,model,0.6);const byId=new Map(events.map(e=>[e.eventId,e]));
const entered=decision.ledger.filter(x=>x.status==='ENTER').map(x=>({...byId.get(x.eventId),direction:x.direction,longProbability:x.longProbability,shortProbability:x.shortProbability}));
const dirRet=(a,b,d)=>(Number(b)/Number(a)-1)*100*(d==='LONG'?1:-1);
const jstHm=iso=>new Date(Date.parse(iso)+32400000).toISOString().slice(11,16);
const regular=b=>{const hm=jstHm(b.timestamp);return (hm>='09:00'&&hm<'11:30')||(hm>='12:30'&&hm<'15:30');};
const converted=b=>({timestamp:b.availableAt??new Date(Date.parse(b.timestamp)+300000).toISOString(),open:b.open,high:b.high,low:b.low,close:b.close,volume:b.volume});
const pathOutcome=(entryPrice,p,direction,cost)=>{assert(p.length>0);const fav=p.map(b=>dirRet(entryPrice,direction==='LONG'?b.high:b.low,direction)),adv=p.map(b=>dirRet(entryPrice,direction==='LONG'?b.low:b.high,direction));const grossReturnPct=dirRet(entryPrice,p.at(-1).close,direction),mfePct=Math.max(0,...fav),maePct=Math.min(0,...adv);return {exitTimestamp:p.at(-1).timestamp,exitPrice:p.at(-1).close,exitReason:'HORIZON_END',barsHeld:p.length,grossReturnPct,netReturnPct:grossReturnPct-cost,mfePct,maePct,givebackPct:Math.max(0,mfePct-grossReturnPct),captureRatio:mfePct>0?grossReturnPct/mfePct:null};};

const trades=[];
for(const e of entered){
  const bars=(barsBySessionSymbol.get(`${e.sessionDate}|${e.symbol}`)??[]).filter(regular).sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));
  const entryTime=Date.parse(e.decisionTimestamp),entryPrice=Number(e.priceReference);if(!Number.isFinite(entryPrice)||entryPrice<=0)continue;
  const context=bars.filter(b=>Date.parse(b.availableAt)<=entryTime).map(converted),future=bars.filter(b=>Date.parse(b.availableAt)>entryTime).map(converted);if(!future.length)continue;
  const row={entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,sessionDate:e.sessionDate,direction:e.direction,signalDirection:e.direction,entryPrice,contextBars:context,futureBars:future};
  const evaluationAnalogPool=analogPool.filter(a=>a.sessionDate<e.sessionDate&&Date.parse(a.fullyRealizedAt)<entryTime);
  const causalEligible=evaluationAnalogPool.length>=cfg.minimumCausalNeighbors;
  const v4=causalEligible?simulateP25ExitV4({row,analogPool:evaluationAnalogPool,roundTripCostPct:cfg.roundTripCostPct}):null;
  const fixed12=pathOutcome(entryPrice,future.slice(0,Math.min(12,future.length)),e.direction,cfg.roundTripCostPct),sessionEnd=pathOutcome(entryPrice,future,e.direction,cfg.roundTripCostPct);sessionEnd.exitReason='SESSION_END';
  const managedBars=future.map((b,i)=>({elapsedBars:i+1,currentReturnPct:dirRet(entryPrice,b.close,e.direction),timestamp:b.timestamp,close:b.close}));
  const v5=causalEligible&&v4?runDynamicStateV1({managedBars,continuationExit:v4}):null;
  trades.push({eventId:e.eventId,sessionDate:e.sessionDate,symbol:e.symbol,direction:e.direction,entryTimestamp:e.decisionTimestamp,causalEligible,evaluationAnalogPoolCount:evaluationAnalogPool.length,fixed12,sessionEnd,v4,v5,dynamicState:v5?.dynamicState??null,dynamicReason:v5?.dynamicReason??null,stateTransitions:v5?.stateTransitions??[]});
}

const metrics=(rows,key)=>{const rs=rows.map(r=>r[key]).filter(Boolean),nets=rs.map(x=>x.netReturnPct),wins=nets.filter(x=>x>0),loss=nets.filter(x=>x<0);let eq=0,peak=0,maxDd=0;for(const x of nets){eq+=x;peak=Math.max(peak,eq);maxDd=Math.min(maxDd,eq-peak);}return {n:rs.length,netSumPct:nets.reduce((s,x)=>s+x,0),profitFactor:loss.length?wins.reduce((s,x)=>s+x,0)/Math.abs(loss.reduce((s,x)=>s+x,0)):null,winRate:mean(nets.map(x=>Number(x>0))),averageTradePct:mean(nets),medianTradePct:median(nets),maxDrawdownProxyPct:maxDd,meanHoldingBars:mean(rs.map(x=>x.barsHeld)),mfeCapture:mean(rs.map(x=>x.captureRatio).filter(Number.isFinite)),meanGivebackPct:mean(rs.map(x=>x.givebackPct).filter(Number.isFinite))};};
const eligible=trades.filter(t=>t.causalEligible&&t.v4&&t.v5),arms=Object.fromEntries(['fixed12','sessionEnd','v4','v5'].map(k=>[k,metrics(k==='fixed12'||k==='sessionEnd'?trades:eligible,k)]));
const deltas=eligible.map(t=>({eventId:t.eventId,sessionDate:t.sessionDate,symbol:t.symbol,direction:t.direction,dynamicReason:t.dynamicReason,deltaVsV4Pct:t.v5.netReturnPct-t.v4.netReturnPct}));
const abs=deltas.map(x=>Math.abs(x.deltaVsV4Pct)).filter(x=>x>1e-12).sort((a,b)=>b-a),sumAbs=abs.reduce((s,x)=>s+x,0),top1AbsShare=sumAbs?abs[0]/sumAbs:0;
const deltaVsV4=arms.v5.netSumPct-arms.v4.netSumPct,ddWorsening=Math.abs(Math.min(0,arms.v5.maxDrawdownProxyPct))-Math.abs(Math.min(0,arms.v4.maxDrawdownProxyPct));
const enoughCausal=eligible.length>=10;
const supportive=enoughCausal&&deltaVsV4>0&&Number(arms.v5.profitFactor)>=Number(arms.v4.profitFactor)&&ddWorsening<=1&&top1AbsShare<0.8;
const reject=enoughCausal&&(deltaVsV4<=0||ddWorsening>1);
const finalDecision=!eligible.length?'BLOCK_C_INVALID_CAUSAL_COVERAGE':!enoughCausal?'BLOCK_C_MIXED_INSUFFICIENT_CAUSAL_SAMPLE':supportive?'BLOCK_C_SUPPORTIVE':reject?'BLOCK_C_REJECT':'BLOCK_C_MIXED';
const stateCounts={firstBarNonAdverse:eligible.filter(t=>t.dynamicReason==='FIRST_BAR_NON_ADVERSE_CONTINUATION').length,recovered:eligible.filter(t=>t.dynamicReason==='RECLAIMED_BEFORE_HORIZON_CONTINUATION').length,bar6Exit:eligible.filter(t=>t.dynamicReason==='NO_RECLAIM_BY_HORIZON_EXIT').length,horizonFallback:eligible.filter(t=>t.dynamicReason==='HORIZON_NOT_AVAILABLE_CONTINUATION_FALLBACK').length};
const report={schemaVersion:1,status:eligible.length?'BLOCK_C_COMPLETE':'BLOCK_C_INVALID',finalDecision,role:cfg.role,sessions:cfg.sessions.map(x=>x.sessionDate),sessionCount:cfg.sessions.length,firstEnter:entered.length,trades:trades.length,causalEligible:eligible.length,causalIneligible:trades.length-eligible.length,LONG:trades.filter(x=>x.direction==='LONG').length,SHORT:trades.filter(x=>x.direction==='SHORT').length,stateCounts,arms,paired:{deltaVsV4PctPoints:deltaVsV4,top1AbsoluteContributionShare:top1AbsShare,nonZeroDifferenceTrades:abs.length,drawdownWorseningPctPoints:ddWorsening,deltas},candidate:{freezeStatus:freeze.status,candidateId:freeze.candidateId,retunedAfterOpen:false,overrideAdded:false,horizonChanged:false},causal:{minimumRequiredNeighbors:cfg.minimumCausalNeighbors,pitViolations:0,analogPoolCount:analogPool.length,eligibleTrades:eligible.length,validDecision:enoughCausal},policy:{v4:P25_EXIT_V4_POLICY_SHA256,candidate:cfg.lockedUpstream.candidateModelSha256},safety:cfg.safety};
fs.writeFileSync(path.join(out,'block-c-report.json'),JSON.stringify(report,null,2)+'\n');fs.writeFileSync(path.join(out,'trades.json'),JSON.stringify(trades,null,2)+'\n');fs.writeFileSync(path.join(out,'block-c-report.json.sha256'),`${hash(fs.readFileSync(path.join(out,'block-c-report.json')))}  block-c-report.json\n`);
console.log('PHASE57_EXIT_V5_BLOCK_C_RESULT='+JSON.stringify({finalDecision,firstEnter:entered.length,trades:trades.length,causalEligible:eligible.length,deltaVsV4,top1AbsShare,ddWorsening,stateCounts,arms}));
