import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';

const release=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-minimal-hybrid-oos-release.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const HORIZONS=[1,2,3,6,12],KS=[1,3,5,8,10,15,20,25,30];
const BANDS=[['1_5',1,5],['6_10',6,10],['11_15',11,15],['16_20',16,20],['21_30',21,30]];
const mean=xs=>xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:null;
const round=value=>value===null?null:Number(value.toFixed(6));
const bpsMean=xs=>xs.length?round(mean(xs)*10000):null;
const quantile=(xs,q)=>{const s=xs.filter(Number.isFinite).sort((a,b)=>a-b);if(!s.length)return null;const p=(s.length-1)*q,l=Math.floor(p),u=Math.ceil(p);return round(s[l]*(1-(p-l))+s[u]*(p-l));};
const distribution=xs=>{const s=xs.filter(Number.isFinite);return {n:s.length,mean:round(mean(s)),median:quantile(s,.5),p25:quantile(s,.25),p75:quantile(s,.75),iqr:s.length?round(quantile(s,.75)-quantile(s,.25)):null,min:s.length?round(Math.min(...s)):null,max:s.length?round(Math.max(...s)):null,positiveRate:s.length?round(s.filter(x=>x>0).length/s.length):null};};
const primary=row=>row.targetsByHorizon?.[6]?.status==='TARGET_READY'?row.targetsByHorizon[6]:null;
const utility=row=>primary(row).twoSidedOpportunity*10000-release.roundTripCostBps;
const sha256=value=>createHash('sha256').update(value).digest('hex');
function findFiles(root,name){const found=[];for(const e of fs.readdirSync(root,{withFileTypes:true})){const p=path.join(root,e.name);if(e.isDirectory())found.push(...findFiles(p,name));else if(e.name===name)found.push(p);}return found.sort();}
function ndjson(root,name){return findFiles(root,`${name}.ndjson.gz`).flatMap(file=>{const text=gunzipSync(fs.readFileSync(file)).toString('utf8').trim();return text?text.split('\n').map(JSON.parse):[];});}
function sessionsFor(fold){return fold==='VALIDATION'?allocation.validation:allocation.untouchedOos;}

function summarizeRows(rows,fold,selector,minRank,maxRank){
  const all=rows.filter(r=>r.fold===fold&&r.selector===selector&&r.rank>=minRank&&r.rank<=maxRank),ready=all.filter(primary);
  const horizons=Object.fromEntries(HORIZONS.map(h=>{const r=all.filter(x=>x.targetsByHorizon?.[h]?.status==='TARGET_READY');return [h,{n:r.length,
    finalCloseReturnBps:bpsMean(r.map(x=>x.targetsByHorizon[h].finalCloseReturn)),upExcursionBps:bpsMean(r.map(x=>x.targetsByHorizon[h].upExcursion)),
    downExcursionBps:bpsMean(r.map(x=>x.targetsByHorizon[h].downExcursion)),twoSidedOpportunityBps:bpsMean(r.map(x=>x.targetsByHorizon[h].twoSidedOpportunity))}];}));
  const sessionUtility=sessionsFor(fold).map(date=>{const r=ready.filter(x=>x.sessionDate===date);return r.length?mean(r.map(utility)):null;}).filter(Number.isFinite);
  return {candidateRows:all.length,readyRows:ready.length,coverageRate:all.length?round(ready.length/all.length):null,costAdjustedUtilityBps:round(mean(ready.map(utility))),
    preSelectionMoveBps:bpsMean(ready.map(x=>x.preSelectionMove)),lateDetectionRate:ready.length?round(ready.filter(x=>x.preSelectionMove>primary(x).twoSidedOpportunity).length/ready.length):null,
    horizons,sessionEqual:{meanUtilityBps:round(mean(sessionUtility)),...distribution(sessionUtility)}};
}

