"""Narrow preperformance integration proof for unchanged Pattern187 transport."""
from copy import deepcopy
import unittest
import numpy as np
from scripts import phase57_exit_finite_r36 as r36
from scripts import phase57_exit_gen2_data_r41 as r41
from scripts.phase57_exit_gen3_pattern_r45 import parallel_patterns
from scripts.phase57_exit_gen3_runtime_r45 import load_protocol, endpoints


class PatternTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = load_protocol()
        cohort = r36.read_json(r36.r25.COHORT)['opportunityIds']
        cls.oid = sorted(cohort)[0]
        raw = r36.read_json(r36.RAW_PATHS)
        cls.raw = {cls.oid: raw[cls.oid]}
        origins = r36.read_json(r36.PATTERN_OPPORTUNITIES)
        cls.origins = {r['id']: r['origin'] for r in origins if r['id'] == cls.oid}
        cls.day = cls.oid.split('|', 1)[0]
        start = r36.chart_minute(cls.origins[cls.oid]['decisionTimestamp'])
        cls.epochs = [t for t in endpoints(cls.day) if t > start][:3]
        assert cls.epochs

    def test_two_worker_bytes_match_serial_for_exact_keys(self):
        keys = [(self.oid, t) for t in self.epochs]
        result = parallel_patterns(self.day, keys[::-1] + keys[:1], self.raw, self.origins,
                                   self.p['features']['patternNames'], 2)
        self.assertEqual(list(result), sorted(keys))
        for oid, now in keys:
            expected = r41.pattern_vector(self.day, now, self.raw[oid], self.origins[oid], self.p['features']['patternNames'])
            np.testing.assert_array_equal(np.asarray(result[(oid, now)], np.float32), np.asarray(expected, np.float32))

    def test_future_suffix_cannot_change_pattern_prefix(self):
        now = self.epochs[0]; path = self.raw[self.oid]
        a = r41.pattern_vector(self.day, now, path, self.origins[self.oid], self.p['features']['patternNames'])
        mutated = deepcopy(path)
        for row in mutated['today']:
            if row[0] + 1 > now:
                for j in range(1, 5):
                    if isinstance(row[j], (int, float)): row[j] *= 1.123
        b = r41.pattern_vector(self.day, now, mutated, self.origins[self.oid], self.p['features']['patternNames'])
        np.testing.assert_array_equal(np.asarray(a, np.float32), np.asarray(b, np.float32))

    def test_worker_count_is_frozen(self):
        with self.assertRaises(ValueError):
            parallel_patterns(self.day, [], {}, {}, self.p['features']['patternNames'], 3)


if __name__ == '__main__':
    unittest.main()
