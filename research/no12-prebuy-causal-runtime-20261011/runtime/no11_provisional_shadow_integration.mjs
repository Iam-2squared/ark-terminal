/**
 * No.1.1 integration stage-1: provisional H2/H3/H5 + read-only synthetic
 * Selector/First Entry/State9 -> cash -> emergency EXIT chain.
 *
 * Reuses existing proven research-only components instead of inventing
 * Frozen-native model or live RSS outputs. Never imports order, Excel,
 * networking or account-writing components. H2/H3/H5 2025 sample scores
 * are diagnostics only, NEVER applied to a 2026 candidate.
 */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {inspectNo11ProspectiveAsOf} from
  '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';
import {rankNo12PreBuyResearch} from './prebuy_candidates.mjs';
import {runNo12SyntheticSession} from './synthetic_cash_lifecycle.mjs';
import {proposeNo12SyntheticEmergencyExits} from './synthetic_emergency_exit.mjs';
import {runNo11SyntheticOriginalCapitalV5} from './no11_frozen_v5_synthetic_stage.mjs';

export const NO11_PROVISIONAL_SHADOW_SCHEMA=
  'ARK_NO11_PROVISIONAL_SYNTHETIC_SHADOW_CHAIN_V1';
export const NO11_PROVISIONAL_SCENARIO_SCHEMA=
  'ARK_NO11_PROVISIONAL_SYNTHETIC_SHADOW_SCENARIO_V1';
const TRAINING_BLOB='8b4406c1778a940e95136644b2a8c994cde1fdd7';
const FROZEN_BLOB='e1546306575e874150fe62518e0b971008922e85';
const STUDY=new URL(
  '../NO11_H235_PROVISIONAL_TRAINING_COMPLETE_INTEGRATION_GATE_20261014.json',import.meta.url);
const FROZEN=new URL(
  '../../ark-integrated-no1-1-freeze-20261008/INTEGRATED_NO1_1_FREEZE.json',import.meta.url);

const error=s=>{throw Error(s)};
const checked=(ok,s)=>{if(!ok)error(s)};
const hex=s=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);
const knownTime=(s,label)=>{
  if(typeof s!=='string'||!/(?:Z|[+-]\d{2}:\d{2})$/.test(s)||
     !Number.isFinite(Date.parse(s)))error(label);
  return Date.parse(s);
};
const gitBlob=buf=>{
  const b=Buffer.from(buf.toString('utf8').replace(/\r\n/g,'\n'));
  return createHash('sha1').update(Buffer.from('blob '+b.length+'\0')).update(b).digest('hex');
};

function pinnedPolicy(file,blob,label){
  const raw=fs.readFileSync(file);
  checked(gitBlob(raw)===blob,'NO11_INTEGRATION_'+label+'_HASH_CHANGED');
  return JSON.parse(raw.toString('utf8'));
}

