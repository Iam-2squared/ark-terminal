import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const levels=[1,2,3,5];
export function strictPath(bars, date, timestamp, reference) {
  const start=Date.parse(timestamp), minute=Number(timestamp.slice(11,13))*60+Number(timestamp.slice(14,16));
  const endMinute=date<'2024-11-05'?900:930;
  const unavailable=reason=>({labelable:false,reason});
  if(!Number.isFinite(start)||timestamp.slice(0,10)!==date||!timestamp.endsWith('+09:00')||!(reference>0))throw Error('INVALID_REFERENCE');
  if(minute>=690&&minute<750||minute<690&&minute+30>690)return unavailable('LUNCH_BREAK');
  if(minute<540||minute+30>endMinute)return unavailable('SESSION_END');
  const byStart=new Map();
  for(const b of bars){if(b.sessionDate!==date)throw Error('CROSS_SESSION_BAR'); const t=Date.parse(b.barStartJst);if(byStart.has(t))throw Error('DUPLICATE_BAR');byStart.set(t,b);}
  const rows=Array.from({length:6},(_,i)=>byStart.get(start+i*300000));
  if(rows.some(b=>!b))return unavailable('PROVIDER_GAP');
  for(let i=0;i<6;i++){const b=rows[i];if(Date.parse(b.availableAtJst)!==start+(i+1)*300000||![b.high,b.low,b.close].every(x=>Number.isFinite(x)&&x>0)||b.low>b.high||b.close>b.high||b.close<b.low)throw Error('INVALID_COMPLETED_BAR');}
  const highReturnPct=100*(Math.max(...rows.map(b=>b.high))/reference-1),closeReturnPct=100*(Math.max(...rows.map(b=>b.close))/reference-1);
  return {labelable:true,reason:null,highReturnPct,closeReturnPct,ordinalClass:levels.filter(x=>highReturnPct>=x).length,closeOrdinalClass:levels.filter(x=>closeReturnPct>=x).length,trueMaePct:Math.min(0,100*(Math.min(...rows.map(b=>b.low))/reference-1)),mfePct:Math.max(0,highReturnPct),barCount:6,sparseMinuteBars:rows.filter(b=>b.observedMinutes<5).length};
}
export function main(cacheRoot,output){
  if(!cacheRoot||!output||fs.existsSync(output))throw Error('EXPLICIT_NEW_OUTPUT_REQUIRED');
  const base='docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement',c=read(`${base}/dataset-contract.json`);
  if(sha(fs.readFileSync(`${base}/dataset-contract.json`))!=='4a1d3e4ec4229d32ee2a50678db8fe3f8739abb3530df521e3036d201e75b441')throw Error('CONTRACT_SHA_MISMATCH');
  for(const [p,h]of Object.entries(c.sourcePins))if(sha(fs.readFileSync(p))!==h)throw Error(`SOURCE_SHA_MISMATCH:${p}`);
  const rows=gunzipSync(fs.readFileSync('docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz')).toString().trim().split('\n').map(JSON.parse);
  const current=JSON.parse(gunzipSync(fs.readFileSync('docs/evidence/phase57-long-only-entry-filter-recovery-audit-v1-first-opportunities.json.gz')));
  const alloc=read('predict/long-only/phase57-long-only-session-allocation-v3.json');
  const l1=read('predict/long-only/phase57-long-only-l1-discovery-sessions.json'),l2=read('predict/long-only/phase57-long-only-l2-development-sessions.json'),v2=read('predict/long-only/phase57-long-only-v2-development-sessions.json');
  const groups=[{sessions:l1.sessions,manifest:'l1-minute-manifest.json',hash:l1.sessionListSha256},{sessions:v2.sessions,manifest:'v2-minute-manifest.json',hash:v2.sessionListSha256},{sessions:[...alloc.partitions.DEVELOPMENT_C,...alloc.partitions.DEVELOPMENT_D],manifest:'l2-minute-manifest.json',hash:l2.sessionListSha256}];
  const events=[],currentEvents=[],sources=[];let parity=0;
  for(const date of c.sessionList){
    const group=groups.filter(g=>g.sessions.includes(date)),parts=Object.entries(alloc.partitions).filter(([,ds])=>ds.includes(date));
    if(group.length!==1||parts.length!==1||!parts[0][0].startsWith('DEVELOPMENT_'))throw Error('SEALED_OR_AMBIGUOUS_SCOPE');
    const dir=path.join(cacheRoot,'phase57-long-only/raw/jquants-v2',date),m=read(path.join(dir,group[0].manifest)),pageFile=path.join(dir,'minute-pages.json'),pages=read(pageFile);
    if(m.sessionDate!==date||m.partition!==parts[0][0]||m.sessionListSha256!==group[0].hash||m.pageCount!==pages.length)throw Error('MINUTE_MANIFEST_MISMATCH');
    for(const p of pages)if(sha(p.responseText)!==p.responseSha256)throw Error('PAGE_SHA_MISMATCH');
    const raw=pages.flatMap(p=>JSON.parse(p.responseText).data??[]);if(raw.length!==m.rowCount)throw Error('ROW_COUNT_MISMATCH');
    if(raw.some(r=>(r.Date??r.date)!==date))throw Error('UNAUTHORIZED_SESSION');
    const normalized=normalizeAndAggregateMinuteRows(raw),bySymbol=new Map();for(const b of normalized.bars){if(!bySymbol.has(b.symbol))bySymbol.set(b.symbol,[]);bySymbol.get(b.symbol).push(b);}
    const sessionRows=rows.filter(r=>r.sessionDate===date),byId=new Map(sessionRows.map(r=>[r.selectorEventId,r]));
    for(const r of sessionRows){
      if(!r.label.labelable){events.push({selectorEventId:r.selectorEventId,labelable:false,reason:r.label.reason});continue;}
      const p=strictPath(bySymbol.get(r.symbol)??[],date,r.decisionTimestamp,r.decisionPrice);
      if(!p.labelable||p.ordinalClass!==r.label.ordinalClass||p.closeOrdinalClass!==r.label.closeOrdinalClass||Math.abs(p.highReturnPct-r.label.highReturnPct)>1e-9||Math.abs(p.closeReturnPct-r.label.closeReturnPct)>1e-9)throw Error(`SAVED_LABEL_PARITY_FAILED:${r.selectorEventId}`);
      parity++;events.push({selectorEventId:r.selectorEventId,...p});
    }
    for(const r of current.filter(x=>x.sessionDate===date&&x.firstPassTimestamp)){
      const original=byId.get(r.firstSelectorEventId);if(!original)throw Error('CURRENT_SELECTOR_ID_MISMATCH');
      currentEvents.push({symbolSessionId:r.symbolSessionId,sessionDate:date,firstPassTimestamp:r.firstPassTimestamp,firstPassPrice:r.firstPassPrice,...strictPath(bySymbol.get(original.symbol)??[],date,r.firstPassTimestamp,r.firstPassPrice)});
    }
    sources.push({sessionDate:date,partition:m.partition,pageCount:pages.length,rawPagesSHA:sha(fs.readFileSync(pageFile)),pageSHAs:pages.map(p=>p.responseSha256),normalizedSHA:sha(JSON.stringify(normalized.bars)),audit:normalized.audit});
    console.log(JSON.stringify({sessionDate:date,status:'PATH_RECOVERY_COMPLETE',providerRequests:0}));
  }
  if(events.length!==3800||parity!==1828)throw Error('EVENT_IDENTITY_MISMATCH');
  const result={purpose:c.purpose,exposure:'IN_SAMPLE_DEVELOPMENT_EXPOSED',datasetContractSHA:sha(fs.readFileSync(`${base}/dataset-contract.json`)),sourceCheckpointRuns:c.sourceCheckpointRuns,integrity:{savedLabelParityRows:parity,providerRequests:0,forwardFill:0,interpolation:0,futureSubstitution:0,oosAccess:0,exitOutcomeAccess:0,scope:'76 DEVELOPMENT sessions only',minuteSemantics:'Frozen provider normalizer retains observed trading-minute bars; sparse-minute bars are disclosed, not filled'},sources,events,currentEvents,safety:c.safety};
  fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(result)+'\n',{flag:'wx'});fs.writeFileSync(`${output}.sha256`,sha(fs.readFileSync(output))+'\n',{flag:'wx'});
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main(process.argv[2],process.argv[3]);