function capacityCurve(rows,points,fold,selector){
  const foldPoints=points.filter(p=>p.fold===fold),byCutoff=new Map();for(const r of rows.filter(x=>x.fold===fold&&x.selector===selector)){if(!byCutoff.has(r.featureCutoff))byCutoff.set(r.featureCutoff,[]);byCutoff.get(r.featureCutoff).push(r);}
  return Object.fromEntries(KS.map(k=>{const sessionValues=new Map(sessionsFor(fold).map(d=>[d,[]]));let available=0,ready=0;
    for(const p of foldPoints){const all=(byCutoff.get(p.featureCutoff)??[]).sort((a,b)=>a.rank-b.rank),top=all.slice(0,k).filter(primary);if(all.length>=k)available+=1;ready+=top.length;sessionValues.get(p.sessionDate).push(...top.map(utility));}
    const sessions=[...sessionValues.values()].map(mean).filter(Number.isFinite);return [k,{utilityAtKBps:round(mean(sessions)),coverageAtK:round(available/foldPoints.length),availableCandidatesMean:round(mean(foldPoints.map(p=>selector==='HYBRID'?p.hybridEligibleCount:p.v1CandidateCount))),readyRows:ready,sessionDistribution:distribution(sessions)}];}));
}

function sameCapacityCurve(rows,points,fold){
  const foldPoints=points.filter(p=>p.fold===fold),groups=new Map();for(const r of rows.filter(x=>x.fold===fold)){const key=`${r.featureCutoff}|${r.selector}`;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(r);}
  return Object.fromEntries(KS.map(k=>{const result={};for(const selector of ['HYBRID','V1']){const bySession=new Map(sessionsFor(fold).map(d=>[d,[]]));for(const p of foldPoints){const actualK=Math.min(k,p.hybridEligibleCount,p.v1CandidateCount);const top=(groups.get(`${p.featureCutoff}|${selector}`)??[]).sort((a,b)=>a.rank-b.rank).slice(0,actualK).filter(primary);bySession.get(p.sessionDate).push(...top.map(utility));}result[selector]=round(mean([...bySession.values()].map(mean).filter(Number.isFinite)));}return [k,result];}));
}

function abstain(points,rows,fold){
  const zero=points.filter(p=>p.fold===fold&&p.hybridSelectedCount===0),zeroCutoffs=new Set(zero.map(p=>p.featureCutoff));const top5=rows.filter(r=>r.fold===fold&&r.selector==='HYBRID'&&zeroCutoffs.has(r.featureCutoff)&&r.rank<=5&&primary(r));
  const byTime={};for(const p of zero)byTime[p.timeOfDay]=(byTime[p.timeOfDay]??0)+1;
  const regime={LOW_BREADTH_0_40:0,MID_BREADTH_40_60:0,HIGH_BREADTH_60_100:0,UNKNOWN:0};for(const p of zero){if(!Number.isFinite(p.marketBreadth))regime.UNKNOWN+=1;else if(p.marketBreadth<.4)regime.LOW_BREADTH_0_40+=1;else if(p.marketBreadth<=.6)regime.MID_BREADTH_40_60+=1;else regime.HIGH_BREADTH_60_100+=1;}
  return {timestamps:zero.length,sessions:new Set(zero.map(p=>p.sessionDate)).size,byTimeOfDay:byTime,marketBreadthBuckets:regime,eligiblePool:distribution(zero.map(p=>p.hybridEligibleCount)),qualifiedPool:distribution(zero.map(p=>p.hybridQualifiedCount)),postHocTop5UtilityBps:round(mean(top5.map(utility)))};
}

