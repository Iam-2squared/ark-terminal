import fs from 'node:fs';
import path from 'node:path';
import {PHASE57_US_CROSS_MARKET_POLICY_SHA256,PHASE57_US_CROSS_MARKET_SAFETY,assertPhase57UsCrossMarketSafety} from '../predict/daytrade/phase57-us-cross-market-policy.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const universePath=arg('--universe'),snapshotPath=arg('--snapshot'),output=arg('--output','tmp/us-marketwide-measurement.json');
if(!universePath||!snapshotPath)throw new Error('usage: --universe frozen.json --snapshot quotes.json --output file');
assertPhase57UsCrossMarketSafety();
const u=JSON.parse(fs.readFileSync(universePath,'utf8')),raw=JSON.parse(fs.readFileSync(snapshotPath,'utf8'));
const frozen=u.status==='US_UNIVERSE_FROZEN';
const collection=u.status==='US_FREE_COLLECTION_UNIVERSE';
if(!frozen&&!collection)throw new Error(`US universe contract mismatch: ${u.status}`);
if(frozen&&u.policySha256!==PHASE57_US_CROSS_MARKET_POLICY_SHA256)throw new Error('US frozen universe policy hash mismatch');
const envelope=Array.isArray(raw)?null:raw;
const rows=Array.isArray(raw)?raw:raw.rows;
if(!Array.isArray(rows))throw new Error('US snapshot must be array or provider envelope');
const freeNonRealtime=envelope?.plan==='FREE'&&envelope?.freshRealtime!==true;
const diagnostic5m=freeNonRealtime&&envelope?.researchIntraday5m===true&&envelope?.feedClassification==='FREE_INTRADAY_5M_DIAGNOSTIC';
if(freeNonRealtime&&!diagnostic5m)throw new Error('US Fresh blocked: free provider data is not real-time; preserve as diagnostic/EOD only');
const sampleDiagnostic=diagnostic5m&&envelope?.sampleDiagnostic===true&&envelope?.marketwide===false;
const allowed=new Set((u.universe??[]).map(x=>String(x.symbol??'').toUpperCase()));
const valid=rows.filter(x=>allowed.has(String(x.symbol??'').toUpperCase())&&Number.isFinite(Number(x.currentPrice))&&Number(x.currentPrice)>0&&Number.isFinite(Number(x.volume))&&Number(x.volume)>=0);
const denominator=sampleDiagnostic?Number(envelope?.sampleSize??0):Number(u.eligibleCount??allowed.size);
const coveragePct=denominator?100*valid.length/denominator:0;
const minCoverage=sampleDiagnostic?40:(diagnostic5m?60:80),minRows=sampleDiagnostic?120:500;
if(valid.length<minRows||coveragePct<minCoverage)throw new Error(`US ${sampleDiagnostic?'sample':'marketwide'} snapshot incomplete ${valid.length}/${denominator} (${coveragePct.toFixed(2)}%)`);
const score=x=>{const ch=Math.abs(Number(x.changePct??0)),vr=Math.max(0,Number(x.volumeRatio??1)),turn=Math.max(0,Number(x.dollarVolume??0));return 0.45*Math.min(1,ch/5)+0.30*Math.min(1,vr/3)+0.25*Math.min(1,Math.log10(1+turn)/9);};
const ranked=valid.map(x=>({...x,usOpportunityScore:score(x)})).sort((a,b)=>b.usOpportunityScore-a.usOpportunityScore||String(a.symbol).localeCompare(String(b.symbol)));
const selected=ranked.slice(0,Math.min(50,ranked.length)),selectedV2=ranked.filter((x,i)=>i<80).sort((a,b)=>{const aq=Math.min(1,Number(a.volumeRatio??1)/3),bq=Math.min(1,Number(b.volumeRatio??1)/3);return (b.usOpportunityScore*0.65+bq*0.35)-(a.usOpportunityScore*0.65+aq*0.35);}).slice(0,Math.min(30,ranked.length));
const payload={
  schemaVersion:4,phase:'57.us-cross-market.intraday-5m',
  status:sampleDiagnostic?'US_SAMPLED_5M_DIAGNOSTIC_MEASURED':(diagnostic5m?'US_MARKETWIDE_5M_DIAGNOSTIC_MEASURED':'US_MARKETWIDE_5M_MEASURED'),
  sessionDate:u.sessionDate??envelope?.sessionDate??null,observedAt:new Date().toISOString(),inputSymbols:valid.length,coveragePct,
  sampleDiagnostic,marketwide:!sampleDiagnostic,sampleSize:sampleDiagnostic?denominator:null,sampleMethod:sampleDiagnostic?envelope?.sampleMethod:null,
  selectedSymbols:selected.length,selectedV2Symbols:selectedV2.length,selected,selectedV2,
  provider:envelope?{name:envelope.provider,plan:envelope.plan,feedClassification:envelope.feedClassification,sourceContract:envelope.sourceContract,sourceObservedAt:envelope.observedAt,rawDigest:envelope.rawDigest,medianAgeSeconds:envelope.medianAgeSeconds}:null,
  classification:{crossMarketProspective:!diagnostic5m,diagnosticIntraday5m:diagnostic5m,sampledDiagnostic:sampleDiagnostic,fullFresh:false,jpxOosSubstitute:false,formalOos:false,promotionEligible:false},
  methodology:{universeFrozenBeforeOpen:frozen,rawCollectionUniverse:collection,pointInTimeOnly:!collection,futureOutcomeUsed:false,missingSymbolsNeverFabricated:true,selectionScoringIsDiagnosticSubstrate:true,marketwideSelectionEquivalent:false},
  policySha256:PHASE57_US_CROSS_MARKET_POLICY_SHA256,safety:PHASE57_US_CROSS_MARKET_SAFETY,
};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,inputSymbols:payload.inputSymbols,coveragePct:Number(coveragePct.toFixed(2)),sampleDiagnostic,v1:selected.length,v2:selectedV2.length},null,2));
