/**
 * Synthetic-only crash replay boundary for the No.1.2 candidate engine.
 * Invariant: reconstruct exactly the saved same-day event stream under
 * the SAME research scenario; do not regenerate/order/acknowledge broker IDs.
 */
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {runNo12SyntheticSession} from './synthetic_cash_lifecycle.mjs';
import {No12SyntheticJournal} from './synthetic_durable_journal.mjs';

export const NO12_SHADOW_SCENARIO_SCHEMA='ARK_NO12_SHADOW_SCENARIO_V1';
const fail=x=>{throw Error(x)};
export function originalNo12ScenarioFingerprint({candidateInput,startingCashYen,externalSymbols}={}){
 if(!candidateInput||!Number.isSafeInteger(startingCashYen)||
    startingCashYen<0||!Array.isArray(externalSymbols))fail('NO12_SHADOW_SCENARIO_INVALID');
 return digest({schemaId:NO12_SHADOW_SCENARIO_SCHEMA,
    candidateInput,startingCashYen,externalSymbols});
}
export function openNo12SyntheticScenario({
 privateRoot,candidateInput,startingCashYen,externalSymbols
}={}){
 const fingerprint=originalNo12ScenarioFingerprint({candidateInput,startingCashYen,externalSymbols});
 const session=candidateInput?.batch?.session;
 return new No12SyntheticJournal({
  privateRoot,session,scenarioSha256:fingerprint,mode:'SYNTHETIC_OFFLINE_ONLY'
 });
}
export function replayNo12SyntheticScenario({
 journal,candidateInput,startingCashYen,externalSymbols,now=new Date()
}={}){
 if(!(journal instanceof No12SyntheticJournal))fail('NO12_SHADOW_REAL_JOURNAL_REQUIRED');
 const signature=originalNo12ScenarioFingerprint({
  candidateInput,startingCashYen,externalSymbols});
 if(signature!==journal.scenarioSha256)fail('NO12_SHADOW_SCENARIO_FINGERPRINT_CHANGED');
 const captured=journal.snapshot();
 if(captured.session!==candidateInput.batch.session||
    captured.orderTransmission!==false)fail('NO12_SHADOW_UNSAFE_REPLAY');
 const evaluated=runNo12SyntheticSession({
  mode:'SYNTHETIC_OFFLINE_ONLY',candidateInput,startingCashYen,externalSymbols,
  events:captured.events,now
 });
 return Object.freeze({
  schemaId:'ARK_NO12_SHADOW_REPLAY_RECEIPT_V1',
  journalEventCount:captured.eventCount,journalSha256:captured.headSha256,
  session:captured.session,scenarioSha256:signature,
  evaluated,effectsSentToBroker:0,
  brokerReconciliationCertified:false,productionReady:false,
  orderTransmission:false
 });
}
