import tempfile
import unittest
import zipfile
from pathlib import Path
from phase57_offline_excel_reader import inspect_fixture, ROOT

class OfflineReaderTests(unittest.TestCase):
    def test_pinned_template(self):
        x = inspect_fixture(ROOT/'tools/templates/ArkParityOffline.xlsx')
        self.assertEqual(len(x['bars']), 7)
        self.assertIs(x['bars'][0]['finalized'], True)
        self.assertEqual(x['bars'][0]['captureAt'], '2026-08-13T00:05:00.000Z')

    def test_unapproved_workbook(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'wrong.xlsx'
            p.write_bytes(b'not a workbook')
            with self.assertRaisesRegex(ValueError, 'UNAPPROVED_WORKBOOK'):
                inspect_fixture(p)

    def test_active_formula_and_cell_error(self):
        original = ROOT/'tools/templates/ArkParityOffline.xlsx'
        for payload,reason in [('<f>1+1</f>', 'ALL_ACTIVE_FORMULAS'), ('<v>#N/A</v>', 'RSS_CELL_ERROR')]:
            with tempfile.TemporaryDirectory() as d:
                p = Path(d)/'mutation.xlsx'
                with zipfile.ZipFile(original) as src, zipfile.ZipFile(p,'w') as dst:
                    for name in src.namelist():
                        data = src.read(name)
                        if name == 'xl/worksheets/sheet3.xml':
                            payload = payload.replace('<f>', '<x:f>').replace('</f>', '</x:f>').replace('<v>', '<x:v>').replace('</v>', '</x:v>')
                            cell = '<x:c r="N2"'+(' t="e"' if 'ERROR' in reason else '')+'>'+payload+'</x:c>'
                            data = data.replace(b'</x:row>', (cell+'</x:row>').encode(), 1)
                        dst.writestr(name,data)
                with self.assertRaisesRegex(ValueError, reason):
                    inspect_fixture(p,pin=False)

if __name__ == '__main__':
    unittest.main()
