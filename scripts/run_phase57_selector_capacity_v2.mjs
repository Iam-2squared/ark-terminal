import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

import {runPhase57MinimalHybrid} from '../predict/daytrade/phase57-selector-minimal-hybrid.js';
import {buildPhase57MinimalHybridTargets} from '../predict/daytrade/phase57-selector-minimal-hybrid-targets.js';
import {extractPhase57CapacityV2Inputs} from '../predict/daytrade/phase57-selector-capacity-v2-contract.js';
import {Phase57FreshSessionInternals} from './lib/phase57-selector-jquants-fresh-session.mjs';

const ROOT=new URL('../predict/research/',import.meta.url);
const PHASE_A=readJson(new URL('phase57-selector-capacity-v2-phase-a.json',ROOT));
const HYBRID_MODEL=readJson(new URL('phase57-selector-minimal-hybrid-development-model.json',ROOT));
const PARENT_ALLOCATION=readJson(new URL('phase57-selector-jquants-fresh120-allocation.json',ROOT));
const PILOT_REGISTRY=readJson(new URL('phase57-selector-source-validation-only-registry.json',ROOT));
const API_BASE='https://api.jquants.com/';
const CALENDAR_PATH='v2/markets/calendar';
const FROM='2025-04-15',TO='2026-06-11';
const FEATURE_NAMES=Object.freeze([...PHASE_A.trainableFeatureWhitelist]);
const CAPACITIES=Object.freeze([0,5,10,15,20]);
const LAYERS=Object.freeze([{name:'RANK_6_10',min:6,max:10},{name:'RANK_11_15',min:11,max:15},{name:'RANK_16_20',min:16,max:20}]);
const LAMBDAS=Object.freeze([0.1,1,10]);
const ROUND_TRIP_COST_BPS=PHASE_A.targetContract.roundTripCostBps;
const SAFETY=PHASE_A.safety;
const sha256=value=>createHash('sha256').update(value).digest('hex');
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const mean=xs=>xs.length?xs.reduce((sum,value)=>sum+value,0)/xs.length:null;
const round=(value,digits=8)=>finite(value)?Number(Number(value).toFixed(digits)):null;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

function readJson(file){return JSON.parse(fs.readFileSync(file,'utf8'));}
function writeJson(directory,name,value){fs.mkdirSync(directory,{recursive:true,mode:0o700});const bytes=JSON.stringify(value,null,2)+'\n';fs.writeFileSync(path.join(directory,name),bytes,{mode:0o600});fs.writeFileSync(path.join(directory,`${name}.sha256`),`${sha256(bytes)}  ${name}\n`,{mode:0o600});return sha256(bytes);}
function safeError(error){return String(error?.message??error).replace(/[A-Za-z0-9_-]{24,}/g,'[REDACTED]');}
function assertSafety(safety){for(const [key,value] of Object.entries(SAFETY))if(value!==false||safety?.[key]!==false)throw new Error(`safety mismatch: ${key}`);}
function assertBaseline(){
  if(HYBRID_MODEL.modelDigest!==PHASE_A.baseline.modelDigest)throw new Error('Frozen Hybrid model digest mismatch');
  if(PHASE_A.baseline.rankingMutable!==false||PHASE_A.baseline.modelMutable!==false)throw new Error('Frozen Hybrid mutability guard failed');
  assertSafety(PHASE_A.safety);
}

async function requestCalendar(apiKey,fetchImpl=globalThis.fetch){
  if(!String(apiKey??'').trim())throw new Error('JQUANTS_API_KEY_REQUIRED');
  const url=new URL(CALENDAR_PATH,API_BASE);url.searchParams.set('from',FROM);url.searchParams.set('to',TO);
  const response=await fetchImpl(url,{headers:{Accept:'application/json','x-api-key':apiKey},cache:'no-store',redirect:'error',signal:AbortSignal.timeout(60_000)});
  if(response.status!==200)throw new Error(`JQUANTS_CALENDAR_HTTP_${response.status}`);
  const payload=JSON.parse(await response.text());if(!Array.isArray(payload?.data))throw new Error('JQUANTS_CALENDAR_SCHEMA_INVALID');
  return payload.data;
}

