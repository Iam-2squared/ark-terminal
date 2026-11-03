"""Offline tests of date-scoped nightly handoff selection."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import daily_cycle as cycle
import launcher_automatic_bridge_v4 as bridge
import install_daily_cycle as installer

def sha(data):
    return hashlib.sha256(data).hexdigest()

class DailyCycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.record={'sessionDate':'2026-11-05','previousSession':'2026-11-04',
                     'nightlyMode':'CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE'}
        self.handoff={'schemaId':'ARK_NO11_MORNING_MASTER_HANDOFF_V1',
                      'sessionDate':'2026-11-05','previousSession':'2026-11-04',
                      'selectedSymbols':['1111.T','2222.T'],'reviewStatus':'NOT_REVIEWED',
                      'datedMasterCreated':False,'productionReady':False,'orderTransmission':False}
        raw=cycle.encode(self.handoff)
        self.handoff_file=self.root/('morning-handoff-'+sha(raw)+'.json')
        self.handoff_file.write_bytes(raw)

    def example(self,friday=False):
        out=[
          'NO11_WEEKLY_NIGHTLY_NEXT_SESSION='+('2026-11-09' if friday else '2026-11-05'),
          'NO11_WEEKLY_NIGHTLY_ASOF='+('2026-11-06' if friday else '2026-11-04'),
          'NO11_PREVIOUS_ARCHIVE_STAGE=C:\\safe\\archive.json',
          'NO11_PREVIOUS_CAPTURE_DIR=C:\\safe\\capture',
          'ORDER_TRANSMISSION=False'
        ]
        if friday:
            out+=['NO11_NIGHTLY_DAILY_RUN=C:\\safe\\full',
                  'NO11_NIGHTLY_CHART50=C:\\safe\\chart.json',
                  'NO11_NIGHTLY_MASK=C:\\safe\\mask.json',
                  'NO11_WEEKLY_NIGHTLY_STAGE=FRIDAY_FULL_UNIVERSE_AND_PREVIOUS_COMPLETE']
        else:
            out+=['NO11_WEEKLY_NIGHTLY_POOL_SOURCE=C:\\safe\\weekly',
                  'NO11_WEEKLY_NIGHTLY_REFRESH_RUN=C:\\safe\\run',
                  'NO11_WEEKLY_NIGHTLY_CURRENT_CHART50=C:\\safe\\chart.json',
                  'NO11_WEEKLY_NIGHTLY_CURRENT_MASK=C:\\safe\\mask.json',
                  'NO11_WEEKLY_NIGHTLY_STAGE=CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE']
        return ('\n'.join(out)+'\n').encode()

    def test_weekday_completion(self):
        value=cycle.parse_nightly(self.example())
        self.assertEqual(value['sessionDate'],'2026-11-05')
        self.assertEqual(value['previousSession'],'2026-11-04')
        self.assertEqual(value['nightlyMode'],self.record['nightlyMode'])

    def test_friday_full_universe(self):
        value=cycle.parse_nightly(self.example(True))
        self.assertEqual(value['sessionDate'],'2026-11-09')
        self.assertEqual(value['weekly'],value['run'])

    def test_failed_job_does_not_become_next_day(self):
        value=self.example().replace(
          b'NO11_WEEKLY_NIGHTLY_STAGE=CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE',
          b'NO11_WEEKLY_NIGHTLY_STAGE=BLOCKED')
        with self.assertRaisesRegex(ValueError,'NIGHTLY_NOT_COMPLETE'):
            cycle.parse_nightly(value)

    def test_duplicate_marker_rejected(self):
        value=self.example()+b'NO11_WEEKLY_NIGHTLY_NEXT_SESSION=2026-11-06\n'
        with self.assertRaisesRegex(ValueError,'NIGHTLY_LOG_MARKER'):
            cycle.parse_nightly(value)

    def test_immutable_pointer_and_trade_selection(self):
        pointer=cycle.publish(self.root,self.record,self.handoff_file,'1'*64,'2'*64)
        self.assertEqual(pointer,self.root/'prepared-days/2026-11-05.json')
        self.assertEqual(pointer,cycle.publish(self.root,self.record,self.handoff_file,'1'*64,'2'*64))
        with self.assertRaisesRegex(ValueError,'DAY_ALREADY_PINNED'):
            cycle.publish(self.root,self.record,self.handoff_file,'3'*64,'2'*64)
        tool=HERE/'daily_cycle.py'
        binding={'sessionDate':'2026-11-04','dailyCycleRoot':str(self.root),
                 'dailyCycleTool':str(tool),'dailyCycleToolSha256':sha(tool.read_bytes())}
        active=bridge.resolve_daily_binding(binding,'2026-11-05')
        self.assertEqual(active['sessionDate'],'2026-11-05')
        self.assertEqual(active['handoff'],str(self.handoff_file))
        self.assertEqual(bridge.resolve_daily_binding(binding,'2026-11-04'),binding)

    def test_edit_protection(self):
        cycle.publish(self.root,self.record,self.handoff_file,'1'*64,'2'*64)
        self.handoff_file.write_bytes(self.handoff_file.read_bytes()+b' ')
        tool=HERE/'daily_cycle.py'
        binding={'sessionDate':'2026-11-04','dailyCycleRoot':str(self.root),
                 'dailyCycleTool':str(tool),'dailyCycleToolSha256':sha(tool.read_bytes())}
        with self.assertRaisesRegex(ValueError,'NEXT_SESSION_HANDOFF_CHANGED'):
            bridge.resolve_daily_binding(binding,'2026-11-05')

    def test_only_weekly_launcher_target_changes(self):
        original=(Path(__file__).resolve().parents[2]/
          'research/no12-prebuy-causal-runtime-20261011/windows/Start-No11UnifiedLauncher.ps1').read_bytes()
        bom=b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b''
        text=original[len(bom):].decode()
        text=text.replace('function RunTrade($cfg,[bool]$approved){',
           'function RunTrade($cfg,[bool]$approved){\n #--same-day-operator-approved\n #No11RssFundingContract.ps1')
        content=bom+text.replace('\n','\r\n').encode()
        patched=installer.patch_weekly_launcher(content)
        self.assertIn(installer.NEW.encode(),patched)
        self.assertNotIn(installer.OLD.encode(),patched)
        self.assertEqual(patched,installer.patch_weekly_launcher(patched))

if __name__=='__main__':
    unittest.main(verbosity=2)
