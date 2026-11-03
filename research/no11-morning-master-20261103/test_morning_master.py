"""Offline synthetic fixtures only. No external network, Excel or brokerage."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import date, timedelta
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import morning_master as m


class FakeSources:
    INDEX = 'https://www.jpx.co.jp/listing/others/ex-rights/index.html'
    SEARCH = 'https://www2.jpx.co.jp/tseHpFront/StockSearch.do?test='

    def fetch(self, url, root):
        raw = url.encode('utf-8')
        (Path(root) / (m.sha(raw) + '.source')).write_bytes(raw)
        return raw, {'url': url, 'sha256': m.sha(raw), 'capturedAtJst': m.clock()}

    def rights_link(self, text, prior, session, today):
        return prior, 'https://www.jpx.co.jp/listing/others/ex-rights/test.xls'

    def parse_rights(self, raw):
        return ['2222.T']

    def parse_company(self, html, symbol):
        return {'symbol': symbol, 'eligible': True, 'segment': 'PRIME',
                'sector': 'FIXTURE_SECTOR', 'reason': 'FIXTURE_SOURCE_ONLY'}


class MorningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / 'private'
        self.engine = self.root / 'engine'
        self.capture = self.root / 'capture'
        for d in (self.out, self.engine, self.capture, self.engine / 'tools'):
            d.mkdir()
        self.selected = ['1111.T', '2222.T']
        self.day = date.today().isoformat()
        self.prior = (date.today() - timedelta(days=1)).isoformat()
        self.chart = {
            'schemaId': 'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1',
            'productionReady': False, 'orderTransmission': False,
            'chartPlan': {'sessionDate': self.day, 'asOfSession': self.prior,
                          'selectorInputSymbols': self.selected, 'sourcePlanId': 'fixture-plan',
                          'planSha256': 'a' * 64, 'productionReady': False,
                          'orderTransmission': False}}
        self.mask = {'schemaId': 'ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1',
                     'productionReady': False, 'orderTransmission': False,
                     'asOfSession': self.prior, 'planId': 'fixture-plan',
                     'observedPassCount': 2, 'observedPassSymbols': self.selected}
        progress = {'completed': 2, 'requested': 2}
        raw = (json.dumps(progress) + '\n').encode()
        (self.capture / 'progress-00002.json').write_bytes(raw)
        self.stage = {'schemaId': 'ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1',
                      'productionReady': False, 'orderTransmission': False,
                      'sessionDate': self.day, 'previousSession': self.prior,
                      'chartPlanSha256': 'a' * 64, 'selectedSymbols': self.selected,
                      'symbols': {x: {} for x in self.selected}, 'progressSha256': m.sha(raw)}
        self.chart_file = self.receipt('no11-chart50-private', self.chart, 16)
        self.mask_file = self.receipt('no11-observed-pass-watch', self.mask, 16)
        self.stage_file = self.receipt('previous-archive-stage', self.stage, 64)
        self.book = self.root / 'broker.xlsx'
        self.book.write_bytes(b'x' * 250001)  # Workbook is not limited as a 200KB JSON.
        self.settings = self.root / 'settings.json'
        self.settings.write_text(json.dumps({
            'schemaId': 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
            'automaticOrderAuthorization': False, 'orderTransmission': False,
            'orderIdWorkbookPath': str(self.book)}))
        self.spec = {'sessionDate': self.day, 'engineRoot': str(self.engine),
                     'chartReceipt': str(self.chart_file), 'passMask': str(self.mask_file),
                     'previousStage': str(self.stage_file), 'previousCaptureDir': str(self.capture),
                     'runtimeRoot': str(self.root), 'h235ModelRoot': str(self.root),
                     'weeklySourceRun': str(self.root), 'settingsFile': str(self.settings),
                     'outputRoot': str(self.out)}
        self.spec_file = self.root / 'spec.json'
        self.spec_file.write_text(json.dumps(self.spec))

    def receipt(self, prefix, obj, digits):
        raw = (json.dumps(obj) + '\n').encode()
        file = self.root / (prefix + '-' + m.sha(raw)[:digits] + '.json')
        file.write_bytes(raw)
        return file

    def prepared(self):
        with patch.object(m, 'clock', return_value=self.day + 'T08:30:00.000+09:00'), \
             patch.object(m, 'native_scope', return_value=self.selected), \
             patch.object(m, 'helper_module', return_value=FakeSources()), \
             patch.object(m.time, 'sleep'), redirect_stdout(io.StringIO()):
            return m.prepare(self.spec_file)

    def test_scope_keeps_exact_original_symbols(self):
        selected, prior = m.validate_scope(self.spec, self.chart, self.mask, self.stage)
        self.assertEqual(selected, self.selected)
        self.assertEqual(prior, self.prior)

    def test_different_previous_session_rejected(self):
        self.stage['previousSession'] = '2000-01-01'
        with self.assertRaisesRegex(ValueError, 'SAVED_PREVIOUS_SCOPE'):
            m.validate_scope(self.spec, self.chart, self.mask, self.stage)

    def test_outside_g1_cannot_be_admitted(self):
        self.mask['observedPassSymbols'] = ['1111.T']
        self.mask['observedPassCount'] = 1
        with self.assertRaisesRegex(ValueError, 'MASK_SCOPE'):
            m.validate_scope(self.spec, self.chart, self.mask, self.stage)

    def test_duplicate_selection_rejected(self):
        self.chart['chartPlan']['selectorInputSymbols'] = ['1111.T', '1111.T']
        with self.assertRaisesRegex(ValueError, 'SELECTED_SCOPE'):
            m.validate_scope(self.spec, self.chart, self.mask, self.stage)

    def test_source_receipt_tamper_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_RECEIPT_HASH_MISMATCH'):
            m.verify_receipt(self.chart_file, b'changed', 'no11-chart50-private', 16)

    def test_duplicate_json_fields_rejected(self):
        file = self.root / 'dup.json'
        file.write_bytes(b'{"a":1,"a":2}')
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_FIELD'):
            m.read(file)

    def test_nonfinite_json_rejected(self):
        file = self.root / 'nan.json'
        file.write_bytes(b'{"a":NaN}')
        with self.assertRaisesRegex(ValueError, 'NONFINITE_JSON'):
            m.read(file)

    def test_content_addressed_output_is_idempotent(self):
        a = m.immutable(self.out, 'fixture', {'a': 1})
        self.assertEqual(a, m.immutable(self.out, 'fixture', {'a': 1}))
        a.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'IMMUTABLE_OUTPUT_CHANGED'):
            m.immutable(self.out, 'fixture', {'a': 1})

    def test_prepare_does_not_touch_engine_settings_or_history(self):
        before = {x: x.read_bytes() for x in (self.settings, self.chart_file,
                                            self.mask_file, self.stage_file)}
        file = self.prepared()
        handoff, _ = m.read(file)
        self.assertEqual(handoff['selectedSymbols'], self.selected)
        self.assertFalse(handoff['datedMasterCreated'])
        self.assertFalse(handoff['historicalRecaptureRequired'])
        self.assertEqual(list((self.engine / 'tools').iterdir()), [])
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_public_source_is_not_approved_security_evidence(self):
        file = self.prepared()
        handoff, _ = m.read(file)
        basis, _ = m.read(handoff['publicSourceBasis'])
        self.assertEqual(basis['reviewStatus'], 'NOT_REVIEWED')
        self.assertFalse(basis['corporateActionReviewPerformed'])
        self.assertTrue(basis['rows'][1]['nearTermRightsEventListed'])
        self.assertEqual(basis['selectedSymbols'], self.selected)
        for row in basis['rows']:
            self.assertNotIn('corporateActionsCleared', row)
            self.assertNotIn('priceBasisVerified', row)
        with self.assertRaisesRegex(ValueError, 'GENUINE_REVIEWED_EVIDENCE_REQUIRED'):
            m.validate_day_and_evidence(handoff, basis, self.day + 'T08:40:00+09:00')

    def test_one_unavailable_public_listing_is_reported_not_fabricated(self):
        class Broken(FakeSources):
            def parse_company(self, html, symbol):
                if symbol == '2222.T':
                    raise ValueError('NO11_AUTO_MASTER_JPX_COMPANY_HEADER_CHANGED')
                return super().parse_company(html, symbol)
        with patch.object(m.time, 'sleep'), redirect_stdout(io.StringIO()):
            result = m.collect_public(Broken(), self.selected, self.prior, self.day, self.out)
        self.assertEqual(len(result['rows']), 2)
        self.assertFalse(result['rows'][1]['eligible'])
        self.assertNotIn('listingSourceSha256', result['rows'][1])
        self.assertFalse(result['datedMasterCreated'])

    def test_wrong_actual_day_blocks_before_excel(self):
        handoff, _ = m.read(self.prepared())
        with self.assertRaisesRegex(ValueError, 'ACTUAL_SESSION_DAY_REQUIRED'):
            m.validate_day_and_evidence(handoff, {}, '2000-01-01T08:00:00+09:00')

    def test_missing_evidence_symbol_blocks(self):
        handoff, _ = m.read(self.prepared())
        evidence = {'schemaId': 'ARK_NO11_SESSION_SECURITY_EVIDENCE_V1',
                    'validForSession': self.day, 'reviewStatus': 'EXTERNALLY_REVIEWED',
                    'productionReady': False, 'orderTransmission': False,
                    'rows': [{'symbol': '1111.T'}]}
        with self.assertRaisesRegex(ValueError, 'EVIDENCE_SELECTED_SCOPE'):
            m.validate_day_and_evidence(handoff, evidence, self.day + 'T08:00:00+09:00')

    def test_native_finalize_uses_saved_capture_and_chains_outputs(self):
        file = self.prepared()
        evidence = {'schemaId': 'ARK_NO11_SESSION_SECURITY_EVIDENCE_V1',
                    'validForSession': self.day, 'reviewStatus': 'EXTERNALLY_REVIEWED',
                    'productionReady': False, 'orderTransmission': False,
                    'rows': [{'symbol': s} for s in self.selected]}
        evidence_file = self.receipt('fixture-reviewed-input', evidence, 64)
        reference = self.receipt('fixture-reference', {'testFixture': True}, 64)
        config = self.receipt('fixture-bootstrap', {'testFixture': True}, 64)
        context = self.receipt('fixture-context', {'symbols': {s: {} for s in self.selected}}, 64)
        report = self.receipt('fixture-report', {'selectedCount': 2, 'masterRows': 2,
                              'master': 'SYNTHETIC_TEST_ONLY', 'previousContext': str(context)}, 64)
        received = {}
        def assemble(**kwargs):
            received.update(kwargs)
            return config, report
        fake = SimpleNamespace(verify_documents=lambda e, d: None, prepare=assemble)
        old_path = list(sys.path)
        try:
            with patch.dict(sys.modules, {'no11_prepare_received_inputs': fake}), \
                 patch.object(m, 'clock', return_value=self.day + 'T08:45:00+09:00'), \
                 patch.object(m, 'capture_reference') as capture, redirect_stdout(io.StringIO()):
                self.assertEqual(m.finalize(file, evidence_file, self.out, reference), config)
                capture.assert_not_called()
        finally:
            sys.path[:] = old_path
        self.assertEqual(received['capture_dir'], self.capture)
        self.assertEqual(received['plan_file'], self.chart_file)
        self.assertEqual(received['mask_file'], self.mask_file)
        template, _ = m.read(received['config_file'])
        self.assertNotIn('shadowAccountConfig', template)
        self.assertNotIn('brokerExecutionConfig', template)
        self.assertFalse(template['orderTransmission'])

    def test_no_trading_or_collection_runner_in_source(self):
        source = Path(m.__file__).read_text(encoding='utf-8')
        for forbidden in ('RssStockOrder(', 'RssCancelOrder(', '-StartShadow',
                          'Run-No11WeeklyCandidateRefreshReadOnly.ps1',
                          'Capture-No11RssTrainingBatchReadOnly.ps1',
                          'Run-No11ReceivedSessionOperatorLive.ps1'):
            self.assertNotIn(forbidden, source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
