import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadFormalL0PartitionFromCache} from '../predict/long-only/phase57-long-only-l0-cache.js';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {buildFixedHorizonTargets} from '../predict/long-only/phase57-long-only-l2-fixed-horizon.js';
import {projectL2Features} from '../predict/long-only/phase57-long-only-l2-selector-v1.js';
import {assertV2PreFitContract,V2_COMPARISON_CONTRACT,V2_DEVELOPMENT} from '../predict/long-only/phase57-long-only-v2-contract.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const cacheRoot=path.resolve(arg('--cache-root')??''),outputDir=path.resolve(arg('--output-dir')??'');
if(!cacheRoot||!outputDir)throw new Error('usage: --cache-root <private cache> --output-dir <private datasets>');
const read=url=>JSON.parse(fs.readFileSync(url,'utf8'));
const plan=read(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url));
const allocation=read(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url));
const l1=read(new URL('../predict/long-only/phase57-long-only-l1-discovery-sessions.json',import.meta.url));
const l2=read(new URL('../predict/long-only/phase57-long-only-l2-development-sessions.json',import.meta.url));
assertV2PreFitContract({allocation,l1Contract:l1,l2Contract:l2});
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2'),sha=value=>createHash('sha256').update(value).digest('hex');
const key=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.S17??row?.Sec17??row?.Sector17Code??row?.Sector33Code??row?.S33??row?.sectorCode??'UNKNOWN');
const columns=['sessionDate','symbol','decisionTimeJst','segment','liquidityBucket','gapBucket','winner','y30Bps','futureMfe30Pct','futureMae30Pct',...V2_COMPARISON_CONTRACT.featureUniverse,'momentum5Pct','momentumAccelerationPct','pullbackDepthPct','decisionVolatilityPct','cumulativeVolume','vwapReclaim5m','gapPct'];
const cell=value=>value===true?'1':value===false?'0':value===null||value===undefined?'':String(value).replaceAll('\t',' ');

fs.mkdirSync(outputDir,{recursive:true});
function writeDataset({name,sessions,manifestName}){
  const output=path.join(outputDir,`${name}.tsv`),fd=fs.openSync(output,'wx',0o600);fs.writeSync(fd,`${columns.join('\t')}\n`);
  const l0ByPartition=new Map(),sessionAudits=[];let rowCount=0;
  for(const sessionDate of sessions){
    const partition=Object.entries(allocation.partitions).find(([,dates])=>dates.includes(sessionDate))?.[0];
    if(!['DEVELOPMENT_A','DEVELOPMENT_B','DEVELOPMENT_C','DEVELOPMENT_D'].includes(partition))throw new Error(`non-Development session rejected: ${sessionDate}`);
    if(!l0ByPartition.has(partition))l0ByPartition.set(partition,loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation}));
    const sessionDir=path.join(base,sessionDate),manifest=JSON.parse(fs.readFileSync(path.join(sessionDir,manifestName),'utf8')),pages=JSON.parse(fs.readFileSync(path.join(sessionDir,'minute-pages.json'),'utf8'));
    const expectedSha=manifestName==='v2-minute-manifest.json'?V2_DEVELOPMENT.sessionListSha256:l2.sessionListSha256;
    if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.sessionListSha256!==expectedSha||pages.length!==manifest.pageCount||pages.some(page=>sha(page.responseText)!==page.responseSha256))throw new Error(`immutable Minute verification failed: ${sessionDate}`);
    const minuteRows=pages.flatMap(page=>JSON.parse(page.responseText).data??[]),intraday=normalizeAndAggregateMinuteRows(minuteRows),sectorBySymbol={};
    const masterPages=JSON.parse(fs.readFileSync(path.join(sessionDir,'master-pages.json'),'utf8'));
    for(const row of masterPages.flatMap(page=>JSON.parse(page.responseText).data??[])){const symbol=codeOf(row);if(symbol)sectorBySymbol[`${sessionDate}|${symbol}`]=sectorOf(row);}
    const dailyRows=l0ByPartition.get(partition).rows.filter(row=>row.sessionDate===sessionDate),crossSection=buildL1CrossSectionDataset({partition,dailyRows,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,sectorBySymbol});
    const targets=buildFixedHorizonTargets({featureRows:crossSection.featureRows,bars5m:intraday.bars,evaluatorOnlyLabels:crossSection.evaluatorOnlyLabels}),targetMap=new Map(targets.map(row=>[key(row),row]));
    let sessionRows=0;const lines=[];
    for(const feature of crossSection.featureRows){const target=targetMap.get(key(feature));if(!Number.isFinite(target?.y30Bps))continue;const projected=projectL2Features(feature),row={sessionDate:feature.sessionDate,symbol:feature.symbol,decisionTimeJst:feature.decisionTimeJst,segment:feature.segment,liquidityBucket:feature.liquidityBucket,gapBucket:feature.gapBucket,winner:target.winner,y30Bps:target.y30Bps,futureMfe30Pct:target.futureMfe30Pct,futureMae30Pct:target.futureMae30Pct,...projected,momentum5Pct:feature.momentum5Pct,momentumAccelerationPct:feature.momentumAccelerationPct,pullbackDepthPct:feature.pullbackDepthPct,decisionVolatilityPct:feature.decisionVolatilityPct,cumulativeVolume:feature.cumulativeVolume,vwapReclaim5m:feature.vwapReclaim5m,gapPct:feature.gapPct};lines.push(columns.map(column=>cell(row[column])).join('\t'));sessionRows++;rowCount++;}
    fs.writeSync(fd,`${lines.join('\n')}\n`);
    sessionAudits.push({sessionDate,partition,pageCount:manifest.pageCount,rawRows:minuteRows.length,targetRows:sessionRows});
    console.log(JSON.stringify({status:'V2_DATASET_SESSION_PREPARED',name,sessionDate,rows:sessionRows}));
  }
  fs.closeSync(fd);return {name,path:output,rowCount,sessions,sessionAudits};
}

const datasets=[
  writeDataset({name:'v2_fit',sessions:V2_DEVELOPMENT.sessions.slice(0,10),manifestName:'v2-minute-manifest.json'}),
  writeDataset({name:'v2_select',sessions:V2_DEVELOPMENT.sessions.slice(10),manifestName:'v2-minute-manifest.json'}),
  writeDataset({name:'development_c',sessions:allocation.partitions.DEVELOPMENT_C,manifestName:'l2-minute-manifest.json'}),
  writeDataset({name:'development_d',sessions:allocation.partitions.DEVELOPMENT_D,manifestName:'l2-minute-manifest.json'}),
];
const manifest={schemaVersion:1,status:'V2_PRIVATE_DATASETS_PREPARED',sessionListSha256:V2_DEVELOPMENT.sessionListSha256,comparisonContractId:V2_COMPARISON_CONTRACT.contractId,columns,datasets,validationOpened:false,oosOpened:false};
fs.writeFileSync(path.join(outputDir,'dataset-manifest.json'),`${JSON.stringify(manifest,null,2)}\n`,{flag:'wx',mode:0o600});