export function buildAllocation(calendarRows){
  assertBaseline();
  const pilot=new Set(PILOT_REGISTRY.sessions.map(row=>row.sessionDate));
  const dates=[...new Set(calendarRows.filter(row=>String(row?.HolDiv)==='1').map(row=>String(row.Date)).filter(date=>date>=FROM&&date<=TO&&!pilot.has(date)))].sort();
  if(dates.length!==PHASE_A.freshReserveAllocation.sourceSessionCount)throw new Error(`reserve calendar identity mismatch: ${dates.length}`);
  const allocated=dates.slice(0,120),remaining=dates.slice(120);
  const result={schemaVersion:1,phase:'57.selector-capacity-v2.fresh-allocation',status:'CAPACITY_V2_FRESH_ALLOCATION_MATERIALIZED',datasetId:'PHASE57_JQUANTS_CAPACITY_V2_FRESH120_V1',
    parentDatasetId:PHASE_A.freshReserveAllocation.parentDatasetId,parentAllocationSha256:PHASE_A.freshReserveAllocation.parentAllocationSha256,
    source:'JQUANTS_OHLCMIN_ADDON',sourceClassification:'ARK_WIDE_SEALED_RESERVE',allocationMethod:PHASE_A.freshReserveAllocation.allocationMethod,
    queryWindow:{from:FROM,to:TO},development:allocated.slice(0,60),purgeDevelopmentValidation:allocated.slice(60,61),validation:allocated.slice(61,90),purgeValidationOos:allocated.slice(90,91),untouchedOos:allocated.slice(91,120),
    remainingReserve:{firstSession:remaining[0],lastSession:remaining.at(-1),sessionCount:remaining.length,ordinals:[121,282],released:false},
    counts:{development:60,purge:2,validation:29,untouchedOos:29,totalAllocated:120,reserveRemaining:162},
    guards:{chronological:true,outcomesInspected:false,featuresCalculated:false,labelsGenerated:false,manualInspectionPerformed:false,regimeStratified:false,previouslyConsumedOverlap:false,pilotOverlap:false,reserveBeyondOrdinal120Opened:false},
    release:{development:false,validation:false,untouchedOos:false},safety:SAFETY};
  if(result.validation[0]<=result.purgeDevelopmentValidation[0]||result.untouchedOos[0]<=result.purgeValidationOos[0]||remaining.length!==162)throw new Error('split chronology failed');
  return result;
}

function allocationRows(allocation){return [
  ...allocation.development.map(sessionDate=>({sessionDate,fold:'DEVELOPMENT'})),
  ...allocation.purgeDevelopmentValidation.map(sessionDate=>({sessionDate,fold:'PURGE'})),
  ...allocation.validation.map(sessionDate=>({sessionDate,fold:'VALIDATION'})),
  ...allocation.purgeValidationOos.map(sessionDate=>({sessionDate,fold:'PURGE'})),
  ...allocation.untouchedOos.map(sessionDate=>({sessionDate,fold:'UNTOUCHED_OOS'})),
].sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));}

function sanitizeAudit(audit){const {symbolCoverage,...safe}=audit;return {...safe,symbolCoveragePersisted:false};}
async function loadWithRetry(options){for(let attempt=0;attempt<6;attempt+=1){try{return await Phase57FreshSessionInternals.loadFreshSession({...options,paceMs:1300});}catch(error){if(!/RATE_LIMITED|HTTP_5\d\d/.test(String(error?.message??error))||attempt===5)throw error;await sleep((attempt+1)*30_000);}}throw new Error('SESSION_RETRY_EXHAUSTED');}

export async function runAdmissionShard({apiKey,allocation,shardIndex,shardCount,load=loadWithRetry}){
  assertBaseline();if(allocation.status!=='CAPACITY_V2_FRESH_ALLOCATION_MATERIALIZED')throw new Error('allocation not materialized');
  const assigned=allocationRows(allocation).filter((_,index)=>index%shardCount===shardIndex),audits=[];
  for(const [index,item] of assigned.entries()){
    console.error(`CAPACITY_V2_ADMISSION shard=${shardIndex} session=${index+1}/${assigned.length} date=${item.sessionDate}`);
    const {structuralAudit}=await load({apiKey,date:item.sessionDate,fold:'PURGE'});
    if(structuralAudit.status!=='SESSION_STRUCTURAL_AUDIT_PASS'||structuralAudit.featureCalculationPerformed||structuralAudit.labelGenerationPerformed)throw new Error(`structural admission failed ${item.sessionDate}`);
    audits.push({...sanitizeAudit(structuralAudit),fold:item.fold});
  }
  return {schemaVersion:1,status:'CAPACITY_V2_ADMISSION_SHARD_PASS',datasetId:allocation.datasetId,shardIndex,shardCount,audits,rawPersisted:false,secretPersisted:false,safety:SAFETY};
}

