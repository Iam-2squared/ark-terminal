"""Offline only: verify 16-digit original + exact 64-digit exclusion lineage."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / 'no12-prebuy-causal-runtime-20261011'
sys.path.insert(0, str(HERE))
import no11_weekly_filtered_lineage as patch


def write(root, prefix, value, length=64):
    body = (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    sha = hashlib.sha256(body).hexdigest()
    dest = root / (prefix + '-' + sha[:length] + '.json')
    dest.write_bytes(body)
    return dest, sha


def native_env():
    def need(ok, reason):
        if not ok:
            raise ValueError('NO11_BOOTSTRAP_' + reason)

    def private(file, directory=False):
        p = Path(file)
        need(p.is_absolute() and not p.is_symlink() and
             (p.is_dir() if directory else p.is_file()), 'PRIVATE_SOURCE_MISSING')
        return p

    def load_json(file):
        p = private(file)
        body = p.read_bytes()
        return json.loads(body), hashlib.sha256(body).hexdigest()

    env = {'need': need, 'private': private, 'load_json': load_json,
           're': re, 'Path': Path}
    exec(patch.HELPER, env)
    return env['verified_weekly_original']


def case(root):
    run = root / 'day'; run.mkdir()
    auto = root / 'automatic-session'; auto.mkdir()
    selected = ['1001.T', '1002.T', '1003.T']
    blocked = ['1002.T']
    old_plan = {'sessionDate': '2026-11-11', 'asOfSession': '2026-11-10',
                'sourcePlanId': 'a'*64,
                'selectorInputSymbols': selected,
                'scanChartSymbols': selected,
                'allRequestedChartSymbols': selected,
                'protectedChartSymbols': ['1002.T'],
                'g1UnscannedCount': 0,
                'occupiedByOtherChartFunctions': 0,
                'arkChartsUsed': 3,
                'totalChartFunctionsBudgeted': 3,
                'entryUniverseMode': 'OBSERVED_PASS_CANDIDATES',
                'reviewedEntrySymbols': selected,
                'unreviewedG1SymbolsExcludedFromEntry': 0,
                'planSha256': 'a'*64}
    orig = {'schemaId': 'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1',
            'source': 'WEEKLY_POOL_DAILY_REFRESH_ONLY_NOT_CURRENT_FULL_MARKET',
            'chartPlan': old_plan, 'productionReady': False,
            'orderTransmission': False}
    orig_path, orig_sha = write(run, 'no11-chart50-private', orig, 16)
    mask = {'observedPassCount': 3, 'orderTransmission': False}
    mask_path, _ = write(run, 'no11-observed-pass-watch', mask, 16)
    report = {'schemaId': 'ARK_NO11_AUTOMATIC_OPERATIONAL_INPUT_RESULT_V1',
              'inputPolicy': 'AUTO_SELECTED_JPX_RSS_UNADJUSTED_PRICE_CONSISTENCY_V1',
              'sessionDate': '2026-11-11', 'selectedCount': 3, 'passedCount': 2,
              'blockedSymbols': [{'symbol': '1002.T', 'reason': 'MOCK_REJECTED'}],
              'humanReviewPerformed': False, 'productionReady': False,
              'orderTransmission': False}
    report_path, report_sha = write(auto, 'automatic-input-result', report)
    master = {'schemaId': 'ARK_NO11_DATED_MASTER_RECEIPT_V1',
              'sessionDate': '2026-11-11', 'rows': [{'symbol': '1001.T'},
                                                     {'symbol': '1003.T'}],
              'inputPolicy': report['inputPolicy'],
              'productionReady': False, 'orderTransmission': False}
    master_path, _ = write(auto, 'dated-master', master)
    new_plan = dict(old_plan)
    new_plan.update(selectorInputSymbols=['1001.T','1003.T'],
                    scanChartSymbols=['1001.T','1003.T'],
                    allRequestedChartSymbols=selected,  # Protected 1002.T retained.
                    g1UnscannedCount=1, arkChartsUsed=3,
                    totalChartFunctionsBudgeted=3,
                    reviewedEntrySymbols=['1001.T','1003.T'],
                    unreviewedG1SymbolsExcludedFromEntry=1,
                    planSha256='b'*64)
    scope = {'schemaId': 'ARK_NO11_VERIFIED_INVALID_SYMBOL_EXCLUSION_V1',
             'sessionDate': '2026-11-11',
             'originalChartReceiptSha256': orig_sha,
             'automaticResultReportSha256': report_sha,
             'blockedSymbols': blocked,
             'passedSymbols': ['1001.T','1003.T'],
             'previousSelectionPreserved': False,
             'originalChartReceiptModified': False,
             'orderTransmission': False}
    derived = dict(orig, chartPlan=new_plan, automaticVerifiedExclusion=scope)
    derived_path, _ = write(run, 'no11-chart50-private', derived)
    cfg = dict(dailyRun=str(run), precomputedChartReceipt=str(derived_path),
               precomputedG1Mask=str(mask_path), datedMaster=str(master_path),
               sessionDate='2026-11-11')
    return {'cfg': cfg, 'orig': orig_path, 'derived': derived_path,
            'report': report_path, 'master': master_path, 'mask': mask_path,
            'run': run, 'original_obj': orig, 'derived_obj': derived}


class FilteredWeeklyLineage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ENGINE / 'tools/no11_received_session_bootstrap.py').read_bytes()
        cls.validate = staticmethod(native_env())

    def test_transform_is_only_original_weekly_source_argument(self):
        out = patch.transform(self.original)
        self.assertEqual(out, patch.transform(out))
        self.assertNotEqual(out, self.original)
        text = out.decode('utf-8-sig')
        self.assertIn(patch.MARK, text)
        self.assertEqual(text.count('def verified_weekly_original(config):'), 1)
        self.assertIn("'--chart', str(original_chart)", text)
        self.assertIn("return (private(config['precomputedChartReceipt']),", text)
        self.assertIn("validate_scope(session, plan_file, mask_file, master_file, now)", text)
        ast.parse(text)
        self.assertNotIn('RssStockOrder(', patch.HELPER)
        self.assertNotIn('RssCancelOrder(', patch.HELPER)
        self.assertNotIn('Start-Process', patch.HELPER)
        self.assertNotIn("WriteAllText", patch.HELPER)
        self.assertNotIn(".write_bytes(", patch.HELPER)
        self.assertNotIn("open(", patch.HELPER)

    def test_normal_original_16_case_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            c = case(Path(d))
            config = dict(c['cfg'], precomputedChartReceipt=str(c['orig']))
            self.assertEqual(self.validate(config), c['orig'])

    def test_64_derived_passes_only_when_exact_pinned_report_and_master(self):
        with tempfile.TemporaryDirectory() as d:
            c = case(Path(d))
            self.assertEqual(self.validate(c['cfg']), c['orig'])
            self.assertTrue(c['derived'].name.endswith('.json'))
            self.assertEqual(len(c['derived'].stem.rsplit('-', 1)[-1]), 64)
            self.assertEqual(len(c['orig'].stem.rsplit('-', 1)[-1]), 16)

    def test_report_must_exist_with_original_hash_not_a_new_claim(self):
        with tempfile.TemporaryDirectory() as d:
            c = case(Path(d))
            c['report'].unlink()
            with self.assertRaisesRegex(ValueError, 'PRIVATE_SOURCE_MISSING'):
                self.validate(c['cfg'])

    def test_master_cannot_reintroduce_excluded_symbol(self):
        with tempfile.TemporaryDirectory() as d:
            c = case(Path(d))
            master = json.loads(c['master'].read_bytes())
            master['rows'].append({'symbol': '1002.T'})
            path, _ = write(c['master'].parent, 'dated-master', master)
            cfg = dict(c['cfg'], datedMaster=str(path))
            with self.assertRaisesRegex(ValueError, 'FILTERED_MASTER_SCOPE_MISMATCH'):
                self.validate(cfg)

    def test_unknown_chart_receipt_is_not_reclassified(self):
        with tempfile.TemporaryDirectory() as d:
            c = case(Path(d))
            data = c['derived'].read_bytes().replace(b'"planSha256":"'+b'b'*64,
                                                     b'"planSha256":"'+b'c'*64)
            c['derived'].write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'FILTERED_CHART_HASH'):
                self.validate(c['cfg'])

    def test_false_report_hash_and_unknown_exclusion_fail(self):
        with tempfile.TemporaryDirectory() as d:
            c = case(Path(d))
            modified = json.loads(c['derived'].read_bytes())
            modified['automaticVerifiedExclusion']['automaticResultReportSha256'] = 'a'*64
            dpath, _ = write(c['run'], 'no11-chart50-private', modified)
            cfg = dict(c['cfg'], precomputedChartReceipt=str(dpath))
            with self.assertRaisesRegex(ValueError, 'PRIVATE_SOURCE_MISSING'):
                self.validate(cfg)

    def test_protected_held_chart_must_remain(self):
        with tempfile.TemporaryDirectory() as d:
            c = case(Path(d))
            modified = json.loads(c['derived'].read_bytes())
            modified['chartPlan']['allRequestedChartSymbols'].remove('1002.T')
            dpath, _ = write(c['run'], 'no11-chart50-private', modified)
            cfg = dict(c['cfg'], precomputedChartReceipt=str(dpath))
            with self.assertRaisesRegex(ValueError, 'FILTERED_CHART_NOT_EXACT_SUBSET'):
                self.validate(cfg)

    def test_extra_receipt_data_must_not_be_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            c = case(Path(d))
            modified = json.loads(c['derived'].read_bytes())
            modified['productionReady'] = True
            dpath, _ = write(c['run'], 'no11-chart50-private', modified)
            cfg = dict(c['cfg'], precomputedChartReceipt=str(dpath))
            with self.assertRaisesRegex(ValueError, 'FILTERED_OTHER_RECEIPT_FIELDS_CHANGED'):
                self.validate(cfg)

    def test_crlf_bom_retained_and_unknown_local_source_stops(self):
        raw = b'\xef\xbb\xbf' + self.original.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        out = patch.transform(raw)
        self.assertTrue(out.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n', out.replace(b'\r\n', b''))
        with self.assertRaisesRegex(ValueError, 'SOURCE_ANCHOR_CHANGED'):
            patch.transform(b"def export_scope(config):\n    pass\n")


if __name__ == '__main__':
    unittest.main(verbosity=2)
