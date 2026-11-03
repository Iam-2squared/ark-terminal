"""Automatic-input tests use synthetic observations; never call public/broker APIs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import automatic_morning as a
from test_entry_scope import EntryScopeTests, ENGINE

DAY, PRIOR = '2026-11-04', '2026-11-02'
NOW = DAY + 'T08:45:00.000+09:00'


class AutomaticMasterTests(unittest.TestCase):
    def setUp(self):
        self.selected = ['1111.T', '2222.T']
        self.info = {'sessionDate': DAY, 'previousSession': PRIOR,
                     'selectedSymbols': self.selected, 'chartPlanSha256': 'a' * 64}
        self.public = {
            'schemaId': 'ARK_NO11_AUTOMATIC_SELECTED_PUBLIC_SOURCES_V1',
            'sessionDate': DAY, 'previousSession': PRIOR, 'selectedSymbols': self.selected,
            'policy': 'JPX_CURRENT_COMMON_EQUITY_AND_NEAR_TERM_RIGHTS_EXCLUSION_V1',
            'observedAtJst': DAY + 'T08:44:00.000+09:00', 'rightsPublishedOn': PRIOR,
            'productionReady': False, 'orderTransmission': False,
            'rows': [{'symbol': s, 'eligible': True, 'nearTermRightsEventListed': False,
                      'segment': 'PRIME', 'sector': 'サービス業'} for s in self.selected]}
        self.reference = {
            'schemaId': 'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1',
            'sessionDate': DAY, 'source': 'RssMarket_SELECTED_REFERENCE_READONLY',
            'chartPlanSha256': 'a' * 64, 'selectedSymbols': self.selected,
            'capturedAtJst': DAY + 'T08:44:50.000+09:00',
            'completedAtJst': DAY + 'T08:44:51.000+09:00',
            'readOnly': True, 'productionReady': False, 'orderTransmission': False,
            'rows': [{'symbol': s, 'marketCode': 'T', 'marketDate': DAY,
                      'previousDate': PRIOR, 'lotShares': 100, 'marketSection': '東証Ｐ',
                      'previousClose': 1234.5, 'dayBasePrice': 1234.5,
                      'exRightsDateRaw': '', 'exDividendDateRaw': '',
                      'interimExDividendDateRaw': ''} for s in self.selected]}
        self.daily = {s: '1234.50' for s in self.selected}

    def build(self, now=NOW):
        return a.build_master(self.info, self.public, self.reference, self.daily,
                              now, 'b' * 64, 'c' * 64)

    def blocked(self, why):
        master, report = self.build()
        self.assertIsNone(master)
        self.assertTrue(any(why in r['reason'] for r in report['blockedSymbols']))
        self.assertFalse(report['manualEvidenceRequired'])
        self.assertFalse(report['manualPriceInputRequired'])

    def test_all_sources_automatic_and_no_external_review_claim(self):
        master, report = self.build()
        self.assertEqual([r['symbol'] for r in master['rows']], self.selected)
        self.assertEqual(report['passedCount'], 2)
        self.assertEqual(master['inputPolicy'], a.POLICY)
        self.assertFalse(master['humanReviewPerformed'])
        self.assertFalse(master['exhaustiveCorporateActionsCertified'])
        self.assertNotIn('EXTERNALLY_REVIEWED', json.dumps(master))
        self.assertNotIn('securityEvidenceSha256', master)
        self.assertFalse(master['orderTransmission'])

    def test_preopen_clock_is_allowed_when_actual_rss_values_available(self):
        master, _ = self.build()
        self.assertEqual(master['knownAtJst'], NOW)
        self.assertLess(master['knownAtJst'][11:16], '09:00')

    def test_original_sources_not_mutated(self):
        old = deepcopy((self.info, self.public, self.reference, self.daily))
        self.build()
        self.assertEqual((self.info, self.public, self.reference, self.daily), old)

    def test_old_session_does_not_get_redated(self):
        self.reference['sessionDate'] = PRIOR
        with self.assertRaisesRegex(ValueError, 'RSS_REFERENCE_CONTRACT'):
            self.build()

    def test_stale_or_future_rss_clock_rejected(self):
        for stamp in (DAY + 'T08:40:00.000+09:00', DAY + 'T08:46:00.000+09:00'):
            self.reference['capturedAtJst'] = self.reference['completedAtJst'] = stamp
            with self.assertRaisesRegex(ValueError, 'RSS_REFERENCE_STALE'):
                self.build()

    def test_old_or_future_public_observation_rejected(self):
        for stamp in (PRIOR + 'T08:44:00.000+09:00', DAY + 'T08:46:00.000+09:00'):
            self.public['observedAtJst'] = stamp
            with self.assertRaisesRegex(ValueError, 'PUBLIC_SOURCE_NOT_CURRENT'):
                self.build()

    def test_stale_rights_publication_rejected(self):
        self.public['rightsPublishedOn'] = '2026-10-30'
        with self.assertRaisesRegex(ValueError, 'RIGHTS_SOURCE_STALE'):
            self.build()

    def test_etf_or_flagged_listing_not_promoted(self):
        self.public['rows'][0]['eligible'] = False
        self.blocked('PRODUCT_OR_FLAGGED_RIGHTS')

    def test_flagged_rights_not_promoted(self):
        self.public['rows'][0]['nearTermRightsEventListed'] = True
        self.blocked('PRODUCT_OR_FLAGGED_RIGHTS')

    def test_unknown_rights_not_treated_as_clear(self):
        self.public['rows'][0]['nearTermRightsEventListed'] = None
        self.blocked('PRODUCT_OR_FLAGGED_RIGHTS')

    def test_missing_previous_price_blocks_without_manual_request(self):
        self.reference['rows'][0]['previousClose'] = None
        self.blocked('PRICE_TYPE')

    def test_previous_daily_mismatch_not_overwritten(self):
        self.daily['1111.T'] = '1200'
        self.blocked('UNADJUSTED_PRICE_MISMATCH')

    def test_adjusted_base_price_not_silently_accepted(self):
        self.reference['rows'][0]['dayBasePrice'] = 600
        self.blocked('UNADJUSTED_PRICE_MISMATCH')

    def test_rss_today_flagged_event_blocks(self):
        for key in ('exRightsDateRaw', 'exDividendDateRaw', 'interimExDividendDateRaw'):
            self.reference['rows'][0][key] = DAY.replace('-', '/')
            self.blocked('RSS_FLAGGED_EVENT')
            self.reference['rows'][0][key] = ''

    def test_error_in_event_field_is_not_a_blank_event(self):
        self.reference['rows'][0]['exRightsDateRaw'] = '#VALUE!'
        self.blocked('EVENT_DATE_FORMAT')

    def test_market_identity_and_lot_must_match(self):
        for key, value in (('marketCode', 'O'), ('previousDate', '2026-10-30'),
                           ('marketSection', '東証Ｇ'), ('lotShares', 1)):
            before = self.reference['rows'][0][key]
            self.reference['rows'][0][key] = value
            self.blocked('RSS_IDENTITY')
            self.reference['rows'][0][key] = before

    def test_duplicate_or_extra_rows_block(self):
        self.reference['rows'][1] = deepcopy(self.reference['rows'][0])
        with self.assertRaisesRegex(ValueError, 'ROW_SCOPE'):
            self.build()

    def test_nonfinite_and_boolean_prices_rejected(self):
        for value in (True, float('nan'), float('inf'), 0, -1, 'bad'):
            with self.assertRaises(ValueError):
                a.number(value)

    def test_empty_event_is_not_claimed_as_exhaustive_evidence(self):
        self.assertIsNone(a.event_date(''))
        master, report = self.build()
        self.assertFalse(master['exhaustiveCorporateActionsCertified'])
        self.assertFalse(report['humanReviewPerformed'])

    def test_invalid_runner_cannot_be_imported(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            file = Path(t) / 'runner.py'
            file.write_text('raise RuntimeError("MUST_NOT_EXECUTE")')
            with self.assertRaisesRegex(ValueError, 'RUNNER_CHANGED'):
                a.load_runner(file)

    def test_no_trade_or_manual_input_functions(self):
        source = Path(a.__file__).read_text(encoding='utf-8')
        for forbidden in ('input(', 'RssStockOrder(', 'RssCancelOrder(',
                          'reviewStatus\": \"EXTERNALLY_REVIEWED', '--security-evidence',
                          '--evidence-documents', 'Capture-No11RssTrainingBatchReadOnly.ps1',
                          'Run-No11WeeklyCandidateRefreshReadOnly.ps1'):
            self.assertNotIn(forbidden, source)


class NativePipelineCompatibilityTests(unittest.TestCase):
    def test_automatic_master_is_accepted_by_unchanged_native_pipeline_validator(self):
        fixture = EntryScopeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        f = AutomaticMasterTests()
        f.setUp()
        selected = fixture.symbols
        f.info['selectedSymbols'] = selected
        f.info['chartPlanSha256'] = fixture.chart['chartPlan']['planSha256']
        f.public['selectedSymbols'] = f.reference['selectedSymbols'] = selected
        f.reference['chartPlanSha256'] = f.info['chartPlanSha256']
        f.public['rows'] = [{**f.public['rows'][0], 'symbol': s} for s in selected]
        f.reference['rows'] = [{**f.reference['rows'][0], 'symbol': s} for s in selected]
        f.daily = {s: '1234.5' for s in selected}
        master, _ = f.build()
        module = ENGINE / 'tools/no11_received_pipeline_tick.mjs'
        code = '''import {pathToFileURL} from 'node:url';
const {validatePipelineInputs}=await import(pathToFileURL(process.argv[1]).href);
let s='';for await(const c of process.stdin)s+=c;
console.log(JSON.stringify(validatePipelineInputs(JSON.parse(s)).selected));'''
        payload = {'sessionDate': DAY, 'chartPlan': fixture.chart['chartPlan'],
                   'mask': fixture.mask, 'master': master, 'throughJst': NOW}
        result = subprocess.run(['node', '--input-type=module', '-e', code, str(module)],
                                input=json.dumps(payload), text=True, encoding='utf-8',
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), selected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
