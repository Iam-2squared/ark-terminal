/** Incremental RSS snapshots -> unchanged Frozen Selector schedule, READ ONLY.
 * Checkpoints are private; never re-create a missed decision from later data.
 * Holds the observed chart universe fixed for the session and pins its Watches.
 * No broker, orders, Excel writes or fitting. CLI time is the real local clock.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {mergeNo11PrivateChartSnapshots,CAPTURE_SCHEMA}
  from './no11_import_chart50_continuous_snapshot.mjs';
import {runOriginalFrozenSelectorShadow,inspectFrozenSelectorAsset}
  from '../runtime/no11_frozen_selector_native_shadow.mjs';
import {validateNo11Chart50Plan}
  from '../runtime/no11_rss_chart_50_prescreen.mjs';
import {isJpxCashTradingDay,previousJpxCashTradingDays}
  from '../runtime/jpx_cash_calendar_2026_2027.mjs';
import {OBSERVED_PASS_GATE_ID} from '../runtime/no11_observed_pass_watch_gate.mjs';
import {RSS_VA_PROXY_RECEIPT} from '../runtime/no11_rss_vendor_va_shadow_adapter.mjs';
export const CHECKPOINT='ARK_NO11_RECEIVED_PIPELINE_CHECKPOINT_V1';
export const MASTER='ARK_NO11_DATED_MASTER_RECEIPT_V1';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const JST=/^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?\+09:00$/;
const FILE=/^snapshot-([a-f0-9]{64})\.json$/;
const sha=x=>createHash('sha256').update(typeof x==='string'||Buffer.isBuffer(x)?x:JSON.stringify(x)).digest('hex');
const fail=x=>{throw Error('NO11_PIPELINE_'+x)};
const need=(x,c)=>{if(!x)fail(c)};
const at=x=>typeof x==='string'&&JST.test(x)?Date.parse(x):NaN;
const key=r=>r.Code+'|'+r.Time;
const copy=x=>structuredClone(x);
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export const nowJst=()=>new Date(Date.now()+9*3600_000).toISOString().replace('Z','+09:00');
function safePath(filename,folder=false){
  need(typeof filename==='string'&&path.isAbsolute(filename),'ABSOLUTE_PRIVATE_PATH_REQUIRED');
  const full=path.resolve(filename);
  need(full!==ROOT&&!full.startsWith(ROOT+path.sep),'PRIVATE_PATH_INSIDE_REPO');
  let p=full;
  while(true){
    if(fs.existsSync(p))need(!fs.lstatSync(p).isSymbolicLink(),'PRIVATE_PATH_SYMLINK');
    const parent=path.dirname(p);if(parent===p)break;p=parent;
  }
  const s=fs.statSync(full);
  need(folder?s.isDirectory():s.isFile(),'PRIVATE_PATH_TYPE');
  return full;
}
export function readPrivate(filename,limit=35_000_000){
  const full=safePath(filename),s=fs.statSync(full);
  need(s.size>0&&s.size<=limit,'PRIVATE_FILE_SIZE');
  return JSON.parse(fs.readFileSync(full,'utf8').replace(/^\uFEFF/,''));
}
export function validatePipelineInputs({sessionDate,chartPlan,mask,master,throughJst}){
  need(isJpxCashTradingDay(sessionDate)&&Number.isFinite(at(throughJst))&&
    throughJst.slice(0,10)===sessionDate,'SESSION_OR_CLOCK_INVALID');
  need(mask?.schemaId===OBSERVED_PASS_GATE_ID&&mask.shadowOnly===true&&
    mask.productionReady===false&&mask.orderTransmission===false&&
    mask.strictNoUnknownFallback===true&&
    mask.asOfSession===previousJpxCashTradingDays(sessionDate,1)[0],
    'PREVIOUS_DAY_MASK_INVALID');
  const selected=validateNo11Chart50Plan({chartPlan,mask,sessionDate});
  need(master?.schemaId===MASTER&&master.sessionDate===sessionDate&&
    master.productionReady===false&&master.orderTransmission===false&&
    Number.isFinite(at(master.knownAtJst))&&master.knownAtJst.slice(0,10)===sessionDate&&
    at(master.knownAtJst)<=at(throughJst)&&Array.isArray(master.rows),'DATED_MASTER_NOT_KNOWN');
  const by=new Map();
  for(const r of master.rows){
    need(r&&typeof r.symbol==='string'&&!by.has(r.symbol),'DATED_MASTER_DUPLICATE');
    by.set(r.symbol,r);
  }
  for(const code of selected){
    const r=by.get(code);
    need(r&&r.asOfSession===sessionDate&&['PRIME','STANDARD','GROWTH'].includes(r.segment)&&
      typeof r.sector==='string'&&r.sector.length>0&&Number.isFinite(r.rawPreviousClose)&&
      r.rawPreviousClose>0&&r.corporateActionsCleared===true&&r.priceBasisVerified===true&&
      r.commonEquity===true,'DATED_MASTER_INCOMPLETE');
  }
  return {selected,inputPin:sha({sessionDate,chartPlan,mask,master})};
}
function seal(body){return {...body,checkpointSha256:sha(body)}}
export function restoreCheckpoint(previous,inputPin,sessionDate){
  if(previous===null)return null;
  const {checkpointSha256,...body}=previous;
  need(checkpointSha256===sha(body)&&body.schemaId===CHECKPOINT&&
    body.sessionDate===sessionDate&&body.inputPin===inputPin&&
    body.productionReady===false&&body.orderTransmission===false&&
    Array.isArray(body.rows)&&Array.isArray(body.envelopes)&&
    Array.isArray(body.snapshotIds)&&body.snapshotIds.length<=650&&
    Array.isArray(body.watches)&&Array.isArray(body.slots),'CHECKPOINT_CHANGED_OR_WRONG_INPUT');
  return copy(body);
}
export function pinCollectedWatches(plan,watches,mask){
  const names=watches.map(w=>w.symbol);
  need(names.every(s=>plan.selectorInputSymbols.includes(s)),'WATCH_OUTSIDE_COLLECTED_UNIVERSE');
  const {planSha256,...body}=copy(plan);
  body.activeWatchSymbols=[...new Set([...body.activeWatchSymbols,...names])];
  body.protectedChartSymbols=[...new Set([...body.protectedChartSymbols,...names])];
  body.scanChartSymbols=body.scanChartSymbols.filter(s=>!body.protectedChartSymbols.includes(s));
  const pinned={...body,planSha256:sha(body)};
  validateNo11Chart50Plan({chartPlan:pinned,mask,sessionDate:plan.sessionDate});
  return pinned;
}
function makeFeed(state,selected,through){
  const rows=state.rows;
  const proxy={schemaId:RSS_VA_PROXY_RECEIPT,
    inputKind:'RSS_MARKET_OBSERVED_60S_CUMULATIVE_DELTA_PROXY',
    sessionDate:state.sessionDate,decisionAtJst:through,selectedSymbols:[...selected],
    selectedSymbolCount:selected.length,validOneMinuteProxyRows:rows.length,
    availableSymbols:[...new Set(rows.map(r=>r.Code))],
    marketObservedAtPCOnly:true,exchangeMinuteBoundaryExact:false,
    marketTurnoverFieldTimestampCertified:false,nativeExactMinuteVaCertified:false,
    modelInputDistributionChanged:true,historicalOriginalVaParityNotRequired:true,
    hasAnyUsableRows:rows.length>0,readOnly:true,shadowOnly:true,
    productionReady:false,orderTransmission:false,derivedMinuteRowsSha256:sha(rows)};
  return {receipt:{schemaId:'ARK_NO11_RSS_CHART50_OFFLINE_JOIN_V1',
    sessionDate:state.sessionDate,decisionAtJst:through,chartPlanSha256:state.capturePlanSha256,
    importedSnapshots:state.snapshotIds.length,approximateMinuteVaRows:rows.length,
    selectedSymbolsCount:selected.length,sourceSnapshotsSha256:sha(state.snapshotIds),
    nativeSelectorExecuted:state.envelopes.length>0,readOnly:true,shadowOnly:true,
    productionReady:false,orderTransmission:false,proxyReceipt:proxy},rows:copy(rows)};
}
export function advanceReceivedPipeline({sessionDate,chartPlan,mask,master,
  previous=null,incoming=[],throughJst,completionClock=()=>throughJst}){
  const {selected,inputPin}=validatePipelineInputs({sessionDate,chartPlan,mask,master,throughJst});
  const asset=inspectFrozenSelectorAsset();
  const state=restoreCheckpoint(previous,inputPin,sessionDate)??{
    schemaId:CHECKPOINT,sessionDate,inputPin,capturePlanSha256:chartPlan.planSha256,
    startedAtJst:throughJst,lastTickAtJst:throughJst,snapshotIds:[],lastSnapshot:null,
    rows:[],envelopes:[],watches:[],slots:[],productionReady:false,orderTransmission:false};
  need(at(throughJst)>=at(state.lastTickAtJst),'PROCESS_CLOCK_REVERSED');
  const rowMap=new Map(state.rows.map(r=>[key(r),r]));
  const lastByCode=new Map();
  for(const r of state.rows)lastByCode.set(r.Code,r.Time);
  const newSnapshots=[...incoming].sort((a,b)=>at(a.payload.observedEndJst)-at(b.payload.observedEndJst));
  for(const item of newSnapshots){
    need(item&&/^[a-f0-9]{64}$/.test(item.sha256)&&!state.snapshotIds.includes(item.sha256),
      'CAPTURE_ID_DUPLICATE_OR_INVALID');
    const c=item.payload;
    need(c?.schemaId===CAPTURE_SCHEMA&&c.sessionDate===sessionDate&&
      c.chartPlanSha256===chartPlan.planSha256&&same(c.selectedSymbols,selected)&&
      c.source==='RssChart_1M_AND_RssMarket_CUMULATIVE_READONLY'&&
      c.shadowOnly===true&&c.productionReady===false&&c.orderTransmission===false&&
      Number.isFinite(at(c.observedEndJst))&&at(c.observedEndJst)<=at(throughJst)&&
      Number.isFinite(at(c.marketObservedAtJst))&&at(c.marketObservedAtJst)<=at(c.observedEndJst)&&
      c.observedEndJst.slice(0,10)===sessionDate&&
      Array.isArray(c.chartRows)&&Array.isArray(c.marketObservations)&&
      c.marketObservations.length===selected.length,'CAPTURE_HEADER_OR_CLOCK_INVALID');
    if(state.lastSnapshot)need(at(c.observedEndJst)>at(state.lastSnapshot.observedEndJst),
      'LATE_CAPTURE_INSERTION');
    for(const r of c.chartRows){
      const old=rowMap.get(key(r));
      if(old)need(['O','H','L','C','Vo'].every(k=>old[k]===r[k]),'USED_CLOSED_BAR_REVISED');
    }
    if(state.lastSnapshot){
      const joined=mergeNo11PrivateChartSnapshots({sessionDate,decisionAtJst:throughJst,
        chartPlanSha256:chartPlan.planSha256,selectedSymbols:selected,
        snapshots:[state.lastSnapshot,c]});
      for(const row of joined.rows){
        const old=rowMap.get(key(row));
        if(old){need(same(old,row),'USED_PROXY_BAR_REVISED');continue;}
        need(!lastByCode.has(row.Code)||row.Time>lastByCode.get(row.Code),'LATE_PROXY_BAR_INSERTION');
        rowMap.set(key(row),copy(row));lastByCode.set(row.Code,row.Time);
      }
    }
    state.snapshotIds.push(item.sha256);state.lastSnapshot=copy(c);
  }
  need(state.snapshotIds.length<=650,'CAPTURE_LIMIT');
  state.rows=[...rowMap.values()].sort((a,b)=>a.Code.localeCompare(b.Code)||a.Time.localeCompare(b.Time));
  const feed=makeFeed(state,selected,throughJst);
  const done=new Set(state.slots.map(x=>x.time));
  for(const time of asset.spec.ranking.decisionTimesJst){
    if(done.has(time))continue;
    const cutoff=sessionDate+'T'+time+':00+09:00';
    const delay=at(throughJst)-at(cutoff);
    if(delay<0)continue;
    if(delay>90_000){state.slots.push({time,status:'MISSED_NOT_BACKFILLED'});continue;}
    if(!state.lastSnapshot||at(state.lastSnapshot.observedEndJst)<at(cutoff)||
      at(throughJst)-at(state.lastSnapshot.observedEndJst)>90_000||!state.rows.length)continue;
    const cutMinute=Number(time.slice(0,2))*60+Number(time.slice(3));
    const rows=state.rows.filter(r=>Number(r.Time.slice(0,2))*60+Number(r.Time.slice(3))+1<=cutMinute);
    if(!rows.length)continue;
    const receipt={...feed.receipt.proxyReceipt,validOneMinuteProxyRows:rows.length,
      hasAnyUsableRows:true,derivedMinuteRowsSha256:sha(rows)};
    const pinned=pinCollectedWatches(chartPlan,state.watches,mask);
    const result=runOriginalFrozenSelectorShadow({sessionDate,decisionTimeJst:time,
      evaluatedAtJst:throughJst,mask,chartPlan:pinned,datedMaster:master.rows,
      sourceReceipt:receipt,nativeMinuteRows:rows,previousWatches:state.watches});
    const finished=completionClock();
    need(Number.isFinite(at(finished))&&at(finished)>=at(throughJst)&&
      finished.slice(0,10)===sessionDate,'COMPLETION_CLOCK_INVALID');
    if(at(finished)-at(cutoff)>90_000){
      state.slots.push({time,status:'MISSED_PROCESSING_DEADLINE'});continue;
    }
    // This is when this process produced/received the result, NOT the bar cutoff.
    state.envelopes.push({kind:'selector',receivedAtJst:finished,payload:result});
    state.watches=copy(result.nextWatches);
    state.slots.push({time,status:result.selected.length?'EXECUTED':'EXECUTED_EMPTY',
      completedAtJst:finished,selected:result.selected.length});
  }
  state.lastTickAtJst=completionClock();
  need(at(state.lastTickAtJst)>=at(throughJst),'FINAL_CLOCK_REVERSED');
  return {state:seal(state),feed,selectorEnvelopes:copy(state.envelopes),
    summary:{schemaId:'ARK_NO11_RECEIVED_PIPELINE_TICK_V1',sessionDate,
      snapshots:state.snapshotIds.length,minuteRows:state.rows.length,watches:state.watches.length,
      executedSlots:state.slots.filter(s=>s.status.startsWith('EXECUTED')).length,
      missedSlots:state.slots.filter(s=>s.status.startsWith('MISSED')).length,
      lastSourceAtJst:state.lastSnapshot?.observedEndJst??null,
      completedAtJst:state.lastTickAtJst,productionReady:false,orderTransmission:false}};
}
export function runPipelineTick(args){
  need(args.length===2&&args[0]==='--request','USAGE_REQUEST');
  const req=readPrivate(args[1],1_000_000);
  need(req.schemaId==='ARK_NO11_RECEIVED_PIPELINE_REQUEST_V1'&&
    req.productionReady===false&&req.orderTransmission===false,'REQUEST_INVALID');
  const chart=readPrivate(req.plan,250_000);
  const mask=readPrivate(req.mask,250_000),master=readPrivate(req.master,1_000_000);
  need(chart.schemaId==='ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1','PLAN_EXPORT_INVALID');
  const previous=req.checkpoint?readPrivate(req.checkpoint,35_000_000).state:null;
  const known=new Set(previous?.snapshotIds??[]);
  const folder=safePath(req.captureFolder,true),incoming=[];
  const names=fs.readdirSync(folder).filter(n=>n.startsWith('snapshot-'));
  need(names.length<=650,'CAPTURE_LIMIT');
  const found=new Set();
  for(const name of names){
    const m=FILE.exec(name);need(m,'CAPTURE_FILENAME_INVALID');found.add(m[1]);
    const file=path.join(folder,name);safePath(file);
    // Already accepted bytes live in a sealed checkpoint. Verify old originals
    // once again on process startup, but don't rescan historical files per tick.
    if(known.has(m[1])&&req.verifyHistory!==true)continue;
    const size=fs.statSync(file).size;need(size<=20_000_000,'CAPTURE_FILE_SIZE');
    const b=fs.readFileSync(file);
    if(sha(b)!==m[1]){
      const age=Date.now()-fs.statSync(file).mtimeMs;
      need(age>=0&&age<10_000,'CAPTURE_HASH_MISMATCH');
      fail('CAPTURE_WRITE_IN_PROGRESS');
    }
    if(!known.has(m[1]))incoming.push({sha256:m[1],payload:JSON.parse(b.toString('utf8').replace(/^\uFEFF/,''))});
  }
  need([...known].every(id=>found.has(id)),'ACCEPTED_CAPTURE_REMOVED');
  const result=advanceReceivedPipeline({sessionDate:req.sessionDate,chartPlan:chart.chartPlan,
    mask,master,previous,incoming,throughJst:nowJst(),completionClock:nowJst});
  const outDir=safePath(req.privateRoot,true);
  const encoded=Buffer.from(JSON.stringify(result)+'\n');
  const output=path.join(outDir,'pipeline-tick-'+sha(encoded)+'.json');
  if(fs.existsSync(output))need(fs.readFileSync(output).equals(encoded),'OUTPUT_CONFLICT');
  else fs.writeFileSync(output,encoded,{flag:'wx',mode:0o600});
  console.log(JSON.stringify({privateTick:output,...result.summary}));
  return result;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
  try{runPipelineTick(process.argv.slice(2));}
  catch(error){console.error(/^NO11_(?:PIPELINE|NATIVE_SELECTOR|RSS_CHART50_IMPORT|CHART50)_/.test(error.message)
    ?error.message:'NO11_PIPELINE_PRIVATE_SOURCE_OR_RUNTIME_FAILURE');process.exitCode=2;}
}