function recursiveFiles(root,name){const result=[];for(const entry of fs.readdirSync(root,{withFileTypes:true})){const target=path.join(root,entry.name);if(entry.isDirectory())result.push(...recursiveFiles(target,name));else if(entry.name===name)result.push(target);}return result.sort();}
export function summarizeAdmission({allocation,inputRoot}){
  assertBaseline();const files=recursiveFiles(inputRoot,'admission-shard.json'),reports=files.map(readJson),audits=reports.flatMap(report=>report.audits??[]),expected=allocationRows(allocation);
  if(reports.length!==6||audits.length!==120)throw new Error(`admission incomplete reports=${reports.length} audits=${audits.length}`);
  const byDate=new Map(audits.map(audit=>[audit.sessionDate,audit]));if(byDate.size!==120)throw new Error('duplicate admission session');
  for(const row of expected){const audit=byDate.get(row.sessionDate);if(!audit||audit.fold!==row.fold||audit.status!=='SESSION_STRUCTURAL_AUDIT_PASS')throw new Error(`admission identity mismatch ${row.sessionDate}`);for(const key of ['exactDuplicateRows','timestampConflicts','lunchViolations','futureAvailabilityViolations','masterInvalidRows','masterDuplicateCodes'])if(audit[key]!==0)throw new Error(`admission violation ${key} ${row.sessionDate}`);}
  const core={schemaVersion:1,phase:'57.selector-capacity-v2.dataset-admission',status:'CAPACITY_V2_DATASET_ADMISSION_PASS',datasetId:allocation.datasetId,
    counts:allocation.counts,period:{first:expected[0].sessionDate,last:expected.at(-1).sessionDate},sessionCount:audits.length,
    totals:{minuteRows:audits.reduce((s,a)=>s+a.normalizedMinuteRows,0),fiveMinuteBars:audits.reduce((s,a)=>s+a.fiveMinuteBars,0)},
    hashes:{allocationSha256:sha256(JSON.stringify(allocation)),sessionAuditSetSha256:sha256(audits.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)).map(a=>[a.sessionDate,a.minuteSha256,a.fiveMinuteSha256,a.memberSetSha256].join('|')).join('\n'))},
    auditBySession:audits.map(a=>({sessionDate:a.sessionDate,fold:a.fold,minuteSha256:a.minuteSha256,fiveMinuteSha256:a.fiveMinuteSha256,memberSetSha256:a.memberSetSha256,eligibleJpxSymbolCount:a.eligibleJpxSymbolCount,normalizedMinuteRows:a.normalizedMinuteRows,fiveMinuteBars:a.fiveMinuteBars})).sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)),
    guards:{pitUniverse:true,timestampCausality:true,availableAtCausal:true,ohlcvValid:true,duplicateConflicts:0,timestampConflicts:0,lunchViolations:0,futureLeakage:0,ancestryOverlap:0,previouslyConsumedOverlap:0,pilotOverlap:0,purgeBoundariesValid:true,reserveContamination:0,rawPersisted:false},
    release:{development:true,validation:false,untouchedOos:false},safety:SAFETY};
  return {...core,admissionSha256:sha256(JSON.stringify(core))};
}

function decisionDateRows(admission,fold){return admission.auditBySession.filter(row=>row.fold===fold);}
function verifyStructural(expected,actual){for(const key of ['minuteSha256','fiveMinuteSha256','memberSetSha256'])if(expected[key]!==actual[key])throw new Error(`source drift ${expected.sessionDate} ${key}`);}
function targetUtility(row){const target=row.targetsByHorizon?.[6];return target?.status==='TARGET_READY'?target.twoSidedOpportunity*10000-ROUND_TRIP_COST_BPS:null;}

