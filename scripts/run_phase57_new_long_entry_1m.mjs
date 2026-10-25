/** Explicit local replay only. No secret/cache export, network or production integration. */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {SPEC,SPEC_SHA,SAFETY,digest,evaluateAnchor,aggregate,screen,frozenExitHandoff}
  from '../predict/long-only/phase57-new-long-entry-1m.mjs';
export function validateInput(input) {
  if(input?.schema!=='ARK_NEW_LONG_ENTRY_1M_REPLAY_INPUT_V1'||input.barIntervalSeconds!==60||
     !['SYNTHETIC_TEST','HISTORICAL_DEVELOPMENT'].includes(input.dataKind)||!Array.isArray(input.candidates))
    throw Error('ONE_MINUTE_SCHEMA_REQUIRED');
  const ids=new Set(),keys=new Set();
  for(const c of input.candidates){
    const a=c.anchor,k=`${a.sessionDate}|${a.symbol}`;
    if(ids.has(a.eventId)||keys.has(k))throw Error('DUPLICATE_ANCHOR');
    ids.add(a.eventId);keys.add(k);
    if(!Array.isArray(c.bars))throw Error('MINUTE_ARRAY_REQUIRED');
  }
  if(input.dataKind==='HISTORICAL_DEVELOPMENT'&&(
      input.sourceHead!=='7599df41199a8c4d1ea86d5f3cb595edd599dd21'||input.candidates.length!==2743||
      input.anchorIdentitySHA256!=='985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121'||
      input.lineage?.status!=='AUTHORIZED_PROJECTION_BOUND_NOT_MEASURED'))throw Error('UNBOUND_HISTORICAL_SOURCE');
  return true;
}
export function run(input) {
  validateInput(input);
  const ledger=input.candidates.map(c=>evaluateAnchor(c.anchor,c.bars));
  const metrics=aggregate(ledger),verdict=screen(metrics,input.dataKind);
  const latency=input.candidates.map(c=>evaluateAnchor(c.anchor,c.bars,1));
  const dates=[...new Set(ledger.map(r=>r.sessionDate))].sort();
  const periods=Array.from({length:4},(_,i)=>{
    const period=new Set(dates.slice(16+i*15,16+(i+1)*15));
    return {dates:[...period],metrics:aggregate(ledger.filter(r=>period.has(r.sessionDate)))};
  });
  const symbolGroups=Array.from({length:5},(_,i)=>({group:i,
    metrics:aggregate(ledger.filter(r=>parseInt(digest(r.symbol).slice(0,8),16)%5===i))}));
  const independentlyNonWorse=groups=>groups.filter(g=>g.metrics.paired>0&&
    g.metrics.challengerD30.mean<=g.metrics.baselineD30.mean).length;
  if(verdict.verdict==='FAST_FAIL_CONTINUE_NOT_VALIDATED'&&(
    independentlyNonWorse(periods)<3||independentlyNonWorse(symbolGroups)<3))
      verdict.verdict='FAST_FAIL_KILL_STABILITY';
  const result={spec:SPEC,specSHA:SPEC_SHA,inputSHA:digest(input),dataKind:input.dataKind,
    ...verdict,metrics,chronological:periods,symbolGroups,
    latencyOneMinuteSensitivity:aggregate(latency),
    actualHistoricalTrades:input.dataKind==='HISTORICAL_DEVELOPMENT'?ledger.filter(r=>r.challenger.status==='REFERENCE_FILLED').length:0,
    syntheticCases:input.dataKind==='SYNTHETIC_TEST'?ledger.length:0,
    candidateAccepted:false,fullPipelineOOS:false,frozenExitReplayPerformed:false,
    portfolioReturn:null,portfolioMaxDD:null,modelFits:0,modelPredictions:0,
    newMarketDataRequests:0,freshAccess:0,oosAccess:0,safety:SAFETY};
  const handoff=ledger.map((r,i)=>frozenExitHandoff(input.candidates[i].anchor,r)).filter(Boolean);
  return {result,ledger,handoff};
}
export function main(argv) {
  if(argv.length!==4||argv[0]!=='--input'||argv[2]!=='--output')throw Error('USAGE: --input JSON --output NEW_DIRECTORY');
  const input=JSON.parse(fs.readFileSync(argv[1],'utf8')),out=argv[3];
  if(fs.existsSync(out))throw Error('NEW_OUTPUT_DIRECTORY_REQUIRED');
  const r=run(input);fs.mkdirSync(out,{recursive:true});
  for(const [name,value]of Object.entries(r)){
    const text=JSON.stringify(value,null,2)+'\n';fs.writeFileSync(path.join(out,name+'.json'),text,{flag:'wx'});
  }
  fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify({specSHA:SPEC_SHA,
    outputs:Object.fromEntries(Object.entries(r).map(([k,v])=>[k+'.json',digest(v)])),safety:SAFETY},null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({verdict:r.result.verdict,dataKind:input.dataKind,metrics:r.result.metrics}));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main(process.argv.slice(2));
