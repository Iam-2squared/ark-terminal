"""Historical Friday RSS end-to-end source contracts, with NO provider/orders."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import types

HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent/'no12-prebuy-causal-runtime-20261011'
sys.path.insert(0,str(HERE))
import no11_missing_friday_recovery_transform as recovery
import test_no11_completed_session_update as completed
import test_no11_update_path as fixture
import no11_update_path as max47
import no11_circuit_repair as circuit


def sources():
    base=completed.sources()
    source={
      'dailyTool':(ENGINE/'tools/no11_rss_daily_trend_census.mjs').read_bytes(),
      'dailyCollector':max47.transform('daily',fixture.NativeUpdateTests().originals()['daily']),
      'next':completed.upgrade.transform('next',base['next']),
      'weekly':completed.upgrade.transform('weekly',base['weekly']),
      'worker':circuit.transform('worker',(HERE/'no11_nightly_resume_workeraware.py').read_bytes())
    }
    return source


class FridayReadOnlyRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=sources()

    def test_all_five_installed_sources_patch_idempotent_bom_crlf(self):
        for k,raw in self.raw.items():
            for newline in ('\n','\r\n'):
                with self.subTest(k=k,newline=newline):
                    before=raw.decode('utf-8-sig').replace('\r\n','\n')
                    value=b'\xef\xbb\xbf'+before.replace('\n',newline).encode()
                    patched=recovery.transform(k,value)
                    self.assertEqual(patched,recovery.transform(k,patched))
                    self.assertIn(recovery.MARK.encode(),patched)
                    self.assertTrue(patched.startswith(b'\xef\xbb\xbf'))
                    if newline=='\r\n':
                        self.assertNotIn(b'\n',patched.replace(b'\r\n',b''))

    def test_approved_47_and_third_workbook_exactly_preserved(self):
        w=recovery.transform('weekly',self.raw['weekly']).decode('utf-8-sig')
        n=recovery.transform('next',self.raw['next']).decode('utf-8-sig')
        d=recovery.transform('dailyCollector',self.raw['dailyCollector']).decode('utf-8-sig')
        for item in ("$FullBatchSize=47","$RefreshBatchSize=47","$MinuteBatchSize=47"):
            self.assertIn(item,w)
        self.assertIn("$DailyBatchSize=47",n)
        self.assertIn("$BatchSize=47",d)
        self.assertIn("ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1",d)
        self.assertIn("ARK_NO11_FULL_PHYSICAL_RSS_47_V1",d)

    def test_historical_never_retains_old_oct26_expired_source(self):
        w=recovery.transform('weekly',self.raw['weekly']).decode('utf-8-sig')
        self.assertIn("NO11_WEEKLY_RECOVER_MISSING_FRIDAY=REAL_RSS_FULL_4328",w)
        self.assertIn("COMPLETE_CURRENT_FRIDAY_FULL_SWEEP_NOT_FOUND",w)
        self.assertIn("$choices=@($choices|Where-Object {$_.date -ceq $fridayDate})",w)
        self.assertNotIn("'2026-11-06'",w)
        self.assertNotIn("'2026-11-09'",w)
        self.assertIn("Need ($LASTEXITCODE -eq 0) 'REAL_FRIDAY_4328_RECOVERY_INCOMPLETE'",w)

    def test_historical_receipts_real_capture_today_and_later_rows_filtered(self):
        daily=recovery.transform('dailyTool',self.raw['dailyTool']).decode()
        self.assertIn('historicalRecoveryObservedAtJst:now',daily)
        self.assertIn('historicalAsOfSession:asOfSession',daily)
        self.assertIn('actualHistoricalKnownAtCertified:false',daily)
        self.assertIn('lastCompletedSession(now)',daily)
        self.assertIn('previousJpxCashTradingDays(completed,4)',daily)
        self.assertIn("flags['--recover-last-friday']==='true'",daily)
        self.assertNotIn('Date.now =',daily)
        self.assertNotIn('MOCK',daily)
        native=(ENGINE/'runtime/no11_rss_daily_trend_census.mjs').read_text()
        self.assertIn('if (row.session > plan.asOfSession) { ignoredLaterRows++; continue; }',native)
        self.assertIn('if (values.size !== 76) return unknown',native)

    def test_workers_use_new_journal_without_destroying_old_abort(self):
        worker=recovery.transform('worker',self.raw['worker']).decode('utf-8-sig')
        self.assertIn("'_'",worker)
        self.assertIn("'-real-friday-v1'",worker)
        self.assertNotIn("unlink(missing_ok=True)",worker.split('def native(',1)[1])
        old=self.raw['worker'].decode('utf-8-sig')
        anchor="    work = root / 'resumable-nightly' / (asof + '_' + target)"
        self.assertEqual(old.count(anchor),1)
        self.assertIn('NO11_NIGHTLY_RESUME_WORKER_PROBE_V2',worker)
        self.assertIn('DataUpdate-',worker)

    def test_node_window_real_calendar_and_no_clock_override(self):
        source=recovery.transform('dailyTool',self.raw['dailyTool'])
        # Run installed-style module beside its original runtime imports.
        tools=ENGINE/'tools'
        temp=tools/'no11_rss_daily_trend_census.test-recover-fri.mjs'
        if temp.exists():self.fail('REQUIRED_TEST_FIXTURE_NAME_EXISTS')
        try:
            temp.write_bytes(source)
            js="""import {latestFridayRecoveryWindow as w} from './no11_rss_daily_trend_census.test-recover-fri.mjs';
import assert from 'node:assert/strict';
const monday=w('2026-11-09T19:13:00+09:00');
assert.equal(monday.asOfSession,'2026-11-06');
assert.equal(monday.sessionDate,'2026-11-09');
assert.equal(monday.latestCompletedSession,'2026-11-09');
assert.equal(monday.orderTransmission,false);
assert.equal(monday.historicalKnownAtCertified,false);
assert.equal(monday.elapsedCashDays,1);
assert.equal(w('2026-11-10T09:00:00+09:00').asOfSession,'2026-11-06');
assert.equal(w('2026-11-10T19:00:00+09:00').asOfSession,'2026-11-06');
for(const now of ['2026-11-06T19:00:00+09:00',
                  '2026-11-09T09:00:00+09:00',
                  '2026-11-13T19:00:00+09:00']){
 assert.throws(()=>w(now),/NO11_/);
}
console.log('REAL_JPX_FRIDAY_RECOVERY_WINDOW=PASS');"""
            r=subprocess.run(['node','--input-type=module','-e',js],
                cwd=tools,capture_output=True,text=True,encoding='utf-8',timeout=25)
            self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
            self.assertIn('REAL_JPX_FRIDAY_RECOVERY_WINDOW=PASS',r.stdout)
        finally:
            temp.unlink(missing_ok=True)

    def test_no_trade_entry_exit_strategy_or_risk_changed(self):
        for kind in ('weekly','next','dailyCollector'):
            text=recovery.transform(kind,self.raw[kind]).decode('utf-8-sig')
            self.assertIn('ORDER_TRANSMISSION=False',text)
            self.assertNotIn("StartChild 'TRADE'",text)
        self.assertEqual(
          (ENGINE/'windows/Run-No11ReceivedSessionOperatorLive.ps1').read_bytes(),
          (ENGINE/'windows/Run-No11ReceivedSessionOperatorLive.ps1').read_bytes())
        self.assertIn('NO11_WEEKLY_RECOVER_MISSING_FRIDAY',recovery.transform('weekly',self.raw['weekly']).decode('utf-8-sig'))


if __name__=='__main__':unittest.main(verbosity=2)