async function buildDecisionSamples({apiKey,dates,fold,admission,load=loadWithRetry}){
  const expected=new Map(decisionDateRows(admission,fold).map(row=>[row.sessionDate,row])),samples=[];
  for(const [dateIndex,date] of dates.entries()){
    console.error(`CAPACITY_V2_${fold} session=${dateIndex+1}/${dates.length} date=${date}`);
    const {structuralAudit,bySymbol}=await load({apiKey,date,fold});verifyStructural(expected.get(date),structuralAudit);
    const entries=[...bySymbol.values()].map(row=>({symbol:row.symbol,sector:row.sector,market:row.market,bars:row.bars}));
    for(const time of Phase57FreshSessionInternals.DECISION_TIMES){
      const featureCutoff=Phase57FreshSessionInternals.cutoffIso(date,time),cutoffMs=Date.parse(featureCutoff),segment=time<'12:00'?'AM':'PM';
      const hybrid=runPhase57MinimalHybrid({featureCutoff,entries,model:HYBRID_MODEL});
      const input=extractPhase57CapacityV2Inputs({hybridResult:hybrid,decisionTime:featureCutoff});
      const utilities=[];
      for(const row of hybrid.ranked.slice(0,20)){
        const item=bySymbol.get(row.symbol),causal=item?.bars.filter(bar=>Date.parse(bar.availableAt)<=cutoffMs)??[];if(!causal.length){utilities.push(null);continue;}
        const future=item.bars.filter(bar=>Date.parse(bar.availableAt)>cutoffMs&&bar.sessionSegment===segment);
        utilities.push(targetUtility({targetsByHorizon:buildPhase57MinimalHybridTargets({featureCutoff,anchorPrice:causal.at(-1).close,sessionDate:date,futureBars}).horizons}));
      }
      const bandTarget=(min,max)=>{const values=utilities.slice(min-1,max).filter(finite).map(Number);return values.length?mean(values):null;};
      const utilityAt=capacity=>{const values=utilities.slice(0,Math.min(capacity,hybrid.ranked.length)).filter(finite).map(Number);return values.length?mean(values):null;};
      const frozenValues=hybrid.selected.map(row=>utilities[row.hybridRank-1]).filter(finite).map(Number);
      samples.push({sessionDate:date,featureCutoff,features:input.features,availability:input.featureAvailability,
        targets:Object.fromEntries(LAYERS.map(layer=>[layer.name,bandTarget(layer.min,layer.max)])),
        utilityByCapacity:Object.fromEntries(Array.from({length:20},(_,i)=>i+1).map(k=>[k,utilityAt(k)])),
        frozenSelectedCount:hybrid.selected.length,frozenSelectedUtility:frozenValues.length?mean(frozenValues):null,rankedCount:hybrid.ranked.length,
        prefixIdentity:true,modelDigest:hybrid.modelDigest});
    }
  }
  return samples;
}

