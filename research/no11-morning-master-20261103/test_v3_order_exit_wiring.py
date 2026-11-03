"""Pure regression tests for BUY -> broker observation -> original EXIT order wiring.

No Excel, broker API, network calls, generated approvals or live orders.
"""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
ENGINE=ROOT/'research/no12-prebuy-causal-runtime-20261011'
sys.path.insert(0,str(HERE))
import live_collector_order_patch as patch

class SessionTransportTests(unittest.TestCase):
    def test_pins_existing_broker_observer_session_not_random_guid(self):
        ps=(HERE/'Prepare-No11AutomaticLiveTransportV3.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('New-No11ExcelSession',ps)
        self.assertIn('BrokerSnapshotLibrary',ps)
        self.assertIn("$sessionKey=[string]$observedSession.sessionKey",ps)
        self.assertNotIn("$sessionKey='ARKNO11:'",ps)
        self.assertIn("$trigger.Value2=0",ps)
        self.assertNotIn("$trigger.Value2=1",ps)
        self.assertIn("approvedForSession=$true",ps)
        self.assertIn("'ARK_NO11_SEND_ONCE'",ps)

    def test_transport_probe_does_not_send_order(self):
        text=(HERE/'Prepare-No11AutomaticLiveTransportV3.ps1').read_text(encoding='utf-8-sig')
        for forbidden in ('RssStockOrder(', 'RssCancelOrder(', 'Set-No11LedgerApproval',
                          'RssOrderList(', 'RssExecutionList('):
            self.assertNotIn(forbidden,text)

    def test_controller_env_is_only_exported_for_live(self):
        source=(ENGINE/patch.CONTROLLER).read_bytes()
        patched=patch.transform_controller(source)
        script=patched.decode('utf-8-sig')
        compile(script,'controller.py','exec')
        self.assertIn(patch.CONTROLLER_MARKER,script)
        self.assertIn('if allow_explicit_live:',script)
        self.assertIn('ARK_NO11_PINNED_C50_READY_SHA256',script)
        self.assertIn('hashlib.sha256(attempt.ready.read_bytes()).hexdigest()',script)
        self.assertIn('should_stop=stopped',script)
        self.assertIn('bootstrap.service.main(consumer_args(',script)
        self.assertEqual(script.count('--preflight-only'),source.decode('utf-8-sig').count('--preflight-only'))
        self.assertEqual(patched,patch.transform_controller(patched))

    def test_sender_accepts_only_pinned_original_collector_temporary_book(self):
        source=(ENGINE/patch.SENDER).read_bytes()
        patched=patch.transform_sender(source)
        text=patched.decode('utf-8-sig')
        self.assertIn(patch.SENDER_MARKER,text)
        self.assertIn('C50_READY_BYTES_CHANGED',text)
        self.assertIn('Get-FileHash -LiteralPath $readyPath -Algorithm SHA256',text)
        self.assertIn("ARK_NO11_C50_COLLECTOR_READY_V1",text)
        self.assertIn("ARK_NO11_C50_TEMP_",text)
        self.assertIn("TEMPORARY_BOOKWORKS_CHART_CHANGED",text.replace(
            "TEMPORARY_WORKBOOKS_CHANGED","TEMPORARY_BOOKWORKS_CHART_CHANGED"))
        self.assertIn('Get-Process -Id',text)
        self.assertIn('Assert-No11Readback',text)
        self.assertIn("OPEN_WORKBOOKS_CHANGED",text)
        self.assertIn("PERMIT_ALREADY_CONSUMED",text)
        self.assertIn("$state.trigger.Value2=1",text)
        self.assertEqual(text.count('$state.trigger.Value2=1'),1)
        self.assertEqual(patched,patch.transform_sender(patched))

    def test_controller_patch_does_not_touch_strategy_or_exit(self):
        source=(ENGINE/patch.CONTROLLER).read_bytes()
        patched=patch.transform_controller(source)
        self.assertEqual(source.count(b'--operator-approved-broker-live'),
                         patched.count(b'--operator-approved-broker-live'))
        self.assertEqual(source.count(b'launch_same_run('),patched.count(b'launch_same_run('))
        self.assertIn('original',b'original'.decode())  # no strategy patched here
        self.assertNotIn('RssStockOrder(',patched.decode('utf-8-sig'))

    def test_upgrade_requires_original_rss_funding_helper(self):
        script=(HERE/'upgrade_live_trade_v3.py').read_text(encoding='utf-8')
        self.assertIn('No11RssFundingContract.ps1',script)
        self.assertIn('AUTO_RSS_BUYING_POWER',script)
        self.assertIn('TRANSPORT_EXCEL_SESSION=ORIGINAL_READ_ONLY_OBSERVER_ID',script)
        self.assertIn("assert_stopped()",script)
        self.assertIn('for path,before,after in reversed(changed):',script)

if __name__=='__main__':
    unittest.main(verbosity=2)
