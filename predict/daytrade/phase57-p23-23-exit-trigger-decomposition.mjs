import fs from 'node:fs';

const input=process.argv[2]??'artifacts/phase57-p23-22-structural-invalidation-exit.json';
const output=process.argv[3]??'artifacts/phase57-p23-23-exit-trigger-decomposition.json';
const x=JSON.parse(fs.readFileSync(input,'utf8'));
const counters={decisions:0,ready:0,notReady:0,probabilityOnly:0,evOnly:0,microBreakOnly:0,probabilityAndEv:0,probabilityAndMicro:0,evAndMicro:0,allThree:0,none:0};
const byDirection={UP:{...counters},DOWN:{...counters}};
const bySetup={};
function fresh(){return Object.fromEntries(Object.keys(counters).map(k=>[k,0]));}
function add(bucket,d){
  bucket.decisions++;
  const e=d?.evidence;
  if(!e?.ready){bucket.notReady++;return;}
  bucket.ready++;
  const p=Number(e.lowerInvalidation90)>.5;
  const ev=Number(e.expectedReturnPct)<0;
  const micro=e?.evidence?.microBreak===true;
  if(p&&!ev&&!micro)bucket.probabilityOnly++;
  if(!p&&ev&&!micro)bucket.evOnly++;
  if(!p&&!ev&&micro)bucket.microBreakOnly++;
  if(p&&ev)bucket.probabilityAndEv++;
  if(p&&micro)bucket.probabilityAndMicro++;
  if(ev&&micro)bucket.evAndMicro++;
  if(p&&ev&&micro)bucket.allThree++;
  if(!p&&!ev&&!micro)bucket.none++;
}
for(const pair of x.pairs??[]){
  const t=pair.invalidation??pair.structural??{};
  const dir=t.direction??pair.baseline?.direction??'UNKNOWN';
  const setup=t.setup??pair.baseline?.setup??'UNKNOWN';
  bySetup[setup]??=fresh();
  for(const d of t.decisions??[]){
    add(counters,d);
    if(byDirection[dir])add(byDirection[dir],d);
    add(bySetup[setup],d);
  }
}
const rates={};for(const [k,v] of Object.entries(counters))rates[k]=counters.ready&&k!=='decisions'&&k!=='ready'&&k!=='notReady'?v/counters.ready:null;
const result={phase:'57.p23.23-exit-trigger-decomposition',status:'EXIT_TRIGGER_DECOMPOSITION_COMPLETE',symbols:x.symbols??[],symbolCount:x.symbolCount??0,sourcePhase:x.phase??null,triggerCounts:counters,triggerRatesOfReady:rates,byDirection,bySetup,diagnosis:{probabilityGatePass:counters.probabilityAndEv,probabilityPlusEvWithoutMicroBreak:Math.max(0,counters.probabilityAndEv-counters.allThree),microBreakWithEv:counters.evAndMicro,allThree:counters.allThree},methodology:{strongEntryFrozenQ4:true,exactSameEntriesPaired:true,noThresholdSweep:true,diagnosticOnly:true,reusesP2322Decisions:true,freshHoldoutConsumed:false},executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,overnightHoldingAllowed:false,transmitted:false,edgeClaimAllowed:false,recommendationAllowed:false};
for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted'])if(result[k]!==false)throw new Error(`${k} must remain false`);
fs.mkdirSync('artifacts',{recursive:true});fs.writeFileSync(output,JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));