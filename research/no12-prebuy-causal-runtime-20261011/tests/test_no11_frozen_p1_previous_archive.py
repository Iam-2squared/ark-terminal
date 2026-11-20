"""Existing archive -> original State9 previous context. Synthetic source fixtures.

No Excel, private user source or orders. Original JS plan validator and original
State9 normalization run, rather than substitute implementations.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_previous_archive_context as adapter
import no11_received_session_bootstrap as bootstrap
import test_no11_frozen_p1_bootstrap as setup_fixture
import test_no11_frozen_p1_rss_state_stream as stream_fixture

DAY, PRIOR = '2026-10-26', '2026-10-23'
PREFETCH = '2026-10-25T15:10:00.000+09:00'
START = DAY + 'T08:55:12.000+09:00'
CODE = '7203.T'


class PreviousArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup_fixture.BootstrapTests.setUpClass()
        cls.scope_fixture = setup_fixture.BootstrapTests.scope

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.capture, self.output = self.root / 'capture', self.root / 'output'
        self.capture.mkdir()
        self.output.mkdir()
        self.plan = self.write('plan.json', self.scope_fixture['plan'])
        self.mask = self.write('mask.json', self.scope_fixture['mask'])
        self.master = self.write('master.json', {
            'schemaId': 'ARK_NO11_DATED_MASTER_RECEIPT_V1', 'sessionDate': DAY,
            'knownAtJst': DAY + 'T08:50:00+09:00',
            'rows': [{'symbol': CODE, 'asOfSession': DAY, 'rawPreviousClose': 100,
                      'segment': 'PRIME', 'sector': '01', 'commonEquity': True,
                      'corporateActionsCleared': True, 'priceBasisVerified': True}],
            'productionReady': False, 'orderTransmission': False})
        prior = stream_fixture.previous(False)['symbols'][CODE]['rows']
        self.rows = [{'label': PRIOR + 'T' + row['Time'] + ':00+09:00',
                      'open': row['O'], 'high': row['H'], 'low': row['L'],
                      'close': row['C'], 'volume': row['Vo']} for row in prior]
        self.raw = {'schemaId': adapter.ARCHIVE, 'symbol': CODE, 'period': '1M',
                    'sourceFunction': 'RssChart', 'evidenceMode': 'OBSERVED_READ_ONLY',
                    'observedAt': '2026-10-25T14:59:00.1234567+09:00',
                    'requestedBars': 3000, 'numericRows': len(self.rows),
                    'validRows': len(self.rows), 'invalidRows': 0, 'duplicateRows': 0,
                    'status': adapter.GOOD, 'rows': deepcopy(self.rows),
                    'privateAccountDataIncluded': False, 'vendorLabelCertified': False,
                    'actualHistoricalKnownAtCertified': False,
                    'vendorDecimalTokenCertified': False, 'nativeSelectorProduced': False,
                    'modelTrainingReady': False, 'productionReady': False, 'orderTransmission': False}
        self.info = adapter.scope(self.plan, self.mask)
        self.save_archive()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return path

    def save_archive(self, raw=None):
        raw = self.raw if raw is None else raw
        self.member_path = self.capture / '00001-7203_T-1M.json'
        data = (json.dumps(raw, ensure_ascii=False) + '\n').encode()
        self.member_path.write_bytes(data)
        self.member = {'symbol': CODE, 'file': self.member_path.name,
                       'sha256': hashlib.sha256(data).hexdigest(), 'status': raw['status'],
                       'rows': len(raw['rows'])}
        self.progress = {'schemaId': adapter.PROGRESS, 'completed': 1, 'requested': 1,
                         'observedSymbols': 1, 'unavailableSymbols': 0, 'files': [self.member],
                         'productionReady': False, 'orderTransmission': False}
        self.progress_path = self.capture / 'progress-00001.json'
        self.progress_path.write_text(json.dumps(self.progress), encoding='utf-8')

    def stage(self):
        return adapter.stage_archive(self.info, self.capture, PREFETCH)

    def test_original_plan_selects_only_needed_symbols(self):
        path, info = adapter.write_symbols(self.plan, self.mask, self.output)
        self.assertEqual(path.read_text().splitlines(), [CODE])
        self.assertEqual(info['previousSession'], PRIOR)
        self.assertEqual(info['sessionDate'], DAY)
        self.assertLessEqual(len(info['selectedSymbols']), 50)
        self.assertEqual(adapter.write_symbols(self.plan, self.mask, self.output)[0], path)

    def test_modified_plan_hash_is_rejected_by_original_js(self):
        plan = deepcopy(self.scope_fixture['plan'])
        plan['chartPlan']['selectorInputSymbols'] = ['6501.T']
        self.write('plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'CHART_PLAN_OR_MASK_INVALID'):
            adapter.scope(self.plan, self.mask)

    def test_preday_source_uses_real_observation_without_creating_future_context(self):
        result = self.stage()
        source = result['symbols'][CODE]
        self.assertEqual(source['rows'][0]['Date'], PRIOR)
        self.assertEqual(source['archiveObservedAtOriginal'], self.raw['observedAt'])
        self.assertEqual(source['originalArchiveSha256'], self.member['sha256'])
        self.assertTrue(all('Va' not in row and 'knownAtJst' not in row for row in source['rows']))
        self.assertFalse(result['priceBasisCertified'])
        self.assertFalse(result['corporateActionsCertified'])
        self.assertFalse(result['previousVaGenerated'])
        self.assertFalse(result['orderTransmission'])

    def test_prefetch_accepts_seven_decimal_windows_timestamp(self):
        self.assertIsNotNone(adapter.instant(self.raw['observedAt']))
        self.assertIn(CODE, self.stage()['symbols'])

    def test_latest_progress_checkpoint_is_used(self):
        one = deepcopy(self.progress)
        one.update(completed=1, requested=2)
        self.progress_path.write_text(json.dumps(one))
        raw = deepcopy(self.raw)
        raw['symbol'] = '6501.T'
        name = '00002-6501_T-1M.json'
        data = json.dumps(raw).encode()
        (self.capture / name).write_bytes(data)
        second = dict(one, completed=2, files=[self.member, {
            'symbol': '6501.T', 'file': name, 'sha256': hashlib.sha256(data).hexdigest(),
            'status': adapter.GOOD, 'rows': len(raw['rows'])}])
        (self.capture / 'progress-00002.json').write_text(json.dumps(second))
        self.assertEqual(adapter.checkpoint(self.capture)[1]['completed'], 2)
        self.assertEqual(set(self.stage()['symbols']), {CODE})

    def test_changed_source_bytes_fail_not_silently_rehashed(self):
        self.member_path.write_bytes(self.member_path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'ARCHIVE_BYTES_CHANGED'):
            self.stage()

    def test_checkpoint_path_traversal_is_rejected(self):
        self.progress['files'][0]['file'] = '../outside.json'
        self.progress_path.write_text(json.dumps(self.progress))
        with self.assertRaisesRegex(ValueError, 'PROGRESS_MEMBER_INVALID'):
            self.stage()

    def test_5minute_archive_not_reinterpreted_as_1minute(self):
        self.raw['period'] = '5M'
        self.save_archive()
        result = self.stage()
        self.assertEqual(result['symbols'], {})
        self.assertIn('CONTRACT_INVALID', result['omittedSymbols'][CODE])

    def test_missing_symbol_stays_missing(self):
        info = dict(self.info, selectedSymbols=[CODE, '6501.T'])
        stage = adapter.stage_archive(info, self.capture, PREFETCH)
        self.assertEqual(stage['omittedSymbols']['6501.T'], 'NOT_IN_CAPTURE_CHECKPOINT')

    def test_insufficient_prior_rows_and_partial_audit_are_not_repaired(self):
        for changed in ({'status': 'ROW_AUDIT_FAILED', 'invalidRows': 1},
                        {'rows': self.rows[:1], 'validRows': 1, 'numericRows': 1}):
            raw = dict(self.raw, **changed)
            self.save_archive(raw)
            self.assertNotIn(CODE, self.stage()['symbols'])

    def test_other_session_rows_are_not_used_as_previous_session(self):
        raw = deepcopy(self.raw)
        raw['rows'][0]['label'] = raw['rows'][0]['label'].replace(PRIOR, '2026-10-22')
        self.save_archive(raw)
        stage = self.stage()
        source = stage['symbols'][CODE]
        self.assertEqual(len(source['rows']), len(self.rows) - 1)
        self.assertEqual(source['sourceRowsIgnoredOutsidePreviousSession'], 1)

    def test_duplicate_or_unclosed_prior_bar_is_rejected(self):
        raw = deepcopy(self.raw)
        raw['rows'][1]['label'] = raw['rows'][0]['label']
        self.save_archive(raw)
        self.assertEqual(self.stage()['symbols'], {})
        raw = deepcopy(self.raw)
        raw['observedAt'] = raw['rows'][0]['label']
        self.save_archive(raw)
        self.assertEqual(self.stage()['symbols'], {})

    def test_future_receipt_or_invalid_price_is_excluded(self):
        for field, value in [('observedAt', '2026-10-26T09:00:00+09:00')]:
            raw = dict(self.raw, **{field: value})
            self.save_archive(raw)
            self.assertEqual(self.stage()['symbols'], {})
        raw = deepcopy(self.raw)
        raw['rows'][0]['high'] = 0
        self.save_archive(raw)
        self.assertEqual(self.stage()['symbols'], {})

    def test_context_cannot_be_finalized_on_previous_day(self):
        with self.assertRaisesRegex(ValueError, 'FINAL_CONTEXT_REQUIRES_ACTUAL_SESSION_DAY'):
            adapter.assemble(self.stage(), self.plan, self.mask, self.master, self.output, PREFETCH)

    def test_original_state9_normalization_accepts_converted_previous_context(self):
        context_file, report_file = adapter.assemble(self.stage(), self.plan, self.mask,
                                                   self.master, self.output, START)
        context = json.loads(context_file.read_text())
        report = json.loads(report_file.read_text())
        self.assertEqual(context['schemaId'], stream_fixture.r.PREVIOUS_SCHEMA)
        self.assertEqual(context['previousSession'], PRIOR)
        source = context['symbols'][CODE]
        self.assertEqual(source['knownAtJst'], START)
        self.assertEqual(source['archiveObservedAtOriginal'], self.raw['observedAt'])
        self.assertEqual(source['rows'], sorted(stream_fixture.previous(False)['symbols'][CODE]['rows'], key=lambda r:r['Time']))
        self.assertTrue(report['originalState9NormalizationExecuted'])
        self.assertEqual(report['usablePreviousCount'], 1)
        self.assertFalse(context['orderTransmission'])

    def test_unverified_master_flags_cannot_be_promoted(self):
        master = json.loads(self.master.read_text())
        master['rows'][0]['corporateActionsCleared'] = False
        self.master.write_text(json.dumps(master))
        with self.assertRaisesRegex(ValueError, 'SOURCE_EXPORT_OR_VALIDATION_FAILED'):
            adapter.assemble(self.stage(), self.plan, self.mask, self.master, self.output, START)
        self.assertEqual(list(self.output.glob('previous-context-*.json')), [])

    def test_config_copy_connects_to_existing_bootstrap_without_editing_original(self):
        context, _ = adapter.assemble(self.stage(), self.plan, self.mask, self.master, self.output, START)
        config = {'schemaId': bootstrap.CONFIG, 'sessionDate': DAY,
                  'dailyRun': str(self.capture), 'datedMaster': str(self.master),
                  'runtimeRoot': str(self.root), 'privateRoot': str(self.output),
                  'previousCaptureFiles': ['placeholder'], 'productionReady': False, 'orderTransmission': False}
        file = self.write('config.json', config)
        before = file.read_bytes()
        new = adapter.updated_config(file, context, self.master, self.info, self.output)
        parsed = json.loads(new.read_text())
        self.assertNotIn('previousCaptureFiles', parsed)
        self.assertEqual(parsed['previousContext'], str(context))
        self.assertEqual(parsed['runtimeRoot'], config['runtimeRoot'])
        self.assertFalse(parsed['orderTransmission'])
        self.assertEqual(file.read_bytes(), before)
        bootstrap.validate_config(parsed)

    def test_symbols_cli_does_not_start_excel_or_score_models(self):
        with mock.patch.object(adapter, 'stage_archive') as capture:
            adapter.main(['--plan', str(self.plan), '--mask', str(self.mask),
                          '--output-root', str(self.output), '--symbols-only'])
            capture.assert_not_called()
        self.assertEqual(len(list(self.output.glob('previous-symbols-*.txt'))), 1)

    def test_prefetch_cli_does_not_produce_previous_context_or_certified_master(self):
        with mock.patch.object(adapter, 'now_jst', return_value=PREFETCH):
            adapter.main(['--plan', str(self.plan), '--mask', str(self.mask),
                          '--output-root', str(self.output), '--capture-dir', str(self.capture)])
        self.assertEqual(len(list(self.output.glob('previous-archive-stage-*.json'))), 1)
        self.assertEqual(list(self.output.glob('previous-context-*.json')), [])
        self.assertEqual(list(self.output.glob('*master*')), [])


if __name__ == '__main__':
    unittest.main()
