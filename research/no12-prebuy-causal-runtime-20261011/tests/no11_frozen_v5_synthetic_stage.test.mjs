import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {runNo11SyntheticOriginalCapitalV5} from '../runtime/no11_frozen_v5_synthetic_stage.mjs';

const request=()=>({
 schemaId:'ARK_NO11_FROZEN_V5_SYNTHETIC_BRIDGE_V1',
 evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
 strategyFreezeCommit:'10c94c92c4bd2a59a22744667fd0210252602df4',
 capitalAuthorityCommit:'710656491be06235901b45c50a8b5cbd714ba4eb',
 researchInputProvenance:'EXPLICIT_SYNTHETIC_NOT_H235_RANK',
 productionReady:false,orderTransmission:false,
 afterFirstLegalSellFill:false,pendingBrokerOrders:false,sessionVerified:false,
 arkCapitalInputs:{cash:700000,equity:700000,exposure:0},
 externalSymbols:['408A.T'],arkManagedSymbols:[],existingBands:[],
 minute:576,
 preorderedCandidates:[{
   entry_id:'e1',brokerSymbol:'7203.T',rank:'S',
   ML:2.5,capital_score:2.2,raw_reference:'1000',block:'1'
 }],
 syntheticTrainingTables:{'1':{
   minute_counts:{'576':[1,0,2]},training_session_N:10,
   B_median:1.3,B_p75:1.4,minute_bucket:{'576':'synthetic'}
 }}
});
const eligible=()=>[{
 entryId:'e1',symbol:'7203.T',quantity:300,
 syntheticReferencePrice:1000
}];
const run=(req=request(),ranked=eligible())=>
 runNo11SyntheticOriginalCapitalV5({
   mode:'SYNTHETIC_OFFLINE_ONLY',
   request:req,rankedCandidates:ranked,startingCashYen:700000
 });

test('Actually execute byte-verified frozen Capital V5 Python S/A/B allocator with synthetic records',()=>{
 const r=run();
 assert.equal(r.status,'ORIGINAL_FROZEN_V5_PYTHON_SAB_COMPUTED_ON_EXPLICIT_SYNTHETIC_INPUT');
 assert.equal(r.fundedCount,1);
 assert.deepEqual(r.fundedEntries,[{entryId:'e1',quantity:300}]);
 assert.equal(r.allocatedDebitJpy,'300150.0000');
 assert.equal(r.remainingBuyingPowerJpy,'399850.0000');
 assert.equal(r.originalFrozenCapitalV5PythonExecutedOnSynthetic,true);
 assert.equal(r.nativeLiveFrozenCapitalV5Executed,false);
 assert.equal(r.originalFrozenR0H235Executed,false);
 assert.equal(r.orderTransmission,false);
 assert.equal(r.productionReady,false);
});

test('Reject absent H235-based native proof, changed ranking, unfunded lot, fake source or live mode',()=>{
 const a=request();a.researchInputProvenance='ORIGINAL_H235_PREBUY_FROZEN';
 assert.throws(()=>run(a),/SYNTHETIC_SOURCE_CONTRACT_INVALID/);
 const b=request();b.afterFirstLegalSellFill=true;
 assert.throws(()=>run(b),/SYNTHETIC_SOURCE_CONTRACT_INVALID/);
 const c=request();c.preorderedCandidates[0].entry_id='not-e1';
 assert.throws(()=>run(c),/UNBOUND_OR_INCONSISTENT_PREBUY_RANK/);
 const d=request();d.preorderedCandidates[0].brokerSymbol='408A.T';
 assert.throws(()=>run(d),/UNBOUND_OR_INCONSISTENT_PREBUY_RANK/);
 const e=eligible();e[0].quantity=100;
 assert.throws(()=>run(request(),e),/CASH_LIFECYCLE_QUANTITY_PARITY_REQUIRED/);
 assert.throws(()=>runNo11SyntheticOriginalCapitalV5({
   mode:'LIVE_TRADING',request:request(),
   rankedCandidates:eligible(),startingCashYen:700000
 }),/LIVE_OR_BROKER_EXECUTION_FORBIDDEN/);
});

test('Only the pinned offline Python Capital V5 bridge is used, no broker imports in new stage',()=>{
 const s=fs.readFileSync(new URL('../runtime/no11_frozen_v5_synthetic_stage.mjs',import.meta.url),'utf8');
 assert.match(s,/no11_capital_v5_crlf_safe_synthetic\.py/);
 const adapter=fs.readFileSync(new URL('../tools/no11_capital_v5_crlf_safe_synthetic.py',import.meta.url),'utf8');
 assert.match(adapter,/no11_capital_v5_shadow\.py/);
 assert.match(adapter,/ORIGINAL_GIT_BLOB/);
 assert.match(adapter,/canonical_git_blob/);
 assert.doesNotMatch(adapter,/RssStockOrder\s*\(|RssCancelOrder\s*\(|Excel\.Application|requests\.|urllib\.|socket\./);
 assert.match(s,/SYNTHETIC_OFFLINE_ONLY/);
 for(const disallowed of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
   /Excel.Application/,/\bfetch\s*\(/,/node:net/,/node:http/,
   /productionReady\s*:\s*true/,/orderTransmission\s*:\s*true/])
  assert.doesNotMatch(s,disallowed);
});
