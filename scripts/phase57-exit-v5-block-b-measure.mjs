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

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const cfg=read(process.env.DIAGNOSTIC_CONFIG??'predict/research/phase57-exit-v5-block-b-unseen-v1.json');
const freeze=read(cfg.candidate.freezePath);
const input=process.env.INPUT_DIR??'artifacts/block-b-input';
const candidatePath=process.env.CANDIDATE_MODEL??'artifacts/input/candidate/candidate-model.json';
const snapshotPath=process.env.ANALOG_SNAPSHOT;
const out=process.env.OUTPUT_DIR??'artifacts/phase57-exit-v5-block-b';
assert.equal(cfg.schemaId,'PHASE57_EXIT_V5_BLOCK_B_UNSEEN_V1');
assert.equal(cfg.sessions.length,cfg.expectedSessionCount);
assert.equal(freeze.status,'FROZEN_FOR_UNSEEN_VALIDATION_NOT_PROMOTED');
assert.equal(freeze.router.routeToV3When,'firstBarDirectionalCloseReturnBps <= 100 AND firstBarMaeBps >= 25');
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
  const v3=causalEligible?simulateP25ExitV3DualGate({row,analogPool:evaluationAnalogPool,roundTripCostPct:cfg.roundTripCostPct}):null;
  const v4=causalEligible?simulateP25ExitV4({row,analogPool:evaluationAnalogPool,roundTripCostPct:cfg.roundTripCostPct}):null;
  const fixed12=pathOutcome(entryPrice,future.slice(0,12),e.direction,cfg.roundTripCostPct),sessionEnd=pathOutcome(entryPrice,future,e.direction,cfg.roundTripCostPct);sessionEnd.exitReason='SESSION_END';
  const ev=labels(e,bars),h1=ev[1]?.[e.direction]??null;
  const firstBarDirectionalCloseReturnBps=Number(h1?.gross),firstBarMaeBps=Number(h1?.mae);
  const route=Number.isFinite(firstBarDirectionalCloseReturnBps)&&Number.isFinite(firstBarMaeBps)&&firstBarDirectionalCloseReturnBps<=100&&firstBarMaeBps>=25?'V3':'V4';
  const v5=causalEligible?(route==='V3'?v3:v4):null;
  trades.push({eventId:e.eventId,sessionDate:e.sessionDate,symbol:e.symbol,direction:e.direction,entryTimestamp:e.decisionTimestamp,firstBarDirectionalCloseReturnBps,firstBarMaeBps,route,causalEligible,evaluationAnalogPoolCount:evaluationAnalogPool.length,fixed12,sessionEnd,v3,v4,v5});
}

const metrics=(rows,key)=>{const rs=rows.map(r=>r[key]).filter(Boolean),nets=rs.map(x=>x.netReturnPct),wins=nets.filter(x=>x>0),loss=nets.filter(x=>x<0);let eq=0,peak=0,maxDd=0;for(const x of nets){eq+=x;peak=Math.max(peak,eq);maxDd=Math.min(maxDd,eq-peak);}return {n:rs.length,netSumPct:nets.reduce((s,x)=>s+x,0),profitFactor:loss.length?wins.reduce((s,x)=>s+x,0)/Math.abs(loss.reduce((s,x)=>s+x,0)):null,winRate:mean(nets.map(x=>Number(x>0))),averageTradePct:mean(nets),medianTradePct:median(nets),maxDrawdownProxyPct:maxDd,meanHoldingBars:mean(rs.map(x=>x.barsHeld)),mfeCapture:mean(rs.map(x=>x.captureRatio).filter(Number.isFinite)),meanGivebackPct:mean(rs.map(x=>x.givebackPct).filter(Number.isFinite))};};
const eligible=trades.filter(t=>t.causalEligible&&t.v3&&t.v4&&t.v5),arms=Object.fromEntries(['fixed12','sessionEnd','v3','v4','v5'].map(k=>[k,metrics(k==='fixed12'||k==='sessionEnd'?trades:eligible,k)]));
const deltas=eligible.map(t=>({eventId:t.eventId,sessionDate:t.sessionDate,symbol:t.symbol,direction:t.direction,route:t.route,deltaVsV4Pct:t.v5.netReturnPct-t.v4.netReturnPct,v3v4DeltaPct:t.v3.netReturnPct-t.v4.netReturnPct}));
const abs=deltas.map(x=>Math.abs(x.deltaVsV4Pct)).filter(x=>x>1e-12).sort((a,b)=>b-a),sumAbs=abs.reduce((s,x)=>s+x,0),top2AbsShare=sumAbs?abs.slice(0,2).reduce((s,x)=>s+x,0)/sumAbs:0;
const deltaVsV4=arms.v5.netSumPct-arms.v4.netSumPct,ddWorsening=Math.abs(Math.min(0,arms.v5.maxDrawdownProxyPct))-Math.abs(Math.min(0,arms.v4.maxDrawdownProxyPct));
const supportive=eligible.length>=10&&deltaVsV4>0&&Number(arms.v5.profitFactor)>=Number(arms.v4.profitFactor)&&ddWorsening<=1&&top2AbsShare<0.8;
const reject=deltaVsV4<=0||ddWorsening>1;
const finalDecision=supportive?'BLOCK_B_SUPPORTIVE':reject?'BLOCK_B_REJECT':'BLOCK_B_MIXED';
const report={schemaVersion:1,status:'BLOCK_B_COMPLETE',finalDecision,role:cfg.role,sessions:cfg.sessions.map(x=>x.sessionDate),sessionCount:cfg.sessions.length,firstEnter:entered.length,trades:trades.length,causalEligible:eligible.length,causalIneligible:trades.length-eligible.length,LONG:trades.filter(x=>x.direction==='LONG').length,SHORT:trades.filter(x=>x.direction==='SHORT').length,routes:{v3:eligible.filter(x=>x.route==='V3').length,v4:eligible.filter(x=>x.route==='V4').length},arms,paired:{deltaVsV4PctPoints:deltaVsV4,top2AbsoluteContributionShare:top2AbsShare,nonZeroDifferenceTrades:abs.length,drawdownWorseningPctPoints:ddWorsening,deltas},candidate:{freezeStatus:freeze.status,routeToV3When:freeze.router.routeToV3When,retunedAfterOpen:false,overrideAdded:false},causal:{minimumRequiredNeighbors:cfg.minimumCausalNeighbors,pitViolations:0,analogPoolCount:analogPool.length},policy:{v3:P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,v4:P25_EXIT_V4_POLICY_SHA256,candidate:cfg.lockedUpstream.candidateModelSha256},safety:cfg.safety};
fs.writeFileSync(path.join(out,'block-b-report.json'),JSON.stringify(report,null,2)+'\n');fs.writeFileSync(path.join(out,'trades.json'),JSON.stringify(trades,null,2)+'\n');fs.writeFileSync(path.join(out,'block-b-report.json.sha256'),`${hash(fs.readFileSync(path.join(out,'block-b-report.json')))}  block-b-report.json\n`);
console.log('PHASE57_EXIT_V5_BLOCK_B_RESULT='+JSON.stringify({finalDecision,firstEnter:entered.length,trades:trades.length,causalEligible:eligible.length,deltaVsV4,top2AbsShare,ddWorsening,arms}));
