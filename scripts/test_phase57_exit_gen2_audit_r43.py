"""Corruption regressions for the post-run model identity/hash boundary."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.phase57_exit_gen2_audit_r43 import model_inventory


class ModelInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'models').mkdir()
        self.protocol = {'predictionSpecs': [{'specId': f'S{i}'} for i in range(4)],
                         'split': {'folds': [{'fold': i} for i in range(1, 5)]},
                         'entryArms': ['A', 'B']}
        self.models, self.journal = [], []
        for spec in self.protocol['predictionSpecs']:
            for fold in range(1, 5):
                for arm in ('A', 'B'):
                    for head in ('CONTINUATION', 'FAILURE'):
                        name = f"{spec['specId']}__F{fold}__{arm}__{head}.joblib"
                        payload = name.encode()
                        (self.root / 'models' / name).write_bytes(payload)
                        row = {'spec': spec['specId'], 'fold': fold, 'arm': arm, 'head': head,
                               'ordinal': len(self.models) + 1, 'file': name,
                               'sha256': hashlib.sha256(payload).hexdigest(),
                               'trainRows': 100, 'scoreRows': 10, 'featureColumns': 5}
                        self.models.append(row)
                        self.journal.extend([{**row, 'status': 'FIT_ATTEMPT_STARTED'},
                                             {**row, 'status': 'FIT_AND_BUNDLE_COMPLETED'}])
        self.write_journal()

    def write_journal(self):
        (self.root / 'fit-progress.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in self.journal))

    def audit(self, models=None):
        return model_inventory(self.root, self.protocol, {'models': models or self.models})

    def test_complete_grid_is_accepted_without_loading_or_fitting_models(self):
        self.assertEqual(self.audit()['completed'], 64)

    def test_duplicate_identity_cannot_hide_missing_model(self):
        models = copy.deepcopy(self.models)
        models[-1] = copy.deepcopy(models[0])
        with self.assertRaisesRegex(ValueError, 'MODEL_IDENTITY_GRID'):
            self.audit(models)

    def test_changed_bundle_rejected_even_with_unchanged_inventory_count(self):
        (self.root / 'models' / self.models[0]['file']).write_bytes(b'corruption')
        with self.assertRaisesRegex(ValueError, 'MODEL_BUNDLE_HASH'):
            self.audit()

    def test_unreported_bundle_rejected(self):
        (self.root / 'models/extra.joblib').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'MODEL_FILE_ALLOWLIST'):
            self.audit()

    def test_reordered_journal_or_extra_attempt_rejected(self):
        self.journal[1], self.journal[3] = self.journal[3], self.journal[1]
        self.write_journal()
        with self.assertRaisesRegex(ValueError, 'FIT_JOURNAL_IDENTITY'):
            self.audit()
        self.journal.append(self.journal[0])
        self.write_journal()
        with self.assertRaisesRegex(ValueError, 'FIT_JOURNAL_COUNT'):
            self.audit()


if __name__ == '__main__':
    unittest.main()
