import fs from 'node:fs';
import path from 'node:path';
import {buildIntradayDynamicUniverseTimeline} from '../predict/daytrade/phase57-p25-intraday-dynamic-universe.js';
import {buildIntradayDynamicUniverseTimelineV2,PHASE57_INTRADAY_UNIVERSE_V2_POLICY} from '../predict/daytrade/phase57-p25-intraday-dynamic-universe-v2.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f};
const input=arg('--input'),priorDir=arg('--prior-dir',null),output=arg('--output','tmp/p25-intraday-dynamic-universe-measurement.json');
if(!input)throw new Error('--input required');
const payload=JSON.parse(fs.readFileSync(input,'utf8')),entries=Array.isArray(payload)?payload:(payload.entries??[]),asOf=payload?.meta?.observedAt??new Date().toISOString();
const asOfMs=Date.parse(asOf);
function priorSelections(){
  if(!priorDir||!fs.existsSync(priorDir))return [];
  const rows=[];
  const walk=dir=>{for(const ent of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,ent.name);if(ent.isDirectory())walk(p);else if(ent.isFile()&&ent.name==='measurement.json'){try{const x=JSON.parse(fs.readFileSync(p,'utf8'));const t=Date.parse(x.observedAt??'');if(Number.isFinite(t)&&t<asOfMs&&asOfMs-t<=30*60_000&&Array.isArray(x.selectedV2))rows.push({t,selected:x.selectedV2});}catch{}}}};
  walk(priorDir);rows.sort((a,b)=>a.t-b.t);return rows.slice(-PHASE57_INTRADAY_UNIVERSE_V2_POLICY.persistenceWindowPoints).map(x=>x.selected);
}
const prior=priorSelections();
const started=performance.now();
const timeline=buildIntradayDynamicUniverseTimeline({snapshots:[{asOf,entries}]});
const timelineV2=buildIntradayDynamicUniverseTimelineV2({snapshots:[{asOf,entries}],priorSelections:prior});
const elapsedMs=performance.now()-started,point=timeline.points[0],pointV2=timelineV2.points[0];
const mapV1=x=>({symbol:x.symbol,sector:x.sector,currentPrice:x.currentPrice,sourceScannedAt:x.sourceScannedAt,opportunityScore:x.opportunityScore,turnoverYen:x.turnoverYen});
const mapV2=x=>({...mapV1(x),v2Score:x.v2Score,components:x.components});
const result={schemaVersion:2,phase:'57.p25.intraday-dynamic-universe-marketwide-measurement',status:'MARKETWIDE_DYNAMIC_5M_MEASUREMENT_READY',observedAt:asOf,inputSymbols:entries.length,selectedSymbols:point?.rawUniverse?.length??0,selectedV2Symbols:pointV2?.rawUniverse?.length??0,allocationEligibleSymbols:point?.allocationEligibleUniverse?.length??0,allocationEligibleV2Symbols:pointV2?.allocationEligibleUniverse?.length??0,selectorCalls:timeline.diagnostics.selectorCalls,prescreenedRows:timeline.diagnostics.prescreenedRows,selectorElapsedMs:Number(elapsedMs.toFixed(3)),priorV2PointCount:prior.length,methodology:timeline.methodology,policy:timeline.policy,safety:timeline.safety,selected:(point?.rawUniverse??[]).map(mapV1),dynamic5mV2:{candidateId:timelineV2.candidateId,methodology:timelineV2.methodology,policy:timelineV2.policy,safety:timelineV2.safety},selectedV2:(pointV2?.rawUniverse??[]).map(mapV2)};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:result.status,observedAt:result.observedAt,inputSymbols:result.inputSymbols,selectedSymbols:result.selectedSymbols,selectedV2Symbols:result.selectedV2Symbols,priorV2PointCount:result.priorV2PointCount},null,2));
if(result.inputSymbols<3000||result.selectedSymbols<20||result.selectedV2Symbols<15||result.selected.some(x=>!Number.isFinite(Number(x.currentPrice))||Number(x.currentPrice)<=0)||result.selectedV2.some(x=>!Number.isFinite(Number(x.currentPrice))||Number(x.currentPrice)<=0))process.exit(1);
