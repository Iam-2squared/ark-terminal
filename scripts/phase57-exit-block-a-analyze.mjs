import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const input=process.env.MEASUREMENT_DIR??'artifacts/phase57-exit-block-a-base';
const out=process.env.OUTPUT_DIR??'artifacts/phase57-exit-block-a-report';
const cfg=read(process.env.DIAGNOSTIC_CONFIG??'predict/research/phase57-exit-block-a-unseen-validation-v1.json');
const base=read(path.join(input,'report.json'));
const trades=read(path.join(input,'trades.json'));
fs.mkdirSync(out,{recursive:true});

assert.equal(cfg.schemaId,'PHASE57_EXIT_BLOCK_A_UNSEEN_VALIDATION_V1');
assert.equal(cfg.sessions.length,30);
assert.equal(new Set(cfg.sessions.map(x=>x.sessionDate)).size,30,'DUPLICATE_SESSION');
assert(cfg.sessions.every(x=>!cfg.exposed20.includes(x.sessionDate)),'OLD20_REUSED');
assert.equal(base.causal.pitViolations,0);
assert(base.causal.minimumObservedNeighborCount>=cfg.minimumCausalNeighbors,'CAUSAL_NEIGHBOR_VIOLATION');
for(const v of Object.values(cfg.safety))assert.equal(v,false,'SAFETY_FLAG_CHANGED');

const mean=xs=>xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;};
const auc=(pos,neg)=>{if(!pos.length||!neg.length)return null;let s=0;for(const p of pos)for(const n of neg)s+=p>n?1:(p===n?0.5:0);return s/(pos.length*neg.length);};
const finite=x=>Number.isFinite(Number(x));
const featureValue=(t,name)=>({
  firstBarDirectionalCloseReturnPct:finite(t.entryQuality?.h1?.gross)?Number(t.entryQuality.h1.gross)/100:null,
  firstBarMfePct:finite(t.entryQuality?.h1?.mfe)?Number(t.entryQuality.h1.mfe)/100:null,
  firstBarMaePct:finite(t.entryQuality?.h1?.mae)?-Number(t.entryQuality.h1.mae)/100:null,
  hybridReciprocalRank:t.entryFeatures?.hybridReciprocalRank,
  hybridScore:t.hybridScore,
  relativeVolume5:t.entryFeatures?.relativeVolume5,
  directionalVwapDistancePct:t.entryFeatures?.directionalVwapDistancePct,
  firstBarVolumeRatio:t.entryFeatures?.firstBarVolumeRatio,
})[name];

const adverseComplete=trades.filter(t=>t.entryQuality?.immediateAdverse&&t.entryQuality?.h6);
const recovered=adverseComplete.filter(t=>Number(t.entryQuality.h6.gross)>0);
const failed=adverseComplete.filter(t=>Number(t.entryQuality.h6.gross)<=0);
const summarizeFeature=(name,rows=adverseComplete)=>{
  const pos=rows.filter(t=>Number(t.entryQuality.h6.gross)>0).map(t=>featureValue(t,name)).filter(finite).map(Number);
  const neg=rows.filter(t=>Number(t.entryQuality.h6.gross)<=0).map(t=>featureValue(t,name)).filter(finite).map(Number);
  const a=auc(pos,neg);
  return {feature:name,recoveredN:pos.length,failureN:neg.length,recoveredMean:mean(pos),recoveredMedian:median(pos),failureMean:mean(neg),failureMedian:median(neg),descriptiveAuc:a,effectDirection:a==null?'UNKNOWN':a>=.5?'HIGHER_IN_RECOVERED':'LOWER_IN_RECOVERED',interpretation:a==null?'INSUFFICIENT':a>=.65?'PROMISING_REPLICATION':a>=.60?'WEAK_PARTIAL':a<=.35?'PROMISING_INVERSE_REPLICATION':a<=.40?'WEAK_INVERSE_PARTIAL':'FAILED_REPLICATION_CANDIDATE',uncertainty:(pos.length<10||neg.length<10)?'VERY_LOW_N':'LOW_N_DESCRIPTIVE_ONLY'};
};
const featureValidation=Object.fromEntries(cfg.frozenFeatureFamily.map(name=>[name,summarizeFeature(name)]));
const byDirection=Object.fromEntries(['LONG','SHORT'].map(direction=>[direction,Object.fromEntries(cfg.frozenFeatureFamily.map(name=>[name,summarizeFeature(name,adverseComplete.filter(t=>t.direction===direction))]))]));

