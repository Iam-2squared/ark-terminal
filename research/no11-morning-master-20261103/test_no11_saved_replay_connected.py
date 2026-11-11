"""Actual native worker/Pipeline -> actual daily stage -> validated handoff.

Only clock/calendar CLI, Excel-process discovery and public HTTP acquisition
are boundary fixtures; native source/Chart50/archive/pointer validators run.
"""
from __future__ import annotations
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import test_no11_auto_minutes_connected_audit as connected
import no11_nightly_resume as n
import no11_circuit_repair as circuit
import no11_auto_minute_worker_transform as transform
import no11_selection_status as status

class SavedWorkerReplay(unittest.TestCase):
    def setUp(self):
        self.f=connected.ConnectedDataStage();self.f.setUp();self.addCleanup(self.f.doCleanups)
        old=circuit.transform('worker',(HERE/'no11_nightly_resume_workeraware.py').read_bytes())
        old=old.decode('utf-8-sig').replace("    work = root / 'resumable-nightly' / (asof + '_' + target)",
          "    work = root / 'resumable-nightly' / (asof + '_' + target + '-data-books-v1-0123456789abcdef')").encode()
        self.worker_path=self.f.tool.parent/'no11_nightly_resume_workeraware.py'
        self.worker_path.write_bytes(transform.transform(old,n.digest(self.f.helper.read_bytes())))
        validator=self.worker_path.with_name('no11_selection_status.py');validator.write_bytes((HERE/validator.name).read_bytes())
        self.worker=connected.load_module(self.worker_path)
        self.f.binding.update(python=str(Path(sys.executable).resolve()),
             nightlyResumeTool=str(self.worker_path),nightlyResumeToolSha256=n.digest(self.worker_path.read_bytes()),
             nightlyResumeValidatorSha256=n.digest(validator.read_bytes()))
        self.f.binding_file.write_bytes(connected.encode(self.f.binding))
        self.symbols=self.f.root/'all-symbols.txt';self.symbols.write_text('7203.T\n',encoding='utf-8')
        self.legacy=self.f.private/'resumable-nightly/2026-11-09_2026-11-10-data-books-v1-0123456789abcdef'
        self.legacy.mkdir(parents=True)
        self.log=self.legacy/('capture-'+'a'*32+'.log');self.log.write_bytes(self.f.log.read_bytes())
        paths={'original':connected.ENGINE/'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1',
               'schedule':connected.ENGINE/'tools/no11_weekly_g1_refresh.mjs','validator':validator}
        paths.update({key:Path(self.f.binding[key]) for key in ('runner','scopeTool','dailyCycleTool','handoff')})
        pins={key:n.digest(path.read_bytes()) for key,path in paths.items()}
        for folder in ('tools','windows'):
            for p in sorted((connected.ENGINE/folder).iterdir()):
                if p.is_file() and p.suffix in ('.py','.ps1','.mjs','.js'):pins[folder+'/'+p.name]=n.digest(p.read_bytes())
        pins['dailyCycleTool']=n.digest(circuit.transform('cycle',(HERE/'daily_cycle.py').read_bytes()))
        identity={'asOfSession':'2026-11-09','sessionDate':'2026-11-10','engine':str(connected.ENGINE),
                  'mode':'WEEKLY_POOL_CANDIDATES_ONLY','symbolsSha256':n.digest(self.symbols.read_bytes()),
                  'pins':pins,'orderTransmission':False}
        self.oldstate=self.legacy/'checkpoint.json'
        n.atomic(self.oldstate,{'schemaId':n.SCHEMA,'phase':'CAPTURING',
            'identity':identity,'identitySha256':n.digest(n.encode(identity)),
            'attemptLog':self.log.name,'orderTransmission':False})
        self.old_bytes=self.oldstate.read_bytes();self.log_bytes=self.log.read_bytes()
        self.capture_calls=0;self.publish_calls=0

    def run_native(self):
        original_run=subprocess.run
        def commands(argv,*args,**kwargs):
            if argv[0]=='node' and len(argv)>2 and argv[2]=='schedule':
                return subprocess.CompletedProcess(argv,0,json.dumps({
                    'schemaId':'ARK_NO11_WEEKLY_REFRESH_SCHEDULE_V1','orderTransmission':False,
                    'asOfSession':'2026-11-09','sessionDate':'2026-11-10','mode':'WEEKLY_POOL_CANDIDATES_ONLY'}),'')
            return original_run(argv,*args,**kwargs)
        original_module=self.worker.module
        def modules(name,path):
            if str(path)==str(self.f.tool):return self.f.daily
            return original_module(name,path)
        def logged(argv,path,timeout=0):
            if argv[0]=='powershell.exe':
                self.capture_calls+=1
                raise AssertionError('UNEXPECTED_RSS_RECAPTURE')
            self.assertIn('stage',argv)
            self.publish_calls+=1
            self.f.log=Path(argv[argv.index('--nightly-log')+1])
            output=self.f.execute_stage()
            Path(path).write_text(output,encoding='utf-8')
        output=io.StringIO()
        with patch.object(self.worker,'datetime',connected.FixedDateTime),\
             patch.object(self.worker,'no_workers'),\
             patch.object(self.worker,'module',side_effect=modules),\
             patch.object(self.worker,'run_logged',side_effect=logged),\
             patch.object(self.worker.subprocess,'run',side_effect=commands),\
             patch.dict('os.environ',{'ARK_AUTO_MINUTE_RESUME_ONLY':'1'}),\
             contextlib.redirect_stdout(output):
            self.worker.native(self.f.binding_file,self.symbols)
        return output.getvalue()

    def test_saved_log_to_46_handoff_without_recollecting(self):
        out=self.run_native()
        self.assertEqual(self.capture_calls,0)
        self.assertEqual(self.publish_calls,1)
        self.assertIn('NEXT_SESSION_HANDOFF_READY',out)
        self.assertEqual(self.oldstate.read_bytes(),self.old_bytes)
        self.assertEqual(self.log.read_bytes(),self.log_bytes)
        pointer=self.f.private/'prepared-days/2026-11-10.json'
        self.assertEqual(status.validate_pointer(pointer,self.f.private)[0]['selectedCount'],46)
        self.run_native()
        self.assertEqual(self.publish_calls,1,'Completed handoff should be reused')
        self.assertEqual(self.capture_calls,0)

    def test_crash_after_log_copy_can_resume_without_collision(self):
        original=self.worker.Pipeline.save
        def cut(pipe,state,**changes):
            if changes.get('phase')=='CAPTURED' and not pipe.state_file.exists():
                raise KeyboardInterrupt('power cut after saved log copy')
            return original(pipe,state,**changes)
        with patch.object(self.worker.Pipeline,'save',new=cut):
            with self.assertRaises(KeyboardInterrupt):self.run_native()
        self.run_native()
        self.assertEqual(self.capture_calls,0)
        self.assertEqual(self.oldstate.read_bytes(),self.old_bytes)

    def test_incomplete_saved_log_does_not_trigger_recollection(self):
        self.log.write_text('NO11_WEEKLY_NIGHTLY_ASOF=2026-11-09\nORDER_TRANSMISSION=False\n',encoding='utf-8')
        with self.assertRaises(ValueError):self.run_native()
        self.assertEqual(self.capture_calls,0)
        self.assertFalse((self.f.private/'prepared-days/2026-11-10.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
