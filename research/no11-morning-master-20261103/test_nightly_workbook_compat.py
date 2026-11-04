"""Nightly Excel book compatibility: strict identity and byte-preserving edits."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import nightly_workbook_compat as c
import install_daily_cycle as installer

ENGINE=ROOT/'research/no12-prebuy-causal-runtime-20261011'

class NightlyBookTests(unittest.TestCase):
    def test_all_three_original_collectors_have_single_specific_anchor(self):
        self.assertEqual(len(c.SCRIPTS),3)
        for name,anchor in c.SCRIPTS.items():
            with self.subTest(name=name):
                raw=(ENGINE/name).read_bytes()
                changed=c.transform_collector(name,raw)
                self.assertNotEqual(changed,raw)
                self.assertIn(c.MARKER.encode(),changed)
                self.assertIn(b'ARK_ORDER_IDS_READONLY',changed)
                self.assertIn(b'Count -notin @(2,3)',changed)
                self.assertNotIn(anchor.encode(),changed)
                self.assertEqual(c.transform_collector(name,changed),changed)

    def test_unknown_collector_rejected(self):
        with self.assertRaisesRegex(ValueError,'UNKNOWN_COLLECTOR'):
            c.transform_collector('windows/other.ps1',b'not original')

    def test_launcher_still_does_normal_trade_check(self):
        path=ENGINE/'windows/Start-No11UnifiedLauncher.ps1'
        original=path.read_bytes()
        bom=b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b''
        text=original[len(bom):].decode('utf-8')
        text=text.replace('function RunTrade($cfg,[bool]$approved){',
          'function RunTrade($cfg,[bool]$approved){\n #--same-day-operator-approved\n #No11RssFundingContract.ps1')
        weekly=installer.patch_weekly_launcher(bom+text.encode())
        new=c.transform_launcher(weekly)
        self.assertIn(c.MARKER.encode(),new)
        self.assertIn(b'if($live -or $files.Count -eq 3)',new)
        self.assertIn(b'CheckExcel $cfg $true',new)
        self.assertNotIn(b'RssStockOrder(',new)
        self.assertEqual(c.transform_launcher(new),new)

    def test_weekly_carry_supports_missing_optional_throughput_argument(self):
        weekly=(ENGINE/'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1').read_bytes()
        optional=b" if($RefreshAutoMaxThroughput){$rargs+=@('-AutoMaxThroughput')}"
        self.assertEqual(weekly.count(optional),1)
        customized=weekly.replace(optional,b'')
        result=c.transform_first_week_carry(customized)
        self.assertIn(c.CARRY_MARKER.encode(),result)
        self.assertNotIn(optional,result)
        self.assertEqual(result.count(b" if($carryFridayRun){$rargs+=@('-CarryFridayRun',$carryFridayRun)}"),1)
        self.assertIn(b" if($WeekendFridayLimited){$rargs+=@('-FirstBuyFridayLimited')}",result)
        self.assertEqual(c.transform_first_week_carry(result),result)

    def test_weekly_carry_rejects_missing_both_argument_anchors(self):
        weekly=(ENGINE/'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1').read_bytes()
        missing_optional=weekly.replace(
            b" if($RefreshAutoMaxThroughput){$rargs+=@('-AutoMaxThroughput')}",b'')
        missing_both=missing_optional.replace(
            b" if($WeekendFridayLimited){$rargs+=@('-FirstBuyFridayLimited')}",b'')
        with self.assertRaisesRegex(ValueError,'CARRY_ORCHESTRATOR_RARGS_CHANGED'):
            c.transform_first_week_carry(missing_both)

    @unittest.skipUnless(os.name=='nt','Windows PowerShell parser')
    def test_patched_powershell_syntax(self):
        for name in c.SCRIPTS:
            raw=(ENGINE/name).read_bytes()
            source=c.transform_collector(name,raw)
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as temp:
                    p=Path(temp)/'candidate.ps1';p.write_bytes(source)
                    command=("$t=$null;$e=$null;"
                        "[void][Management.Automation.Language.Parser]::ParseFile('"
                        +str(p).replace("'","''")+"',[ref]$t,[ref]$e);"
                        "if($e.Count){$e|Out-String|Write-Host;exit 2}")
                    r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive',
                                       '-Command',command],capture_output=True,text=True,timeout=50)
                    self.assertEqual(r.returncode,0,r.stdout+r.stderr)

if __name__=='__main__':
    unittest.main(verbosity=2)