const cmp=(a,b,eps=1e-12)=>Math.abs(a-b)<=eps?'EQUAL':a>b?'V4_GT_V3':'V3_GT_V4';
const divergence=trades.map(t=>{
  const kind=cmp(Number(t.v4.netReturnPct),Number(t.v3.netReturnPct));
  const v3d=t.management?.v3??[],v4d=t.management?.v4??[];
  const timestamps=[...new Set([...v3d.map(x=>x.timestamp),...v4d.map(x=>x.timestamp)])].sort();
  const divergenceTimestamp=timestamps.find(ts=>{
    const a=v3d.find(x=>x.timestamp===ts)?.gate?.decision??'NO_DECISION';
    const b=v4d.find(x=>x.timestamp===ts)?.gate?.decision??'NO_DECISION';
    return a!==b;
  })??null;
  return {eventId:t.eventId,sessionDate:t.sessionDate,symbol:t.symbol,direction:t.direction,comparison:kind,deltaPct:Number(t.v4.netReturnPct)-Number(t.v3.netReturnPct),v3Reason:t.v3.exitReason,v4Reason:t.v4.exitReason,v3Bars:t.v3.barsHeld,v4Bars:t.v4.barsHeld,divergenceTimestamp};
});
const divergenceSummary={different:divergence.filter(x=>x.comparison!=='EQUAL').length,v4Greater:divergence.filter(x=>x.comparison==='V4_GT_V3').length,v3Greater:divergence.filter(x=>x.comparison==='V3_GT_V4').length,equal:divergence.filter(x=>x.comparison==='EQUAL').length,byDirection:Object.fromEntries(['LONG','SHORT'].map(d=>[d,{n:divergence.filter(x=>x.direction===d).length,v4Greater:divergence.filter(x=>x.direction===d&&x.comparison==='V4_GT_V3').length,v3Greater:divergence.filter(x=>x.direction===d&&x.comparison==='V3_GT_V4').length,equal:divergence.filter(x=>x.direction===d&&x.comparison==='EQUAL').length,netDeltaPct:divergence.filter(x=>x.direction===d).reduce((s,x)=>s+x.deltaPct,0)}]))};

const winnerObservations=[];
for(const t of trades){
  const v3=t.management?.v3??[],v4=t.management?.v4??[],all=[...new Set([...v3.map(x=>x.timestamp),...v4.map(x=>x.timestamp)])].sort();
  let priorMfe=0,lastMfeIndex=0,runningMae=0;
  for(const [i,ts] of all.entries()){
    const a=v3.find(x=>x.timestamp===ts),b=v4.find(x=>x.timestamp===ts),src=b??a;if(!src)continue;
    const mfe=Number(src.mfePct??priorMfe),cur=Number(src.currentReturnPct),improved=mfe>priorMfe+1e-12;
    if(improved)lastMfeIndex=i;
    runningMae=Math.min(runningMae,cur);
    winnerObservations.push({eventId:t.eventId,sessionDate:t.sessionDate,symbol:t.symbol,direction:t.direction,timestamp:ts,holdingBars:i+1,currentReturnPct:cur,runningMfePct:mfe,runningMaeCloseProxyPct:runningMae,givebackRatio:mfe>0?(mfe-cur)/mfe:null,mfeVelocityPctPerBar:i?mfe/(i+1):mfe,timeSinceLastMfeUpdateBars:i-lastMfeIndex,entryDirectionalVwapDistancePct:t.entryFeatures?.directionalVwapDistancePct??null,entryRvol5:t.entryFeatures?.relativeVolume5??null,v3Decision:a?.gate?.decision??'NO_DECISION',v3Reason:a?.gate?.reason??null,v4Decision:b?.gate?.decision??'NO_DECISION',v4Reason:b?.gate?.reason??null});
    priorMfe=Math.max(priorMfe,mfe);
  }
}

const primary=[featureValidation.firstBarDirectionalCloseReturnPct,featureValidation.firstBarMfePct];
const delayed=Number(base.entryQuality.horizons['3']?.meanNetBps)>Number(base.entryQuality.horizons['1']?.meanNetBps)&&Number(base.entryQuality.horizons['6']?.meanNetBps)>Number(base.entryQuality.horizons['1']?.meanNetBps);
const adverseReplicated=Number(base.entryQuality.immediateAdverseRate)>=.6;
const strong=primary.some(x=>x.descriptiveAuc>=.65),partial=primary.some(x=>x.descriptiveAuc>=.60);
const finalDecision=strong&&adverseReplicated&&delayed?'BLOCK_A_GO':(partial||adverseReplicated||delayed)?'BLOCK_A_PARTIAL':'BLOCK_A_FAIL';
const report={schemaVersion:1,status:'BLOCK_A_COMPLETE',finalDecision,role:cfg.role,datesFrozenBeforeOutcome:true,sessions:cfg.sessions.map(x=>x.sessionDate),sessionCount:cfg.sessions.length,baseMeasurement:base,healthyPullback:{primaryLabel:cfg.primaryLabel,immediateAdverseCompleteN:adverseComplete.length,recoveredN:recovered.length,failureN:failed.length,featureValidation,byDirection,noThresholdOrWeightsFit:true},v3v4:{divergenceSummary,divergence},winnerContinuation:{observationCount:winnerObservations.length,thresholdOrModelCreated:false,fields:['currentReturnPct','runningMfePct','runningMaeCloseProxyPct','givebackRatio','mfeVelocityPctPerBar','timeSinceLastMfeUpdateBars','holdingBars','entryDirectionalVwapDistancePct','entryRvol5','v3Decision','v4Decision','direction']},replicationChecks:{delayedEdgeStructure:delayed,immediateAdverseStructure:adverseReplicated,primaryFeaturePromising:strong,primaryFeaturePartial:partial},access:{blockASessionsOpened:cfg.sessions.length,old20Reused:0,automaticExpansion:0},safety:cfg.safety};
const write=(name,obj)=>fs.writeFileSync(path.join(out,name),JSON.stringify(obj,null,2)+'\n');
write('block-a-report.json',report);write('winner-observations.json',winnerObservations);
fs.writeFileSync(path.join(out,'block-a-report.json.sha256'),`${hash(fs.readFileSync(path.join(out,'block-a-report.json')))}  block-a-report.json\n`);
console.log('PHASE57_BLOCK_A_RESULT='+JSON.stringify({status:report.status,finalDecision,pairedTrades:trades.length,immediateAdverseCompleteN:adverseComplete.length,recoveredN:recovered.length,failureN:failed.length,divergenceSummary}));
