"""Read-only source contracts for 08:30 standby -> one 09:00 native request.

Does not create a reservation, start Excel, send orders, or reach the broker.
"""
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent / "no12-prebuy-causal-runtime-20261011" / "windows" / "Start-No11UnifiedLauncher.ps1"


class PreopenContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = (HERE / "Start-No11PreopenStandby.ps1").read_text(encoding="utf-8-sig")
        cls.installer = (HERE / "Apply-No11PreopenStandby.ps1").read_text(encoding="utf-8-sig")
        cls.ui = (HERE / "Start-No11OneClick.ps1").read_text(encoding="utf-8-sig")
        cls.native = NATIVE.read_text(encoding="utf-8-sig")

    def test_does_not_weaken_native_0900_gate(self):
        self.assertIn("-ge '09:00:00'", self.native)
        self.assertIn("Need $approved 'TODAYS_EXPLICIT_OPERATOR_APPROVAL_REQUIRED'", self.native)
        self.assertIn("CheckExcel $cfg $true", self.native)
        self.assertIn("StartChild 'TRADE'", self.native)

    def test_standby_0830_and_single_native_0900(self):
        w = self.worker
        self.assertIn("HH:mm:ss') -ge '08:30:00'", w)
        self.assertIn("HH:mm:ss') -lt '09:00:00'", w)
        self.assertIn("HH:mm:ss') -ge '09:00:00'", w)
        self.assertIn("HH:mm:ss') -lt '09:02:00'", w)
        self.assertIn("'PREOPEN-'+$day+'.request.json'", w)
        self.assertIn("'PREOPEN-'+$day+'.execution-claimed'", w)
        self.assertIn("[IO.FileMode]::CreateNew", w)
        self.assertIn("PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED", w)
        self.assertIn("'TRADE-'+$day+'.launch.json'", w)
        self.assertIn("TRADE_ALREADY_STARTED_NO_DUPLICATE", w)
        self.assertIn("HANDOFF_CHANGED_SINCE_APPROVAL", w)
        self.assertIn("NATIVE_CODE_CHANGED_SINCE_APPROVAL", w)
        self.assertIn("STANDBY_CODE_CHANGED", w)
        self.assertIn("0900_PRECHECK_FAILED", w)
        self.assertIn("'-Mode','Trade','-IApproveOrdersForToday'", w)
        self.assertIn("PREOPEN_NEVER_RETRIES_TRADE=True", w)
        self.assertNotIn("Stop-Process", w)
        self.assertNotIn("Set-Content", w)
        self.assertNotIn("RssStockOrder", w)
        self.assertNotIn("Remove-Item", w)

    def test_manual_today_approval_before_queue(self):
        w, ui = self.worker, self.ui
        self.assertIn("Need $IApproveOrdersForToday 'SAME_DAY_EXPLICIT_APPROVAL_REQUIRED'", w)
        self.assertIn("$req.sameDayExplicitOrderApproval -eq $true", w)
        self.assertIn("HANDOFF_NOT_PREOPEN_READY", w)
        self.assertIn("'OUTSIDE_ENTRY_WINDOW'", w)
        self.assertIn("'NEW_ENTRY_WINDOW_CLOSED'", w)
        self.assertIn("if(CanQueuePreopen $s){", ui)
        self.assertIn("if($approval -ne [System.Windows.Forms.DialogResult]::Yes){return}", ui)
        self.assertIn("-Mode Arm -IApproveOrdersForToday", ui)
        self.assertIn("NO11_PREOPEN_STANDBY=ARMED", ui)
        self.assertIn("$trade.Enabled=(($s.canRequestTrade -eq $true) -or $preopen) -and (-not $reserved)", ui)
        self.assertIn("ARK_NO11_ONECLICK_PREOPEN_STANDBY_0830_V1", ui)

    def test_white_theme_byte_equal_outside_patches(self):
        p = self.installer
        self.assertIn("LOCAL_TRADING_ANCHOR_CHANGED", p)
        self.assertIn("LOCAL_ENABLE_ANCHOR_CHANGED", p)
        self.assertIn("LOCAL_CLICK_ANCHOR_CHANGED", p)
        self.assertIn("WHITE_THEME_OR_LAYOUT_CHANGED", p)
        self.assertIn("$local.Substring($s0,$s1-$s0) -ceq $patched.Substring($p0,$p1-$p0)", p)
        self.assertIn("WhiteOneClick.before.ps1", p)
        self.assertIn("[IO.File]::Replace($candidate,$target,$replaceBackup)", p)
        self.assertNotIn("[IO.File]::Replace($candidate,$target,$null)", p)
        self.assertIn("WHITE_ONECLICK_THEME_CHANGED=False", p)
        self.assertIn("NATIVE_0900_BROKER_GATES_UNCHANGED=True", p)
        self.assertNotIn("Invoke-No11MsiiOrder.ps1", p)


if __name__ == "__main__":
    unittest.main()
