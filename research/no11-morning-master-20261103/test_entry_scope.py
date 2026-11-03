"""Synthetic local fixtures; native Node chart validator; no network or trading."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import morning_master as m
import scope_morning_master as s

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / 'research/no12-prebuy-causal-runtime-20261011'
DAY, PRIOR = '2026-11-04', '2026-11-02'


class EntryScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docs = self.root / 'public-source-documents'
        self.docs.mkdir()
        self.daily = self.root / 'daily'
        self.daily.mkdir()
        self.capture = self.root / 'saved-47-archive'
        self.capture.mkdir()
        self.symbols = ['1111.T', '2222.T', '3333.T']
        self.mask = {'schemaId': 'ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1',
                     'planId': 'c' * 64, 'asOfSession': PRIOR, 'observedPassCount': 3,
                     'observedPassSymbols': self.symbols, 'shadowOnly': True,
                     'strictNoUnknownFallback': True, 'priceBasisCertified': False,
                     'corporateActionsCertified': False, 'productionReady': False,
                     'orderTransmission': False}
        self.mask_file = self.receipt(self.daily, 'no11-observed-pass-watch', self.mask, 16)
        module = ENGINE / 'runtime/no11_rss_chart_50_prescreen.mjs'
        script = '''import fs from 'node:fs';import {pathToFileURL} from 'node:url';
const [module,maskFile]=process.argv.slice(2);
const {makeNo11G1Chart50Plan}=await import(pathToFileURL(module).href);
const mask=JSON.parse(fs.readFileSync(maskFile,'utf8'));
const chartPlan=makeNo11G1Chart50Plan({mask,sessionDate:'2026-11-04',
 priorityRows:mask.observedPassSymbols.map((symbol,i)=>({symbol,minMarginPct:3-i,meanMarginPct:4-i}))});
console.log(JSON.stringify({schemaId:'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1',
 chartPlan,productionReady:false,orderTransmission:false}));'''
        raw = m.run(['node', '--input-type=module', '-', str(module), str(self.mask_file)],
                    'FIXTURE_NATIVE_PLAN', input_text=script).encode()
        self.chart_file = self.daily / ('no11-chart50-private-' + m.sha(raw)[:16] + '.json')
        self.chart_file.write_bytes(raw)
        self.chart = json.loads(raw)
        self.stage = {'schemaId': 'ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1',
                      'sessionDate': DAY, 'previousSession': PRIOR,
                      'chartPlanSha256': self.chart['chartPlan']['planSha256'],
                      'selectedSymbols': self.symbols,
                      'symbols': {x: {'archiveObservedAtOriginal': '2026-11-03T21:00:00+09:00',
                                      'fixture': 'SYNTHETIC_NOT_MARKET_DATA'} for x in self.symbols},
                      'omittedSymbols': {}, 'progressSha256': 'f' * 64,
                      'productionReady': False, 'orderTransmission': False}
        self.stage_file = self.receipt(self.root, 'previous-archive-stage', self.stage, 64)
        documents = []
        def doc(url):
            raw = ('OFFLINE_TEST_FIXTURE:' + url).encode()
            sha = m.sha(raw)
            (self.docs / (sha + '.source')).write_bytes(raw)
            documents.append({'url': url, 'sha256': sha, 'capturedAtJst': '2026-11-03T21:05:00+09:00'})
            return sha
        doc('https://www.jpx.co.jp/listing/others/ex-rights/index.html')
        doc('https://www.jpx.co.jp/listing/others/ex-rights/fixture-att/20261102.xls')
        rows = []
        for symbol in self.symbols:
            sh = doc('https://www2.jpx.co.jp/tseHpFront/StockSearch.do?method=topsearch&topSearchStr=' + symbol[:4])
            rows.append({'symbol': symbol, 'eligible': symbol != '3333.T',
                         'nearTermRightsEventListed': symbol == '3333.T',
                         'listingSourceSha256': sh, 'reviewStatus': 'NOT_REVIEWED',
                         'segment': 'PRIME', 'sector': 'SYNTHETIC_SECTOR', 'reason': 'FIXTURE_ONLY'})
        self.basis = {'schemaId': 'ARK_NO11_MORNING_PUBLIC_SOURCE_BASIS_V1',
                      'sessionDate': DAY, 'previousSession': PRIOR,
                      'selectedSymbols': self.symbols, 'rows': rows, 'documents': documents,
                      'rightsSourceParsed': True, 'rightsPublishedOn': PRIOR, 'sourceBlockers': [],
                      'reviewStatus': 'NOT_REVIEWED', 'corporateActionReviewPerformed': False,
                      'priceBasisCertified': False, 'datedMasterCreated': False,
                      'productionReady': False, 'orderTransmission': False}
        self.basis_file = self.receipt(self.root, 'public-master-basis', self.basis, 64)
        self.spec = {'sessionDate': DAY, 'engineRoot': str(ENGINE),
                     'chartReceipt': str(self.chart_file), 'passMask': str(self.mask_file),
                     'previousStage': str(self.stage_file), 'previousCaptureDir': str(self.capture),
                     'runtimeRoot': str(self.root), 'h235ModelRoot': str(self.root),
                     'weeklySourceRun': str(self.root), 'settingsFile': str(self.root / 'settings.json'),
                     'outputRoot': str(self.root)}
        self.handoff = {'schemaId': 'ARK_NO11_MORNING_MASTER_HANDOFF_V1',
                        'sessionDate': DAY, 'previousSession': PRIOR, 'selectedSymbols': self.symbols,
                        'spec': self.spec,
                        'sourcePins': {'chartReceipt': m.sha(self.chart_file.read_bytes()),
                                       'passMask': m.sha(self.mask_file.read_bytes()),
                                       'previousStage': m.sha(self.stage_file.read_bytes())},
                        'publicSourceBasis': str(self.basis_file),
                        'publicSourceBasisSha256': m.sha(self.basis_file.read_bytes()),
                        'historicalRecaptureRequired': False, 'fullUniverseRescanRequired': False,
                        'reviewStatus': 'NOT_REVIEWED', 'datedMasterCreated': False,
                        'productionReady': False, 'orderTransmission': False}
        self.handoff_file = self.receipt(self.root, 'morning-handoff', self.handoff, 64)

    def receipt(self, root, prefix, obj, digits):
        raw = (json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
        file = root / (prefix + '-' + m.sha(raw)[:digits] + '.json')
        file.write_bytes(raw)
        return file

    def execute(self):
        with redirect_stdout(io.StringIO()):
            return s.scope(m, self.handoff_file, expected_count=2)

    def test_end_to_end_native_chart_and_saved_stage_binding(self):
        file = self.execute()
        new, raw = m.read(file)
        m.verify_receipt(file, raw, 'morning-handoff', 64)
        chart, cb = m.read(new['spec']['chartReceipt'])
        stage, sb = m.read(new['spec']['previousStage'])
        basis, _ = m.read(new['publicSourceBasis'])
        self.assertEqual(new['selectedSymbols'], ['1111.T', '2222.T'])
        self.assertEqual(m.native_scope(ENGINE, new['spec']['chartReceipt'], self.mask_file),
                         new['selectedSymbols'])
        self.assertEqual(new['sourcePins']['chartReceipt'], m.sha(cb))
        self.assertEqual(new['sourcePins']['previousStage'], m.sha(sb))
        self.assertEqual(new['spec']['previousCaptureDir'], str(self.capture))
        self.assertEqual(list(stage['symbols']), new['selectedSymbols'])
        self.assertEqual(stage['symbols']['1111.T'], self.stage['symbols']['1111.T'])
        self.assertEqual(basis['selectedSymbols'], new['selectedSymbols'])
        self.assertEqual(new['excludedFromEntry'], ['3333.T'])
        self.assertFalse(new['datedMasterCreated'])
        self.assertEqual(new['reviewStatus'], 'NOT_REVIEWED')
        self.assertEqual(chart['chartPlan']['reserveEmptyChartSlots'], 3)

    def test_original_receipts_and_model_paths_are_preserved(self):
        files = (self.chart_file, self.mask_file, self.stage_file, self.basis_file, self.handoff_file)
        before = {file: file.read_bytes() for file in files}
        new, _ = m.read(self.execute())
        for file, raw in before.items():
            self.assertEqual(file.read_bytes(), raw)
        for key in ('runtimeRoot', 'h235ModelRoot', 'weeklySourceRun', 'settingsFile', 'previousCaptureDir'):
            self.assertEqual(new['spec'][key], self.spec[key])

    def test_repeat_same_source_is_idempotent(self):
        self.assertEqual(self.execute(), self.execute())

    def test_rights_true_excludes_even_when_listing_eligible(self):
        basis = deepcopy(self.basis)
        basis['rows'][0]['nearTermRightsEventListed'] = True
        allowed, excluded = s.eligible_scope(self.handoff, basis)
        self.assertEqual(allowed, ['2222.T'])
        self.assertEqual([r['symbol'] for r in excluded], ['1111.T', '3333.T'])

    def test_unknown_rights_not_promoted_to_clear(self):
        basis = deepcopy(self.basis)
        basis['rows'][0]['nearTermRightsEventListed'] = None
        with self.assertRaisesRegex(ValueError, 'SOURCE_ROW_INCOMPLETE'):
            s.eligible_scope(self.handoff, basis)

    def test_incomplete_rights_publication_rejected(self):
        basis = deepcopy(self.basis)
        basis['rightsSourceParsed'] = False
        with self.assertRaisesRegex(ValueError, 'PUBLIC_BASIS_NOT_USABLE'):
            s.eligible_scope(self.handoff, basis)

    def test_duplicate_or_reordered_public_rows_rejected(self):
        for rows in ([self.basis['rows'][0]] * 3, list(reversed(self.basis['rows']))):
            basis = deepcopy(self.basis)
            basis['rows'] = rows
            with self.assertRaisesRegex(ValueError, 'PUBLIC_ROWS_SCOPE'):
                s.eligible_scope(self.handoff, basis)

    def test_zero_eligible_does_not_create_runnable_scope(self):
        basis = deepcopy(self.basis)
        for row in basis['rows']:
            row['eligible'] = False
        with self.assertRaisesRegex(ValueError, 'NO_ELIGIBLE_ENTRIES'):
            s.eligible_scope(self.handoff, basis)

    def test_document_tamper_stops_before_outputs(self):
        file = self.docs / (self.basis['rows'][0]['listingSourceSha256'] + '.source')
        file.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'DOCUMENT_BYTES_CHANGED'):
            self.execute()
        self.assertFalse(list(self.root.glob('entry-eligibility-*')))

    def test_wrong_symbol_document_rejected(self):
        basis = deepcopy(self.basis)
        basis['rows'][0]['listingSourceSha256'] = basis['rows'][1]['listingSourceSha256']
        with self.assertRaisesRegex(ValueError, 'LISTING_DOCUMENT_SYMBOL_MISMATCH'):
            s.verify_documents(m, self.handoff, basis)

    def test_expected_count_change_blocks_before_writes(self):
        with self.assertRaisesRegex(ValueError, 'EXPECTED_ENTRY_COUNT_CHANGED'):
            s.scope(m, self.handoff_file, expected_count=3)
        self.assertFalse(list(self.root.glob('entry-eligibility-*')))

    def test_wrong_runner_is_not_imported(self):
        file = self.root / 'untrusted.py'
        file.write_text('raise AssertionError("MUST_NOT_IMPORT")', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'EXISTING_RUNNER_CHANGED'):
            s.load_runner(file)

    def test_native_narrow_retains_protected_exit_chart(self):
        # Direct transform test: exclusion must not delete a chart pinned by the
        # original plan for holdings, Watch or pending orders.
        chart = deepcopy(self.chart)
        plan = chart['chartPlan']
        plan['protectedChartSymbols'] = ['3333.T']
        plan['pendingOrderSymbols'] = ['3333.T']
        plan['scanChartSymbols'] = ['1111.T', '2222.T']
        body = {k: v for k, v in plan.items() if k != 'planSha256'}
        plan['planSha256'] = m.sha(json.dumps(body, separators=(',', ':'), ensure_ascii=False).encode())
        file = self.receipt(self.daily, 'no11-chart50-private', chart, 16)
        evidence = m.immutable(self.root, 'entry-eligibility', {
            'schemaId': 'ARK_NO11_AUTOMATIC_MASTER_ELIGIBILITY_V1', 'sessionDate': DAY,
            'parentChartPlanSha256': plan['planSha256'],
            'eligibleSymbols': ['1111.T', '2222.T'], 'orderTransmission': False})
        spec = {**self.spec, 'chartReceipt': str(file)}
        _, narrowed, _ = s.narrow_chart(m, spec, evidence)
        self.assertIn('3333.T', narrowed['chartPlan']['allRequestedChartSymbols'])
        self.assertNotIn('3333.T', narrowed['chartPlan']['selectorInputSymbols'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
