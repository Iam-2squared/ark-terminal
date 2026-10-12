import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadFormalL0PartitionFromCache} from '../predict/long-only/phase57-long-only-l0-cache.js';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {buildFixedHorizonTargets} from '../predict/long-only/phase57-long-only-l2-fixed-horizon.js';
import {projectL2Features,scoreL2Candidate} from '../predict/long-only/phase57-long-only-l2-selector-v1.js';
import {normalizeMinuteProvenance,measureCorrectedRow} from '../predict/long-only/phase57-long-only-corrected-measurement.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
for(const name of ['--cache-root','--freeze-report','--output-dir','--unavailable-sessions'])if(!arg(name))throw new Error(`required ${name}`);
const cacheRoot=path.resolve(arg('--cache-root')),outputDir=path.resolve(arg('--output-dir'));
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const sha=value=>createHash('sha256').update(value).digest('hex');
const plan=read(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url));
const allocation=read(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url));
const l1=read(new URL('../predict/long-only/phase57-long-only-l1-discovery-sessions.json',import.meta.url));
const l2=read(new URL('../predict/long-only/phase57-long-only-l2-development-sessions.json',import.meta.url));
const v2=read(new URL('../predict/long-only/phase57-long-only-v2-development-sessions.json',import.meta.url));
const freezeReport=read(path.resolve(arg('--freeze-report'))),artifact=freezeReport.freeze.finalArtifact;
const allowedMissing=new Set(read(path.resolve(arg('--unavailable-sessions'))));
const features=freezeReport.freeze.selectedFeatureNames;
if(artifact.artifactSha256!=='994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb'||artifact.candidateId!=='RIDGE_Y30'||JSON.stringify(features)!==JSON.stringify(artifact.heads[0].featureNames)||features.length!==15)throw new Error('saved C+D v1 identity mismatch');
const groups=[{name:'L1',sessions:l1.sessions,manifest:'l1-minute-manifest.json',sessionHash:l1.sessionListSha256},
  {name:'V2',sessions:v2.sessions,manifest:'v2-minute-manifest.json',sessionHash:v2.sessionListSha256},
  {name:'C',sessions:allocation.partitions.DEVELOPMENT_C,manifest:'l2-minute-manifest.json',sessionHash:l2.sessionListSha256},
  {name:'D',sessions:allocation.partitions.DEVELOPMENT_D,manifest:'l2-minute-manifest.json',sessionHash:l2.sessionListSha256}];
if(sha(JSON.stringify(l1.sessions))!==l1.sessionListSha256||sha(JSON.stringify(v2.sessions))!==v2.sessionListSha256||sha(JSON.stringify(l2.sessions))!==l2.sessionListSha256)throw new Error('session contract hash mismatch');
const allowlist=groups.flatMap(g=>g.sessions);
if(allowlist.length!==80||new Set(allowlist).size!==80||[...allowedMissing].some(x=>!l1.sessions.includes(x)))throw new Error('session scope mismatch');
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');
const columns=[...new Set(['sessionDate','symbol','decisionTimeJst','partition','sourceGroup','segment','liquidityBucket','currentReturnPct','decisionVolatilityPct',
  'decisionPrice','decisionPriceValid','decisionPriceKind','referenceAgeMin','legacyReferencePrice','legacyReferenceAgeMin',
  'corrected30ReturnBps','corrected30EndpointMinute','corrected30EndpointAgeMin','corrected30EndpointKind','corrected30Evaluable',
  'mfe30Pct','mae30Pct','sessionMfePct','sessionMaePct','futureBarCount','futureAuctionCount',
  'highOpportunity2','highOpportunity3','highOpportunity5','closeOpportunity2','closeOpportunity3','closeOpportunity5',
  'auctionCloseOpportunity2','auctionCloseOpportunity3','auctionCloseOpportunity5',
  'timeToHigh2Min','timeToHigh3Min','timeToHigh5Min','timeToClose2Min','timeToClose3Min','timeToClose5Min',
  'firstCloseHitKind2','firstCloseHitKind3','firstCloseHitKind5','legacySixObservationReturnBps','legacySixObservationElapsedMin',
  'finalAdditionalPct','finalPreviousReturnPct','finalPrevious5','savedV1Score',...features])];
