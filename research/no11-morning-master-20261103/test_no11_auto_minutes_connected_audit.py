"""Connected regressions, not merely isolated transformer string checks.

Uses real archive parsing, native Node Chart50 validation, original morning
prepare/scope and pointer validation. Network public-source acquisition is a
synthetic boundary fixture and no Excel/provider/order operation is executed.
"""
from __future__ import annotations
import contextlib
from copy import deepcopy
from datetime import datetime as RealDateTime, timezone, timedelta
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent/'no12-prebuy-causal-runtime-20261011'
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(ENGINE/'tools'))
import no11_previous_archive_context as archives
import morning_master as morning
import scope_morning_master as entry_scope
import no11_selection_status as status
import launcher_automatic_bridge_v4 as bridge
import no11_nightly_resume as n
import no11_circuit_repair as circuit
import no11_auto_minute_exclusion as exclusion
import no11_auto_minute_cycle_transform as transform
import no11_auto_minute_worker_transform as worker_transform
import install_no11_auto_minutes_release as installer
from test_no11_auto_minute_exclusion import plan_fixture
from test_no11_auto_minute_install import AutoMinuteInstallerTests


def encode(value):
    return (json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode()


def load_module(path):
    spec=importlib.util.spec_from_file_location('audit_'+path.stem,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FixedDateTime(RealDateTime):
    @classmethod
    def now(cls,tz=None):
        value=cls(2026,11,10,0,5,tzinfo=timezone(timedelta(hours=9)))
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


class ConnectedDataStage(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='ark-connected-')
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.run=self.root/'weekly-refresh';self.run.mkdir()
        self.capture=self.root/'rss-capture';self.capture.mkdir()
        self.private=self.root/'daily-cycle';self.private.mkdir()
        selected=[f'{3000+i}.T' for i in range(47)]
        self.mask,self.chart,self.chart_obj=plan_fixture(ENGINE,self.run,selected,'2026-11-10')
        self.selected=list(self.chart_obj['chartPlan']['selectorInputSymbols'])
        self.bad=self.selected[-1]
        files=[]
        for index,code in enumerate(self.selected,1):
            rows=[{'label':'2026-11-09T09:00:00+09:00','open':100,'high':102,'low':99,'close':101,'volume':1000},
                  {'label':'2026-11-09T09:01:00+09:00','open':101,'high':103,'low':100,'close':102,'volume':1100}]
            if code==self.bad:
                rows=rows[:1] # observable but insufficient previous-session bars
            obj={'schemaId':archives.ARCHIVE,'symbol':code,'period':'1M',
                 'sourceFunction':'RssChart','evidenceMode':'OBSERVED_READ_ONLY',
                 'observedAt':'2026-11-09T23:45:00+09:00','requestedBars':3000,
                 'numericRows':len(rows),'validRows':len(rows),'invalidRows':0,'duplicateRows':0,
                 'status':archives.GOOD,'rows':rows,'privateAccountDataIncluded':False,
                 'vendorLabelCertified':False,'actualHistoricalKnownAtCertified':False,
                 'vendorDecimalTokenCertified':False,'modelTrainingReady':False,
                 'productionReady':False,'orderTransmission':False}
            raw=encode(obj);name=f'{index:05d}-{code.replace(".","_")}-1M.json'
            (self.capture/name).write_bytes(raw)
            files.append({'symbol':code,'file':name,'sha256':n.digest(raw),'status':archives.GOOD,'rows':len(rows)})
        progress={'schemaId':archives.PROGRESS,'requested':47,'completed':47,
                  'files':files,'observedSymbols':47,'unavailableSymbols':0,'rows':93,
                  'productionReady':False,'orderTransmission':False}
        self.progress=self.capture/'progress-00047.json';self.progress.write_bytes(encode(progress))
        info=archives.scope(self.chart,self.mask)
        self.stage=archives.stage_archive(info,self.capture,'2026-11-10T00:01:00+09:00')
        self.assertEqual(len(self.stage['symbols']),46)
        self.assertEqual(list(self.stage['omittedSymbols']),[self.bad])
        self.stage_file=morning.immutable(self.root,'previous-archive-stage',self.stage)
        self.originals={p:p.read_bytes() for p in [self.chart,self.mask,self.stage_file,self.progress,*self.capture.glob('*-1M.json')]}
        package=self.root/'package';package.mkdir()
        raw=circuit.transform('cycle',(HERE/'daily_cycle.py').read_bytes())
        self.tool=package/'daily_cycle.py';self.tool.write_bytes(transform.transform(raw))
        self.helper=package/'no11_auto_minute_exclusion.py';self.helper.write_bytes((HERE/self.helper.name).read_bytes())
        self.daily=load_module(self.tool)
        self.runner_dir=self.root/'runner';self.runner_dir.mkdir()
        (self.runner_dir/'xls-reader').mkdir()
        self.runner=self.runner_dir/'morning_master.py'
        self.runner.write_bytes((HERE/self.runner.name).read_bytes())
        self.scope_file=HERE/'scope_morning_master.py'
        self.workbook=self.root/'configured-order.xlsx';self.workbook.write_bytes(b'SYNTHETIC_NO_EXCEL')
        self.settings=self.root/'settings.json'
        self.settings.write_bytes(encode({'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
           'automaticOrderAuthorization':False,'orderTransmission':False,
           'orderIdWorkbookPath':str(self.workbook)}))
        runtime=self.root/'runtime';runtime.mkdir()
        model=self.root/'model';model.mkdir()
        self.spec={'sessionDate':'2026-11-04','engineRoot':str(ENGINE),
          'chartReceipt':str(self.chart),'passMask':str(self.mask),
          'previousStage':str(self.stage_file),'previousCaptureDir':str(self.capture),
          'runtimeRoot':str(runtime),'h235ModelRoot':str(model),
          'weeklySourceRun':str(self.run),'settingsFile':str(self.settings),
          'outputRoot':str(self.root)}
        self.seed=morning.immutable(self.root,'morning-handoff',{
          'schemaId':morning.SCHEMA,'sessionDate':'2026-11-04','spec':self.spec,
          'productionReady':False,'orderTransmission':False})
        self.binding={'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
          'orderTransmission':False,'manualEvidenceRequired':False,'manualPriceInputRequired':False,
          'dailyCycleRoot':str(self.private),'engine':str(ENGINE),'sessionDate':'2026-11-04',
          'runner':str(self.runner),'runnerSha256':n.digest(self.runner.read_bytes()),
          'scopeTool':str(self.scope_file),'scopeToolSha256':n.digest(self.scope_file.read_bytes()),
          'handoff':str(self.seed),'handoffSha256':n.digest(self.seed.read_bytes()),
          'dailyCycleTool':str(self.tool),'dailyCycleToolSha256':n.digest(self.tool.read_bytes()),
          'autoMinuteExclusionToolSha256':n.digest(self.helper.read_bytes())}
        self.binding_file=self.root/'automatic-inputs.json';self.binding_file.write_bytes(encode(self.binding))
        self.log=self.root/'completed-capture.log'
        self.log.write_text('\n'.join([
          'NO11_WEEKLY_NIGHTLY_ASOF=2026-11-09','NO11_WEEKLY_NIGHTLY_NEXT_SESSION=2026-11-10',
          'NO11_WEEKLY_NIGHTLY_POOL_SOURCE='+str(self.run),
          'NO11_WEEKLY_NIGHTLY_REFRESH_RUN='+str(self.run),
          'NO11_WEEKLY_NIGHTLY_CURRENT_CHART50='+str(self.chart),
          'NO11_WEEKLY_NIGHTLY_CURRENT_MASK='+str(self.mask),
          'NO11_PREVIOUS_ARCHIVE_STAGE='+str(self.stage_file),
          'NO11_PREVIOUS_CAPTURE_DIR='+str(self.capture),
          'NO11_WEEKLY_NIGHTLY_STAGE=CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE',
          'ORDER_TRANSMISSION=False','']),encoding='utf-8')

    def public_fixture(self,helper,selected,prior,session,root):
        docs=[];rows=[]
        rights=b'SYNTHETIC RIGHTS SOURCE; NO LIVE HTTP'
        sha=n.digest(rights);(root/(sha+'.source')).write_bytes(rights)
        docs.append({'sha256':sha,'url':'https://www.jpx.co.jp/listing/others/ex-rights/test/20261109.xls'})
        for code in selected:
            raw=('SYNTHETIC LISTING '+code).encode();sha=n.digest(raw)
            (root/(sha+'.source')).write_bytes(raw)
            docs.append({'sha256':sha,'url':'https://www2.jpx.co.jp/tseHpFront/StockSearch.do?topSearchStr='+code[:4]})
            rows.append({'symbol':code,'eligible':True,'nearTermRightsEventListed':False,
              'listingSourceSha256':sha,'reviewStatus':'NOT_REVIEWED','segment':'PRIME','sector':'TEST'})
        return {'schemaId':'ARK_NO11_MORNING_PUBLIC_SOURCE_BASIS_V1','sessionDate':session,
          'previousSession':prior,'selectedSymbols':selected,'rows':rows,'documents':docs,
          'rightsSourceParsed':True,'rightsPublishedOn':'2026-11-09','sourceBlockers':[],
          'reviewStatus':'NOT_REVIEWED','corporateActionReviewPerformed':False,
          'priceBasisCertified':False,'datedMasterCreated':False,'productionReady':False,'orderTransmission':False}

    def execute_stage(self):
        real=self.daily.native_module
        def boundary(name,path):
            if name=='ark_pinned_morning':return morning
            if name=='ark_pinned_entry_scope':return entry_scope
            return real(name,path)
        output=io.StringIO()
        with patch.object(self.daily,'native_module',side_effect=boundary),\
             patch.object(self.daily,'datetime',FixedDateTime),\
             patch.object(morning,'clock',return_value='2026-11-10T00:05:00+09:00'),\
             patch.object(morning,'helper_module',return_value=None),\
             patch.object(morning,'collect_public',side_effect=self.public_fixture),\
             contextlib.redirect_stdout(output):
            self.daily.stage(self.binding_file,self.log)
        return output.getvalue()

    def test_real_archive_to_native_46_handoff_and_trade_bridge(self):
        output=self.execute_stage()
        self.assertIn('NO11_AUTO_MINUTE_EXCLUDED=1/47',output)
        self.assertIn('NO11_DAILY_CYCLE_STATUS=NEXT_SESSION_HANDOFF_READY',output)
        pointer=self.private/'prepared-days/2026-11-10.json'
        p,h,c,m=status.validate_pointer(pointer,self.private)
        self.assertEqual(p['selectedCount'],46)
        self.assertNotIn(self.bad,p['selectedSymbols'])
        active=bridge.resolve_daily_binding(self.binding,'2026-11-10')
        self.assertEqual(active['handoff'],p['handoff'])
        for path,raw in self.originals.items():self.assertEqual(path.read_bytes(),raw)
        # Same saved inputs can be retried without overwriting a pointer.
        first=pointer.read_bytes();self.execute_stage();self.assertEqual(pointer.read_bytes(),first)

    def test_protected_missing_symbol_is_not_silently_removed(self):
        chart=deepcopy(self.chart_obj);body=chart['chartPlan'];body.pop('planSha256')
        body['protectedChartSymbols']=[self.bad];body['heldSymbols']=[self.bad]
        # Use native JS hashing to preserve JSON numerical identity.
        script='import fs from "node:fs";import {createHash} from "node:crypto";const c=JSON.parse(fs.readFileSync(0,"utf8"));c.chartPlan.planSha256=createHash("sha256").update(JSON.stringify(c.chartPlan)).digest("hex");console.log(JSON.stringify(c));'
        result=subprocess.run(['node','--input-type=module','-e',script],input=json.dumps(chart),text=True,capture_output=True,check=True)
        raw=result.stdout.encode();path=self.run/('no11-chart50-private-'+n.digest(raw)[:16]+'.json');path.write_bytes(raw)
        stage=deepcopy(self.stage);stage['chartPlanSha256']=json.loads(raw)['chartPlan']['planSha256']
        stage_path=morning.immutable(self.root,'previous-archive-stage',stage)
        record=self.daily.parse_nightly(self.log.read_bytes());record.update(chart=str(path),stage=str(stage_path))
        with self.assertRaisesRegex(ValueError,'PROTECTED_HOLDING_EXIT_CONTEXT'):
            exclusion.prune(morning,record,self.private,self.binding,self.daily.previous_checkpoint)
        self.assertFalse((self.private/'prepared-days/2026-11-10.json').exists())

    def test_original_receipts_are_not_aliased_to_new_writable_files(self):
        self.execute_stage()
        mirrors=list((self.private/'auto-minute-exclusions').rglob('*-1M.json'))
        self.assertEqual(len(mirrors),46)
        mirror=mirrors[0];original=self.capture/mirror.name;before=original.read_bytes()
        mirror.write_bytes(b'SIMULATED_MUTATION_OF_DERIVED_COPY')
        self.assertEqual(original.read_bytes(),before,'Derived file is a hard link: original is also corrupted')


class SavedReplayAndInstallerAudit(unittest.TestCase):
    def test_child_failure_is_not_reported_as_success(self):
        fixture=AutoMinuteInstallerTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        binding=n.read(fixture.binding)
        binding['python']=str(Path(sys.executable).resolve())
        fixture.binding.write_bytes(encode(binding))
        _,j=installer.install(fixture.store,HERE,True,True)
        fail=subprocess.CompletedProcess([],2,stdout='NO11_NIGHTLY_RESUME=BLOCKED|TEST\n',stderr='')
        with patch.object(installer,'locate_saved',return_value=('2026-11-10',fixture.root,fixture.root/'capture.log')),\
             patch.object(installer.subprocess,'run',return_value=fail):
            with self.assertRaisesRegex(ValueError,'SAVED_STAGE_FAILED'):
                installer.resume(fixture.store,j)

    def test_completed_install_still_checks_bound_package_bytes(self):
        fixture=AutoMinuteInstallerTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        _,j=installer.install(fixture.store,HERE,True,True)
        binding=n.read(fixture.binding)
        Path(binding['dailyCycleTool']).write_bytes(b'CORRUPTED_AFTER_INSTALL')
        with self.assertRaises(ValueError):installer.install(fixture.store,HERE,True,True)

    def test_saved_worker_adoption_rejects_unverified_final_log(self):
        fixture=AutoMinuteInstallerTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        raw=worker_transform.transform(fixture.current_worker.read_bytes(),'a'*64)
        compile(raw.decode('utf-8-sig'),'worker.py','exec')
        self.assertIn(b'ARK_AUTO_MINUTE_RESUME_ONLY',raw)
        self.assertIn(b'SAVED_CAPTURE_NOT_VERIFIED_NO_RECAPTURE',raw)

if __name__=='__main__':unittest.main(verbosity=2)