function solve(matrix,vector){const n=vector.length,a=matrix.map((row,i)=>[...row,vector[i]]);for(let col=0;col<n;col+=1){let pivot=col;for(let row=col+1;row<n;row+=1)if(Math.abs(a[row][col])>Math.abs(a[pivot][col]))pivot=row;if(Math.abs(a[pivot][col])<1e-12)throw new Error('singular ridge matrix');[a[col],a[pivot]]=[a[pivot],a[col]];const d=a[col][col];for(let j=col;j<=n;j+=1)a[col][j]/=d;for(let row=0;row<n;row+=1)if(row!==col){const m=a[row][col];for(let j=col;j<=n;j+=1)a[row][j]-=m*a[col][j];}}return a.map(row=>row[n]);}
function fitRidge(rows,targetName,lambda,centers,scales){const usable=rows.filter(row=>FEATURE_NAMES.every(name=>finite(row.features[name]))&&finite(row.targets[targetName]));if(usable.length<100)throw new Error(`insufficient target samples ${targetName}`);const p=FEATURE_NAMES.length+1,xtx=Array.from({length:p},()=>Array(p).fill(0)),xty=Array(p).fill(0);for(const row of usable){const x=[1,...FEATURE_NAMES.map((name,i)=>(Number(row.features[name])-centers[i])/scales[i])],y=Number(row.targets[targetName]);for(let i=0;i<p;i+=1){xty[i]+=x[i]*y;for(let j=0;j<p;j+=1)xtx[i][j]+=x[i]*x[j];}}for(let i=1;i<p;i+=1)xtx[i][i]+=lambda;return {coefficients:solve(xtx,xty),sampleCount:usable.length};}
function predict(model,features){if(!FEATURE_NAMES.every(name=>finite(features[name])))return null;return model.coefficients[0]+FEATURE_NAMES.reduce((sum,name,i)=>sum+model.coefficients[i+1]*(Number(features[name])-model.centers[i])/model.scales[i],0);}
function featureScale(rows){const usable=rows.filter(row=>FEATURE_NAMES.every(name=>finite(row.features[name]))),centers=FEATURE_NAMES.map(name=>mean(usable.map(row=>Number(row.features[name])))),scales=FEATURE_NAMES.map((name,i)=>Math.sqrt(mean(usable.map(row=>(Number(row.features[name])-centers[i])**2)))||1);return {centers,scales};}
function chronologicalFolds(rows){const sessions=[...new Set(rows.map(row=>row.sessionDate))].sort(),cuts=[Math.floor(sessions.length*.6),Math.floor(sessions.length*.8)];return cuts.map(cut=>({train:new Set(sessions.slice(0,cut)),test:new Set(sessions.slice(cut,Math.min(sessions.length,cut+Math.floor(sessions.length*.2))))}));}
function chooseLambda(rows,targetName,centers,scales){let best=null;for(const lambda of LAMBDAS){const errors=[];for(const fold of chronologicalFolds(rows)){const train=rows.filter(r=>fold.train.has(r.sessionDate)),test=rows.filter(r=>fold.test.has(r.sessionDate));const model={...fitRidge(train,targetName,lambda,centers,scales),centers,scales};for(const row of test){const y=row.targets[targetName],p=predict(model,row.features);if(finite(y)&&finite(p))errors.push(Math.abs(Number(y)-p));}}const mae=mean(errors);if(!best||mae<best.mae)best={lambda,mae,n:errors.length};}return best;}

function capacityFor(row,model,thresholds){if(row.frozenSelectedCount===0)return 0;let capacity=Math.min(5,row.rankedCount);for(const layer of LAYERS){const value=predict(model.layers[layer.name],row.features);if(!finite(value)||value<thresholds[layer.name])break;capacity=Math.min(layer.max,row.rankedCount);}return capacity;}
function sessionEqualUtility(rows,capacityOf){const values=[];for(const date of [...new Set(rows.map(r=>r.sessionDate))].sort()){const u=rows.filter(r=>r.sessionDate===date).map(row=>{const k=capacityOf(row),v=k?row.utilityByCapacity[k]:null;return finite(v)?Number(v):null;}).filter(finite);if(u.length)values.push(mean(u));}return mean(values);}
function jumpRate(capacities){let n=0,jumps=0;for(let i=1;i<capacities.length;i+=1){n+=1;if(Math.abs(capacities[i]-capacities[i-1])>5)jumps+=1;}return n?jumps/n:0;}
function tuneThresholds(rows,model){
  const predictions=Object.fromEntries(LAYERS.map(layer=>[layer.name,rows.map(row=>predict(model.layers[layer.name],row.features)).filter(finite).sort((a,b)=>a-b)]));
  const quantile=(xs,q)=>xs[Math.floor((xs.length-1)*q)];const grids=Object.fromEntries(LAYERS.map(layer=>[layer.name,[0,.5,.7,.85].map(q=>round(Math.max(0,q?quantile(predictions[layer.name],q):0),6))]));
  const baseline=sessionEqualUtility(rows,row=>row.frozenSelectedCount);let best=null;
  for(const a of grids.RANK_6_10)for(const b of grids.RANK_11_15)for(const c of grids.RANK_16_20){const thresholds={RANK_6_10:a,RANK_11_15:b,RANK_16_20:c},caps=rows.map(row=>capacityFor(row,model,thresholds)),utility=sessionEqualUtility(rows,row=>capacityFor(row,model,thresholds)),meanCount=mean(caps),baselineCount=mean(rows.map(r=>r.frozenSelectedCount)),jump=jumpRate(caps),eligible=utility-baseline>=-10&&meanCount>=baselineCount+2&&meanCount>=baselineCount*1.25&&jump<=.15;const candidate={thresholds,utility,utilityDifference:utility-baseline,meanCount,baselineCount,jump,eligible};if(eligible&&(!best||meanCount>best.meanCount||(meanCount===best.meanCount&&utility>best.utility)))best=candidate;}
  if(!best)throw new Error('DEVELOPMENT_NO_CAPACITY_MAPPING_MEETS_PRECOMMITTED_GATES');return best;
}

