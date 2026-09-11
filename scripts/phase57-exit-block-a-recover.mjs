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
const cfg=read(process.env.DIAGNOSTIC_CONFIG??'predict/research/phase57-exit-block-a-unseen-validation-v1.json');
const input=process.env.INPUT_DIR??'artifacts/block-a-input';
const candidatePath=process.env.CANDIDATE_MODEL??'artifacts/input/candidate/candidate-model.json';
const snapshotPath=process.env.ANALOG_SNAPSHOT;
const out=process.env.OUTPUT_DIR??'artifacts/phase57-exit-block-a-recovery';
assert(snapshotPath&&fs.existsSync(snapshotPath),'ANALOG_SNAPSHOT_REQUIRED');
assert.equal(cfg.schemaId,'PHASE57_EXIT_BLOCK_A_UNSEEN_VALIDATION_V1');
assert.equal(cfg.sessions.length,30);assert.equal(cfg.minimumCausalNeighbors,30);
for(const v of Object.values(cfg.safety))assert.equal(v,false,'SAFETY_FLAG_CHANGED');
fs.mkdirSync(out,{recursive:true});

const candidateBytes=fs.readFileSync(candidatePath);assert.equal(hash(candidateBytes),cfg.lockedUpstream.candidateModelSha256,'CANDIDATE_SHA_MISMATCH');
const model=JSON.parse(candidateBytes);assert.equal(model.threshold,0.6);assert.equal(model.selectorModelDigest,CONTRACT.selectorModelDigest);assert.equal(model.selectorFreezeSHA,CONTRACT.selectorFreezeSHA);
const snapshotBytes=fs.readFileSync(snapshotPath);assert.equal(hash(snapshotBytes),PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,'ANALOG_SNAPSHOT_SHA_MISMATCH');
const history=buildP252PinnedHistoricalSessions({snapshot:JSON.parse(snapshotBytes),snapshotSha256:hash(snapshotBytes)});
const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:history.sessions});
assert(analogPool.length>=30,'ANALOG_POOL_TOO_SMALL');
const analogLatest=[...new Set(analogPool.map(r=>r.sessionDate))].sort().at(-1);

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
const pathOutcome=(entryPrice,p,direction,cost)=>{assert(p.length>0,'EMPTY_EXIT_PATH');const fav=p.map(b=>dirRet(entryPrice,direction==='LONG'?b.high:b.low,direction)),adv=p.map(b=>dirRet(entryPrice,direction==='LONG'?b.low:b.high,direction));const grossReturnPct=dirRet(entryPrice,p.at(-1).close,direction),mfePct=Math.max(0,...fav),maePct=Math.min(0,...adv);return {exitTimestamp:p.at(-1).timestamp,exitPrice:p.at(-1).close,exitReason:'HORIZON_END',barsHeld:p.length,grossReturnPct,netReturnPct:grossReturnPct-cost,mfePct,maePct,givebackPct:Math.max(0,mfePct-grossReturnPct),captureRatio:mfePct>0?grossReturnPct/mfePct:null};};

