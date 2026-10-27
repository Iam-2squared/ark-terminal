"""Actual original input contracts with synthetic reference/review/archive data."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_prepare_received_inputs as prep
import no11_received_session_bootstrap as bootstrap
import test_no11_frozen_p1_previous_archive as old


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old.PreviousArchiveTests.setUpClass()
        cls.scope_fixture = old.PreviousArchiveTests.scope_fixture

    write = old.PreviousArchiveTests.write
    save_archive = old.PreviousArchiveTests.save_archive
    tearDown = old.PreviousArchiveTests.tearDown

    def setUp(self):
        old.PreviousArchiveTests.setUp(self)
        self.docs = self.root / 'documents'
        self.docs.mkdir()
        data = b'SYNTHETIC TEST DOCUMENT; NOT ACTUAL SECURITY EVIDENCE\n'
        self.docsha = hashlib.sha256(data).hexdigest()
        (self.docs / (self.docsha + '.source')).write_bytes(data)
        self.reference = {'schemaId': prep.REFERENCE, 'sessionDate': old.DAY,
            'source': 'RssMarket_SELECTED_REFERENCE_READONLY',
            'capturedAtJst': old.DAY + 'T08:55:05+09:00',
            'completedAtJst': old.DAY + 'T08:55:10+09:00',
            'chartPlanSha256': self.info['chartPlanSha256'], 'selectedSymbols': [old.CODE],
            'rows': [{'symbol': old.CODE, 'marketCode': 'T', 'marketDate': old.DAY,
                      'previousDate': old.PRIOR, 'previousClose': 100.1, 'dayBasePrice': 100.1,
                      'marketSection': '東証P', 'lotShares': 100}],
            'readOnly': True, 'productionReady': False, 'orderTransmission': False}
        self.evidence = {'schemaId': prep.EVIDENCE, 'validForSession': old.DAY,
            'knownAtJst': old.PREFETCH, 'reviewStatus': 'EXTERNALLY_REVIEWED',
            'rows': [{'symbol': old.CODE, 'segment': 'PRIME', 'sector': '01', 'commonEquity': True,
                      'corporateActionsCleared': True, 'priceBasisVerified': True,
                      'reviewedPreviousClose': 100.1, 'sourceDocumentSha256': [self.docsha]}],
            'productionReady': False, 'orderTransmission': False}
        for name in ('daily', 'runtime', 'private'):
            (self.root / name).mkdir()
        self.template = {'schemaId': bootstrap.CONFIG, 'sessionDate': old.DAY,
            'dailyRun': str(self.root / 'daily'), 'runtimeRoot': str(self.root / 'runtime'),
            'privateRoot': str(self.root / 'private'), 'datedMaster': str(self.root / 'not-created.json'),
            'previousContext': str(self.root / 'also-not-created.json'),
            'productionReady': False, 'orderTransmission': False}

    def build(self, reference=None, evidence=None, now=old.START):
        return prep.build_master(self.info, reference or self.reference, evidence or self.evidence,
            reference_sha='a'*64, evidence_sha='b'*64, prepared_at=now)

    def prepare(self):
        reference = self.write('reference.json', self.reference)
        evidence = self.write('evidence.json', self.evidence)
        template = self.write('template.json', self.template)
        return prep.prepare(plan_file=self.plan, mask_file=self.mask, reference_file=reference,
            evidence_file=evidence, evidence_documents=self.docs, capture_dir=self.capture,
            config_file=template, output_root=self.output, prepared_at=old.START)

    def test_reference_review_original_archive_reaches_existing_bootstrap(self):
        original = deepcopy(self.template)
        config_file, report_file = self.prepare()
        cfg = json.loads(config_file.read_text())
        bootstrap.validate_config(cfg)
        report = json.loads(report_file.read_text())
        master = json.loads(Path(cfg['datedMaster']).read_text())
        self.assertEqual(master['rows'][0]['rawPreviousClose'], 100.1)
        self.assertEqual(master['rows'][0]['sector'], '01')
        self.assertEqual(bootstrap.validate_scope(old.DAY, self.plan, self.mask, cfg['datedMaster'], old.START), [old.CODE])
        context = json.loads(Path(cfg['previousContext']).read_text())
        self.assertIn(old.CODE, context['symbols'])
        self.assertFalse(report['independentCorporateActionReviewPerformed'])
        self.assertFalse(report['modelsExecuted'])
        self.assertFalse(report['orderTransmission'])
        self.assertEqual(json.loads((self.root / 'template.json').read_text()), original)
        self.assertTrue(all('Va' not in r for r in context['symbols'][old.CODE]['rows']))

    def test_repeat_same_inputs_is_immutable_and_idempotent(self):
        first = self.prepare()
        self.assertEqual(self.prepare(), first)

    def test_equal_previous_and_base_price_never_certifies_corporate_actions(self):
        self.evidence['rows'][0]['corporateActionsCleared'] = False
        with self.assertRaisesRegex(ValueError, 'SECURITY_EVIDENCE_NOT_CONFIRMED'):
            self.build()

    def test_unknown_price_basis_and_common_equity_not_promoted(self):
        for key in ('priceBasisVerified', 'commonEquity'):
            e = deepcopy(self.evidence)
            del e['rows'][0][key]
            with self.assertRaisesRegex(ValueError, 'SECURITY_EVIDENCE_NOT_CONFIRMED'):
                self.build(evidence=e)

    def test_reviewed_price_must_match_actual_rss_previous_close(self):
        self.evidence['rows'][0]['reviewedPreviousClose'] = 100.2
        with self.assertRaisesRegex(ValueError, 'REVIEWED_PRICE_MISMATCH'):
            self.build()

    def test_fullwidth_rss_section_must_equal_external_reviewed_segment(self):
        for rss, section in [('東証Ｐ', 'PRIME'), ('東証Ｓ', 'STANDARD'), ('東証Ｇ', 'GROWTH')]:
            r, e = deepcopy(self.reference), deepcopy(self.evidence)
            r['rows'][0]['marketSection'] = rss
            e['rows'][0]['segment'] = section
            master = self.build(reference=r, evidence=e)
            self.assertEqual(master['rows'][0]['segment'], section)
            self.assertEqual(r['rows'][0]['marketSection'], rss)
            e['rows'][0]['corporateActionsCleared'] = False
            with self.assertRaisesRegex(ValueError, 'SECURITY_EVIDENCE_NOT_CONFIRMED'):
                self.build(reference=r, evidence=e)
        r = deepcopy(self.reference)
        r['rows'][0]['marketSection'] = '東証Ｐ'
        with self.assertRaisesRegex(ValueError, 'RSS_IDENTITY_DATE_OR_CLASS_MISMATCH'):
            e = deepcopy(self.evidence)
            e['rows'][0]['segment'] = 'STANDARD'
            self.build(reference=r, evidence=e)
        for bad in ['東証プライム', '東証Ｘ', '東証Ｐ ', '東証p']:
            r['rows'][0]['marketSection'] = bad
            with self.assertRaisesRegex(ValueError, 'RSS_IDENTITY_DATE_OR_CLASS_MISMATCH'):
                self.build(reference=r)

    def test_wrong_previous_day_and_market_class_are_rejected(self):
        for key, value in [('previousDate', '2026-10-22'), ('marketDate', old.PRIOR),
                           ('marketSection', '東証S'), ('lotShares', 1), ('marketCode', 'JNX')]:
            r = deepcopy(self.reference)
            r['rows'][0][key] = value
            with self.assertRaisesRegex(ValueError, 'RSS_IDENTITY_DATE_OR_CLASS_MISMATCH'):
                self.build(reference=r)

    def test_no_future_known_time_or_preday_master(self):
        with self.assertRaisesRegex(ValueError, 'ACTUAL_SESSION_REQUIRED'):
            self.build(now=old.PREFETCH)
        r = deepcopy(self.reference)
        r['completedAtJst'] = old.DAY + 'T09:00:00+09:00'
        with self.assertRaisesRegex(ValueError, 'REFERENCE_CLOCK'):
            self.build(reference=r)
        self.evidence['knownAtJst'] = old.DAY + 'T09:00:00+09:00'
        with self.assertRaisesRegex(ValueError, 'SECURITY_EVIDENCE_REQUIRED'):
            self.build()

    def test_symbol_duplicates_and_unselected_rows_are_rejected(self):
        self.reference['rows'].append(deepcopy(self.reference['rows'][0]))
        with self.assertRaisesRegex(ValueError, 'ROW_IDENTITY_OR_DUPLICATE'):
            self.build()
        self.reference['rows'][-1]['symbol'] = '6501.T'
        with self.assertRaisesRegex(ValueError, 'REFERENCE_SCOPE_MISMATCH'):
            self.build()

    def test_real_price_is_required_not_a_boolean_or_missing_number(self):
        for v in (None, True, 0, -1, float('nan'), float('inf'), '100.1'):
            r = deepcopy(self.reference)
            r['rows'][0]['previousClose'] = v
            with self.assertRaises(ValueError):
                self.build(reference=r)

    def test_all_symbols_require_named_evidence(self):
        self.evidence['rows'][0]['symbol'] = '6501.T'
        with self.assertRaisesRegex(ValueError, 'SECURITY_EVIDENCE_MISSING'):
            self.build()

    def test_changed_evidence_document_bytes_block_output_config(self):
        (self.docs / (self.docsha + '.source')).write_bytes(b'CHANGED')
        with self.assertRaisesRegex(ValueError, 'DOCUMENT_BYTES_CHANGED'):
            self.prepare()
        self.assertEqual(list(self.output.glob('bootstrap-ready-inputs-*.json')), [])

    def test_absent_evidence_file_is_not_replaced_with_generated_true_flags(self):
        self.evidence['rows'][0]['sourceDocumentSha256'] = []
        with self.assertRaisesRegex(ValueError, 'REVIEW_SOURCE_REFERENCE_REQUIRED'):
            self.build()

    def test_original_previous_archive_hash_gate_is_still_enforced(self):
        self.member_path.write_bytes(self.member_path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'ARCHIVE_BYTES_CHANGED'):
            self.prepare()
        self.assertEqual(list(self.output.glob('bootstrap-ready-inputs-*.json')), [])

    def test_input_objects_and_original_archives_are_unchanged(self):
        a, b, data = deepcopy(self.reference), deepcopy(self.evidence), self.member_path.read_bytes()
        self.prepare()
        self.assertEqual(self.reference, a)
        self.assertEqual(self.evidence, b)
        self.assertEqual(self.member_path.read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