const key=r=>`${r.sessionDate}|${r.symbol}|${r.decisionTimeJst}`;
const symkey=r=>`${r.sessionDate}|${r.symbol}`;
const cell=v=>v===null||v===undefined||typeof v==='number'&&!Number.isFinite(v)?'':String(v).replaceAll('\t',' ');
const bySymbol=rows=>{const m=new Map();for(const r of rows){const k=symkey(r);if(!m.has(k))m.set(k,[]);m.get(k).push(r);}return m;};
const codeOf=r=>String(r?.Code??r?.code??r?.symbol??'').trim().toUpperCase();
const sectorOf=r=>String(r?.S17??r?.Sec17??r?.Sector17Code??r?.Sector33Code??r?.S33??r?.sectorCode??'UNKNOWN');
fs.mkdirSync(outputDir,{recursive:true,mode:0o700});
const l0s=new Map(),sessionAudits=[],files=[];
for(const group of groups){
  const filename=`${group.name}.tsv`,fd=fs.openSync(path.join(outputDir,filename),'wx',0o600);
  fs.writeSync(fd,columns.join('\t')+'\n');let rowCount=0;
  try{
    for(const sessionDate of group.sessions){
      const partition=Object.entries(allocation.partitions).find(([,dates])=>dates.includes(sessionDate))?.[0];
      if(!['DEVELOPMENT_A','DEVELOPMENT_B','DEVELOPMENT_C','DEVELOPMENT_D'].includes(partition))throw new Error(`sealed/non-development date rejected: ${sessionDate}`);
      const dir=path.join(base,sessionDate),manifestPath=path.join(dir,group.manifest);
      if(!fs.existsSync(manifestPath)){
        if(!allowedMissing.has(sessionDate))throw new Error(`unexpected missing Minute: ${sessionDate}`);
        sessionAudits.push({sessionDate,partition,sourceGroup:group.name,status:'SOURCE_UNAVAILABLE_NO_FETCH'});continue;
      }
      const manifest=read(manifestPath),pages=read(path.join(dir,'minute-pages.json'));
      if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.sessionListSha256!==group.sessionHash||pages.length!==manifest.pageCount||pages.some(p=>sha(p.responseText)!==p.responseSha256))throw new Error(`Minute identity/hash mismatch: ${sessionDate}`);
      const aggregateSha=sha(JSON.stringify(pages.map(p=>p.responseSha256)));
      if(manifest.aggregateSha256&&aggregateSha!==manifest.aggregateSha256)throw new Error(`Minute aggregate hash mismatch: ${sessionDate}`);
      const raw=pages.flatMap(p=>JSON.parse(p.responseText).data??[]);
      if(raw.length!==manifest.rowCount)throw new Error(`Minute row count mismatch: ${sessionDate}`);
      if(!l0s.has(partition))l0s.set(partition,loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation}));
      const dailyRows=l0s.get(partition).rows.filter(r=>r.sessionDate===sessionDate);
      const intraday=normalizeAndAggregateMinuteRows(raw),provenance=normalizeMinuteProvenance(raw),barsMap=bySymbol(intraday.bars),auctionMap=bySymbol(intraday.terminalAuctions),dailyMap=new Map(dailyRows.map(r=>[symkey(r),r]));
      const masterPages=read(path.join(dir,'master-pages.json')),sectorBySymbol={};
      for(const p of masterPages){if(sha(p.responseText)!==p.responseSha256)throw new Error('master hash mismatch');for(const r of JSON.parse(p.responseText).data??[]){const s=codeOf(r);if(s)sectorBySymbol[`${sessionDate}|${s}`]=sectorOf(r);}}
      const built=buildL1CrossSectionDataset({partition,dailyRows,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,sectorBySymbol});
      const targets=buildFixedHorizonTargets({featureRows:built.featureRows,bars5m:intraday.bars,evaluatorOnlyLabels:built.evaluatorOnlyLabels});
      const targetMap=new Map(targets.map(r=>[key(r),r])),labelMap=new Map(built.evaluatorOnlyLabels.map(r=>[key(r),r]));
      const rows=[];let corrected30Evaluable=0,freshDecisionPrice=0,causalChecks=0;
      for(const feature of built.featureRows){
        if(feature.latestAvailableAtJst>feature.decisionAtJst)throw new Error('future feature provenance');
        const projected=projectL2Features(feature),target=targetMap.get(key(feature)),label=labelMap.get(key(feature));
        const semantics=measureCorrectedRow({feature,target,label,bars:barsMap.get(symkey(feature))??[],minutes:provenance.get(symkey(feature))??[],terminalAuctions:auctionMap.get(symkey(feature))??[],daily:dailyMap.get(symkey(feature))});
        const row={...projected,sessionDate,symbol:feature.symbol,decisionTimeJst:feature.decisionTimeJst,partition,sourceGroup:group.name,segment:feature.segment,liquidityBucket:feature.liquidityBucket,
          decisionVolatilityPct:feature.decisionVolatilityPct,...semantics,savedV1Score:scoreL2Candidate(feature,artifact)};
        if(semantics.referenceAgeMin<0)throw new Error('future decision reference');
        rows.push(columns.map(c=>cell(row[c])).join('\t'));corrected30Evaluable+=semantics.corrected30Evaluable;freshDecisionPrice+=semantics.decisionPriceValid;causalChecks++;
      }
      fs.writeSync(fd,rows.join('\n')+'\n');rowCount+=rows.length;
      sessionAudits.push({sessionDate,partition,sourceGroup:group.name,status:'CORRECTED_INPUT_PREPARED',rawRows:raw.length,pageCount:pages.length,minuteAggregateSha256:aggregateSha,rows:rows.length,freshDecisionPrice,corrected30Evaluable,causalChecks,...built.audit});
      console.log(JSON.stringify({status:'CORRECTED_SAVED_SESSION_PREPARED',sourceGroup:group.name,sessionDate,rows:rows.length,freshDecisionPrice,corrected30Evaluable}));
    }
  }finally{fs.closeSync(fd);}
  files.push({path:filename,sourceGroup:group.name,rows:rowCount,sha256:sha(fs.readFileSync(path.join(outputDir,filename)))});
}
const manifest={schemaVersion:1,contractId:'CORRECTED-MEASUREMENT-1',contractCommit:'20356553ddece7309a6a00654c3b1e276d1a3466',sourceHead:'962b96fd74964081d23dcdfc37d87fc00a98200f',files,columns,featureUniverse:features,sessionAudits,
  model:{name:'CORRECTED_MEASUREMENT_RIDGE_SAVED_CD',artifactSha256:artifact.artifactSha256,fitPartitions:['DEVELOPMENT_C','DEVELOPMENT_D'],trainingRows:artifact.heads[0].trainingRows,historicalCOnly:'UNAVAILABLE_NO_SAVED_WEIGHTS_OR_SCORES',v2:'OUT_OF_SCOPE_NO_RETEST',notOriginal117bpsBenchmark:true},
  providerRequestsThisRun:0,fitCalls:0,validationOpened:false,oosOpened:false,targetChanged:false,modelChanged:false,policyChanged:false,featureUniverseChanged:false,liveEnabled:false,shortEnabled:false,marginEnabled:false,leverageEnabled:false};
fs.writeFileSync(path.join(outputDir,'dataset-manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx',mode:0o600});
console.log(JSON.stringify({status:'CORRECTED_PRIVATE_INPUT_READY',sessions:sessionAudits.filter(x=>x.status==='CORRECTED_INPUT_PREPARED').length,rows:files.reduce((a,x)=>a+x.rows,0),fitCalls:0,providerRequests:0}));
