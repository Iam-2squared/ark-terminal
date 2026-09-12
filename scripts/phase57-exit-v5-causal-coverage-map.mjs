import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {buildP252PinnedHistoricalSessions,PHASE57_P25_2K_POLICY} from '../predict/daytrade/phase57-p25-2k-pinned-history-bridge.js';
import {buildP25DataDrivenExitAnalogPool} from '../predict/daytrade/phase57-p25-data-driven-exit.js';

const hash=b=>createHash('sha256').update(b).digest('hex');
const snapshotPath=process.env.ANALOG_SNAPSHOT;
assert(snapshotPath&&fs.existsSync(snapshotPath),'ANALOG_SNAPSHOT_REQUIRED');
const minimum=Number(process.env.MINIMUM_CAUSAL_NEIGHBORS??30);
assert(Number.isInteger(minimum)&&minimum>0,'INVALID_MINIMUM');

const bytes=fs.readFileSync(snapshotPath);
assert.equal(hash(bytes),PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,'ANALOG_SNAPSHOT_SHA_MISMATCH');
const history=buildP252PinnedHistoricalSessions({snapshot:JSON.parse(bytes),snapshotSha256:hash(bytes)});
const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:history.sessions});

const allDates=[...new Set(analogPool.map(x=>x.sessionDate).filter(Boolean))].sort();
const jstOpenMs=date=>Date.parse(`${date}T09:00:00+09:00`);
const coverage=allDates.map(sessionDate=>({
  sessionDate,
  causalAnalogsAtOpen:analogPool.filter(a=>a.sessionDate<sessionDate&&Date.parse(a.fullyRealizedAt)<jstOpenMs(sessionDate)).length,
}));
const firstEligible=coverage.find(x=>x.causalAnalogsAtOpen>=minimum)??null;
const latest=coverage.at(-1)??null;
const report={
  schemaVersion:1,
  schemaId:'PHASE57_EXIT_V5_CAUSAL_COVERAGE_MAP_V1',
  generatedFrom:'PINNED_ANALOG_SNAPSHOT_ONLY_NO_EXIT_OUTCOMES',
  minimumCausalNeighbors:minimum,
  analogPoolCount:analogPool.length,
  firstSessionDateWithMinimumAt0900Jst:firstEligible,
  latestObservedCoverage:latest,
  methodology:{
    outcomeAccess:false,
    futureLabelAccess:false,
    targetSessionMarketDataAccess:false,
    criterion:'count frozen analog rows with analog.sessionDate < target sessionDate and fullyRealizedAt < 09:00 JST target session open',
    purpose:'prevent wasting unseen blocks that cannot support frozen v4 causal evaluation',
  },
  safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false},
};
fs.mkdirSync('artifacts/phase57-exit-v5-causal-coverage',{recursive:true});
fs.writeFileSync('artifacts/phase57-exit-v5-causal-coverage/report.json',JSON.stringify(report,null,2)+'\n');
console.log('PHASE57_EXIT_V5_CAUSAL_COVERAGE='+JSON.stringify(report));
