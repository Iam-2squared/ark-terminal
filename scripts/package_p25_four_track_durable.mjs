import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const FALSE_KEYS=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'];
const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const sha=value=>crypto.createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');
const write=(file,value)=>{fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n');};
const assertSafety=(x,label)=>{for(const k of FALSE_KEYS)if(x?.[k]!==false)throw new Error(`${label} safety ${k} must remain false`);};
const selectedCountOf=measurement=>{
  const direct=Number(measurement?.selectedCount??measurement?.selectedSymbols);
  if(Number.isFinite(direct)&&direct>=0)return direct;
  if(Array.isArray(measurement?.selected))return measurement.selected.length;
  throw new Error('dynamic 5m selected count missing');
};

export function buildFourTrackDurable({measurement,marketwideNdjson,laneC,entryRef,exitRef,selectionRef,laneCRef,sourceRunId}){
  if(measurement?.status!=='MARKETWIDE_DYNAMIC_5M_MEASUREMENT_READY')throw new Error('dynamic 5m measurement not ready');
  if(Number(measurement?.inputSymbols)<3000)throw new Error('dynamic 5m measurement is not market-wide');
  assertSafety(measurement.safety,'dynamic5m');
  if(laneC?.status!=='LANE_C_CAPITAL_EFFICIENCY_DIAGNOSTIC_READY')throw new Error('Lane C diagnostic not ready');
  if(laneC?.interpretation?.winnerSelectionAllowed!==false||laneC?.interpretation?.formalOos!==false||laneC?.interpretation?.promotionEligible!==false)throw new Error('Lane C diagnostic classification guard');
  assertSafety(laneC.safety,'laneC');
  const rows=String(marketwideNdjson??'').trim().split(/\r?\n/).filter(Boolean);
  if(rows.length!==1)throw new Error(`expected exactly one marketwide snapshot record, got ${rows.length}`);
  const snapshot=JSON.parse(rows[0]);
  if(Number(snapshot?.symbolCount)<3000||snapshot?.methodology?.pointInTimeOnly!==true||snapshot?.methodology?.deduplicated!==true)throw new Error('marketwide snapshot contract guard');
  assertSafety(snapshot.safety,'marketwideSnapshot');
  const bucket=String(snapshot.bucket??'');
  const safeBucket=bucket.replaceAll(':','-');
  if(!/^\d{4}-\d{2}-\d{2}T/.test(bucket))throw new Error('invalid snapshot bucket');
  const safety=Object.fromEntries(FALSE_KEYS.map(k=>[k,false]));
  return {
    schemaVersion:1,
    phase:'57.p25.four-track-durable-persistence',
    status:'FOUR_TRACK_DURABLE_EVIDENCE_READY',
    bucket,
    durableKey:safeBucket,
    sourceRunId:Number(sourceRunId),
    tracks:{
      entry:{status:'DURABLE_EXISTING',ref:entryRef,role:'Frozen DYNAMIC_50 Entry / formal evidence lineage'},
      dynamic5m:{status:'DURABLE_APPEND_ONLY',ref:selectionRef,inputSymbols:Number(measurement.inputSymbols),selectedCount:selectedCountOf(measurement),measurementSha256:sha(measurement),snapshotStateHash:String(snapshot.stateHash??''),snapshotSha256:sha(rows[0])},
      exitV3:{status:'DURABLE_EXISTING',ref:exitRef,role:'Frozen EXIT v3 append-only evidence'},
      capitalAllocation:{status:'DURABLE_APPEND_ONLY',ref:laneCRef,diagnosticSha256:sha(laneC),evidenceClass:String(laneC.evidenceClass??'LEGACY27_DIAGNOSTIC_ONLY')},
    },
    interpretation:{researchOnly:true,formalOos:false,promotionEligible:false,winnerSelectionAllowed:false,retuningAllowed:false},
    safety,
  };
}

const measurementPath=arg('--measurement');const snapshotPath=arg('--marketwide-ndjson');const laneCPath=arg('--lane-c');const output=arg('--output');
if(measurementPath&&snapshotPath&&laneCPath&&output){
  const result=buildFourTrackDurable({measurement:read(measurementPath),marketwideNdjson:fs.readFileSync(snapshotPath,'utf8'),laneC:read(laneCPath),entryRef:arg('--entry-ref'),exitRef:arg('--exit-ref'),selectionRef:arg('--selection-ref'),laneCRef:arg('--lane-c-ref'),sourceRunId:arg('--source-run-id','0')});
  write(output,result);
  console.log(JSON.stringify(result,null,2));
}