const trades=[];
for(const e of entered){
  const bars=(barsBySessionSymbol.get(`${e.sessionDate}|${e.symbol}`)??[]).filter(regular).sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));
  const entryTime=Date.parse(e.decisionTimestamp),entryPrice=Number(e.priceReference);assert(Number.isFinite(entryPrice)&&entryPrice>0,'INVALID_ENTRY_PRICE');
  const context=bars.filter(b=>Date.parse(b.availableAt)<=entryTime).map(converted),future=bars.filter(b=>Date.parse(b.availableAt)>entryTime).map(converted);if(!future.length)continue;
  const row={entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,sessionDate:e.sessionDate,direction:e.direction,signalDirection:e.direction,entryPrice,contextBars:context,futureBars:future};
  const evaluationAnalogPool=analogPool.filter(a=>a.sessionDate<e.sessionDate&&Date.parse(a.fullyRealizedAt)<entryTime);
  const causalEligible=evaluationAnalogPool.length>=cfg.minimumCausalNeighbors;
  const v3=causalEligible?simulateP25ExitV3DualGate({row,analogPool:evaluationAnalogPool,roundTripCostPct:cfg.roundTripCostPct}):null;
  const v4=causalEligible?simulateP25ExitV4({row,analogPool:evaluationAnalogPool,roundTripCostPct:cfg.roundTripCostPct}):null;
  const fixed12=pathOutcome(entryPrice,future.slice(0,12),e.direction,cfg.roundTripCostPct),sessionEnd=pathOutcome(entryPrice,future,e.direction,cfg.roundTripCostPct);sessionEnd.exitReason='SESSION_END';
  const ev=labels(e,bars),h1=ev[1]?.[e.direction]??null,h3=ev[3]?.[e.direction]??null,h6=ev[6]?.[e.direction]??null,adverse=Boolean(h1&&h1.mae>0);
  const sideFeature=(e.directionFeatures??[]).find(x=>(e.direction==='LONG'?1:-1)===Number(x.direction));
  const priorVolumes=context.slice(-5).map(x=>Number(x.volume)).filter(Number.isFinite),priorMeanVolume=priorVolumes.length===5?mean(priorVolumes):null;
  trades.push({eventId:e.eventId,sessionDate:e.sessionDate,symbol:e.symbol,direction:e.direction,entryTimestamp:e.decisionTimestamp,entryPrice,hybridRank:e.hybridRank??null,hybridScore:e.hybridScore??null,entryFeatures:{directionalVwapDistancePct:sideFeature?.features?.directionalVwapDistancePct??null,relativeVolume5:sideFeature?.features?.relativeVolume5??null,hybridReciprocalRank:sideFeature?.features?.hybridReciprocalRank??(Number(e.hybridRank)>0?1/Number(e.hybridRank):null),firstBarVolumeRatio:h1&&priorMeanVolume>0?Number(future[0]?.volume)/priorMeanVolume:null},entryQuality:{h1,h3,h6,immediateAdverse:adverse,recoveredBy3Close:Boolean(adverse&&h3&&h3.gross>0),recoveredBy6Close:Boolean(adverse&&h6&&h6.gross>0),recoveredBy3Touch:Boolean(adverse&&h3&&h3.mfe>0),recoveredBy6Touch:Boolean(adverse&&h6&&h6.mfe>0),remainedLoserBy6:Boolean(adverse&&h6&&h6.gross<=0)},fixed12,sessionEnd,v3:v3?{...v3,managementDecisions:undefined}:null,v4:v4?{...v4,managementDecisions:undefined}:null,management:{v3:v3?.managementDecisions??[],v4:v4?.managementDecisions??[]},causal:{eligible:causalEligible,evaluationAnalogPoolCount:evaluationAnalogPool.length,exclusionReason:causalEligible?null:'V3V4_NOT_CAUSAL_ELIGIBLE'}});
}

