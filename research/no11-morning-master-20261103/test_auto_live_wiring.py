"""Offline tests for first same-day broker wiring. No Excel, network, broker or orders."""
import hashlib, json
from pathlib import Path
import sys, tempfile, unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import launcher_automatic_bridge_v2 as b

class AutoLiveWiringTests(unittest.TestCase):
    def test_arrival_discovery_is_hash_pinned(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); data=b'fixture-arrival'
            old_size,old_sha=b.ARRIVAL_BYTES,b.ARRIVAL_SHA256
            try:
                b.ARRIVAL_BYTES=len(data); b.ARRIVAL_SHA256=hashlib.sha256(data).hexdigest()
                (root/'wrong').write_bytes(b'x'*len(data))
                good=root/'deep'; good.mkdir(); (good/'arrival.json').write_bytes(data)
                self.assertEqual(b.discover_original_arrival(root), (good/'arrival.json').resolve())
            finally:
                b.ARRIVAL_BYTES, b.ARRIVAL_SHA256=old_size,old_sha

    def test_current_rss_broker_merge_preserves_physical_and_private_root(self):
        day='2026-11-04'
        prepared={'schemaId':'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1','sessionDate':day,
          'productionReady':False,'orderTransmission':False,'privateRoot':'P2',
          'orderIdWorkbookPath':'C:/broker.xlsx','runtimeRoot':'R','h235ModelRoot':'H',
          'precomputedChartReceipt':'C','precomputedG1Mask':'M','weeklySourceRun':'W'}
        old=dict(prepared,privateRoot='P1',brokerExecutionConfig='B')
        broker={'schemaId':'ARK_NO11_BROKER_EXECUTION_CONFIG_V1','sessionDate':day,
          'fundingPolicy':'RSS_BUYING_POWER','feeCourse':'ZERO','orderTransmission':True,
          'productionReady':False,'transport':{'sessionDate':day,'mode':'LIVE',
          'operatorEnabled':True,'approvedForSession':True,'orderTransmission':True,
          'workbookPath':'C:/broker.xlsx'},'ledger':{'maxSymbols':3,'lotSize':100,
          'account':'一般','allocatedCashJpy':'AUTO_RSS_BUYING_POWER'},
          'orderTerms':{'sor':True,'accountType':1,'accountTypeVerified':True,
          'orderType':'MARKET','timeInForce':'DAY'}}
        merged=b.merge_current_broker(prepared,old,broker,day)
        self.assertEqual(merged['privateRoot'],'P1')
        self.assertEqual(merged['brokerExecutionConfig'],'B')
        self.assertFalse(merged['orderTransmission'])

    def test_old_session_broker_cannot_merge(self):
        p={'sessionDate':'2026-11-04'}
        with self.assertRaisesRegex(ValueError,'BROKER_MUST_BE_CURRENT_SESSION'):
            b.merge_current_broker(p,{'sessionDate':'2026-11-03'}, {}, '2026-11-04')

    def test_probe_and_bridge_do_not_contain_order_trigger_write(self):
        root=Path(__file__).resolve().parent
        probe=(root/'Prepare-No11AutomaticLiveTransport.ps1').read_text(encoding='utf-8-sig')
        bridge=Path(b.__file__).read_text(encoding='utf-8')
        self.assertNotIn('RssStockOrder(', probe)
        self.assertNotIn('RssCancelOrder(', probe)
        self.assertNotIn('$trigger.Value2=1', probe)
        self.assertNotIn('RssStockOrder(', bridge)
        self.assertIn('SAME_DAY_OPERATOR_APPROVAL_REQUIRED', bridge)
        self.assertIn('RSS_BUYING_POWER', bridge)

    def test_transport_probe_initializes_only_zero_trigger(self):
        text=(Path(__file__).resolve().parent/'Prepare-No11AutomaticLiveTransport.ps1').read_text(encoding='utf-8-sig')
        self.assertIn("$trigger.Value2=0",text)
        self.assertIn("guardValue='ARK_NO11_SEND_ONCE'",text)
        self.assertIn("approvedForSession=$true",text)
        self.assertIn("SameDayOperatorApproved",text)

if __name__=='__main__':
    unittest.main(verbosity=2)
