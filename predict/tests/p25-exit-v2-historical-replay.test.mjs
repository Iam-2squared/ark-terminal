import test from 'node:test';
import assert from 'node:assert/strict';
import {classifyP25ExitV2ReplayDate,P25_EXIT_V2_HISTORICAL_REPLAY_SAFETY} from '../daytrade/phase57-p25-exit-v2-historical-replay.js';

test('historical replay labels development data as diagnostic only',()=>{const x=classifyP25ExitV2ReplayDate('2026-08-12');assert.equal(x.bucket,'DEVELOPMENT_REPLAY');assert.equal(x.formalOos,false);assert.equal(x.diagnosticOnly,true);});
test('historical replay labels legacy 27 window as diagnostic only',()=>{for(const d of ['2026-08-19','2026-08-20','2026-08-21','2026-08-24','2026-08-25']){const x=classifyP25ExitV2ReplayDate(d);assert.equal(x.bucket,'LEGACY27_DIAGNOSTIC_REPLAY');assert.equal(x.formalOos,false);}});
test('historical replay never consumes fresh holdout or enables trading/promotion',()=>{for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(P25_EXIT_V2_HISTORICAL_REPLAY_SAFETY[k],false);});
test('historical replay rejects malformed date',()=>assert.throws(()=>classifyP25ExitV2ReplayDate('08/19/2026'),/YYYY-MM-DD/));
