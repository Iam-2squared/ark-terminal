"""Actual installed-style source transforms and filesystem tests; no broker I/O."""
from datetime import datetime, timedelta, timezone
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent/'no12-prebuy-causal-runtime-20261011'
sys.path.insert(0,str(HERE))
import test_no11_update_path as fixture
import no11_update_path as old
import no11_nightly_resume as n
import install_no11_completed_session_update as upgrade


def sources():
    baseline=fixture.NativeUpdateTests().originals()
    result={key:old.transform(key,baseline[key]) for key in ('status','native','weekly','next')}
    result['planner']=(ENGINE/'tools/no11_weekly_g1_refresh.mjs').read_bytes()
    return result


class CompletedSessionSourceTests(unittest.TestCase):
    def test_all_installed_sources_upgrade_idempotently_and_keep_line_endings(self):
        for kind,raw in sources().items():
            for newline in ('\n','\r\n'):
                with self.subTest(kind=kind,newline=newline):
                    inp=b'\xef\xbb\xbf'+raw.decode('utf-8-sig').replace('\r\n','\n').replace('\n',newline).encode()
                    out=upgrade.transform(kind,inp)
                    self.assertIn(upgrade.MARK.encode(),out)
                    self.assertEqual(upgrade.transform(kind,out),out)
                    self.assertTrue(out.startswith(b'\xef\xbb\xbf'))
                    if newline=='\r\n':self.assertNotIn(b'\n',out.replace(b'\r\n',b''))

    def test_weekly_and_daily_maximum_preserved_and_pair_handed_through(self):
        original=sources()
        weekly=upgrade.transform('weekly',original['weekly']).decode('utf-8-sig')
        nxt=upgrade.transform('next',original['next']).decode('utf-8-sig')
        for p in ('$FullBatchSize=47','$RefreshBatchSize=47','$MinuteBatchSize=47'):
            self.assertIn(p,weekly)
        for p in ('$DailyBatchSize=47','$MinuteBatchSize=47'):
            self.assertIn(p,nxt)
        self.assertIn("'-AsOfSession',$asOf,'-CompletedSessionUpdate'",weekly)
        self.assertIn('$calendar.asOfSession -ceq $AsOfSession',nxt)
        self.assertIn('$calendar.sessionDate -ceq $SessionDate',nxt)
        self.assertIn('$identity.plan.asOfSession -ceq $AsOfSession',nxt)

    def test_trade_stop_excel_check_and_weekly_marker_logic_byte_unchanged(self):
        raw=sources()['native'].decode('utf-8-sig').replace('\r\n','\n')
        out=upgrade.transform('native',sources()['native']).decode('utf-8-sig').replace('\r\n','\n')
        self.assertEqual(raw[:raw.index('function RunWeekly($cfg){')],out[:out.index('function RunWeekly($cfg){')])
        self.assertEqual(raw[raw.index('function StopRunningEngine('):],out[out.index('function StopRunningEngine('):])
        self.assertIn("& node $scheduleTool schedule",out)
        run=out[out.index('function RunWeekly($cfg){'):out.index('function StopRunningEngine(')]
        self.assertNotIn('2026-11-09',run)
        self.assertNotIn('IApproveOrders',run)
        self.assertNotIn("StartChild 'TRADE'",run)

    def test_monday_open_button_enabled_without_trade_authorization(self):
        code=upgrade.transform('status',sources()['status']).decode('utf-8-sig')
        status=types.ModuleType('test_status')
        exec(compile(code,'status','exec'),status.__dict__)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); tool=root/'cycle.py';tool.write_text('')
            cycle=root/'data';cycle.mkdir()
            cfg=root/'settings.json';binding=root/'binding.json'
            cfg.write_bytes(n.encode({'normalMaxPositions':3,'sameDayApprovalRequired':True,
                'automaticOrderAuthorization':False,'orderTransmission':False}))
            binding.write_bytes(n.encode({'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
                'orderTransmission':False,'dailyCycleTool':str(tool),'dailyCycleRoot':str(cycle)}))
            for hour in (7,9,10,12,15,17,19):
                out=status.inspect(cfg,binding,at=datetime(2026,11,9,hour,tzinfo=timezone(timedelta(hours=9))))
                self.assertTrue(out['canRunNightly'],str(hour))
                self.assertFalse(out['canRequestTrade'])
                self.assertFalse(out['brokerOrderTransmission'])

    def test_unknown_native_data_function_not_silently_replaced(self):
        source=sources()['native'].replace(b'CheckExcel $cfg $false',b'UnknownLocalFunction $cfg')
        with self.assertRaisesRegex(ValueError,'NATIVE_DATA_FUNCTION_CHANGED'):
            upgrade.transform('native',source)


class CompletedSessionInstallTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name); self.store=root/'store';self.engine=root/'engine'
        (self.store/'oneclick').mkdir(parents=True)
        self.white=self.store/'oneclick/Start-No11OneClick.ps1'
        self.white.write_bytes(b'USER APPROVED WHITE GUI\r\n')
        self.paths={}
        for key,rel in upgrade.RELATIVE.items():
            p=self.engine/rel[7:] if rel.startswith('engine/') else self.store/rel
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(sources()[key]);self.paths[key]=p
        (self.store/'automatic-inputs.json').write_bytes(n.encode({
            'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1','engine':str(self.engine),
            'orderTransmission':False}))
        self.before={p:p.read_bytes() for p in (*self.paths.values(),self.white,self.store/'automatic-inputs.json')}

    def test_audit_changes_no_sources(self):
        self.assertEqual(upgrade.install(self.store,_test=True),'READY')
        for p,raw in self.before.items():self.assertEqual(p.read_bytes(),raw)
        self.assertFalse((self.store/'completed-session-update-transaction.json').exists())

    def test_install_idempotent_and_white_ui_and_binding_untouched(self):
        self.assertEqual(upgrade.install(self.store,True,_test=True),'PASS')
        self.assertEqual(upgrade.install(self.store,True,_test=True),'ALREADY_APPLIED')
        for key,p in self.paths.items():self.assertEqual(p.read_bytes(),upgrade.transform(key,self.before[p]))
        self.assertEqual(self.white.read_bytes(),self.before[self.white])
        b=self.store/'automatic-inputs.json';self.assertEqual(b.read_bytes(),self.before[b])

    def test_failure_rolls_back_all_native_files(self):
        original=upgrade.replace
        def fail(path,before,after):
            if path==self.paths['weekly']:raise OSError('mock disk fault')
            return original(path,before,after)
        with patch.object(upgrade,'replace',side_effect=fail):
            with self.assertRaises(OSError):upgrade.install(self.store,True,_test=True)
        for p,raw in self.before.items():self.assertEqual(p.read_bytes(),raw)

    def test_power_loss_durable_reentry_without_marker_deletion(self):
        original=upgrade.replace
        def crash(path,before,after):
            original(path,before,after);raise KeyboardInterrupt('mock power loss')
        with patch.object(upgrade,'replace',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):upgrade.install(self.store,True,_test=True)
        self.assertEqual(upgrade.install(self.store,True,_test=True),'PASS')
        self.assertEqual(self.white.read_bytes(),self.before[self.white])

    def test_unknown_external_edit_after_interruption_not_overwritten(self):
        original=upgrade.replace
        def crash(path,before,after):
            original(path,before,after);raise KeyboardInterrupt()
        with patch.object(upgrade,'replace',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):upgrade.install(self.store,True,_test=True)
        p=self.paths['planner'];p.write_bytes(b'UNKNOWN EDIT')
        with self.assertRaisesRegex(ValueError,'JOURNAL_UNKNOWN_EDIT'):
            upgrade.install(self.store,True,_test=True)
        self.assertEqual(p.read_bytes(),b'UNKNOWN EDIT')

if __name__=='__main__':unittest.main(verbosity=2)
