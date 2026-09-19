import fs from 'node:fs';
import zlib from 'node:zlib';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {replayFrozenV5Bar5,observeBar5Prefix} from './lib/phase57-long-exit-v5-bar5-adapter.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
const base='docs/evidence/phase57-long-exit-v5-fast-track';
const read=p=>JSON.parse(fs.readFileSync(p));
const countBy=(rows,key)=>Object.fromEntries([...new Set(rows.map(key))].sort().map(k=>[k,rows.filter(r=>key(r)===k).length]));
const rate=(n,d)=>({count:n,denominator:d,ratePct:d?100*n/d:null});
export function diagnose(out=base){
 const c=read(`${base}/contract.json`);
 for(const [p,h] of Object.entries(c.pins))assert.equal(sha(fs.readFileSync(p)),h,p);
 const prior=read('docs/evidence/phase57-long-exit-v345-paired/contract.json');
 for(const [p,h] of Object.entries(prior.sourcePins))assert.equal(sha(fs.readFileSync(p)),h,p);
 const ledger=read(c.ledgerPath),raw=zlib.gunzipSync(fs.readFileSync(c.pathArtifact)),d=JSON.parse(raw);
 assert.equal(sha(raw),c.pathUncompressedSHA);assert.equal(ledger.length,277);assert.equal(d.events.length,277);
 const byId=new Map(d.events.map(e=>[e.selectorEventId,e]));assert.equal(byId.size,277);
 const records=ledger.map(identity=>{
  const e=byId.get(identity.selectorEventId);for(const [k,v] of Object.entries(identity))assert.deepEqual(e[k],v);
  assert.equal(e.direction,'LONG');assert.equal(e.v4,null);
  // Never fabricate the prerequisite v4 outcome, even for adverse-only paths.
  const replay=replayFrozenV5Bar5({direction:'LONG',causalEligible:false,v4:null});
  const prefix=observeBar5Prefix(e);
  return {...identity,prefix,replay,strict30mAvailable:e.horizons['30'].available,strict30mGrossClosePct:e.horizons['30'].available?e.horizons['30'].returnPct:null,fixedPathAvailable:e.horizons.FIXED_12.available};
 });
 const adverse=records.filter(r=>r.prefix.firstAdverse===true),known=records.filter(r=>r.prefix.firstAdverse!==null);
 const reclaimed=adverse.filter(r=>r.prefix.state==='RECLAIM_OBSERVED_REQUIRES_V4'),noReclaim=adverse.filter(r=>r.prefix.state==='NO_RECLAIM_THROUGH_BAR5_OBSERVED');
 const recovered30=reclaimed.filter(r=>r.strict30mAvailable),failed30=noReclaim.filter(r=>r.strict30mAvailable);
 const metrics=Object.fromEntries(['netSum','averageTrade','medianTrade','winRate','profitFactor','worstTrade','maxDrawdown','maeDistribution','badSide5','maeMinus10CohortFinalLoss','downsideTailReductionVsFixed','mfeMedian','mfeCapture','giveback','mfe3FinalNet','mfe5FinalNet','prematureWinnerExit','savedWinners','lostWinners','recoveredFinalWinnerRate','nonRecoveredFinalOutcome','falseRecovery','falseDefensiveExit','top1Contribution','top3Contribution','top5Contribution','symbolConcentration','sessionConcentration'].map(k=>[k,null]));
 const result={status:'V5_LONG_MEASUREMENT_BLOCKED',runtimeStatus:'V5_RUNTIME_SEMANTICS_BLOCKED',adapterStatus:'BAR5_SELECTED_SIMULATOR_MECHANICAL_PARITY_PASS',onlineStandaloneRuntimeResolved:false,role:c.role,contractSHA:sha(fs.readFileSync(`${base}/contract.json`)),entryIdentitySHA:c.pins[c.ledgerPath],entries:277,pairedEligibleN:0,blocked277Reason:'CAUSAL_V4_CONTINUATION_UNAVAILABLE',bar5VsBar6Resolved:true,existingInsufficientV4Fallback:'NO_DEFINED_REPLACEMENT; ORIGINAL_SIMULATOR_RETURNS_NULL_BEFORE_STATE_LOGIC',rawMarketPrefixDiagnostic:{notFullV5StateReplay:true,firstBarObserved:known.length,firstBarAdverse:rate(adverse.length,known.length),states:countBy(records,r=>r.prefix.state),unknownReasons:countBy(records.filter(r=>r.prefix.state==='UNKNOWN'),r=>r.prefix.reason),defensiveObserved:adverse.length,reclaimObserved:reclaimed.length,noReclaimThroughBar5Observed:noReclaim.length,reclaimAmongAllObservedAdverseLowerBound:rate(reclaimed.length,adverse.length),reclaimAmongResolvedAdverse:rate(reclaimed.length,reclaimed.length+noReclaim.length),reclaimBars:countBy(reclaimed,r=>r.prefix.reclaimBar),observedReclaimThenNegativeStrict30mClose:rate(recovered30.filter(r=>r.strict30mGrossClosePct<0).length,recovered30.length),observedNoReclaimThenNonnegativeStrict30mClose:rate(failed30.filter(r=>r.strict30mGrossClosePct>=0).length,failed30.length),actualV5RecoveredCount:null,actualV5ForcedExitCount:null},arms:{FIXED:{eligibleN:0,metrics},V5_BAR5:{eligibleN:0,metrics}},fixedStandalonePathAvailability:records.filter(r=>r.fixedPathAvailable).length,limitations:['All76 sessions are direct Entry Development IN_SAMPLE','Raw path prefixes cannot replace truncated causal v4 management traces','Reclaim proxy is not realized final winner or false recovery measurement','Session-end/auction fallback is not invented','V5_LONG_MINIMAL_ADAPTATION_REQUIRED cannot be inferred without full v5 performance'],nextAction:'Explicitly specify a standalone continuation for LONG as a new Development contract; not a mechanical adapter and not authorized by a measured MINIMAL_ADAPTATION_REQUIRED verdict here. Keep v3/v4 analog construction stopped.',counts:{entryPredictions:0,entryChanges:0,selectorChanges:0,v3Replay:0,v4Replay:0,v5FullReplay:0,analogPoolsBuilt:0,exitFit:0,thresholdSweep:0,providerRequests:0,freshAccess:0,oosAccess:0,freshBudgetConsumption:0,shortEvaluation:0,forwardFill:0,interpolation:0,futureSubstitution:0},safety:c.safety};
 fs.mkdirSync(out,{recursive:true});for(const [name,value] of [['summary.json',result],['prefix-ledger.json',records]])fs.writeFileSync(`${out}/${name}`,JSON.stringify(value,null,2)+'\n',{flag:'wx'});
 return result;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)console.log(JSON.stringify(diagnose(process.argv[2]??base).rawMarketPrefixDiagnostic));