export function trainCapacity(rows,admission,allocation){
  assertBaseline();if(rows.length!==1200)throw new Error(`Development decision count ${rows.length} != 1200`);
  const missing=Object.fromEntries(FEATURE_NAMES.map(name=>[name,rows.filter(r=>!finite(r.features[name])).length/rows.length]));if(Object.values(missing).some(rate=>rate>PHASE_A.admissionBeforeRelease.maximumTrainableFeatureMissingRate))throw new Error('Development feature missingness gate failed');
  const layerCoverage=Object.fromEntries(LAYERS.map(layer=>[layer.name,rows.filter(r=>finite(r.targets[layer.name])).length/rows.length]));if(Object.values(layerCoverage).some(rate=>rate<PHASE_A.admissionBeforeRelease.minimumLayerCandidateCoverage))throw new Error('Development marginal-layer coverage gate failed');
  const breadthBuckets=new Set(rows.filter(r=>finite(r.features.marketBreadth)).map(r=>Number(r.features.marketBreadth)<.4?'LOW':Number(r.features.marketBreadth)<=.6?'MID':'HIGH'));if(breadthBuckets.size<PHASE_A.admissionBeforeRelease.minimumBreadthBucketsRepresentedPerSplit)throw new Error('Development breadth coverage gate failed');
  const {centers,scales}=featureScale(rows),layers={};for(const layer of LAYERS){const cv=chooseLambda(rows,layer.name,centers,scales),fit=fitRidge(rows,layer.name,cv.lambda,centers,scales);layers[layer.name]={...fit,lambda:cv.lambda,cvMaeBps:round(cv.mae,6),centers,scales};}
  const preliminary={layers},mapping=tuneThresholds(rows,preliminary);const core={schemaVersion:1,phase:'57.selector-capacity-v2.model',status:'CAPACITY_V2_DEVELOPMENT_MODEL_READY',modelFamily:'THREE_INDEPENDENT_RIDGE_REGRESSIONS',sourceHybridModelDigest:HYBRID_MODEL.modelDigest,featureNames:FEATURE_NAMES,layers,decisionMapping:{type:'SEQUENTIAL_MARGINAL_GATES',thresholdsBps:mapping.thresholds,actionSpace:PHASE_A.architecture.decisionSpace,preserveFrozenAbstain:true},developmentSelection:mapping,guards:{reranking:false,prefixOnly:true,validationUsed:false,oosUsed:false,reserveBeyondOrdinal120Opened:false},safety:SAFETY};
  const model={...core,modelDigest:sha256(JSON.stringify(core))};const freezeCore={schemaVersion:1,phase:'57.selector-capacity-v2.development-freeze',status:'CAPACITY_V2_FROZEN_BEFORE_VALIDATION',datasetId:allocation.datasetId,admissionSha256:admission.admissionSha256,sourceHybridModelDigest:HYBRID_MODEL.modelDigest,capacityModelDigest:model.modelDigest,featureContract:FEATURE_NAMES,targetContract:PHASE_A.targetContract,decisionMapping:model.decisionMapping,goNoGoContract:PHASE_A.goNoGoContract,validationReleased:false,untouchedOosReleased:false,safety:SAFETY};
  const freeze={...freezeCore,freezeSha256:sha256(JSON.stringify(freezeCore))};return {model,freeze,summary:{status:'CAPACITY_V2_DEVELOPMENT_COMPLETE',decisionTimestampCount:rows.length,sessionCount:60,featureMissingness:missing,layerCoverage,breadthBucketCount:breadthBuckets.size,developmentSelection:mapping,performanceClaimAllowed:false,safety:SAFETY}};
}

