"""Reproduce broken installed PowerShell literal and audit one-file recovery.

All scenarios are synthetic, offline, zero broker/Excel/market operations.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import no11_nightly_resume as n
import no11_missing_friday_recovery_transform as transform
import test_no11_missing_friday_recovery as fixture
import install_no11_historical_calendar_pathfix as hotfix


class CalendarPathfixTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='ark-no11-friday-path-')
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.store=root/'store'
        (self.store/'oneclick').mkdir(parents=True)
        self.engine=root/'engine'
        (self.engine/'windows').mkdir(parents=True)
        (self.engine/'tools').mkdir(parents=True)
        self.daily_root=root/'daily-cycle'
        self.daily_root.mkdir()
        self.ui=self.store/'oneclick/Start-No11OneClick.ps1'
        self.ui.write_bytes(b'EXISTING WHITE GUI FOREVER\n')
        self.trade=self.engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1'
        self.trade.write_bytes(b'EXISTING BUY SELL EXIT FROZEN\n')
        self.settings=self.store/'settings.json'
        self.settings.write_bytes(n.encode({
          'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
          'normalMaxPositions':3,'sameDayApprovalRequired':True,
          'automaticOrderAuthorization':False,'orderTransmission':False}))
        original=fixture.sources()
        new_good=transform.transform('next',original['next'])
        good=new_good.decode('utf-8-sig').replace('\r\n','\n')
        self.assertEqual(good.count(hotfix.CORRECT),1)
        bad=good.replace(hotfix.CORRECT,hotfix.BROKEN)
        self.assertEqual(bad.count(hotfix.BROKEN),1)
        self.child=self.engine/'windows/Prepare-No11NextSessionNightlyReadOnly.ps1'
        self.child.write_bytes(bad.encode('utf-8'))
        self.engine_sources={}
        for kind,rel in (
            ('dailyTool','tools/no11_rss_daily_trend_census.mjs'),
            ('dailyCollector','windows/Run-No11RssDailyTrendCensusReadOnly.ps1'),
            ('weekly','windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1')):
            target=self.engine/rel
            target.write_bytes(transform.transform(kind,original[kind]))
            self.engine_sources[kind]=target
        self.engine_sources['next']=self.child
        self.worker_dir=self.store/'real-friday-worker-old';self.worker_dir.mkdir()
        self.worker=self.worker_dir/'no11_nightly_resume_workeraware.py'
        self.worker.write_bytes(transform.transform('worker',original['worker']))
        self.validator=self.worker_dir/'no11_selection_status.py'
        self.validator.write_bytes((HERE/'no11_selection_status.py').read_bytes())
        self.binding=self.store/'automatic-inputs.json'
        b={'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
           'orderTransmission':False,
           'manualPriceInputRequired':False,'manualEvidenceRequired':False,
           'engine':str(self.engine),'python':sys.executable,
           'nightlyResumeTool':str(self.worker),
           'nightlyResumeToolSha256':n.digest(self.worker.read_bytes()),
           'nightlyResumeValidatorSha256':n.digest(self.validator.read_bytes()),
           'dailyCycleRoot':str(self.daily_root),
           'liveTradeConfig':'USER_FROZEN'}
        self.binding.write_bytes(n.encode(b))
        prior={
          'schemaId':n.SCHEMA,'kind':'ARK_NO11_MISSING_FRIDAY_REAL_RSS_RECOVERY_RELEASE_V1',
          'orderTransmission':False,'phase':'COMPLETE',
          'engineUpdates':{
             kind:{'path':str(path),'afterSha256':n.digest(path.read_bytes())}
             for kind,path in self.engine_sources.items()
          },
          'workerSha256':n.digest(self.worker.read_bytes())
        }
        self.previous_journal=self.store/'missing-friday-real-rss-transaction.json'
        n.atomic(self.previous_journal,prior)
        self.initial={p:p.read_bytes() for p in (
          self.child,self.worker,self.validator,self.binding,self.settings,self.ui,self.trade,
          self.previous_journal,*self.engine_sources.values())}
        # The previous broken read-only attempt and its receipt log stay intact.
        self.oldwork=self.daily_root/'resumable-nightly/2026-11-09_2026-11-10-real-friday-v1'
        self.oldwork.mkdir(parents=True)
        self.oldlog=self.oldwork/'capture-original.log'
        self.oldlog.write_bytes(b'HISTORICAL_WINDOW_MISSING, not a successful capture\n')

    def test_exploit_reproduction_and_one_literal_fix(self):
        before=self.child.read_bytes()
        self.assertIn(b'tools\no11_rss_daily',before)
        after=hotfix.patch_next(before)
        self.assertIn(b'tools\\no11_rss_daily',after)
        self.assertNotIn(b'tools\no11_rss_daily',after)
        self.assertEqual(
            before.decode().replace(hotfix.BROKEN,hotfix.CORRECT),after.decode())
        self.assertNotIn(b'StartChild TRADE',after)

    def test_dry_run_no_writes(self):
        self.assertEqual(hotfix.install(self.store,test=True),'READY')
        self.assertFalse((self.store/hotfix.JOURNAL).exists())
        self.assertEqual(self.oldlog.read_bytes(),b'HISTORICAL_WINDOW_MISSING, not a successful capture\n')
        for p,raw in self.initial.items():
            self.assertEqual(p.read_bytes(),raw)

    def check(self):
        self.assertEqual(self.child.read_bytes(),
             hotfix.patch_next(self.initial[self.child]))
        self.assertEqual(n.checkpoint(self.store/hotfix.JOURNAL)['phase'],'COMPLETE')
        b=n.read(self.binding)
        self.assertFalse(b['orderTransmission'])
        self.assertEqual(b['nightlyResumeValidatorSha256'],n.digest(self.validator.read_bytes()))
        p=Path(b['nightlyResumeTool'])
        self.assertTrue(p.is_file())
        self.assertIn(b'real-friday-v1-pathfix-v2',p.read_bytes())
        self.assertEqual(n.digest(p.read_bytes()),b['nightlyResumeToolSha256'])
        self.assertEqual(self.worker.read_bytes(),self.initial[self.worker])
        for p in (self.ui,self.trade,self.settings,self.validator):
            self.assertEqual(p.read_bytes(),self.initial[p])
        self.assertEqual(self.previous_journal.read_bytes(),self.initial[self.previous_journal])
        for kind,p in self.engine_sources.items():
            if kind!='next':self.assertEqual(p.read_bytes(),self.initial[p])
        self.assertEqual(self.oldlog.read_bytes(),b'HISTORICAL_WINDOW_MISSING, not a successful capture\n')

    def test_upgrade_and_repeated_invocation(self):
        self.assertEqual(hotfix.install(self.store,do_apply=True,test=True),'PASS')
        self.check()
        self.assertEqual(hotfix.install(self.store,do_apply=True,test=True),'ALREADY_APPLIED')
        self.check()

    def test_power_failure_after_script_update_resumes_without_reset(self):
        real=hotfix.switch
        def interrupt(p,before,after):
            real(p,before,after)
            if Path(p)==self.child:raise KeyboardInterrupt('simulated power cut')
        with patch.object(hotfix,'switch',side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                hotfix.install(self.store,do_apply=True,test=True)
        self.assertEqual(n.checkpoint(self.store/hotfix.JOURNAL)['phase'],'PREPARED')
        with self.assertRaisesRegex(ValueError,'PREPARED_JOURNAL_REQUIRES_APPLY'):
            hotfix.install(self.store,do_apply=False,test=True)
        self.assertEqual(hotfix.install(self.store,do_apply=True,test=True),'PASS')
        self.check()

    def test_power_failure_after_binding_switch_resumes_without_reset(self):
        real=hotfix.switch
        def interrupt(p,before,after):
            real(p,before,after)
            if Path(p)==self.binding:raise KeyboardInterrupt('simulated power cut')
        with patch.object(hotfix,'switch',side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                hotfix.install(self.store,do_apply=True,test=True)
        self.assertEqual(hotfix.install(self.store,do_apply=True,test=True),'PASS')
        self.check()

    def test_unknown_user_engine_edit_blocks_fail_closed(self):
        self.child.write_bytes(self.child.read_bytes()+b'\nCUSTOM')
        before=self.binding.read_bytes()
        with self.assertRaisesRegex(ValueError,'ENGINE_CHANGED_SINCE_SIGNED_FRIDAY_INSTALL'):
            hotfix.install(self.store,do_apply=True,test=True)
        self.assertEqual(self.binding.read_bytes(),before)
        self.assertFalse((self.store/hotfix.JOURNAL).exists())

    def test_no_repatch_if_corrected_without_journal(self):
        self.child.write_bytes(hotfix.patch_next(self.child.read_bytes()))
        with self.assertRaisesRegex(ValueError,'EXACT_CHILD_PATH_BUG_NOT_PRESENT'):
            hotfix.install(self.store,do_apply=True,test=True)

    def test_worker_original_status_not_altered(self):
        updated=hotfix.patch_worker(self.worker.read_bytes())
        old=self.worker.read_bytes()
        self.assertNotEqual(updated,old)
        self.assertIn(b'ARK_NO11_REAL_FRIDAY_CALENDAR_PATHFIX_V2',updated)
        self.assertIn(b'DataUpdate-',updated)
        self.assertIn(b'NO11_NIGHTLY_RESUME_WORKER_PROBE_V2',updated)
        self.assertIn(b'real-friday-v1-pathfix-v2',updated)

if __name__=='__main__':unittest.main(verbosity=2)