export function inspectNo11ProvisionalIntegrationPolicy(){
  const training=pinnedPolicy(STUDY,TRAINING_BLOB,'TRAINING');
  const frozen=pinnedPolicy(FROZEN,FROZEN_BLOB,'FROZEN');
  checked(training.schemaId===
    'ARK_NO11_H235_PROVISIONAL_DEVELOPMENT_COMPLETION_20261014_V1'&&
    training.decision==='USER_AUTHORIZED_PROVISIONAL_TRAINING_COMPLETE_AND_START_INTEGRATION'&&
    training.study?.modelHeads?.join('|')==='H2|H3|H5'&&
    training.study?.oofCandidates===1039&&
    training.study?.finalDevelopmentFitRows===1588&&
    training.study?.originalFrozenModelReplacement===false&&
    training.additional2026Rss?.native2026LabeledTrainingRows===0&&
    training.safety?.productionReady===false&&
    training.safety?.orderTransmission===false&&
    training.safety?.automaticPromotion===false,
    'NO11_INTEGRATION_TRAINING_POLICY_REJECTED');
  checked(frozen.document_id==='ARK_INTEGRATED_NO1_1_FREEZE_20261008'&&
    frozen.status==='USER_SELECTED_FROZEN_COMBINATION_NO1_1'&&
    frozen.newly_selected_vacancy_policy?.policy_id===
      'WAIT_AFTER_FIRST_LEGAL_SELL_FILL_UNTIL_NEXT_TRADING_SESSION'&&
    frozen.inherited_frozen_state_filter?.excluded_formal_entry_states?.join('|')===
      'PULLBACK|SHARP_DROP'&&
    frozen.promotion?.automatic_promotion_allowed===false&&
    frozen.safety?.productionReady===false&&
    frozen.safety?.transmitted===false,
    'NO11_INTEGRATION_FROZEN_POLICY_REJECTED');
  return Object.freeze({
    status:'2025_H235_PROVISIONAL_RESEARCH_FIXED_FOR_SYNTHETIC_INTEGRATION',
    trainingGateGitBlob:TRAINING_BLOB,frozenNo11GitBlob:FROZEN_BLOB,
    researchHeads:Object.freeze(['H2','H3','H5']),
    trainingExamples2026:0,
    frozenOriginalModelsReplaced:false,
    originalFrozenStrategyChanged:false,
    productionReady:false,orderTransmission:false
  });
}

// Reject outcomes at their source, not merely in the model projection.
// This is intentionally narrower than the *synthetic cash event* grammar:
// BUY_FILL and SELL_FILL events are legal only after entry evaluation.
const prebuyForbidden=/^(?:future(?:[A-Z_]|$)|teacher(?:[A-Z_]|$)|label(?:[A-Z_]|$)|outcome(?:[A-Z_]|$)|realized(?:[A-Z_]|$)|actualFill|fill(?:Price|Time|Minute|_))|(?:^|\/)(?:entry\/)?fill_clock$/i;
function blockOutcomeFields(value,depth=0,visited=new Set()){
  checked(depth<=10,'NO11_INTEGRATION_PREBUY_DEPTH_EXCEEDED');
  if(value===null||typeof value!=='object')return;
  checked(!visited.has(value),'NO11_INTEGRATION_PREBUY_CYCLE');
  visited.add(value);
  for(const [key,v] of Object.entries(value)){
    checked(!prebuyForbidden.test(key),
      'NO11_INTEGRATION_PREBUY_FUTURE_OR_FILL_FIELD:'+key);
    blockOutcomeFields(v,depth+1,visited);
  }
  visited.delete(value);
}

export function inspectNo11ProvisionalH235ResearchReceipts(receipts){
  if(receipts===undefined||receipts===null){
    return Object.freeze({
      status:'2025_PROVISIONAL_MODELS_FROZEN_SAMPLE_RECEIPTS_NOT_ATTACHED',
      modelReceiptsInspected:0,usableFor2026CandidateRanking:false,
      originalFrozenH235Executed:false,productionReady:false,
      orderTransmission:false
    });
  }
  checked(Array.isArray(receipts)&&receipts.length===3,
    'NO11_INTEGRATION_H235_THREE_RECEIPTS_REQUIRED');
  const heads=new Map(),models=new Set(),featureHashes=new Set();
  for(const item of receipts){
    checked(item&&typeof item==='object'&&!Array.isArray(item)&&
      item.schemaId==='ARK_NO11_ASOF_RESEARCH_OFFLINE_SCORE_V1'&&
      item.mode==='OFFLINE_RESEARCH_ONLY'&&
      ['H2','H3','H5'].includes(item.head)&&!heads.has(item.head)&&
      Number.isFinite(item.research_probability)&&
      item.research_probability>=0&&item.research_probability<=1&&
      hex(item.modelSha256)&&hex(item.featureSha256)&&
      item['2026NativeSelectorEntryRebuilt']===false&&
      item['2026SupervisedTrainingRows']===0&&
      item.brokerActualKnownAtCertified===false&&
      item.newModelAutomaticallyPromoted===false&&
      item.productionReady===false&&item.orderTransmission===false,
      'NO11_INTEGRATION_H235_UNAPPROVED_RESEARCH_RECEIPT');
    checked(!models.has(item.modelSha256),
      'NO11_INTEGRATION_H235_DUPLICATED_MODEL_HASH');
    heads.set(item.head,item.research_probability);
    models.add(item.modelSha256);featureHashes.add(item.featureSha256);
  }
  checked(featureHashes.size===1,
    'NO11_INTEGRATION_H235_FEATURE_ROW_MISMATCH');
  return Object.freeze({
    status:'2025_PROVISIONAL_H235_SAMPLE_SCORES_LOADED_NOT_BOUND_TO_2026',
    modelReceiptsInspected:3,
    researchSampleProbabilities:Object.freeze(Object.fromEntries(
      ['H2','H3','H5'].map(name=>[name,heads.get(name)]))),
    historicalSampleFeatureSha256:[...featureHashes][0],
    usableFor2026CandidateRanking:false,originalFrozenH235Executed:false,
    productionReady:false,orderTransmission:false
  });
}

