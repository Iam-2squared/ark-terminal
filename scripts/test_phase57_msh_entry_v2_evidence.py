"""Saved Development evidence integrity; never fit or predict Project rows."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import audit_phase57_msh_entry_v2_predevelopment as frozen
from scripts import phase57_msh_entry_v2_development as dev
from scripts.phase57_msh_entry_v2_evaluation import choose_threshold, entry_gates
from predict.research import phase57_msh_entry_long_v2_d30 as model

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/phase57-msh-entry-long-v2-development'


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


class SavedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = read(ROOT / frozen.CONTRACT)
        cls.result = read(BASE / 'run/development.json.gz')
        with gzip.open(ROOT / frozen.FEATURE_ROWS, 'rt') as handle:
            cls.rows = {r['selectorEventId']: r for r in map(json.loads, handle)}

    def setUp(self):
        for name in ('fit', 'predict'):
            guard = patch.object(model, name, side_effect=AssertionError('NO_PROJECT_FIT_OR_PREDICTION_IN_EVIDENCE_AUDIT'))
            guard.start()
            self.addCleanup(guard.stop)

    def test_manifest_frozen_sources_and_prefit_implementation_unchanged(self):
        payload = (BASE / 'manifest.json').read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), (BASE / 'manifest.sha256').read_text().strip())
        manifest = json.loads(payload)
        self.assertEqual(manifest['contractSHA'], model.CONTRACT_SHA)
        self.assertEqual(manifest['verdict'], self.result['status'])
        for path, digest in manifest['files'].items():
            self.assertEqual(frozen.sha(ROOT / path), digest, path)
        audit, _ = frozen.audit()
        self.assertTrue(audit['frozenSelectorEntryExitAllocationLedgerUnchanged'])
        dev.require_prefit(read(BASE / 'prefit-tests.json'))
        self.assertEqual(self.result['pathSHA'], frozen.sha(BASE / 'paths.json.gz'))

    def test_saved_models_have_only_permitted_inner_training_rows(self):
        manifest = read(BASE / 'run/fit-manifest.json')
        self.assertEqual(len(manifest), 24)
        self.assertEqual(len(list((BASE / 'run/models').glob('*.json'))), 24)
        for record in manifest:
            name = record['name']
            self.assertTrue(name.endswith('-inner'))
            path = BASE / 'run/models' / (name + '.json')
            self.assertEqual(frozen.sha(path), record['fileSHA'])
            artifact = model.load_artifact(path)
            self.assertEqual(artifact['artifactSHA'], record['artifactSHA'])
            self.assertEqual(artifact['featureOrder'], self.result['runtimePredictorFeatureOrder'])
            self.assertEqual(artifact['lambda'], 1)
            parts = name.split('-')
            number = int(parts[1] if parts[0] == 'chrono' else parts[3])
            group = None if parts[0] == 'chrono' else int(parts[1])
            fold = self.contract['cv']['folds'][number - 1]
            fit, cal, _, evaluation, leak = dev.partition(list(self.rows.values()), fold, self.contract, group)
            self.assertEqual(sum(leak.values()), 0)
            training = artifact['training']
            eligible, excluded = set(training['eligibleIds']), set(training['excludedIds'])
            self.assertFalse(eligible & excluded)
            self.assertEqual(len(eligible), training['eligibleRows'])
            self.assertEqual(len(excluded), training['excludedLabelRows'])
            self.assertEqual(eligible | excluded, {r['selectorEventId'] for r in fit})
            self.assertTrue(all(self.rows[e]['label']['labelable'] for e in eligible))
            self.assertTrue(all(not self.rows[e]['label']['labelable'] for e in excluded))
            self.assertFalse((eligible | excluded) & {r['selectorEventId'] for r in cal + evaluation})
            self.assertEqual(record['evaluationRows'], len(cal))
            if group is not None:
                self.assertTrue(all(frozen.symbol_group(s) != group for s in training['symbols']))

    def test_all_fixed_threshold_gates_reproduce_none_without_new_predictions(self):
        replicas = self.result['chronological'] + self.result['symbolDisjoint']
        self.assertEqual(len(replicas), 24)
        self.assertEqual({r['heldGroup'] for r in self.result['symbolDisjoint']}, set(range(5)))
        for replica in replicas:
            self.assertEqual(replica['status'], 'SELECTION_INCONCLUSIVE_NO_CANDIDATE')
            candidates = replica['innerThresholdResults']
            self.assertEqual(set(candidates), {'1', '2', '5', '10'})
            for candidate in candidates.values():
                self.assertEqual(candidate['gates'], entry_gates(replica['innerBaseline'], candidate['metrics'], self.contract))
                self.assertTrue(any(g['status'] != 'PASS' for g in candidate['gates']))
            self.assertEqual(choose_threshold(candidates), replica['selection'])
            self.assertIsNone(replica['selection']['threshold'])
            self.assertEqual(replica['outerPredictions'], [])
            self.assertEqual(replica['outerDecisions'], [])

    def test_incomplete_oof_and_unpriced_portfolio_cannot_claim_performance(self):
        result = self.result
        self.assertEqual(result['status'], 'MSH_ENTRY_LONG_V2_DEVELOPMENT_BLOCKED')
        self.assertTrue(result['stop'])
        self.assertIsNone(result['selectedThreshold'])
        self.assertIsNone(result['portfolioV2'])
        for name, stream in result['streams'].items():
            self.assertEqual(stream, read(BASE / 'run' / (name + '-oof.json.gz')))
            self.assertEqual(stream['plannedRows'], 3000)
            self.assertEqual(stream['oofRows'], 0)
            self.assertEqual(stream['duplicateCount'], 0)
            self.assertEqual(stream['missingPredictionCount'], 3000)
            self.assertFalse(stream['complete'])
            self.assertIsNone(stream['metrics'])
        self.assertTrue(all(g['status'] == 'INCONCLUSIVE' for g in result['allFrozenGates']))
        baseline = result['portfolioBaseline']
        self.assertEqual(baseline['status'], 'FULL_PORTFOLIO_UNPRICED_EXPOSURE')
        for field in ('finalEquityJpy', 'totalReturnPct', 'maxDrawdownPct', 'maxDrawdownJpy'):
            self.assertIsNone(baseline[field])
        self.assertEqual(result['coverage']['v1PortfolioUnresolved'], 1)
        self.assertIsNone(result['coverage']['v2PortfolioAccepted'])
        self.assertEqual(result['coverage']['candidates'], 3800)
        self.assertEqual(result['coverage']['v1FrozenEnter'], 277)
        self.assertEqual(result['baselineFull76']['strict30mCount'], 181)
        self.assertEqual(result['projectCounters'], {'projectFitAttempts': 24, 'projectFits': 24,
            'predictionRows': 10000, 'predictionBatches': 24, 'thresholdPerformanceCandidates': 4})
        self.assertTrue(all(value == 0 for value in result['integrity'].values()))
        self.assertTrue(all(value is False for value in result['safety'].values()))
        self.assertEqual(len(result['safety']), 9)
        for filename, expected in [('all-threshold-metrics.csv', 96), ('fold-models-and-medians.csv', 24), ('all-frozen-gates.csv', 24)]:
            with (BASE / filename).open() as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
