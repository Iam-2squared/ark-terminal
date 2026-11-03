"""Pure entry/EXIT separation tests; no account access or trading."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scope_morning_master as s


class ExitContextGuardTests(unittest.TestCase):
    def test_exclusion_of_held_watch_or_pending_requires_existing_context(self):
        for key in ('protectedChartSymbols', 'heldSymbols', 'activeWatchSymbols', 'pendingOrderSymbols'):
            chart = {'chartPlan': {key: ['3333.T']}}
            with self.subTest(key=key), self.assertRaisesRegex(
                    ValueError, 'ACTIVE_EXCLUDED_SYMBOL_REQUIRES_EXISTING_EXIT_CONTEXT'):
                s.protect_exit_context(chart, [{'symbol': '3333.T'}])

    def test_unrelated_protected_charts_remain_unchanged(self):
        chart = {'chartPlan': {'protectedChartSymbols': ['1111.T'], 'heldSymbols': ['1111.T'],
                              'activeWatchSymbols': [], 'pendingOrderSymbols': []}}
        old = deepcopy(chart)
        s.protect_exit_context(chart, [{'symbol': '3333.T'}])
        self.assertEqual(chart, old)


if __name__ == '__main__':
    unittest.main(verbosity=2)
