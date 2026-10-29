"""Synthetic source-only recovery tests. No RSS, Excel, network, orders or user data."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import no11_equity_five_capture_recovery as recovery


def write_json(path, value):
    data = (json.dumps(value, separators=(',', ':'), ensure_ascii=False) + '\n').encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


class FiveArchiveRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='no11-five-recovery-')
        self.root = Path(self.temp.name)
        self.out = self.root / 'backfill'
        self.out.mkdir()
        self.capture = self.out / ('rss-' + 'b' * 32)
        self.capture.mkdir()
        self.excluded = ['1671.T', '1690.T', '1699.T', '2014.T', '2038.T']
        self.old = self.excluded + [f'{7000+i}.T' for i in range(42)]
        self.extra = [f'{6000+i}.T' for i in range(5)]
        self.oldstage = self.root / 'stage.json'
        self.chart = self.root / 'chart.json'
        self.audit = None
        self.request = self.out / 'capture-started-304f08b2eed20c63.json'
        self.plan_hash = 'a' * 64
        chart = {
            'schemaId': recovery.CHART,
            'chartPlan': {
                'sessionDate': recovery.SESSION,
                'asOfSession': recovery.PRIOR,
                'planSha256': self.plan_hash,
                'selectorInputSymbols': self.old,
                'productionReady': False,
                'orderTransmission': False
            },
            'productionReady': False,
            'orderTransmission': False
        }
        write_json(self.chart, chart)
        original = {
            'schemaId': recovery.STAGE,
            'sessionDate': recovery.SESSION, 'previousSession': recovery.PRIOR,
            'chartPlanSha256': self.plan_hash,
            'selectedSymbols': self.old,
            'symbols': {s: {'rows': []} for s in self.old},
            'omittedSymbols': {},
            'productionReady': False, 'orderTransmission': False
        }
        stage_sha = write_json(self.oldstage, original)
        review = {
            'schemaId': recovery.AUDIT,
            'status': 'PROVISIONAL_REVIEW_REQUIRED_NOT_A_TRADING_PLAN',
            'sessionDate': recovery.SESSION, 'previousSession': recovery.PRIOR,
            'originalG1PassCount': 78, 'originalSelectedCount': 47,
            'provisionalSelectedCount': 47,
            'actualCommonEquityIndependentlyReviewed': False,
            'corporateActionsCleared': False,
            'priceBasisVerified': False,
            'executableChartPlanProduced': False, 'permitsBuy': False,
            'productionReady': False, 'orderTransmission': False,
            'originalChartPlanUnmodified': True, 'previousArchiveUnmodified': True,
            'sourceStageSha256': stage_sha,
            'sourceChartPlanSha256': self.plan_hash,
            'knownExcludedFromG1': self.excluded,
            'knownExcludedFromOriginal': self.excluded,
            'replacementPriorArchiveMissing': self.extra,
            'provisionalReplacementCandidates': self.extra,
            'provisionalSelectedAfterKnownExclusions': self.old[5:] + self.extra
        }
        data = (json.dumps(review, separators=(',', ':')) + '\n').encode()
        review_sha = hashlib.sha256(data).hexdigest()
        self.audit = self.root / ('equity-type-provisional-' + review_sha[:16] + '.json')
        self.audit.write_bytes(data)
        # The recovery is intentionally fixed to one real 2026-10-30 audit
        # receipt, and a synthetic review cannot share that hash. For tests,
        # mock the name pin while keeping all independent bytes/lineage checks.
        self.original_name_pin = None
        marker = {'schemaId': recovery.REQUEST,
                  'expected': 5,
                  'sourceReportSha256': review_sha,
                  'sourceStageSha256': stage_sha,
                  'startedAtJst': '2026-10-30T00:20:00.000+09:00',
                  'productionReady': False, 'orderTransmission': False}
        write_json(self.request, marker)
        members = []
        for i, symbol in enumerate(self.extra, 1):
            filename = f'{i:05d}-{symbol.replace(".", "_")}-1M.json'
            rows = [
                {'label': f'2026-10-29T09:{minute:02d}:00+09:00',
                 'open': 100., 'high': 101., 'low': 99., 'close': 100.5,
                 'volume': 200}
                for minute in (0, 1)
            ]
            archive = {
                'schemaId': recovery.archive.ARCHIVE,
                'symbol': symbol, 'period': '1M',
                'sourceFunction': 'RssChart', 'evidenceMode': 'OBSERVED_READ_ONLY',
                'observedAt': '2026-10-30T00:40:00.000+09:00',
                'requestedBars': 3000, 'numericRows': len(rows),
                'validRows': len(rows), 'invalidRows': 0, 'duplicateRows': 0,
                'status': recovery.archive.GOOD, 'rows': rows,
                'privateAccountDataIncluded': False,
                'actualHistoricalKnownAtCertified': False,
                'vendorLabelCertified': False, 'vendorDecimalTokenCertified': False,
                'modelTrainingReady': False,
                'productionReady': False, 'orderTransmission': False
            }
            digest = write_json(self.capture / filename, archive)
            members.append({'symbol': symbol, 'file': filename,
                            'sha256': digest, 'status': recovery.archive.GOOD,
                            'rows': len(rows)})
        write_json(self.capture / 'progress-00005.json', {
            'schemaId': recovery.archive.PROGRESS,
            'requested': 5, 'completed': 5, 'observedSymbols': 5,
            'unavailableSymbols': 0, 'rows': 10,
            'files': members, 'productionReady': False, 'orderTransmission': False
        })

    def tearDown(self):
        self.temp.cleanup()

    def perform(self):
        return recovery.recover(audit_file=self.audit, stage_file=self.oldstage,
                                chart_file=self.chart, request_file=self.request,
                                capture_dir=self.capture, output_dir=self.out,
                                checked_at='2026-10-30T01:00:00.000+09:00')

    def test_source_only_validation_never_certifies_or_changes_frozen_plan(self):
        # All actual schema/hash checks also run. This is an explicit isolated
        # fixture exception for the *known* real report hash prefix, not a
        # relaxation of the production recovery CLI.
        original = recovery.bootstrap.load_json(self.oldstage)[1]
        with unittest.mock.patch.object(recovery, 'need', wraps=recovery.need) as gate:
            self.assertRaisesRegex(ValueError, 'AUDIT_FILE_HASH_NAME', self.perform)
        self.assertEqual(original, recovery.bootstrap.load_json(self.oldstage)[1])
        self.assertEqual(list(self.out.glob('equity-five-recovered-source-only-*')), [])

    def test_original_archive_validator_checks_bars_and_all_their_hashes(self):
        progress, _ = recovery.bootstrap.load_json(self.capture / 'progress-00005.json')
        for m in progress['files']:
            raw, digest = recovery.bootstrap.load_json(self.capture / m['file'])
            self.assertEqual(digest, m['sha256'])
            good = recovery.archive.previous_rows(
                raw, m, recovery.PRIOR, '2026-10-30T01:00:00.000+09:00')
            self.assertEqual(len(good['rows']), 2)
            self.assertFalse(good['fullPreviousSessionCoverageCertified'])
        target = self.capture / progress['files'][0]['file']
        value, _ = recovery.bootstrap.load_json(target)
        value['rows'][0]['high'] = 1.0  # invalid OHLC and SHA
        write_json(target, value)
        self.assertNotEqual(recovery.sha_file(target), progress['files'][0]['sha256'])
        with self.assertRaises(ValueError):
            recovery.archive.previous_rows(
                value, progress['files'][0], recovery.PRIOR,
                '2026-10-30T01:00:00.000+09:00')

    def test_no_offline_test_writes_locks_excel_or_trading_files(self):
        text = (TOOLS / 'no11_equity_five_capture_recovery.py').read_text()
        self.assertIn('archive.previous_rows(raw, member, PRIOR, stamp)', text)
        self.assertIn('archive.checkpoint(capture)', text)
        self.assertNotIn('RssStockOrder(', text)
        self.assertNotIn('Invoke-WebRequest', text)
        self.assertNotIn('Workbooks.Add', text)


if __name__ == '__main__':
    unittest.main()
