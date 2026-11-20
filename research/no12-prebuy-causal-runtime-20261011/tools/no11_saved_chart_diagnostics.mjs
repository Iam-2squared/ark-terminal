/** Diagnose bounded saved C50 captures without Excel, network or raw-value output. */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {mergeNo11PrivateChartSnapshots} from './no11_import_chart50_continuous_snapshot.mjs';
import {observeNo11RssCumulativeVa} from '../runtime/no11_rss_cumulative_va_observability.mjs';
const repo=fileURLToPath(new URL('../../../',import.meta.url));
const fail=code=>{throw Error('NO11_SAVED_DIAGNOSTIC_'+code)};
const sha=b=>createHash('sha256').update(b).digest('hex');
export function diagnoseCaptures(input){
 if(!Array.isArray(input)||input.length<2||input.length>10)fail('TWO_TO_TEN_FRAMES_REQUIRED');
 const captures=[...input].sort((a,b)=>String(a.observedEndJst).localeCompare(String(b.observedEndJst)));
 const first=captures[0],last=captures.at(-1);
 // Reuse the actual importer validations and Va policy. No relaxed freshness,
 // backdating, invented turnover, or mutation of first-observed chart rows.
 const {receipt}=mergeNo11PrivateChartSnapshots({sessionDate:first.sessionDate,
  decisionAtJst:last.observedEndJst,chartPlanSha256:first.chartPlanSha256,
  selectedSymbols:first.selectedSymbols,snapshots:captures});
 let previousCharts=null,previousMarkets=null;
 const frames=captures.map((c,i)=>{
  const charts=new Map(c.chartRows.map(r=>[r.Code+'|'+r.Time,JSON.stringify([r.O,r.H,r.L,r.C,r.Vo])]));
  const markets=new Map(),statuses={};
  for(const r of c.marketObservations){
   const s=observeNo11RssCumulativeVa({record:r,observedEndJst:c.marketObservedAtJst}).status;
   statuses[s]=(statuses[s]??0)+1;
   markets.set(r.symbol,JSON.stringify([r.marketDate,r.cumulativeVolumeRaw,r.cumulativeTurnoverRaw,r.vendorVolumeWeightedAverage]));
  }
  const times=c.chartRows.map(r=>r.Time).sort();
  const ages=c.chartRows.map(r=>(Date.parse(r.knownAtJst)-Date.parse(r.Date+'T'+r.Time+':00+09:00')-60000)/1000);
  const result={sample:i+1,marketReadAt:c.marketObservedAtJst,captureFinishedAt:c.observedEndJst,
   latestChartBarTime:times.at(-1)??null,chartRows:c.chartRows.length,
   minimumBarReceiptDelaySeconds:ages.length?Math.min(...ages):null,
   maximumBarReceiptDelaySeconds:ages.length?Math.max(...ages):null,
   addedBarKeys:previousCharts?[...charts.keys()].filter(k=>!previousCharts.has(k)).length:null,
   missingPriorBarKeys:previousCharts?[...previousCharts.keys()].filter(k=>!charts.has(k)).length:null,
   changedExistingBarRows:previousCharts?[...charts].filter(([k,v])=>previousCharts.has(k)&&previousCharts.get(k)!==v).length:null,
   changedMarketRows:previousMarkets?[...markets].filter(([k,v])=>previousMarkets.has(k)&&previousMarkets.get(k)!==v).length:null,
   cumulativeValidation:statuses};
  previousCharts=charts;previousMarkets=markets;return result;
 });
 return {schemaId:'ARK_NO11_SAVED_CHART_DIAGNOSTIC_V1',source:'SAVED_FILES_ONLY',
  sessionDate:first.sessionDate,frames,importedSnapshots:receipt.importedSnapshots,
  selectedSymbolsCount:receipt.selectedSymbolsCount,
  uniqueUnmodifiedClosedChartRows:receipt.uniqueUnmodifiedClosedChartRows,
  invalidatedRevisedChartRows:receipt.invalidatedRevisedChartRows,
  approximateMinuteVaRows:receipt.approximateMinuteVaRows,skippedBars:receipt.skippedBars,
  newBarKeysObserved:frames.slice(1).some(f=>f.addedBarKeys>0),
  marketValuesChanged:frames.slice(1).some(f=>f.changedMarketRows>0),
  status:receipt.approximateMinuteVaRows>0?'USABLE_PROXY_ROWS_OBSERVED_NOT_LIVE_CERTIFIED':'NO_USABLE_PROXY_ROWS',
  scopeComparedToOriginalPlan:false,rawPricesOrSymbolsIncluded:false,excelAccessed:false,
  shadowTested:false,recoveryTested:false,productionReady:false,orderTransmission:false};
}
function privatePath(value){
 if(typeof value!=='string'||!path.isAbsolute(value))fail('ABSOLUTE_PRIVATE_PATH_REQUIRED');
 const full=path.resolve(value),root=path.resolve(repo);
 if(full===root||full.startsWith(root+path.sep))fail('PATH_IN_REPOSITORY');
 let cursor=full;
 for(;;){
  if(fs.existsSync(cursor)&&fs.lstatSync(cursor).isSymbolicLink())fail('SYMLINK');
  const parent=path.dirname(cursor);if(parent===cursor)break;cursor=parent;
 }
 return full;
}
export function diagnoseFolder(folder){
 const full=privatePath(folder);
 if(!fs.lstatSync(full).isDirectory())fail('DIRECTORY_REQUIRED');
 const names=fs.readdirSync(full).filter(n=>n.startsWith('snapshot-'));
 if(names.length<2||names.length>10)fail('TWO_TO_TEN_FRAMES_REQUIRED');
 let total=0;
 const frames=names.map(name=>{
  const match=/^snapshot-([a-f0-9]{64})\.json$/.exec(name);if(!match)fail('NAME');
  const file=path.join(full,name),stat=fs.lstatSync(file);total+=stat.size;
  if(!stat.isFile()||stat.isSymbolicLink()||stat.size<=0||stat.size>20000000||total>60000000)fail('FILE_LIMIT');
  const bytes=fs.readFileSync(file);if(sha(bytes)!==match[1])fail('HASH');
  return JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));
 });
 return {...diagnoseCaptures(frames),snapshotHashesVerified:true};
}
export function main(args){
 if(!([2,4].includes(args.length))||args[0]!=='--folder'||(args.length===4&&args[2]!=='--output'))fail('ARGUMENTS');
 const report=diagnoseFolder(args[1]);
 const text=JSON.stringify(report,null,2)+'\n';
 if(args.length===4)fs.writeFileSync(privatePath(args[3]),text,{flag:'wx',encoding:'utf8'});
 console.log(text.trimEnd());return report;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{main(process.argv.slice(2));}catch(e){
  console.error(/^(NO11_[A-Z0-9_]+)$/.test(e.message)?e.message:'NO11_SAVED_DIAGNOSTIC_INPUT_FAILURE');process.exitCode=2;
 }
}
