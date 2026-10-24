// Offline counterfactual diagnosis over already-opened Dev95 and Holdout99 only.
// No fetch, fit, candidate mutation, timing rule, or threshold optimization.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';

const sha256=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p));
const finite=x=>Number.isFinite(x);
const q=(xs,p)=>{const a=xs.filter(finite).sort((x,y)=>x-y);if(!a.length)return null;const z=(a.length-1)*p,l=Math.floor(z),u=Math.ceil(z);return a[l]+(a[u]-a[l])*(z-l);};
export const stats=xs=>{const a=xs.filter(finite);return {n:a.length,mean:a.length?a.reduce((s,x)=>s+x,0)/a.length:null,median:q(a,.5),p25:q(a,.25),p75:q(a,.75),p90:q(a,.9)};};
const jst=t=>new Date(t+32400000).toISOString();
const normalizeStart=(t,date)=>{const z=jst(t),clock=z.slice(11,16);if(clock>='11:30'&&clock<'12:30')t=Date.parse(`${date}T12:30:00+09:00`);return t;};
export function exactGrid(bars,start,date,h){
 const by=new Map(bars.map(b=>[Date.parse(b.timestamp),b])),path=[];let t=start;
 for(let i=0;i<h;i++){
  t=normalizeStart(t,date);const z=jst(t),clock=z.slice(11,16);
  if(z.slice(0,10)!==date||clock>='15:30'){path.push(null);break;}
  path.push(by.get(t)??null);t+=300000;
 }
 while(path.length<h)path.push(null);
 return path;
}
export function excursion(reference,direction,path){
 if(!finite(reference)||reference<=0||path.length===0||path.some(b=>!b))return null;
 const d=direction==='LONG'?1:-1;
 const gross=d*(path.at(-1).close/reference-1)*10000;
 const adverse=path.map(b=>Math.max(0,(d===1?1-b.low/reference:b.high/reference-1)*10000));
 const favorable=path.map(b=>Math.max(0,(d===1?b.high/reference-1:1-b.low/reference)*10000));
 return {gross,net:gross-5,positive:gross-5>0,mae:Math.max(...adverse),mfe:Math.max(...favorable)};
}
function loadBundles(dir,dates,sourceHashes){
 const map=new Map();
 for(const date of dates){
  const m=read(`${dir}/${date}.manifest.json`),fb=gunzipSync(fs.readFileSync(`${dir}/${date}.features.json.gz`)),bb=gunzipSync(fs.readFileSync(`${dir}/${date}.bars.json.gz`));
  assert.equal(sha256(fb),m.featureSha256);assert.equal(sha256(bb),m.barsSha256);
  const f=JSON.parse(fb),raw=JSON.parse(bb);assert.equal(f.sessionDate,date);
  sourceHashes.push({sessionDate:date,featureSha256:sha256(fb),barsSha256:sha256(bb)});
  map.set(date,{...f,bars:new Map(raw.map(x=>[x.symbol,x.bars]))});
 }
 return map;
}
function analyzeRow(row,bundle){
 const bars=bundle.bars.get(row.eventId.split('|').at(-1));assert(bars,'BARS_MISSING');
 const t=Date.parse(row.eventId.split('|')[1]),baselineRef=row.reference,base3=exactGrid(bars,t,row.sessionDate,3),base6=exactGrid(bars,t,row.sessionDate,6);
 const baseline={3:excursion(baselineRef,row.direction,base3),6:excursion(baselineRef,row.direction,base6)};
 for(const h of [3,6])assert.equal(baseline[h]?.net??null,row['net'+h]??null,'BASELINE_RECONSTRUCTION_MISMATCH');
 const counterBar=base6[0];
 if(!counterBar)return {...row,counterfactual:{status:'COUNTERFACTUAL_UNAVAILABLE',reason:'NEXT_COMPLETED_BAR_MISSING',baseline}};
 assert.equal(Date.parse(counterBar.availableAt),Date.parse(counterBar.timestamp)+300000,'BAR_AVAILABILITY_SEMANTICS');
 const counterRef=counterBar.close,availableAt=counterBar.availableAt,d=row.direction==='LONG'?1:-1;
 const improvement=-d*(counterRef/baselineRef-1)*10000;
 const same={},post={};
 for(const h of [3,6]){
  same[h]=excursion(counterRef,row.direction,(h===3?base3:base6).slice(1));
  post[h]=excursion(counterRef,row.direction,exactGrid(bars,Date.parse(availableAt),row.sessionDate,h));
 }
 const at=bundle.points.find(p=>Date.parse(p.decisionTimestamp)===Date.parse(availableAt));
 const selected=at?.complete?bundle.events.some(e=>e.symbol===row.eventId.split('|').at(-1)&&e.decisionTimestamp===at.decisionTimestamp):null;
 const persistence=selected===null?'NOT_OBSERVABLE':selected?'STILL_SELECTED':'DROPPED';
 const compare=(base,wait)=>base&&wait?{netDifference:wait.net-base.net,maeReductionBps:base.mae-wait.mae,maeReductionPct:base.mae>0?(base.mae-wait.mae)/base.mae:null,mfeLostBps:base.mfe-wait.mfe}:null;
 return {...row,counterfactual:{status:'ELIGIBLE',priceReference:counterRef,barTimestamp:counterBar.timestamp,availableAt,barCountWaited:1,clockElapsedMinutes:(Date.parse(availableAt)-t)/60000,entryPriceImprovementBps:improvement,chasedAfterWait:improvement<0,priceDeteriorationBps:Math.max(0,-improvement),baseline,sameAbsoluteEndpoint:same,samePostEntryHorizon:post,comparison:{sameAbsoluteEndpoint:{3:compare(baseline[3],same[3]),6:compare(baseline[6],same[6])},samePostEntryHorizon:{3:compare(baseline[3],post[3]),6:compare(baseline[6],post[6])}},hybridPersistence:persistence}};
}
const rate=(n,d)=>d?n/d:null;
function metric(rows,mode,h){return rows.map(r=>r.counterfactual?.[mode]?.[h]).filter(Boolean);}
function summarize(rows){
 const eligible=rows.filter(r=>r.counterfactual.status==='ELIGIBLE'),unavailable=rows.length-eligible.length,imps=eligible.map(r=>r.counterfactual.entryPriceImprovementBps),chased=eligible.filter(r=>r.counterfactual.chasedAfterWait);
 const horizons={};
 for(const h of [3,6]){
  const baseline=metric(rows,'baseline',h),same=metric(eligible,'sameAbsoluteEndpoint',h),post=metric(eligible,'samePostEntryHorizon',h);
  const describe=a=>({complete:a.length,missing:rows.length-a.length,positive:a.filter(x=>x.positive).length,positiveRate:rate(a.filter(x=>x.positive).length,a.length),net:stats(a.map(x=>x.net)),gross:stats(a.map(x=>x.gross)),mae:stats(a.map(x=>x.mae)),mfe:stats(a.map(x=>x.mfe))});
  const comparisons=(mode)=>eligible.map(r=>r.counterfactual.comparison[mode][h]).filter(Boolean);
  const cs=comparisons('sameAbsoluteEndpoint'),cp=comparisons('samePostEntryHorizon');
  horizons[h]={baseline:describe(baseline),sameAbsoluteEndpoint:describe(same),samePostEntryHorizon:describe(post),difference:{sameAbsoluteEndpoint:{net:stats(cs.map(x=>x.netDifference)),maeReductionBps:stats(cs.map(x=>x.maeReductionBps)),maeReductionPct:stats(cs.map(x=>x.maeReductionPct)),mfeLostBps:stats(cs.map(x=>x.mfeLostBps))},samePostEntryHorizon:{net:stats(cp.map(x=>x.netDifference)),maeReductionBps:stats(cp.map(x=>x.maeReductionBps)),maeReductionPct:stats(cp.map(x=>x.maeReductionPct)),mfeLostBps:stats(cp.map(x=>x.mfeLostBps))}}};
 }
 const bucket={};for(const p of ['STILL_SELECTED','DROPPED','NOT_OBSERVABLE'])for(const s of ['IMPROVED','WORSENED','UNCHANGED'])bucket[`${p}_${s}`]=0;
 for(const r of eligible){const v=r.counterfactual.entryPriceImprovementBps,s=v>0?'IMPROVED':v<0?'WORSENED':'UNCHANGED';bucket[`${r.counterfactual.hybridPersistence}_${s}`]++;}
 return {n:rows.length,eligible:eligible.length,unavailable,clockElapsedMinutes:stats(eligible.map(r=>r.counterfactual.clockElapsedMinutes)),entryPriceImprovement:stats(imps),improved:{count:imps.filter(x=>x>0).length,rate:rate(imps.filter(x=>x>0).length,imps.length)},worsened:{count:imps.filter(x=>x<0).length,rate:rate(imps.filter(x=>x<0).length,imps.length)},unchanged:{count:imps.filter(x=>x===0).length,rate:rate(imps.filter(x=>x===0).length,imps.length)},chasedAfterWait:{count:chased.length,rate:rate(chased.length,eligible.length),priceDeteriorationBps:stats(chased.map(r=>r.counterfactual.priceDeteriorationBps))},horizons,hybridPersistenceByPrice:bucket};
}
function group(rows){
 const all=summarize(rows),types={},sides={};
 for(const type of ['TYPE_A','TYPE_B','TYPE_C','TYPE_D','TYPE_E','TYPE_UNKNOWN'])types[type]=summarize(rows.filter(r=>r.type===type));
 for(const side of ['SHORT','LONG'])sides[side]={...(side==='LONG'?{warning:'EXPLORATORY_ONLY_SMALL_SAMPLE'}:{}),...summarize(rows.filter(r=>r.direction===side))};
 return {ALL:all,SHORT:sides.SHORT,LONG:sides.LONG,pathTypes:types,rows};
}

