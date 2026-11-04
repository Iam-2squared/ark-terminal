"""Source-only safety contracts for the OneClick -> native LIVE UI2 handoff."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
ENGINE = ROOT.parent / "no12-prebuy-causal-runtime-20261011" / "windows"


class OneClickUi2AutoOpenTests(unittest.TestCase):
    def setUp(self):
        self.one = (ROOT / "Start-No11OneClick.ps1").read_text(encoding="utf-8-sig")
        self.watch = (ROOT / "Watch-No11OneClickTradeUi.ps1").read_text(encoding="utf-8-sig")
        self.install = (ROOT / "Apply-No11OneClickUi2AutoOpen.ps1").read_text(encoding="utf-8-sig")
        self.native = (ENGINE / "Start-No11UnifiedLauncher.ps1").read_text(encoding="utf-8-sig")

    def test_old_native_trade_already_opens_readonly_ui(self):
        self.assertIn("$ui=Join-Path $PSScriptRoot 'Start-No11LiveUiReadOnly.ps1'", self.native)
        self.assertIn("StartChild 'TRADE' $trade", self.native)
        self.assertIn("NO11_UI2_LIVE_ONLY=LOCAL_BROWSER_OPEN_REQUESTED", self.native)
        self.assertIn("NO11_UNIFIED_UI2_LIVE=", self.native)

    def test_oneclick_only_watches_trade_after_native_launch(self):
        marker = "ARK_NO11_ONECLICK_TRADE_UI2_AUTOOPEN_WATCH_V1"
        self.assertEqual(self.one.count(marker), 1)
        start = self.one.index("function StartOriginal")
        end = self.one.index("if($Mode -eq 'Status')", start)
        subset = self.one[start:end]
        self.assertLess(subset.index("Start-Process -FilePath 'powershell.exe'"),
                        subset.index(marker))
        self.assertIn("if($runMode -eq 'Trade')", subset)
        self.assertIn("'-NativeLog',(Quote $files[0])", subset)
        self.assertIn("Watch-No11OneClickTradeUi.ps1", subset)
        self.assertIn("return $p.Id", subset)
        self.assertIn("if($answer -ne [System.Windows.Forms.DialogResult]::Yes){return}", self.one)
        self.assertIn("$trade.Enabled=(($s.canRequestTrade -eq $true) -or $preopen) -and (-not $reserved)", self.one)

    def test_watcher_cannot_launch_trade_or_override_halt(self):
        self.assertIn("NO11_UNIFIED_TRADE_LAUNCHED_PID=", self.watch)
        self.assertIn("NO11_UNIFIED_UI2_LIVE=LIVE_ONLY_UI_FAILED_CHECK_BROKER_AND_LOGS", self.watch)
        self.assertIn("NO11_UNIFIED_UI2_LIVE=LIVE_ONLY_UI_BROWSER_REQUESTED", self.watch)
        self.assertIn("EXPLICIT_UI_FAILURE", self.watch)
        self.assertIn("NO_CONFIRMED_TRADE_REQUEST", self.watch)
        self.assertIn("TRADE_RECEIPT_NOT_SAME_DAY", self.watch)
        self.assertIn("-File $helper -ConfigFile $config", self.watch)
        self.assertNotIn("-IApproveOrdersForToday", self.watch)
        self.assertNotIn("-IApproveFullArkLiveOrdersForThisSession", self.watch)
        self.assertNotIn("Stop-Process", self.watch)
        self.assertNotIn("Remove-Item", self.watch)
        self.assertNotIn("RssStockOrder", self.watch)

    def test_installer_preserves_local_theme_and_original_orders(self):
        self.assertIn("$target=Join-Path $oneclick 'Start-No11OneClick.ps1'", self.install)
        self.assertIn("LOCAL_STARTORIGINAL_ANCHOR_NOT_FOUND", self.install)
        self.assertIn("CLOSE_ONECLICK_AND_ARK_ENGINE_FIRST", self.install)
        self.assertIn("WHITE_ONECLICK_THEME_REPLACED=False", self.install)
        self.assertIn("Start-No11OneClick.before.ps1", self.install)
        self.assertIn("GitBlob $watchBytes", self.install)
        self.assertIn("Parse $candidate", self.install)
        self.assertIn("$normal.Replace($anchor,$replacement)", self.install)
        self.assertIn("$replaceBackup=Join-Path $backup 'Start-No11OneClick.replace-original.ps1'", self.install)
        self.assertIn("[IO.File]::Replace($candidate,$target,$replaceBackup)", self.install)
        self.assertNotIn("[IO.File]::Replace($candidate,$target,$null)", self.install)
        self.assertIn("ARK_NO11_ONECLICK_TRADE_UI2_AUTOOPEN_WATCH_V1", self.install)
        self.assertNotIn("Set-Content", self.install)
        self.assertNotIn("Invoke-No11MsiiOrder.ps1", self.install)


if __name__ == "__main__":
    unittest.main()