const armMetrics=name=>{const rows=trades.filter(r=>r[name]),rs=rows.map(r=>r[name]),nets=rs.map(x=>x.netReturnPct),wins=nets.filter(x=>x>0),loss=nets.filter(x=>x<0);let eq=0,peak=0,maxDd=0;for(const x of nets){eq+=x;peak=Math.max(peak,eq);maxDd=Math.min(maxDd,eq-peak);}return {n:rs.length,netReturnPct:nets.reduce((s,x)=>s+x,0),profitFactor:loss.length?wins.reduce((s,x)=>s+x,0)/Math.abs(loss.reduce((s,x)=>s+x,0)):null,winRate:mean(nets.map(x=>Number(x>0))),averageTradePct:mean(nets),medianTradePct:median(nets),maxDrawdownPct:maxDd,meanMfePct:mean(rs.map(x=>x.mfePct).filter(Number.isFinite)),meanMaePct:mean(rs.map(x=>x.maePct).filter(Number.isFinite)),meanCaptureRatio:mean(rs.map(x=>x.captureRatio).filter(Number.isFinite)),meanGivebackPct:mean(rs.map(x=>x.givebackPct).filter(Number.isFinite)),meanHoldingBars:mean(rs.map(x=>x.barsHeld).filter(Number.isFinite))};};
const q=h=>trades.map(r=>r.entryQuality[`h${h}`]).filter(Boolean),symbols=Object.entries(trades.reduce((m,r)=>(m[r.symbol]=(m[r.symbol]??0)+1,m),{})).sort((a,b)=>b[1]-a[1]);
const share=n=>trades.length?symbols.slice(0,n).reduce((s,x)=>s+x[1],0)/trades.length:null,immediate=trades.filter(r=>r.entryQuality.immediateAdverse);
const horizons=Object.fromEntries([1,3,6].map(h=>{const xs=q(h);return [h,{n:xs.length,meanGrossBps:mean(xs.map(x=>x.gross)),medianGrossBps:median(xs.map(x=>x.gross)),meanNetBps:mean(xs.map(x=>x.net)),medianNetBps:median(xs.map(x=>x.net)),positiveGrossRate:mean(xs.map(x=>Number(x.gross>0))),positiveNetRate:mean(xs.map(x=>Number(x.net>0))),meanMfeBps:mean(xs.map(x=>x.mfe)),meanMaeBps:mean(xs.map(x=>x.mae)),meanTimeToMfeMinutes:mean(xs.map(x=>x.timeToMfe))}];}));
const entryQuality={firstEnter:entered.length,pairedFirstEnter:trades.length,missingOutcomePathEvents:entered.length-trades.length,sessionsMeasured:new Set(trades.map(r=>r.sessionDate)).size,firstEnterPerSession:entered.length/cfg.sessions.length,uniqueSymbols:symbols.length,LONG:trades.filter(r=>r.direction==='LONG').length,SHORT:trades.filter(r=>r.direction==='SHORT').length,top1SymbolShare:share(1),top3SymbolShare:share(3),top5SymbolShare:share(5),horizons,immediateAdverseCount:immediate.length,immediateAdverseRate:trades.length?immediate.length/trades.length:null,recoveryBy3CloseAmongImmediateAdverse:immediate.length?mean(immediate.map(r=>Number(r.entryQuality.recoveredBy3Close))):null,recoveryBy6CloseAmongImmediateAdverse:immediate.length?mean(immediate.map(r=>Number(r.entryQuality.recoveredBy6Close))):null,recoveryBy3TouchAmongImmediateAdverse:immediate.length?mean(immediate.map(r=>Number(r.entryQuality.recoveredBy3Touch))):null,recoveryBy6TouchAmongImmediateAdverse:immediate.length?mean(immediate.map(r=>Number(r.entryQuality.recoveredBy6Touch))):null,remainedLoserBy6AmongImmediateAdverse:immediate.length?mean(immediate.map(r=>Number(r.entryQuality.remainedLoserBy6))):null};

