import fs from 'node:fs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a,v,i,x)=>{if(v.startsWith('--'))a.push([v.slice(2),x[i+1]]);return a},[]));
const manifest=JSON.parse(fs.readFileSync(args.manifest,'utf8'));
const measurement=JSON.parse(fs.readFileSync(args.measurement,'utf8'));
const rows=fs.readFileSync(args.snapshot,'utf8').trim().split(/\n+/).filter(Boolean).map(x=>JSON.parse(x));
const safetyKeys=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'];
const coverage=Number(measurement.matchedJpxSymbols ?? measurement.jpxMatched ?? measurement.marketCoverageSymbols ?? measurement.universeMatched ?? 0);
const selected=Number(measurement.selectedSymbols?.length ?? measurement.selectedCount ?? 0);
const unsafe=safetyKeys.filter(k=>manifest.safety?.[k]!==false);
const tracks=['entry','dynamic5m','exitV3','capitalAllocation'];
const badTracks=tracks.filter(k=>!String(manifest.tracks?.[k]?.status||'').startsWith('DURABLE_'));
const checks={
  marketCoverage3000Plus: coverage>=3000,
  snapshotPresent: rows.length>0,
  dynamicCandidatesPresent: selected>0,
  fourTracksDurable: badTracks.length===0,
  safetyAllFalse: unsafe.length===0,
  formalOosLocked: manifest.interpretation?.formalOos===false,
  promotionLocked: manifest.interpretation?.promotionEligible===false,
  winnerSelectionLocked: manifest.interpretation?.winnerSelectionAllowed===false,
};
const healthy=Object.values(checks).every(Boolean);
const report={schemaVersion:'phase57-p25-day-fresh-health-v1',generatedAt:new Date().toISOString(),status:healthy?'HEALTHY':'ALERT',durableKey:manifest.durableKey??null,sourceRunId:manifest.sourceRunId??null,metrics:{coverage,selectedCandidates:selected,snapshotRows:rows.length},checks,alerts:[...unsafe.map(k=>`SAFETY:${k}`),...badTracks.map(k=>`TRACK:${k}`),...(coverage<3000?[`COVERAGE:${coverage}`]:[]),...(rows.length===0?['SNAPSHOT_EMPTY']:[]),...(selected<=0?['NO_DYNAMIC_CANDIDATES']:[])],lineage:Object.fromEntries(tracks.map(k=>[k,manifest.tracks?.[k]?.ref??manifest.tracks?.[k]?.sourceRef??null])),safety:manifest.safety};
fs.mkdirSync(args.output,{recursive:true});
fs.writeFileSync(`${args.output}/health-report.json`,JSON.stringify(report,null,2)+'\n');
const icon=healthy?'✅':'🚨';
const text=[`${icon} Ark DAY — Fresh Pipeline ${healthy?'HEALTHY':'ALERT'}`,`Durable key: ${report.durableKey??'unknown'}`,`Coverage: ${coverage}`,`Dynamic candidates: ${selected}`,`Snapshot rows: ${rows.length}`,`4-Track durable: ${checks.fourTracksDurable?'OK':'FAIL'}`,`Safety: ${checks.safetyAllFalse?'ALL FALSE':'ALERT'}`,`Alerts: ${report.alerts.length?report.alerts.join(', '):'none'}`].join('\n');
fs.writeFileSync(`${args.output}/health-summary.txt`,text+'\n');
console.log(text);
if(!healthy) process.exitCode=2;
