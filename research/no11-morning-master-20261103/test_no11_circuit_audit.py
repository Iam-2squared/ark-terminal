"""Integration audit. Synthetic market/broker inputs; never contact Excel/orders.

These tests connect actual log parsing, atomic pointer publication and next-day
bridge resolution. Windows uses real nested PowerShell and venv processes.
Real RSS, broker order acceptance, fills and live EXIT remain separate checks.
"""
from __future__ import annotations
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import venv

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import no11_circuit_repair as repair
import daily_cycle as original_cycle
import launcher_automatic_bridge_v4 as original_bridge


def fixed(kind):
    file={'cycle':'daily_cycle.py','bridge':'launcher_automatic_bridge_v4.py',
          'worker':'no11_nightly_resume_workeraware.py'}[kind]
    raw=repair.transform(kind,(HERE/file).read_bytes())
    mod=types.ModuleType('circuit_'+kind)
    mod.__file__=str(HERE/file)
    exec(compile(raw.decode('utf-8-sig'),str(HERE/file),'exec'),mod.__dict__)
    return mod,raw


class CircuitAudit(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.cycle,self.cycle_raw=fixed('cycle')
        self.bridge,self.bridge_raw=fixed('bridge')
        self.worker,self.worker_raw=fixed('worker')

    def write_json(self,path,obj):
        path.write_bytes(self.cycle.encode(obj));return path

    def broker_inputs(self):
        day='2026-11-09'
        base={'schemaId':'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1',
              'chartPlan':{'sourcePlanId':'a'*64,'sessionDate':day,
              'selectorInputSymbols':['1111.T','2222.T','3333.T']}}
        before=self.write_json(self.root/'original.json',base)
        sha=self.bridge.digest(before.read_bytes())
        subset={**base,'chartPlan':{**base['chartPlan'],'selectorInputSymbols':['1111.T','3333.T']},
                'automaticVerifiedExclusion':{'schemaId':'ARK_NO11_VERIFIED_INVALID_SYMBOL_EXCLUSION_V1',
                  'sessionDate':day,'originalChartReceiptSha256':sha,'originalChartReceiptModified':False,
                  'orderTransmission':False,'blockedSymbols':['2222.T'],'passedSymbols':['1111.T','3333.T']}}
        narrowed=self.write_json(self.root/'subset.json',subset)
        master=self.write_json(self.root/'master.json',{'rows':[{'symbol':s} for s in ['1111.T','3333.T']]})
        prepared={'schemaId':'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1','sessionDate':day,
           'productionReady':False,'orderTransmission':False,'orderIdWorkbookPath':'SYNTHETIC_ORDER_BOOK',
           'runtimeRoot':'SYNTHETIC_RUNTIME','h235ModelRoot':'SYNTHETIC_MODEL',
           'precomputedG1Mask':'SYNTHETIC_MASK','weeklySourceRun':'SYNTHETIC_WEEKLY',
           'precomputedChartReceipt':str(narrowed),'datedMaster':str(master),'privateRoot':str(self.root)}
        old={**prepared,'precomputedChartReceipt':str(before),'brokerExecutionConfig':'EXISTING_BROKER',
             'samples':9,'historyBars':50,'warmupSeconds':30}
        broker={'schemaId':'ARK_NO11_BROKER_EXECUTION_CONFIG_V1','sessionDate':day,
           'fundingPolicy':'RSS_BUYING_POWER','feeCourse':'ZERO','orderTransmission':True,'productionReady':False,
           'transport':{'sessionDate':day,'mode':'LIVE','operatorEnabled':True,'approvedForSession':True,
                        'orderTransmission':True,'workbookPath':'SYNTHETIC_ORDER_BOOK'},
           'ledger':{'maxSymbols':3,'lotSize':100,'account':'一般','allocatedCashJpy':'AUTO_RSS_BUYING_POWER'},
           'orderTerms':{'sor':True,'accountType':1,'accountTypeVerified':True,'orderType':'MARKET','timeInForce':'DAY'}}
        return prepared,old,broker,day

    def test_reproduce_old_digest_bug_then_reuse_broker_without_reinitialization(self):
        prepared,old,broker,day=self.broker_inputs()
        with self.assertRaisesRegex(ValueError,'VERIFIED_SYMBOL_EXCLUSION_ONLY'):
            original_bridge.merge_current_broker(prepared,old,broker,day)
        result=self.bridge.merge_current_broker(prepared,old,broker,day)
        self.assertEqual(result['brokerExecutionConfig'],old['brokerExecutionConfig'])
        self.assertEqual(result['privateRoot'],old['privateRoot'])
        self.assertEqual(result['samples'],9)
        self.assertEqual(result['precomputedChartReceipt'],prepared['precomputedChartReceipt'])
        subset=json.loads(Path(prepared['precomputedChartReceipt']).read_bytes())
        subset['automaticVerifiedExclusion']['originalChartReceiptSha256']='0'*64
        self.write_json(Path(prepared['precomputedChartReceipt']),subset)
        with self.assertRaisesRegex(ValueError,'VERIFIED_SYMBOL_EXCLUSION_ONLY'):
            self.bridge.merge_current_broker(prepared,old,broker,day)

    def handoff(self):
        hand={'schemaId':'ARK_NO11_MORNING_MASTER_HANDOFF_V1','sessionDate':'2026-11-09',
              'previousSession':'2026-11-06','selectedSymbols':['1111.T','3333.T'],
              'reviewStatus':'NOT_REVIEWED','datedMasterCreated':False,'productionReady':False,
              'orderTransmission':False}
        raw=self.cycle.encode(hand)
        return self.write_json(self.root/('morning-handoff-'+self.cycle.digest(raw)+'.json'),hand)

    def capture_log(self):
        return ('\n'.join([
          'NO11_WEEKLY_NIGHTLY_ASOF=2026-11-06',
          'NO11_WEEKLY_NIGHTLY_NEXT_SESSION=2026-11-09',
          'NO11_NIGHTLY_DAILY_RUN=C:\\検証\\daily',
          'NO11_NIGHTLY_MASK=C:\\検証\\mask.json',
          'NO11_NIGHTLY_CHART50=C:\\検証\\chart.json',
          'NO11_PREVIOUS_ARCHIVE_STAGE=C:\\検証\\stage.json',
          'NO11_PREVIOUS_CAPTURE_DIR=C:\\検証\\minutes',
          'NO11_WEEKLY_NIGHTLY_STAGE=FRIDAY_FULL_UNIVERSE_AND_PREVIOUS_COMPLETE',
          'ORDER_TRANSMISSION=False'])+'\n')

    def test_real_parse_publish_bridge_connection_for_japanese_paths(self):
        hand=self.handoff()
        tool=self.root/'daily_cycle.py';tool.write_bytes(self.cycle_raw)
        for encoding in ('utf-8','utf-16','cp932'):
            with self.subTest(encoding=encoding):
                raw=self.capture_log().encode(encoding)
                record=self.cycle.parse_nightly(raw)
                self.assertEqual(record['chart'],'C:\\検証\\chart.json')
                self.assertEqual(record['sessionDate'],'2026-11-09')
                root=self.root/encoding;root.mkdir()
                ptr=self.cycle.publish(root,record,hand,'a'*64,'b'*64)
                binding={'sessionDate':'2026-11-04','dailyCycleRoot':str(root),
                         'dailyCycleTool':str(tool),'dailyCycleToolSha256':self.cycle.digest(self.cycle_raw)}
                active=self.bridge.resolve_daily_binding(binding,'2026-11-09')
                self.assertEqual(active['handoff'],str(hand.resolve()))
                self.assertEqual(active['sessionDate'],'2026-11-09')
                self.assertTrue(ptr.is_file())

    def test_pointer_cannot_be_left_partial_on_io_failure(self):
        record=self.cycle.parse_nightly(self.capture_log().encode())
        with patch.object(self.cycle.os,'link',side_effect=OSError('simulated filesystem failure')):
            with self.assertRaises(OSError):
                self.cycle.publish(self.root,record,self.handoff(),'a'*64,'b'*64)
        self.assertFalse((self.root/'prepared-days/2026-11-09.json').exists())
        self.assertEqual(list((self.root/'prepared-days').glob('.handoff-pending-*')),[])
        p=self.cycle.publish(self.root,record,self.handoff(),'a'*64,'b'*64)
        self.assertEqual(json.loads(p.read_bytes())['sessionDate'],'2026-11-09')

    def test_existing_different_pointer_never_overwritten(self):
        rec=self.cycle.parse_nightly(self.capture_log().encode())
        p=self.cycle.publish(self.root,rec,self.handoff(),'a'*64,'b'*64)
        before=p.read_bytes()
        with self.assertRaisesRegex(ValueError,'DAY_ALREADY_PINNED'):
            self.cycle.publish(self.root,rec,self.handoff(),'a'*64,'c'*64)
        self.assertEqual(p.read_bytes(),before)

    def test_prep_lock_recovers_after_killed_process_and_blocks_concurrent(self):
        mod=self.root/'fixed_bridge.py';mod.write_bytes(self.bridge_raw)
        lock=self.root/'automatic-inputs.lock'
        code='import sys,time;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import fixed_bridge as b\nwith b.lock(Path(sys.argv[2])):\n print("LOCKED",flush=True);time.sleep(60)\n'
        child=subprocess.Popen([sys.executable,'-u','-c',code,str(self.root),str(lock)],
              stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(),'LOCKED')
            with self.assertRaisesRegex(ValueError,'PREPARATION_ALREADY_RUNNING'):
                with self.bridge.lock(lock):pass
        finally:
            child.kill();child.communicate(timeout=10)
        self.assertTrue(lock.exists())
        with self.bridge.lock(lock):pass
        self.assertTrue(lock.exists())
        with self.assertRaisesRegex(ValueError,'RUNNING_OR_INTERRUPTED'):
            with original_bridge.lock(lock):pass

    def test_actual_subprocess_logs_surface_failure_before_generic_wrapper(self):
        log=self.root/'capture.log';output=io.StringIO()
        with contextlib.redirect_stdout(output):
            with self.assertRaisesRegex(ValueError,'NATIVE_STAGE_FAILED'):
                self.worker.run_logged([sys.executable,'-u','-c',
                    'print("NO11_TEST_STAGE=CAPTURE");print("NO11_CAPTURE=BLOCKED|MOCK_RSS_ERROR");raise SystemExit(2)'],log)
        text=output.getvalue()
        self.assertIn('NO11_NIGHTLY_RESUME_CHILD_LOG='+str(log),text)
        self.assertIn('NO11_NIGHTLY_RESUME_CHILD_EXIT=2',text)
        self.assertIn('NO11_CAPTURE=BLOCKED|MOCK_RSS_ERROR',text)
        self.assertIn(b'MOCK_RSS_ERROR',log.read_bytes())

    def test_failed_capture_never_creates_trading_handoff(self):
        raw=self.capture_log().replace('FRIDAY_FULL_UNIVERSE_AND_PREVIOUS_COMPLETE','BLOCKED|MOCK').encode()
        with self.assertRaisesRegex(ValueError,'NIGHTLY_NOT_COMPLETE'):
            self.cycle.parse_nightly(raw)
        self.assertFalse((self.root/'prepared-days').exists())

    def test_existing_active_session_is_checked_before_transport_setup(self):
        # Transformer intentionally preserves the source platform's CRLF/BOM.
        source=self.bridge_raw.decode('utf-8-sig').replace('\r\n','\n')
        start=source.index('        if merged is None:\n            candidate_root')
        end=source.index('            result, broker_path = make_initial_broker(',start)
        self.assertIn('ACTIVE_SESSION_NO_REBIND',source[start:end])

    def test_transform_idempotent_and_preserves_bom_crlf(self):
        names={'cycle':'daily_cycle.py','bridge':'launcher_automatic_bridge_v4.py','worker':'no11_nightly_resume_workeraware.py'}
        for kind,name in names.items():
            text=(HERE/name).read_text(encoding='utf-8-sig')
            inp=b'\xef\xbb\xbf'+text.replace('\r\n','\n').replace('\n','\r\n').encode()
            out=repair.transform(kind,inp)
            self.assertEqual(repair.transform(kind,out),out)
            self.assertTrue(out.startswith(b'\xef\xbb\xbf'))
            self.assertNotIn(b'\n',out.replace(b'\r\n',b''))


@unittest.skipUnless(os.name=='nt','real Windows launch chain')
class WindowsActualChain(unittest.TestCase):
    def test_native_powershell_venv_python_probe_without_self_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);environment=root/'venv'
            venv.EnvBuilder(with_pip=False).create(environment)
            python=environment/'Scripts/python.exe'
            outer=root/'Start-No11UnifiedLauncher.ps1'
            inner=root/'Run-No11NightlyCycle.ps1'
            worker_file=root/'probe_entry.py'
            worker_file.write_text('import sys\nsys.path.insert(0,'+repr(str(HERE))+')\nimport no11_nightly_resume_workeraware as w\nw.no_workers()\nprint("ACTUAL_NATIVE_VENV_CHAIN=PASS")\n',encoding='utf-8')
            inner.write_text('param([string]$Python,[string]$Entry)\n& $Python -B -X utf8 $Entry\nexit $LASTEXITCODE\n',encoding='utf-8')
            outer.write_text('param([string]$Inner,[string]$Python,[string]$Entry)\n& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $Inner -Python $Python -Entry $Entry\nexit $LASTEXITCODE\n',encoding='utf-8')
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(outer),'-Inner',str(inner),'-Python',str(python),'-Entry',str(worker_file)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            self.assertIn('ACTUAL_NATIVE_VENV_CHAIN=PASS',result.stdout)


if __name__=='__main__':unittest.main(verbosity=2)