const finite=x=>Number.isFinite(Number(x));
const featureValue=(t,name)=>({firstBarDirectionalCloseReturnPct:finite(t.entryQuality?.h1?.gross)?Number(t.entryQuality.h1.gross)/100:null,firstBarMfePct:finite(t.entryQuality?.h1?.mfe)?Number(t.entryQuality.h1.mfe)/100:null,firstBarMaePct:finite(t.entryQuality?.h1?.mae)?-Number(t.entryQuality.h1.mae)/100:null,hybridReciprocalRank:t.entryFeatures?.hybridReciprocalRank,hybridScore:t.hybridScore,relativeVolume5:t.entryFeatures?.relativeVolume5,directionalVwapDistancePct:t.entryFeatures?.directionalVwapDistancePct,firstBarVolumeRatio:t.entryFeatures?.firstBarVolumeRatio})[name];
const auc=(pos,neg)=>{if(!pos.length||!neg.length)return null;let s=0;for(const p of pos)for(const n of neg)s+=p>n?1:(p===n?.5:0);return s/(pos.length*neg.length);};
const adverseComplete=trades.filter(t=>t.entryQuality?.immediateAdverse&&t.entryQuality?.h6),recovered=adverseComplete.filter(t=>Number(t.entryQuality.h6.gross)>0),failed=adverseComplete.filter(t=>Number(t.entryQuality.h6.gross)<=0);
const summarizeFeature=(name,rows=adverseComplete)=>{const pos=rows.filter(t=>Number(t.entryQuality.h6.gross)>0).map(t=>featureValue(t,name)).filter(finite).map(Number),neg=rows.filter(t=>Number(t.entryQuality.h6.gross)<=0).map(t=>featureValue(t,name)).filter(finite).map(Number),a=auc(pos,neg);return {feature:name,recoveredN:pos.length,failureN:neg.length,recoveredMean:mean(pos),recoveredMedian:median(pos),failureMean:mean(neg),failureMedian:median(neg),descriptiveAuc:a,effectDirection:a==null?'UNKNOWN':a>=.5?'HIGHER_IN_RECOVERED':'LOWER_IN_RECOVERED',interpretation:a==null?'INSUFFICIENT':a>=.65?'PROMISING_REPLICATION':a>=.60?'WEAK_PARTIAL':a<=.35?'PROMISING_INVERSE_REPLICATION':a<=.40?'WEAK_INVERSE_PARTIAL':'FAILED_REPLICATION_CANDIDATE'};};
const featureValidation=Object.fromEntries(cfg.frozenFeatureFamily.map(name=>[name,summarizeFeature(name)]));
const eligible=trades.filter(t=>t.causal.eligible&&t.v3&&t.v4);
const divergence=eligible.map(t=>({eventId:t.eventId,sessionDate:t.sessionDate,symbol:t.symbol,direction:t.direction,comparison:Math.abs(t.v4.netReturnPct-t.v3.netReturnPct)<=1e-12?'EQUAL':t.v4.netReturnPct>t.v3.netReturnPct?'V4_GT_V3':'V3_GT_V4',deltaPct:t.v4.netReturnPct-t.v3.netReturnPct,v3Reason:t.v3.exitReason,v4Reason:t.v4.exitReason,v3Bars:t.v3.barsHeld,v4Bars:t.v4.barsHeld}));
const divergenceSummary={eligibleN:eligible.length,ineligibleN:trades.length-eligible.length,v4Greater:divergence.filter(x=>x.comparison==='V4_GT_V3').length,v3Greater:divergence.filter(x=>x.comparison==='V3_GT_V4').length,equal:divergence.filter(x=>x.comparison==='EQUAL').length};
const winnerObservations=[];for(const t of eligible){const v3=t.management.v3,v4=t.management.v4,all=[...new Set([...v3.map(x=>x.timestamp),...v4.map(x=>x.timestamp)])].sort();let priorMfe=0,lastMfeIndex=0,runningMae=0;for(const [i,ts] of all.entries()){const a=v3.find(x=>x.timestamp===ts),b=v4.find(x=>x.timestamp===ts),src=b??a;if(!src)continue;const mfe=Number(src.mfePct??priorMfe),cur=Number(src.currentReturnPct),improved=mfe>priorMfe+1e-12;if(improved)lastMfeIndex=i;runningMae=Math.min(runningMae,cur);winnerObservations.push({eventId:t.eventId,sessionDate:t.sessionDate,symbol:t.symbol,direction:t.direction,timestamp:ts,holdingBars:i+1,currentReturnPct:cur,runningMfePct:mfe,runningMaeCloseProxyPct:runningMae,givebackRatio:mfe>0?(mfe-cur)/mfe:null,mfeVelocityPctPerBar:mfe/(i+1),timeSinceLastMfeUpdateBars:i-lastMfeIndex,entryDirectionalVwapDistancePct:t.entryFeatures?.directionalVwapDistancePct??null,entryRvol5:t.entryFeatures?.relativeVolume5??null,v3Decision:a?.gate?.decision??'NO_DECISION',v4Decision:b?.gate?.decision??'NO_DECISION'});priorMfe=Math.max(priorMfe,mfe);}}

