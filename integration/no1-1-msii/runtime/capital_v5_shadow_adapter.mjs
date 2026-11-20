/**
 * Read-only, SYNTHETIC-ONLY composition into byte-exact Frozen Capital v5.
 * Funding is sourced exclusively from the authenticated read-only snapshot.
 * No production signal source or exchange execution is certified by this module.
 */
import {inspectNo11CapitalFunding} from './capital_funding_bridge.mjs';

const NO11_FREEZE='10c94c92c4bd2a59a22744667fd0210252602df4';
const V5_CAPITAL_AUTHORITY='710656491be06235901b45c50a8b5cbd714ba4eb';
const BLOCK = reason => Object.freeze({status:'BLOCKED',blockers:[reason],
  orderAllowed:false,transmitted:false,productionReady:false});

export function prepareNo11SyntheticCapitalV5({snapshot,health,ownership,batch,now=new Date()}={}) {
  const funding=inspectNo11CapitalFunding({snapshot,health,ownership,now});
  if(funding.status!=='READ_ONLY_CAPITAL_PREVIEW'){
    return Object.freeze({status:'BLOCKED',blockers:funding.blockers,
      orderAllowed:false,transmitted:false,productionReady:false});
  }
  if(batch?.schemaId!=='ARK_NO11_SYNTHETIC_FROZEN_V5_BATCH_V1'||
     batch.evidenceMode!=='SYNTHETIC_OFFLINE_ONLY'){
    return BLOCK('REAL_FROZEN_NO11_ENTRY_EXPORT_NOT_AVAILABLE');
  }
  if(batch.afterFirstLegalSellFill!==false || batch.pendingBrokerOrders!==false ||
     batch.sessionVerified!==false){return BLOCK('SYNTHETIC_BATCH_FLAG_UNSAFE');}
  if(!Array.isArray(batch.preorderedCandidates)||
     !Array.isArray(batch.existingBands)||
     !Number.isInteger(batch.minute)||
     !batch.syntheticTrainingTables||typeof batch.syntheticTrainingTables!=='object'){
    return BLOCK('SYNTHETIC_BATCH_INCOMPLETE');
  }
  return Object.freeze({
    status:'SYNTHETIC_SHADOW_REQUEST_ONLY',
    request:{
      schemaId:'ARK_NO11_FROZEN_V5_SYNTHETIC_BRIDGE_V1',
      evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
      strategyFreezeCommit:NO11_FREEZE,
      capitalAuthorityCommit:V5_CAPITAL_AUTHORITY,
      afterFirstLegalSellFill:false,pendingBrokerOrders:false,sessionVerified:false,
      arkCapitalInputs:funding.arkCapitalInputs,
      externalSymbols:ownership.externalPositions.map(x=>x.symbol),
      arkManagedSymbols:ownership.arkManagedPositions.map(x=>x.symbol),
      existingBands:batch.existingBands,
      minute:batch.minute,
      preorderedCandidates:batch.preorderedCandidates,
      syntheticTrainingTables:batch.syntheticTrainingTables,
    },
    liveFeedTimestampCertified:false,orderAllowed:false,
    transmitted:false,productionReady:false
  });
}
