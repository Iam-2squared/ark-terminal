import copy
import unittest
from scripts.phase57_causal_entry_daily_audit import DAILY_DERIVED, corrected_rows


class DailyAblationAuditTests(unittest.TestCase):
    def test_all_daily_dependencies_excluded_from_intraday(self):
        f = {k: i for i, k in enumerate(DAILY_DERIVED)}
        f.update({'DAILY/returnOC5': 1.2, 'ret5': .1, 'previousRange': 3., 'SCORE/PULLBACK': .5})
        before = [{'features': f, 'path': 'EVALUATOR_ONLY'}]
        snapshot = copy.deepcopy(before)
        after = corrected_rows(before)
        selected = {k: v for k, v in after[0]['features'].items() if not k.startswith('DAILY/')}
        self.assertEqual(selected, {'ret5': .1, 'previousRange': 3., 'SCORE/PULLBACK': .5})
        self.assertEqual(before, snapshot)
        self.assertEqual(after[0]['path'], before[0]['path'])
        for k in DAILY_DERIVED:
            self.assertEqual(after[0]['features']['DAILY/derived/' + k], f[k])

    def test_missing_checkpoint_and_value_remain_missing(self):
        source = [{'features': None}, {'features': {'dailyHighDistance': None}}]
        result = corrected_rows(source)
        self.assertIsNone(result[0]['features'])
        self.assertIsNone(result[1]['features']['DAILY/derived/dailyHighDistance'])


if __name__ == '__main__':
    unittest.main()
