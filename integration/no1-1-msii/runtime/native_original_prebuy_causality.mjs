// Original Frozen Capital V5 feature chronology; audit-only, never signal generation.
import fs from 'node:fs';
import {createHash} from 'node:crypto';
export const ORIGINAL_CORE_BLOB='685a7774ed96556b810aa23957d12fda8f9654ba';
export const POST_FILL_FEATURES=Object.freeze([
  'entry/fill_clock','entry/intent_to_fill_active_delay',
  'selector/raw_entry_vs_first_price_pct'
]);
const source=new URL('../frozen-native-code/core_features.py',import.meta.url);
const fail=x=>{throw Error(x)};
const clock=(x,label)=>typeof x==='string'&&/(Z|[+-]\d{2}:\d{2})$/.test(x)&&Number.isFinite(Date.parse(x))
  ?Date.parse(x):fail(label);
export function assertFrozenOriginalCore(){
  const original=fs.readFileSync(source);
  const bytes=Buffer.from(original.toString('utf8').replace(/\r\n/g,'\n'));
  const id=createHash('sha1').update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');
  if(id!==ORIGINAL_CORE_BLOB)fail('FROZEN_CORE_IDENTITY_MISMATCH');
  const text=bytes.toString('utf8');
  for(const field of POST_FILL_FEATURES)if(!text.includes("'"+field+"'"))fail('FROZEN_ORIGINAL_FEATURE_IDENTITY_MISMATCH');
  for(const phrase of ["t=entry['fill_minute']","entry['fill_price']"])
    if(!text.includes(phrase))fail('FROZEN_ORIGINAL_FILL_USAGE_MISSING');
  return true;
}
export function auditOriginalPreBuyCausality({
  stage,decisionAt,confirmedFillAt=null,featureKnownTimes=null,now=new Date()
}={}){
  assertFrozenOriginalCore();
  const t=clock(decisionAt,'DECISION_CLOCK_REQUIRED');
  const nowMs=now instanceof Date?now.getTime():clock(now,'CURRENT_CLOCK_REQUIRED');
  if(!Number.isFinite(nowMs)||t>nowMs+1000)fail('DECISION_NOT_YET_CAUSALLY_AVAILABLE');
  if(stage==='BEFORE_BUY_FILL'){
    return Object.freeze({
      status:'ORIGINAL_PRE_BUY_RANK_CAUSALITY_NOT_PROVEN',
      postFillDependencies:POST_FILL_FEATURES,originalSourceVerified:true,
      preBuyFrozenRankCertified:false,liveDecisionPublished:false,
      productionReady:false,orderTransmission:false
    });
  }
  if(stage!=='AFTER_CONFIRMED_BUY_FILL')fail('UNSUPPORTED_FEATURE_EVALUATION_STAGE');
  const filled=clock(confirmedFillAt,'BROKER_FILL_RECEIPT_REQUIRED');
  if(filled>t)fail('FILL_NOT_YET_AVAILABLE');
  if(!featureKnownTimes||typeof featureKnownTimes!=='object')fail('FEATURE_TIME_PROOF_REQUIRED');
  for(const feature of POST_FILL_FEATURES){
    if(!Object.hasOwn(featureKnownTimes,feature))fail('POSTFILL_KNOWN_TIME_MISSING');
    const seen=clock(featureKnownTimes[feature],'POSTFILL_KNOWN_TIME_INVALID');
    if(seen<filled||seen>t)fail('POSTFILL_CHRONOLOGY_INVALID');
  }
  return Object.freeze({
    status:'POST_FILL_CHRONOLOGY_OBSERVED_NOT_PRE_BUY',
    originalSourceVerified:true,preBuyFrozenRankCertified:false,
    liveDecisionPublished:false,productionReady:false,orderTransmission:false
  });
}
