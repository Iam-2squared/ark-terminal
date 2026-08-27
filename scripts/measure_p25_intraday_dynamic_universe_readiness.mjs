import fs from 'node:fs';
import path from 'node:path';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const write=(file,value)=>{fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n','utf8');};

export const SAFETY=Object.freeze({
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

function sessionRows(capturesDir){
  const files=fs.readdirSync(capturesDir).filter(x=>x.endsWith('.json')).sort();
  const rows=[];
  for(const file of files){
    const capture=read(path.join(capturesDir,file));
    for(const session of capture?.sessions??[]){
      const bars=session?.sessionBarsBySymbol??{};
      const symbols=Object.keys(bars);
      const barCounts=symbols.map(s=>Array.isArray(bars[s])?bars[s].length:0);
      const marketWideSnapshots=Array.isArray(session?.marketWideSnapshots)?session.marketWideSnapshots:[];
      const snapshotsWithEntries=marketWideSnapshots.filter(x=>Array.isArray(x?.entries)&&x.entries.length>0);
      rows.push({
        sessionDate:String(session?.sessionDate??session?.universeRecord?.sessionDate??''),
        capturedSymbolCount:symbols.length,
        minBars:barCounts.length?Math.min(...barCounts):0,
        maxBars:barCounts.length?Math.max(...barCounts):0,
        averageBars:barCounts.length?barCounts.reduce((a,b)=>a+b,0)/barCounts.length:0,
        marketWideSnapshotCount:marketWideSnapshots.length,
        marketWideSnapshotsWithEntries:snapshotsWithEntries.length,
        maximumMarketWideEntryCount:snapshotsWithEntries.length?Math.max(...snapshotsWithEntries.map(x=>x.entries.length)):0,
      });
    }
  }
  return rows.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
}

export function buildReadinessMeasurement({capturesDir}){
  const sessions=sessionRows(capturesDir);
  if(!sessions.length)throw new Error('no capture sessions found');
  const maxCapturedSymbols=Math.max(...sessions.map(x=>x.capturedSymbolCount));
  const totalMarketWideSnapshots=sessions.reduce((a,b)=>a+b.marketWideSnapshotCount,0);
  const maxMarketWideEntries=Math.max(...sessions.map(x=>x.maximumMarketWideEntryCount));
  const marketWidePointInTimeAvailable=totalMarketWideSnapshots>0&&maxMarketWideEntries>maxCapturedSymbols;
  const performanceMeasurementAllowed=marketWidePointInTimeAvailable;
  return {
    schemaVersion:1,
    phase:'57.p25.intraday-dynamic-universe.measurement-readiness',
    status:performanceMeasurementAllowed?'READY_FOR_MARKET_WIDE_INTRADAY_MEASUREMENT':'BLOCKED_MARKET_WIDE_POINT_IN_TIME_DATA_MISSING',
    evidenceClass:'HISTORICAL_INPUT_COVERAGE_AUDIT',
    sessions,
    summary:{
      sessionCount:sessions.length,
      maxCapturedSymbols,
      minCapturedSymbols:Math.min(...sessions.map(x=>x.capturedSymbolCount)),
      totalMarketWideSnapshots,
      maxMarketWideEntries,
      marketWidePointInTimeAvailable,
      performanceMeasurementAllowed,
    },
    interpretation:{
      frozenD50PerformanceComparable:true,
      marketWide5mPerformanceComparable:performanceMeasurementAllowed,
      portfolioReturnForIntradayDynamic5mAvailable:false,
      winnerSelectionAllowed:false,
      formalOos:false,
      promotionEligible:false,
      note:performanceMeasurementAllowed
        ?'Market-wide point-in-time snapshots are available; proceed to causal 5m candidate replay.'
        :'Existing archive contains only bounded captured symbols, not market-wide point-in-time screener snapshots. Do not fabricate JPX-wide return/PF/MaxDD from this archive.',
    },
    requiredNextEvidence:{
      cadenceMinutes:5,
      eachSnapshotNeedsPointInTimeEntries:true,
      desiredScope:'JPX_DOMESTIC_PRIME_STANDARD_GROWTH',
      futureOutcomeFieldsForbidden:true,
      capturedFields:['symbol','sector','market','currentPrice','volume','volumeRatio','dailyChangePercent','atrPercent','discoveryScore','technicalScore','confidence','qualityScore','scannedAt','status'],
    },
    safety:SAFETY,
  };
}

const capturesDir=arg('--captures-dir');
const outputPath=arg('--output','tmp/intraday-dynamic-universe-readiness.json');
if(capturesDir){
  const result=buildReadinessMeasurement({capturesDir});
  write(outputPath,result);
  console.log(JSON.stringify(result,null,2));
}
