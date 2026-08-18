import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildP253EvidenceLineageManifest,
  PHASE57_P25_3B_SAFETY,
} from '../daytrade/phase57-p25-3b-evidence-lineage-manifest.js';

const historyPack={
  phase:'57.p25.2k.pinned-history-bridge-cli',
  status:'P25_2_PINNED_HISTORY_PACK_READY',
  canonicalSourceRunId:31785422471,
  canonicalSnapshotSha256:'10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a',
  sessionCount:190,
  perSymbolSessionCount:{'7203.T':38,'6758.T':38,'9984.T':38,'8306.T':38,'8035.T':38},
  methodology:{freshHoldoutConsumed:false},
};
function capture(sessionDate,shaChar,ready=true){
  return {
    artifactSha256:shaChar.repeat(64),
    artifactPath:`${sessionDate}.json`,
    artifact:{
      phase:'57.p25.2j.routine-nonrss-5m-source-cli',
      expectedSessionDates:[sessionDate],
      collection:{sessionDate,ready,targetSymbolCount:67},
      sessions:ready?[{universeRecord:{sourceSnapshotFingerprint:`universe-${sessionDate}`}}]:[],
    },
  };
}
function integrity(rows){
  const confirmed=rows.filter(x=>x.classification!=='VERIFIED_NON_TRADING_SESSION'&&!x.classification.startsWith('UNRESOLVED')).map(x=>x.sessionDate);
  const unresolved=rows.filter(x=>x.classification.startsWith('UNRESOLVED')).map(x=>x.sessionDate);
  const closed=rows.filter(x=>x.classification==='VERIFIED_NON_TRADING_SESSION').map(x=>x.sessionDate);
  return {
    phase:'57.p25.3a.session-integrity-ledger',
    rows,
    confirmedTradingSessionDates:confirmed,
    unresolvedSessionDates:unresolved,
    verifiedNonTradingSessionDates:closed,
    recommendedExpectedSessionDatesForP252H:[...confirmed,...unresolved].sort(),
    methodology:{outerOosPerformanceUsedForClassification:false},
  };
}

test('lineage chain is chronological, deterministic and anchored to pinned P24 history',()=>{
  const captures=[capture('2026-08-20','b'),capture('2026-08-19','a')];
  const rows=[
    {sessionDate:'2026-08-19',classification:'READY_CONFIRMED_TRADING_SESSION',artifactSha256:'a'.repeat(64)},
    {sessionDate:'2026-08-20',classification:'BLOCKED_CONFIRMED_TRADING_SESSION',artifactSha256:'b'.repeat(64)},
  ];
  const first=buildP253EvidenceLineageManifest({historyPack,captureArtifacts:captures,sessionIntegrityLedger:integrity(rows)});
  const second=buildP253EvidenceLineageManifest({historyPack,captureArtifacts:[...captures].reverse(),sessionIntegrityLedger:integrity([...rows].reverse())});
  assert.equal(first.status,'P25_3_EVIDENCE_LINEAGE_MANIFEST_READY');
  assert.deepEqual(first.nodes.map(x=>x.sessionDate),['2026-08-19','2026-08-20']);
  assert.equal(first.manifestHeadSha256,second.manifestHeadSha256);
  assert.equal(first.historyIdentity.canonicalSourceRunId,31785422471);
  assert.match(first.chainSeedSha256,/^[a-f0-9]{64}$/);
  assert.equal(first.nodes[1].previousChainSha256,first.nodes[0].chainSha256);
});

test('capture SHA must match the integrity ledger and duplicate sessions fail closed',()=>{
  const one=capture('2026-08-19','a');
  const rows=[{sessionDate:'2026-08-19',classification:'READY_CONFIRMED_TRADING_SESSION',artifactSha256:'b'.repeat(64)}];
  assert.throws(()=>buildP253EvidenceLineageManifest({historyPack,captureArtifacts:[one],sessionIntegrityLedger:integrity(rows)}),/capture SHA disagrees/);
  const matching=[{sessionDate:'2026-08-19',classification:'READY_CONFIRMED_TRADING_SESSION',artifactSha256:'a'.repeat(64)}];
  assert.throws(()=>buildP253EvidenceLineageManifest({historyPack,captureArtifacts:[one,one],sessionIntegrityLedger:integrity(matching)}),/duplicate P25\.3B capture session/);
});

test('lineage identity rejects outer-OOS performance fields',()=>{
  const one=capture('2026-08-19','a');
  one.artifact.netReturnPct=12.3;
  const rows=[{sessionDate:'2026-08-19',classification:'READY_CONFIRMED_TRADING_SESSION',artifactSha256:'a'.repeat(64)}];
  assert.throws(()=>buildP253EvidenceLineageManifest({historyPack,captureArtifacts:[one],sessionIntegrityLedger:integrity(rows)}),/forbidden performance identity fields/);
});

test('pinned history identity cannot drift',()=>{
  const bad={...historyPack,canonicalSnapshotSha256:'0'.repeat(64)};
  assert.throws(()=>buildP253EvidenceLineageManifest({historyPack:bad,captureArtifacts:[],sessionIntegrityLedger:integrity([])}),/canonical history snapshot SHA mismatch/);
});

test('all execution and promotion surfaces remain disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(PHASE57_P25_3B_SAFETY[key],false,key);
});
