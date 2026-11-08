import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import patch_no11_transport_resilience as p


class TransportResilienceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(__file__).with_name('Prepare-No11AutomaticLiveTransportV3.ps1').read_bytes()

    def test_real_original_transforms(self):
        self.assertEqual(p.blob(self.source.replace(b'\r\n', b'\n')), p.BASE_BLOB)
        out = p.transform(self.source).decode('utf-8-sig')
        self.assertIn(p.MARKER, out)
        self.assertIn('FINAL_EXCEL_SESSION_IDENTITY', out)
        self.assertIn('AUTOMATIC_TRANSPORT_DIAGNOSTIC_STAGE=', out)
        self.assertIn('AUTOMATIC_TRANSPORT_HRESULT=', out)
        self.assertIn('AUTOMATIC_TRANSPORT_SOURCE_LINE=', out)

    def test_no_write_retry_and_no_broker_send(self):
        out = p.transform(self.source).decode('utf-8-sig')
        for token in ("$guard.Value2='ARK_NO11_SEND_ONCE'", '$trigger.Value2=0',
                      '$session.Value2=$sessionKey', '$formula.ClearContents()',
                      '$orderBook=$excel.Workbooks.Open($order)'):
            self.assertEqual(out.count(token), 1)
        helper = out[out.index('function Wait-No11TransportReadiness'):out.index('function Assert-No11TransportSessionStable')]
        self.assertNotIn('.Value2=', helper)
        self.assertNotIn('.Open(', helper)
        self.assertNotIn('RssStockOrder(', out)
        self.assertNotIn('$trigger.Value2=1', out)

    def test_all_original_fail_closed_checks_remain(self):
        original = self.source.decode('utf-8-sig').replace('\r\n', '\n')
        out = p.transform(self.source).decode('utf-8-sig')
        for line in original.splitlines():
            if line.lstrip().startswith('Need ') and "'EXCEL_NOT_READY'" not in line:
                self.assertIn(line, out)

    def test_unknown_local_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_LOCAL_SOURCE'):
            p.transform(self.source + b'# local\n')

    def test_crlf_bom_are_preserved(self):
        raw = b'\xef\xbb\xbf' + self.source.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        out = p.transform(raw)
        self.assertTrue(out.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n', out.replace(b'\r\n', b''))

    def test_patch_is_not_reapplied_to_modified_source(self):
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_LOCAL_SOURCE'):
            p.transform(p.transform(self.source))

if __name__ == '__main__':
    unittest.main(verbosity=2)