function positionsForExit(cash){
  const fills=cash.history.filter(x=>x.type==='SYNTHETIC_BUY_FILL');
  return cash.positions.map(pos=>{
    const received=[...fills].reverse().find(x=>x.symbol===pos.symbol);
    checked(received&&typeof received.observedAt==='string',
      'NO11_INTEGRATION_EXIT_SYNTHETIC_BUY_FILL_MISSING');
    return {symbol:pos.symbol,entryId:pos.entryId,quantity:pos.quantity,
      syntheticArkOwned:true,confirmedSyntheticBuyFillKnownAt:received.observedAt};
  });
}

function syntheticExitIntent(proposal,index){
  return Object.freeze({
    kind:'SELL_INTENT',eventId:proposal.eventId,
    session:proposal.session,knownAt:proposal.knownAt,
    orderId:'no11-offline-exit-'+(index+1),
    symbol:proposal.symbol,quantity:proposal.quantity,
    transmitted:false,syntheticIntentOnly:true
  });
}

function vetConfirmations(events,intents,decisionAt){
  checked(Array.isArray(events)&&events.length<=1000,
    'NO11_INTEGRATION_CONFIRMATIONS_ARRAY_REQUIRED');
  const permitted=new Set(intents.map(x=>x.orderId));
  const exitT=knownTime(decisionAt,'NO11_INTEGRATION_EXIT_DECISION_INVALID');
  const fills=new Set();
  for(const event of events){
    checked(event&&typeof event==='object'&&!Array.isArray(event)&&
      event.productionReady!==true&&event.transmitted!==true&&
      ['SELL_FILL','ENTRY_SIGNAL'].includes(event.kind),
      'NO11_INTEGRATION_POST_EXIT_EVENT_NOT_SYNTHETIC');
    const at=knownTime(event.knownAt,'NO11_INTEGRATION_POST_EXIT_KNOWN_INVALID');
    checked(at>=exitT,'NO11_INTEGRATION_POST_EXIT_EVENT_BEFORE_PROPOSAL');
    if(event.kind==='SELL_FILL'){
      checked(permitted.has(event.orderId)&&
        event.syntheticMatchedOrder===true&&
        !fills.has(event.orderId),
        'NO11_INTEGRATION_EXIT_FILL_WITHOUT_PROPOSAL');
      fills.add(event.orderId);
    }
  }
  return events;
}

/**
 * This truly composes existing offline modules in source -> rank -> synthetic
 * buy/cash -> observed synthetic state EXIT -> optional matched synthetic
 * sell/cash/replacement latch. No synthetic output is a native No.1.1 order.
 */