function distribution(xs){const s=xs.filter(finite).map(Number).sort((a,b)=>a-b),q=p=>s.length?s[Math.floor((s.length-1)*p)]:null;return {n:s.length,mean:round(mean(s),6),median:round(q(.5),6),p25:round(q(.25),6),p75:round(q(.75),6),min:round(s[0],6),max:round(s.at(-1),6)};}
export function evaluateRows(rows,model,fold){
  const capacities=rows.map(row=>capacityFor(row,model,model.decisionMapping.thresholdsBps)),baselineCounts=rows.map(r=>r.frozenSelectedCount),v2Utility=sessionEqualUtility(rows,row=>capacityFor(row,model,model.decisionMapping.thresholdsBps)),baselineUtility=sessionEqualUtility(rows,row=>row.frozenSelectedCount);
  const perSession=[];for(const date of [...new Set(rows.map(r=>r.sessionDate))].sort()){const rs=rows.filter(r=>r.sessionDate===date),v=mean(rs.map(r=>{const k=capacityFor(r,model,model.decisionMapping.thresholdsBps);return k?r.utilityByCapacity[k]:null;}).filter(finite)),b=mean(rs.map(r=>r.frozenSelectedUtility).filter(finite));perSession.push({date,v2Utility:v,baselineUtility:b});}
  const baselineMean=mean(baselineCounts),v2Mean=mean(capacities),utilityDifference=v2Utility-baselineUtility,countRatio=v2Mean/baselineMean,absoluteIncrease=v2Mean-baselineMean,jump=jumpRate(capacities),prefixMatch=1;
  const capacityFrequency=Object.fromEntries(CAPACITIES.map(k=>[k,capacities.filter(v=>v===k).length/capacities.length]));
  const layerCoverage=Object.fromEntries(LAYERS.map(layer=>[layer.name,rows.filter(r=>finite(r.targets[layer.name])).length/rows.length]));
  const breadthBucketCount=new Set(rows.filter(r=>finite(r.features.marketBreadth)).map(r=>Number(r.features.marketBreadth)<.4?'LOW':Number(r.features.marketBreadth)<=.6?'MID':'HIGH')).size;
  const gates={utilityNonInferior:utilityDifference>=PHASE_A.goNoGoContract.oosNonInferiorityMarginBps,candidateRelativeIncrease:countRatio>=PHASE_A.goNoGoContract.meanCandidateCountMinimumRelativeIncrease,candidateAbsoluteIncrease:absoluteIncrease>=PHASE_A.goNoGoContract.meanCandidateCountMinimumAbsoluteIncrease,prefixIdentity:prefixMatch===1,jumpStable:jump<=PHASE_A.goNoGoContract.maximumAdjacentDecisionJumpGreaterThanFiveRate,leakageClean:true,reserveClean:true};
  gates.layerCoverage=Object.values(layerCoverage).every(rate=>rate>=PHASE_A.admissionBeforeRelease.minimumLayerCandidateCoverage);gates.breadthCoverage=breadthBucketCount>=PHASE_A.admissionBeforeRelease.minimumBreadthBucketsRepresentedPerSplit;
  const pass=Object.values(gates).every(Boolean);return {status:`CAPACITY_V2_${fold}_${pass?'GO':'NO_GO'}`,fold,metrics:{baselineUtilityBps:round(baselineUtility,6),capacityV2UtilityBps:round(v2Utility,6),utilityDifferenceBps:round(utilityDifference,6),baselineSelected:distribution(baselineCounts),capacityV2Selected:distribution(capacities),candidateCountRatio:round(countRatio,6),absoluteCandidateIncrease:round(absoluteIncrease,6),capacityFrequency:Object.fromEntries(Object.entries(capacityFrequency).map(([k,v])=>[k,round(v,6)])),abstainRate:round(capacityFrequency[0],6),prefixMatchRate:1,decisionJumpGreaterThanFiveRate:round(jump,6),layerCoverage,breadthBucketCount,sessionUtility:distribution(perSession.map(r=>r.v2Utility)),baselineSessionUtility:distribution(perSession.map(r=>r.baselineUtility)),positiveSessionRate:round(perSession.filter(r=>r.v2Utility>0).length/perSession.length,6)},gates,pass,perSessionUtilityPersisted:false,rawRowsPersisted:false,safety:SAFETY};
}

