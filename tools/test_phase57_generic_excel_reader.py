import tempfile
import unittest
import zipfile
from html import escape
from pathlib import Path
from phase57_generic_excel_reader import inspect_generic_workbook

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

def column(index):
    result = ''
    while index:
        index, remainder = divmod(index - 1, 26); result = chr(65 + remainder) + result
    return result

def sheet_xml(rows, formula=False):
    output = [f'<worksheet xmlns="{NS}"><sheetData>']
    for row_index, row in enumerate(rows, 1):
        output.append(f'<row r="{row_index}">')
        for col_index, value in enumerate(row, 1):
            ref = f'{column(col_index)}{row_index}'
            if isinstance(value, bool): output.append(f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>')
            elif isinstance(value, (int, float)): output.append(f'<c r="{ref}"><v>{value}</v></c>')
            else: output.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        if formula and row_index == 1: output.append('<c r="Z1"><f>1+1</f><v>2</v></c>')
        output.append('</row>')
    output.append('</sheetData></worksheet>')
    return ''.join(output)

def make_workbook(file, *, formula=False, actual=False):
    names = ['ARK_CONFIG', 'ARK_MASTER', 'ARK_BARS', 'ARK_HEALTH']
    workbook = [f'<workbook xmlns="{NS}" xmlns:r="{REL_NS}"><sheets>']
    relations = [f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for index, name in enumerate(names, 1):
        workbook.append(f'<sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>')
        relations.append(f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>')
    workbook.append('</sheets></workbook>'); relations.append('</Relationships>')
    config = [['key', 'value'], ['schemaId', 'ARK_GENERIC_TIMESERIES_V1'], ['mode', 'LOCAL_SHADOW_RESEARCH_ONLY'], ['sourceClass', 'SYNTHETIC_TRANSPORT_TEST'], ['actualMarketData', actual], ['universeComplete', True], ['masterComplete', True], ['sessionDate', '2026-08-13']]
    master = [['sourceCode', 'symbol', 'sector', 'marketCode', 'productCategory', 'effectiveAt'], ['1000', '1000.T', 'TEST', 'TSE', 'EQUITY', '2026-08-12T00:00:00.000Z']]
    bars = [['captureId', 'symbol', 'timestamp', 'availableAt', 'open', 'high', 'low', 'close', 'volume']]
    for index in range(12):
        start = f'2026-08-13T00:{index*5:02d}:00.000Z' if index < 12 else ''
        available = f'2026-08-13T00:{(index+1)*5:02d}:00.000Z' if index < 11 else '2026-08-13T01:00:00.000Z'
        bars.append(['capture-12', '1000.T', start, available, 100, 102, 99, 101, 1000])
    health = [['captureId', 'timestamp', 'connected', 'workbookHealthy', 'stale', 'rssError', 'sessionEnd'], ['capture-12', '2026-08-13T01:00:00.000Z', True, True, False, False, False]]
    with zipfile.ZipFile(file, 'w') as archive:
        archive.writestr('xl/workbook.xml', ''.join(workbook))
        archive.writestr('xl/_rels/workbook.xml.rels', ''.join(relations))
        for index, rows in enumerate([config, master, bars, health], 1): archive.writestr(f'xl/worksheets/sheet{index}.xml', sheet_xml(rows, formula=formula and index == 3))

class GenericReaderTests(unittest.TestCase):
    def test_formula_free_complete_master_becomes_full_pit_point(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'input.xlsx'; make_workbook(file)
            packet = inspect_generic_workbook(file)
            self.assertEqual(packet['schemaId'], 'ARK_PHASE57_FROZEN_MAIN_PACKET_V1')
            self.assertEqual(len(packet['points']), 1)
            self.assertEqual(len(packet['points'][0]['universe'][0]['bars']), 12)
            self.assertTrue(packet['points'][0]['universeComplete'])
            self.assertEqual(len(packet['points'][0]['memberSetSha256']), 64)

    def test_formula_and_source_class_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            formula = Path(directory) / 'formula.xlsx'; make_workbook(formula, formula=True)
            with self.assertRaisesRegex(ValueError, 'ALL_FORMULAS_FORBIDDEN'): inspect_generic_workbook(formula)
            actual = Path(directory) / 'actual.xlsx'; make_workbook(actual, actual=True)
            with self.assertRaisesRegex(ValueError, 'SOURCE_CLASS_DATA_FLAG_MISMATCH'): inspect_generic_workbook(actual)

if __name__ == '__main__': unittest.main()
