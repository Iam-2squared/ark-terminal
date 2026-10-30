/**
 * No.1.2 isolated SYNTHETIC emergency EXIT proposal from current State9.
 * Inherits the original SHARP_DROP-first/structural-control priority;
 * no order, no sell fill, no cash/slot release, no live broker certification.
 */
import {CAUSAL_FRAME_SCHEMA,inspectNo11ProspectiveAsOf} from
  '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';

const fail=x=>{throw Error(x)};
const ms=(s,label)=>{
 if(typeof s!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(s)||!Number.isFinite(Date.parse(s)))fail(label);
 return Date.parse(s);
};
const symbol=x=>{
 const y=String(x??'').trim().toUpperCase();
 if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(y))fail('NO12_EXIT_SYMBOL_INVALID');
 return y.endsWith('.T')?y:y+'.T';
};
const validStates=new Set(['RISE_STOP','RISE','SHARP_RISE','PULLBACK','RANGE',
 'REBOUND','SHARP_DROP','DROP','DROP_STOP']);
export function proposeNo12SyntheticEmergencyExits({
 mode,observationFrame,managedPositions,checkpoints,now=new Date()
}={}){
 if(mode!=='SYNTHETIC_OFFLINE_ONLY')fail('NO12_REAL_EXIT_NOT_CERTIFIED');
 if(observationFrame?.schemaId!==CAUSAL_FRAME_SCHEMA)fail('NO12_EXIT_FRAME_REQUIRED');
 const receipt=inspectNo11ProspectiveAsOf({frame:observationFrame,now});
 const when=ms(observationFrame.decisionAt,'NO12_EXIT_DECISION_AT_INVALID');
 if(!Array.isArray(managedPositions)||!Array.isArray(checkpoints))
  fail('NO12_EXIT_ARRAYS_REQUIRED');
 const active=new Map(),used=new Set();
 for(const p of managedPositions){
   const s=symbol(p.symbol);
   if(active.has(s)||p.syntheticArkOwned!==true||
     !Number.isSafeInteger(p.quantity)||p.quantity<1||
     typeof p.entryId!=='string'||!p.entryId.trim())
      fail('NO12_EXIT_POSITION_UNPROVEN_OR_DUPLICATE');
   const fill=ms(p.confirmedSyntheticBuyFillKnownAt,'NO12_EXIT_BUY_FILL_REQUIRED');
   if(fill>when)fail('NO12_EXIT_FILL_AFTER_DECISION');
   active.set(s,{...p,fill});
 }
 const source=new Map(observationFrame.records.map(r=>[r.recordId,r]));
 const exits=[],pending=[],blocked=[];
 for(const row of checkpoints){
   if(!row||typeof row!=='object'||Array.isArray(row))fail('NO12_EXIT_CHECKPOINT_INVALID');
   const s=symbol(row.symbol);
   if(used.has(s))fail('NO12_EXIT_SAME_SYMBOL_CHECKPOINT_DUPLICATE');
   used.add(s);
   const p=active.get(s);
   if(!p){blocked.push({symbol:s,reason:'NO_ARK_MANAGED_POSITION'});continue;}
   const evidence=source.get(row.stateRecordId);
   if(!evidence||evidence.sourceType!=='ORIGINAL_NATIVE_FEATURE_OBSERVATION')
     fail('NO12_EXIT_STATE9_SOURCE_UNAVAILABLE');
   const checkpoint=ms(evidence.knownAt,'NO12_EXIT_STATE_KNOWN_AT_INVALID');
   if(checkpoint<=p.fill||checkpoint>when)fail('NO12_EXIT_CHECKPOINT_NOT_POST_BUY_FILL');
   if(row.stateUsable!==true||!validStates.has(row.formalState9Primary)){
     blocked.push({symbol:s,reason:'STATE9_EVIDENCE_GAP_NOT_IMPUTED'});continue;
   }
   if(row.intentAlreadyIssued===true){
     pending.push({symbol:s,reason:'EARLIER_EXIT_INTENT_LATCHED'});continue;
   }
   if(row.controlIntentKnownAt!==null&&row.controlIntentKnownAt!==undefined){
     const controlAt=ms(row.controlIntentKnownAt,'NO12_EXIT_CONTROL_TIME_INVALID');
     if(controlAt<=checkpoint){
       pending.push({symbol:s,reason:'ORIGINAL_CONTROL_EXIT_PRIORITY'});continue;
     }
   }
   if(row.formalState9Primary==='SHARP_DROP'){
     exits.push(Object.freeze({
       eventId:'sd:'+p.entryId,kind:'SELL_INTENT',session:observationFrame.session,
       symbol:s,entryId:p.entryId,quantity:p.quantity,
       knownAt:observationFrame.decisionAt,
       syntheticIntentOnly:true,transmitted:false,
       reason:'FIRST_CAUSALLY_USABLE_SHARP_DROP'
     }));
   }else{
     pending.push({symbol:s,reason:'NO_SHARP_DROP_DELEGATE_ORIGINAL_EXIT'});
   }
 }
 return Object.freeze({
   schemaId:'ARK_NO12_SYNTHETIC_EXIT_PROPOSAL_V1',
   status:blocked.length?'EVIDENCE_GAP_OR_OWNERSHIP_BLOCKED':'SYNTHETIC_EXIT_CHECKPOINT_EVALUATED',
   sourceFrameSha256:receipt.sourceFrameSha256,
   exits:Object.freeze(exits),pending:Object.freeze(pending),blocked:Object.freeze(blocked),
   originalStructuralExitRuntimeConnected:false,
   brokerFillCertified:false,brokerOrderAllowed:false,
   productionReady:false,orderTransmission:false
 });
}