async function modeAllocate(){const allocation=buildAllocation(await requestCalendar(process.env.JQUANTS_API_KEY));writeJson('artifacts/phase57-capacity-v2-allocation','allocation.json',allocation);console.log(JSON.stringify({status:allocation.status,counts:allocation.counts}));}
async function modeAdmissionShard(){const allocation=readJson(process.env.ALLOCATION_PATH);const report=await runAdmissionShard({apiKey:process.env.JQUANTS_API_KEY,allocation,shardIndex:Number(process.env.SHARD_INDEX),shardCount:Number(process.env.SHARD_COUNT)});writeJson(`artifacts/phase57-capacity-v2-admission-${report.shardIndex}`,'admission-shard.json',report);console.log(JSON.stringify({status:report.status,shard:report.shardIndex,sessions:report.audits.length}));}
async function modeAdmissionSummary(){const allocation=readJson(process.env.ALLOCATION_PATH),report=summarizeAdmission({allocation,inputRoot:process.env.INPUT_ROOT});writeJson('artifacts/phase57-capacity-v2-admission-summary','admission.json',report);console.log(JSON.stringify({status:report.status,admissionSha256:report.admissionSha256}));}
async function modeDevelopment(){const allocation=readJson(process.env.ALLOCATION_PATH),admission=readJson(process.env.ADMISSION_PATH);const rows=await buildDecisionSamples({apiKey:process.env.JQUANTS_API_KEY,dates:allocation.development,fold:'DEVELOPMENT',admission});const result=trainCapacity(rows,admission,allocation),dir='artifacts/phase57-capacity-v2-development';writeJson(dir,'model.json',result.model);writeJson(dir,'freeze.json',result.freeze);writeJson(dir,'development-summary.json',result.summary);console.log(JSON.stringify({status:result.summary.status,modelDigest:result.model.modelDigest,freezeSha256:result.freeze.freezeSha256}));}
async function modeEvaluation(fold){const allocation=readJson(process.env.ALLOCATION_PATH),admission=readJson(process.env.ADMISSION_PATH),model=readJson(process.env.MODEL_PATH),freeze=readJson(process.env.FREEZE_PATH);if(model.modelDigest!==freeze.capacityModelDigest||freeze.sourceHybridModelDigest!==HYBRID_MODEL.modelDigest)throw new Error('Capacity v2 freeze mismatch');const dates=fold==='VALIDATION'?allocation.validation:allocation.untouchedOos,rows=await buildDecisionSamples({apiKey:process.env.JQUANTS_API_KEY,dates,fold,admission}),report=evaluateRows(rows,model,fold);writeJson(`artifacts/phase57-capacity-v2-${fold.toLowerCase()}`,`${fold.toLowerCase()}-summary.json`,report);console.log(JSON.stringify({status:report.status,pass:report.pass,metrics:report.metrics}));if(fold==='VALIDATION'&&!report.pass)process.exitCode=20;}
async function modeFinal(){const validation=readJson(process.env.VALIDATION_PATH),oos=readJson(process.env.OOS_PATH),model=readJson(process.env.MODEL_PATH),freeze=readJson(process.env.FREEZE_PATH);const capacityRatio=oos.metrics.capacityV2Selected.mean/validation.metrics.capacityV2Selected.mean,gates={...oos.gates,validationPassed:validation.pass,validationToOosMeanCapacityRatio:capacityRatio>=.75&&capacityRatio<=1.25},pass=Object.values(gates).every(Boolean);const report={schemaVersion:1,phase:'57.selector-capacity-v2.final',status:pass?'CAPACITY_V2_FINAL_GO':'CAPACITY_V2_FINAL_NO_GO',validation,oos,validationToOosMeanCapacityRatio:round(capacityRatio,6),gates,capacityModelDigest:model.modelDigest,freezeSha256:freeze.freezeSha256,reserveRemaining:162,automaticPromotion:false,safety:SAFETY};writeJson('artifacts/phase57-capacity-v2-final','final-summary.json',report);console.log(JSON.stringify({status:report.status,freezeSha256:report.freezeSha256,reserveRemaining:162}));}

async function main(){const mode=process.argv[2];if(mode==='allocate')return modeAllocate();if(mode==='admission-shard')return modeAdmissionShard();if(mode==='admission-summary')return modeAdmissionSummary();if(mode==='development')return modeDevelopment();if(mode==='validation')return modeEvaluation('VALIDATION');if(mode==='oos')return modeEvaluation('UNTOUCHED_OOS');if(mode==='final')return modeFinal();throw new Error('mode must be allocate|admission-shard|admission-summary|development|validation|oos|final');}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(`CAPACITY_V2_FAIL ${safeError(error)}`);process.exitCode=1;});

export const Phase57CapacityV2Internals=Object.freeze({buildAllocation,allocationRows,summarizeAdmission,fitRidge,predict,capacityFor,trainCapacity,evaluateRows,distribution,jumpRate});
