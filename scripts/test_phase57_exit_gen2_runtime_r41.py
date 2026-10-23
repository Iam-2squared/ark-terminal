"""Synthetic contract checks; no Development model fits or policy performance."""
import ast
import copy
import math
from pathlib import Path
import unittest

from scripts import phase57_exit_gen2_runtime_r41 as runtime


class Gen2RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.contract = runtime.load_protocol()
        self.c = self.contract['candidates'][0]

    def test_hash_pinned_unique_finite_grid(self):
        self.assertEqual(len(self.contract['candidates']), 16)
        self.assertEqual(self.contract['execution']['expectedModelFitCount'], 64)
        self.assertEqual(len(self.contract['features']['patternNames']), 187)
        self.assertEqual(len({(c['predictionSpec'], c['continuationWeakMax'],
                              c['failureStrongMin'], c['persistenceFreshCheckpoints'])
                              for c in self.contract['candidates']}), 16)

    def test_mutating_loaded_contract_cannot_change_runtime(self):
        self.contract['candidates'][0]['continuationWeakMax'] = 1.
        with self.assertRaisesRegex(ValueError, 'UNREGISTERED_POLICY'):
            runtime.intent([.8, .9], True, 0, self.contract['candidates'][0], 600)
        self.assertEqual(runtime.load_protocol()['candidates'][0]['continuationWeakMax'], .35)

    def test_only_weak_continuation_and_strong_failure_exits(self):
        self.assertEqual(runtime.intent([.35, .60], True, 0, self.c, 600)['action'], 'EXIT_INTENT')
        for values in ([.8, .8], [.8, .2], [.2, .2], [.351, .6], [.35, .599]):
            self.assertEqual(runtime.intent(values, True, 8, self.c, 600), {'action': 'HOLD', 'consecutive': 0})

    def test_fresh_persistence_missing_does_not_become_false(self):
        c = self.contract['candidates'][1]
        a = runtime.intent([.2, .8], True, 0, c, 600)
        self.assertEqual(a, {'action': 'HOLD', 'consecutive': 1})
        for values, fresh in (([.2, .8], False), ([None, .8], True), ([math.nan, .8], True)):
            self.assertEqual(runtime.intent(values, fresh, 1, c, 601), a)
        self.assertEqual(runtime.intent([.2, .8], True, 1, c, 602)['action'], 'EXIT_INTENT')
        self.assertEqual(runtime.intent([.8, .8], True, 1, c, 602)['consecutive'], 0)

    def test_unknown_out_of_range_and_boolean_scores_hold(self):
        for scores in ([True, .8], [-.1, .8], [.2, 1.1], [math.inf, .9], [1], None):
            self.assertEqual(runtime.intent(scores, True, 1, self.c, 600), {'action': 'HOLD', 'consecutive': 1})

    def test_terminal_bypasses_scores_and_freshness(self):
        self.assertEqual(runtime.intent(None, False, 1, self.c, 925), {'action': 'FORCE_TERMINAL', 'consecutive': 1})
        self.assertEqual(runtime.calendar_features('2025-07-03', 925), [0, 0, 0])

    def test_lunch_is_scheduled_active_time(self):
        self.assertEqual(runtime.calendar_features('2025-07-03', 690), [175, 60, 15])
        self.assertEqual(runtime.calendar_features('2025-07-03', 751), [174, 60, 15])
        self.assertEqual(runtime.calendar_features('2025-07-03', 920), [5, 5, 5])

    def test_invalid_epoch_and_unregistered_configuration_rejected(self):
        for now in (True, 540, 700, 750, 930):
            with self.assertRaises(ValueError): runtime.calendar_features('2025-07-03', now)
        for key, value in (('candidateId', 'GEN2_R41_17'), ('failureStrongMin', .59), ('extraStop', 1)):
            c = dict(self.c); c[key] = value
            with self.assertRaisesRegex(ValueError, 'UNREGISTERED_POLICY'):
                runtime.intent([.2, .8], True, 0, c, 600)

    def test_runtime_import_graph_has_no_label_trainer_or_evaluator(self):
        tree = ast.parse(Path(runtime.__file__).read_text())
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        local = [m for m in imports if m and m.startswith('scripts')]
        self.assertEqual(local, ['scripts.phase57_exit_execution_contract_v1'])
        args = [a.arg for a in ast.parse(Path(runtime.__file__).read_text()).body[-1].args.args]
        self.assertEqual(args, ['scores', 'fresh', 'previous_count', 'candidate', 'now'])

    def test_future_suffix_cannot_alter_known_prefix(self):
        from scripts.phase57_exit_checkpoints_v1 import closed_prefix
        original = [[600, 100, 101, 99, 100, 10, 1000], [601, 100, 102, 98, 100, 10, 1000]]
        changed = copy.deepcopy(original); changed[1][1:5] = [1e8, 1e9, 1, 2]
        self.assertEqual(closed_prefix('2025-07-03', 601, original),
                         closed_prefix('2025-07-03', 601, changed))


if __name__ == '__main__':
    unittest.main()