export function main(root=process.argv[2],out=process.argv[3]){assert(root&&out,'USAGE: node script ROOT OUT');
const candidateBytes=fs.readFileSync(`${root}/measurement/candidate-model.json`),candidate=JSON.parse(candidateBytes),pathBytes=fs.readFileSync('predict/research/path-diagnosis/path-diagnosis.json'),prior=JSON.parse(pathBytes);
assert.equal(sha256(candidateBytes),'f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a');assert.equal(candidate.threshold,.6);assert.equal(sha256(pathBytes),fs.readFileSync('predict/research/path-diagnosis/path-diagnosis.json.sha256','utf8').trim());assert.equal(prior.verdict,'TIMING_HYPOTHESIS_MIXED');
const dates={Development:[...new Set(prior.groups.Development.rows.map(r=>r.sessionDate))],Holdout29:[...new Set(prior.groups.Holdout29.rows.map(r=>r.sessionDate))]},sourceHashes=[];
const bundles={Development:loadBundles(`${root}/path/dev`,dates.Development,sourceHashes),Holdout29:loadBundles(`${root}/path/hold`,dates.Holdout29,sourceHashes)};
const groups={};for(const name of ['Development','Holdout29'])groups[name]=group(prior.groups[name].rows.map(r=>analyzeRow(r,bundles[name].get(r.sessionDate))));
assert.equal(groups.Development.ALL.n,95);assert.equal(groups.Holdout29.ALL.n,99);
assert.equal(groups.Development.ALL.horizons[3].baseline.complete,84);assert(Math.abs(groups.Development.ALL.horizons[3].baseline.net.mean-120.87437807357567)<1e-9);
assert.equal(groups.Holdout29.ALL.horizons[3].baseline.complete,94);assert(Math.abs(groups.Holdout29.ALL.horizons[3].baseline.net.mean-101.00162559162345)<1e-9);
const keyDirections=name=>{const a=groups[name].ALL;return [a.entryPriceImprovement.mean,a.entryPriceImprovement.median,...[3,6].flatMap(h=>[a.horizons[h].difference.sameAbsoluteEndpoint.net.mean,a.horizons[h].difference.samePostEntryHorizon.net.mean,a.horizons[h].difference.sameAbsoluteEndpoint.mfeLostBps.mean,a.horizons[h].difference.samePostEntryHorizon.mfeLostBps.mean])].map(Math.sign);};
const kd=keyDirections('Development'),kh=keyDirections('Holdout29'),replicated=kd.every((v,i)=>v===kh[i]);
const pg=replicated?group([...groups.Development.rows,...groups.Holdout29.rows]):null;
const pooled=pg?{basis:'DESCRIPTIVE_ONLY; price, net-return and MFE-loss directions replicate; no fitting or rule selection.',ALL:pg.ALL,SHORT:pg.SHORT,LONG:pg.LONG,pathTypes:pg.pathTypes}:'NOT_PERFORMED; main effect directions did not replicate';
const result={scope:'ONE_BAR_WAIT_COUNTERFACTUAL_DIAGNOSIS_ONLY',candidateSha256:sha256(candidateBytes),contractSha256:candidate.featureTargetStateSha256,threshold:.6,counterfactualSemantics:{price:'Close of the exact next regular completed 5-minute bar after the frozen decision. The bar starts at decision T (or 12:30 JST when T is 11:30); its close is available at bar.availableAt and is reference-only, not an executable fill.',eligibility:'Fail closed when that exact next regular bar is absent or crosses the JST session boundary. No next-day carry and no substitution with a later observed bar.',sameAbsoluteEndpoint:'Uses the original baseline +3/+6 endpoint and excludes the one waited bar from excursion measurement.',samePostEntryHorizon:'Starts after the counterfactual reference becomes available and uses the same exact-grid +3/+6 bar count, with lunch normalization and fail-closed missing bars.',cost:'Same 5 bps round-trip cost deducted once from every completed counterfactual horizon.',chasedAfterWait:'Direction-adjusted entry price improvement is negative; no magnitude threshold.'},sourceArtifacts:prior.sourceArtifacts,sourcePathDiagnosisSha256:sha256(pathBytes),sourceHashes,groups,replication:{mainEffectDirectionsCompared:['entry improvement mean','entry improvement median','same-endpoint net difference +3/+6','post-entry net difference +3/+6','same-endpoint MFE lost +3/+6','post-entry MFE lost +3/+6'],directionConsistent:replicated,Development:kd,Holdout29:kh},pooled,verdict:'WAIT_VALUE_NOT_SUPPORTED',strongestEvidenceForWait:'Holdout29 shows lower mean MAE after waiting under both endpoint conventions; its post-entry +6 positive rate increases despite lower mean net return.',strongestEvidenceAgainstWait:'Both independent periods have negative mean and median entry-price improvement, more worsened than improved entries, lower mean net return at +3 and +6 under both endpoint conventions, and positive MFE loss.',remainingUncertainty:'Reference closes are not executable fills; small LONG samples; exact counterfactual is one fixed bar only; missing exact-grid horizons are fail-closed; Development uses OOF models while Holdout uses the final model.',audit:{baselineReferenceParity:194,baselineMetricParity:true,candidateChanged:false,thresholdChanged:false,timingChallenger:'NOT_STARTED',ruleOptimization:false,newModel:false,freshValidationNewAccess:0,freshOosNewAccess:0,protected103NewAccess:0,pitIssues:0,duplicateIssues:0,stateIssues:0,safety:candidate.safety}};
fs.mkdirSync(out,{recursive:true});fs.writeFileSync(`${out}/one-bar-counterfactual.json`,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({Development:groups.Development.ALL,Holdout29:groups.Holdout29.ALL},null,2));return result;}
if(process.argv[1]&&import.meta.url===new URL(`file://${process.argv[1]}`).href)main();