const primary=[featureValidation.firstBarDirectionalCloseReturnPct,featureValidation.firstBarMfePct],delayed=Number(horizons[3]?.meanNetBps)>Number(horizons[1]?.meanNetBps)&&Number(horizons[6]?.meanNetBps)>Number(horizons[1]?.meanNetBps),adverseReplicated=Number(entryQuality.immediateAdverseRate)>=.6,strong=primary.some(x=>x.descriptiveAuc>=.65),partial=primary.some(x=>x.descriptiveAuc>=.60),finalDecision=strong&&adverseReplicated&&delayed?'BLOCK_A_GO':(partial||adverseReplicated||delayed)?'BLOCK_A_PARTIAL':'BLOCK_A_FAIL';
const counts=trades.map(t=>t.causal.evaluationAnalogPoolCount),eligibleCounts=eligible.map(t=>t.causal.evaluationAnalogPoolCount);
const report={schemaVersion:1,status:'BLOCK_A_COMPLETE',finalDecision,role:cfg.role,datesFrozenBeforeOutcome:true,sessions:cfg.sessions.map(x=>x.sessionDate),sessionCount:cfg.sessions.length,entryQuality,arms:{fixed12:armMetrics('fixed12'),sessionEnd:armMetrics('sessionEnd'),v3:armMetrics('v3'),v4:armMetrics('v4')},healthyPullback:{primaryLabel:cfg.primaryLabel,immediateAdverseCompleteN:adverseComplete.length,recoveredN:recovered.length,failureN:failed.length,featureValidation,noThresholdOrWeightsFit:true},v3v4:{...divergenceSummary,scope:'CAUSAL_ELIGIBLE_ONLY',divergence},winnerContinuation:{observationCount:winnerObservations.length,thresholdOrModelCreated:false},causal:{mode:'PER_EVENT_STRICT_PRE_SESSION_AND_FULLY_REALIZED',minimumRequiredNeighbors:cfg.minimumCausalNeighbors,eligibleTrades:eligible.length,ineligibleTrades:trades.length-eligible.length,evaluationAnalogPoolCountRange:counts.length?{min:Math.min(...counts),max:Math.max(...counts)}:null,eligibleAnalogPoolCountRange:eligibleCounts.length?{min:Math.min(...eligibleCounts),max:Math.max(...eligibleCounts)}:null,pitViolations:0,analogPoolCount:analogPool.length,analogLatestSessionDate:analogLatest},replicationChecks:{delayedEdgeStructure:delayed,immediateAdverseStructure:adverseReplicated,primaryFeaturePromising:strong,primaryFeaturePartial:partial},access:{blockASessionsOpened:cfg.sessions.length,old20Reused:0,automaticExpansion:0,featureArtifactsReusedFromRun:Number(process.env.REUSED_FEATURE_RUN_ID??0)},policy:{v3:P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,v4:P25_EXIT_V4_POLICY_SHA256,analogSnapshot:PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,candidate:cfg.lockedUpstream.candidateModelSha256},safety:cfg.safety};
fs.writeFileSync(path.join(out,'block-a-report.json'),JSON.stringify(report,null,2)+'\n');fs.writeFileSync(path.join(out,'trades.json'),JSON.stringify(trades,null,2)+'\n');fs.writeFileSync(path.join(out,'winner-observations.json'),JSON.stringify(winnerObservations,null,2)+'\n');fs.writeFileSync(path.join(out,'block-a-report.json.sha256'),`${hash(fs.readFileSync(path.join(out,'block-a-report.json')))}  block-a-report.json\n`);console.log('PHASE57_BLOCK_A_RECOVERY_RESULT='+JSON.stringify({finalDecision,trades:trades.length,causalEligible:eligible.length,causalIneligible:trades.length-eligible.length,immediateAdverseCompleteN:adverseComplete.length,recoveredN:recovered.length,failureN:failed.length,divergenceSummary}));