export function summarizeCapacity({inputRoot}={}){
  const rows=ndjson(inputRoot,'records'),points=ndjson(inputRoot,'points'),reports=findFiles(inputRoot,'report.json').map(f=>JSON.parse(fs.readFileSync(f,'utf8')));
  if(reports.length!==12||reports.some(r=>r.frozenHybridChanged||r.retuningPerformed||r.reserveSessionsTouched!==0))throw new Error('capacity shards incomplete or contaminated');
  for(const fold of ['VALIDATION','UNTOUCHED_OOS'])if(points.filter(p=>p.fold===fold).length!==480)throw new Error(`${fold} points incomplete`);
  const folds={};for(const fold of ['VALIDATION','UNTOUCHED_OOS']){folds[fold]={rankBands:{}};for(const selector of ['HYBRID','V1'])folds[fold].rankBands[selector]=Object.fromEntries(BANDS.map(([name,min,max])=>[name,summarizeRows(rows,fold,selector,min,max)]));}
  for(const fold of ['VALIDATION','UNTOUCHED_OOS']){folds[fold].capacityCurve={HYBRID:capacityCurve(rows,points,fold,'HYBRID'),V1:capacityCurve(rows,points,fold,'V1')};folds[fold].sameCapacityCurve=sameCapacityCurve(rows,points,fold);folds[fold].abstain=abstain(points,rows,fold);}
  const oos=folds.UNTOUCHED_OOS.rankBands.HYBRID,top=oos['1_5'].sessionEqual.meanUtilityBps,band6=oos['6_10'].sessionEqual.meanUtilityBps,band11=oos['11_15'].sessionEqual.meanUtilityBps;
  const ratio6=Number.isFinite(top)&&top!==0?band6/top:null,ratio11=Number.isFinite(top)&&top!==0?band11/top:null;
  const diagnosis=ratio6>=.75&&ratio11>=.5?'A_CAPACITY_CONSTRAINED':ratio6<.5&&ratio11<.5?'B_QUALITY_FRONTIER_REACHED':'C_MIXED_OR_REGIME_DEPENDENT';
  const core={schemaVersion:1,phase:'57.selector-minimal-hybrid.post-hoc-capacity-diagnostic',status:'POST_HOC_CAPACITY_DIAGNOSTIC_COMPLETE',methodology:'OPENED_VALIDATION_AND_OOS_REPLAY_ONLY_NOT_FROZEN_OOS_PERFORMANCE',
    datasetId:allocation.datasetId,modelDigest:release.expectedModelDigest,freezeSha256:release.expectedHybridFreezeSha256,roundTripCostBps:release.roundTripCostBps,folds,capacityDiagnosis:diagnosis,
    classificationRule:{frozenBeforeReplay:true,rank6To10VsTop5Ratio:round(ratio6),rank11To15VsTop5Ratio:round(ratio11),A:'ratios >= 0.75 and 0.50',B:'both ratios < 0.50',C:'otherwise'},
    guards:{frozenHybridChanged:false,retrainingPerformed:false,refitPerformed:false,featureChanged:false,thresholdChanged:false,dynamicNChanged:false,abstainChanged:false,reserveOpened:false,reserveSessionsTouched:0,postHocOnly:true},
    claims:{frozenHybridOosPerformanceClaimAllowed:false,capacityV2DecisionAllowed:false,productionReadyAllowed:false},safety:release.safety};
  return {...core,evidenceSha256:sha256(JSON.stringify(core))};
}

async function main(){const report=summarizeCapacity({inputRoot:process.env.INPUT_ROOT||'artifacts/capacity-results'});const dir='artifacts/phase57-capacity-summary';fs.mkdirSync(dir,{recursive:true,mode:0o700});const bytes=JSON.stringify(report,null,2)+'\n';fs.writeFileSync(`${dir}/capacity-diagnostic.json`,bytes,{mode:0o600});console.log('PHASE57_CAPACITY_SUMMARY '+JSON.stringify({status:report.status,capacityDiagnosis:report.capacityDiagnosis,evidenceSha256:report.evidenceSha256,reserveSessionsTouched:0}));}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(e=>{console.error(`PHASE57_CAPACITY_SUMMARY_FAIL ${String(e?.message??e)}`);process.exitCode=1;});

export const Phase57CapacitySummaryInternals=Object.freeze({distribution,summarizeRows,capacityCurve,sameCapacityCurve,abstain});