export function runNo11ProvisionalSyntheticShadow({
  mode,scenario,now=new Date()
}={}){
  checked(mode==='SYNTHETIC_OFFLINE_ONLY',
    'NO11_INTEGRATION_LIVE_OR_BROKER_MODE_DISABLED');
  checked(scenario?.schemaId===NO11_PROVISIONAL_SCENARIO_SCHEMA&&
    scenario.evidenceMode==='SYNTHETIC_OFFLINE_ONLY'&&
    scenario.productionReady===false&&scenario.orderTransmission===false&&
    scenario.frozenNo11Modified===false,
    'NO11_INTEGRATION_SCENARIO_FLAGS_INVALID');
  const policy=inspectNo11ProvisionalIntegrationPolicy();
  const input=scenario.candidateInput;
  checked(input?.batch&&input?.observationFrame&&input?.ownership,
    'NO11_INTEGRATION_SOURCE_FRAME_OR_OWNERSHIP_MISSING');
  blockOutcomeFields(input);
  const source=inspectNo11ProspectiveAsOf({
    frame:input.observationFrame,now
  });
  const candidates=rankNo12PreBuyResearch({
    mode:'SYNTHETIC_OFFLINE_ONLY',...input,now
  });
  checked(candidates.sourceFrameSha256===source.sourceFrameSha256,
    'NO11_INTEGRATION_PREBUY_SOURCE_PARITY_FAILED');
  const h235=inspectNo11ProvisionalH235ResearchReceipts(
    scenario.provisionalH235SampleReceipts);
  checked(Array.isArray(scenario.entryEvents),
    'NO11_INTEGRATION_ENTRY_EVENT_SEQUENCE_REQUIRED');
  const frozenV5=scenario.syntheticFrozenV5Request===undefined?null:
    runNo11SyntheticOriginalCapitalV5({
      mode:'SYNTHETIC_OFFLINE_ONLY',
      request:scenario.syntheticFrozenV5Request,
      rankedCandidates:candidates.eligible,
      startingCashYen:scenario.startingCashYen
    });
  if(frozenV5){
    const funded=new Set(frozenV5.fundedEntries.map(x=>x.entryId));
    for(const event of scenario.entryEvents){
      if(event.kind==='ENTRY_SIGNAL')
        checked(funded.has(event.entryId),
          'NO11_INTEGRATION_ENTRY_NOT_FUNDED_BY_ORIGINAL_V5_SYNTHETIC');
    }
  }
  const cashBeforeExit=runNo12SyntheticSession({
    mode:'SYNTHETIC_OFFLINE_ONLY',
    candidateInput:input,events:scenario.entryEvents,
    startingCashYen:scenario.startingCashYen,
    externalSymbols:scenario.externalSymbols,now
  });
  checked(cashBeforeExit.status==='SYNTHETIC_SCENARIO_EVALUATED',
    'NO11_INTEGRATION_ENTRY_RECONCILIATION_BLOCK');
  const hasCheckpoint=scenario.exitObservationFrame!==undefined;
  let exitResult=null,syntheticExitIntents=[],cashAfterExit=cashBeforeExit;
  if(hasCheckpoint){
    checked(Array.isArray(scenario.exitCheckpoints),
      'NO11_INTEGRATION_EXIT_CHECKPOINTS_REQUIRED');
    const entryTime=knownTime(input.observationFrame.decisionAt,
      'NO11_INTEGRATION_ENTRY_DECISION_INVALID');
    const exitTime=knownTime(scenario.exitObservationFrame.decisionAt,
      'NO11_INTEGRATION_EXIT_DECISION_INVALID');
    checked(exitTime>entryTime,
      'NO11_INTEGRATION_EXIT_BEFORE_OR_AT_ENTRY');
    exitResult=proposeNo12SyntheticEmergencyExits({
      mode:'SYNTHETIC_OFFLINE_ONLY',
      observationFrame:scenario.exitObservationFrame,
      managedPositions:positionsForExit(cashBeforeExit),
      checkpoints:scenario.exitCheckpoints,now
    });
    syntheticExitIntents=exitResult.exits.map(syntheticExitIntent);
    if(scenario.postExitEvents!==undefined){
      const post=vetConfirmations(
        scenario.postExitEvents,syntheticExitIntents,
        scenario.exitObservationFrame.decisionAt);
      cashAfterExit=runNo12SyntheticSession({
        mode:'SYNTHETIC_OFFLINE_ONLY',candidateInput:input,
        events:[...scenario.entryEvents,...syntheticExitIntents,...post],
        startingCashYen:scenario.startingCashYen,
        externalSymbols:scenario.externalSymbols,now
      });
      checked(cashAfterExit.status==='SYNTHETIC_SCENARIO_EVALUATED',
        'NO11_INTEGRATION_SELL_RECONCILIATION_BLOCK');
    }
  } else {
    checked(scenario.postExitEvents===undefined&&
      scenario.exitCheckpoints===undefined,
      'NO11_INTEGRATION_EXIT_EVENTS_WITHOUT_CHECKPOINT');
  }
  checked(cashAfterExit.orderTransmission===false&&
    cashAfterExit.productionReady===false,
    'NO11_INTEGRATION_SYNTHETIC_LEDGER_NOT_SAFE');
  return Object.freeze({
    schemaId:NO11_PROVISIONAL_SHADOW_SCHEMA,
    status:'SYNTHETIC_STAGE_WIRING_PASS_NATIVE_NO11_NOT_CERTIFIED',
    mode:'SYNTHETIC_OFFLINE_ONLY',
    training:policy,
    stages:Object.freeze({
      market:Object.freeze({status:source.status,
        sourceFrameSha256:source.sourceFrameSha256,
        brokerArrivalCertified:false}),
      selector:Object.freeze({status:'SYNTHETIC_OBSERVATION_ONLY_NOT_FROZEN_SELECTOR',
        nativeExecuted:false}),
      firstEntry:Object.freeze({
        status:'SYNTHETIC_FIRST_ENTRY_THRESHOLD_GATE_ONLY',
        eligible:candidates.eligible.length,declined:candidates.declined.length,
        originalFrozenFirstEntryExecuted:false}),
      state9:Object.freeze({status:'SYNTHETIC_FORMAL_STATE_CHECKED_NOT_NATIVE_STATE9',
        nativeExecuted:false}),
      h235:h235,
      capital:Object.freeze({
        status:frozenV5?'ORIGINAL_V5_PYTHON_SYNTHETIC_SAB_PLUS_NO12_CASH_CHECK':
          'NO12_SYNTHETIC_CASH_MAX3_ONLY_NOT_FROZEN_CAPITAL_V5_SAB',
        startingCashYen:cashAfterExit.startingCashYen,
        endingCashYen:cashAfterExit.endingCashYen,
        managedPositions:cashAfterExit.positions.length,
        firstSellLatch:cashAfterExit.subsequentBuyProhibited,
        originalFrozenCapitalV5PythonExecutedOnSynthetic:!!frozenV5,
        nativeCapitalV5Executed:false}),
      exit:Object.freeze({
        status:exitResult===null?'NATIVE_EXIT_NOT_OBSERVED':
           'SYNTHETIC_SHARP_DROP_PROPOSAL_ONLY_NOT_STRUCTURAL_EXIT',
        syntheticExitProposals:exitResult?.exits.length??0,
        blockedCheckpoints:exitResult?.blocked.length??0,
        pendingControl:exitResult?.pending.length??0,
        originalStructuralExitExecuted:false})
    }),
    frozenV5SyntheticAllocation:frozenV5,
    preExitLedger:cashBeforeExit,
    exitProposal:exitResult,
    syntheticExitIntents:Object.freeze(syntheticExitIntents),
    finalLedger:cashAfterExit,
    nativeReadiness:Object.freeze({
      frozenSelectorExecuted:false,frozenFirstEntryExecuted:false,
      frozenState9Executed:false,originalH235R0Executed:false,
      frozenCapitalV5SabExecuted:false,
      originalFrozenCapitalV5PythonRunOnSynthetic:!!frozenV5,
      originalStructuralExitExecuted:false,
      realMarketKnownAtCertified:false,realBrokerFillsCertified:false,
      originalNo11EndToEndCertified:false
    }),
    frozenNo11Modified:false,productionReady:false,
    orderTransmission:false,automaticPromotion:false
  });
}
