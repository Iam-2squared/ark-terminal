import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildP253SessionIntegrityLedger,
  PHASE57_P25_3A_SAFETY,
} from '../daytrade/phase57-p25-3a-session-integrity-ledger.js';

const safety=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});
function artifact(sessionDate,{target=50,collected=50,ready=true}={}){
  const sourceBySymbol=Object.fromEntries(Array.from({length:collected},(_,i)=>[`${1000+i}.T`,{provider:'TEST'}]));
  return {
    phase:'57.p25.2j.routine-nonrss-5m-source-cli',
    status:ready?'ROUTINE_NONRSS_5M_SESSION_READY':'BLOCKED_ROUTINE_NONRSS_5M_SESSION',
    expectedSessionDates:[sessionDate],
    sessions:ready?[{sessionDate}]:[],
    collection:{
      ready,sessionDate,targetSymbolCount:target,collectedSymbolCount:collected,failedSymbolCount:target-collected,sourceBySymbol,
    },
    methodology:{routineDailyMarketSpeedRequired:false,boardOrTickUsed:false},
    safety,
  };
}

test('whole-union ready capture is a confirmed trading session',()=>{
  const result=buildP253SessionIntegrityLedger({captureArtifacts:[artifact('2026-08-19')]});
  assert.equal(result.status,'SESSION_INTEGRITY_CLASSIFIED');
  assert.deepEqual(result.readyTradingSessionDates,['2026-08-19']);
  assert.deepEqual(result.confirmedTradingSessionDates,['2026-08-19']);
  assert.deepEqual(result.recommendedExpectedSessionDatesForP252H,['2026-08-19']);
});

test('partial valid bars prove the market traded and the blocked day stays in Days-to-400 denominator',()=>{
  const result=buildP253SessionIntegrityLedger({captureArtifacts:[artifact('2026-08-20',{collected:17,ready:false})]});
  assert.deepEqual(result.blockedConfirmedTradingSessionDates,['2026-08-20']);
  assert.deepEqual(result.recommendedExpectedSessionDatesForP252H,['2026-08-20']);
  assert.equal(result.rows[0].classification,'BLOCKED_CONFIRMED_TRADING_SESSION');
  assert.equal(result.methodology.blockedConfirmedTradingDayCountsAsZeroEntryOperationalDay,true);
});

test('zero valid symbols cannot be silently called a holiday and remains in conservative pace',()=>{
  const result=buildP253SessionIntegrityLedger({captureArtifacts:[artifact('2026-09-21',{collected:0,ready:false})]});
  assert.equal(result.status,'SESSION_INTEGRITY_HAS_UNRESOLVED_DATES');
  assert.deepEqual(result.unresolvedSessionDates,['2026-09-21']);
  assert.deepEqual(result.optimisticConfirmedTradingSessionDates,[]);
  assert.deepEqual(result.conservativeExpectedTradingSessionDates,['2026-09-21']);
  assert.deepEqual(result.recommendedExpectedSessionDatesForP252H,['2026-09-21']);
});

test('independently evidenced non-trading date is excluded only when it has no valid bars',()=>{
  const closed=artifact('2026-09-21',{collected:0,ready:false});
  const result=buildP253SessionIntegrityLedger({
    captureArtifacts:[closed],
    verifiedNonTradingSessions:[{sessionDate:'2026-09-21',evidenceId:'JPX_CALENDAR_RECORD_2026-09-21',source:'PINNED_JPX_CALENDAR'}],
  });
  assert.deepEqual(result.verifiedNonTradingSessionDates,['2026-09-21']);
  assert.deepEqual(result.recommendedExpectedSessionDatesForP252H,[]);
  assert.equal(result.rows[0].classification,'VERIFIED_NON_TRADING_SESSION');
  assert.throws(()=>buildP253SessionIntegrityLedger({
    captureArtifacts:[artifact('2026-09-21')],
    verifiedNonTradingSessions:[{sessionDate:'2026-09-21',evidenceId:'BAD_CONFLICT'}],
  }),/conflicts with valid 5m bars/);
});

test('duplicate session artifacts and unsafe capture artifacts fail closed',()=>{
  const row=artifact('2026-08-19');
  assert.throws(()=>buildP253SessionIntegrityLedger({captureArtifacts:[row,row]}),/duplicate P25\.3A capture artifact session/);
  const unsafe=structuredClone(row);
  unsafe.safety.executionAllowed=true;
  assert.throws(()=>buildP253SessionIntegrityLedger({captureArtifacts:[unsafe]}),/executionAllowed must be false/);
});

test('all execution and promotion surfaces remain disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(PHASE57_P25_3A_SAFETY[key],false,key);
});
