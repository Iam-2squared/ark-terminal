"""Synthetic adapter/policy tests only; no provider or protected input opened."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from scripts import phase57_dual_entry_exit_integration_v1 as m


class DualEntryExitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = m.load_module(m.CANDIDATE, 'test_frozen_candidate_a_dual')
        cls.fixed = m.load_module(m.FIXED, 'test_frozen_fixed12_dual')

    def entry(self, minute=570, day='2025-06-02'):
        oid = day + '|12340'
        return {'opportunity': oid, 'session': day, 'symbol': '12340',
                'entryId': oid + '|' + str(minute), 'entryMinute': minute, 'price': 100.05}

    def raw(self, minutes):
        return {'today': [[t, 100., 101., 99., 100., 100., 10000.] for t in minutes], 'sourceHash': 'synthetic'}

    def event(self, specs, start=570):
        bars = []
        for i, spec in enumerate(specs):
            minute = start + i * 5
            b = {'slot': i + 1, 'start': m.stamp('2025-06-02', minute),
                 'end': m.stamp('2025-06-02', minute + 5), 'minutes': (i + 1) * 5,
                 'openTimestamp': m.stamp('2025-06-02', minute), 'observedMinutes': 5,
                 'missing': False, 'o': 0., 'h': 0., 'l': 0., 'c': 0.}
            b.update(spec)
            bars.append(b)
        return {'direction': 'LONG', 'status': 'REFERENCE_POSITION', 'expectedBars': len(bars),
                'positionStartTimestamp': m.stamp('2025-06-02', start), 'future': bars}

    def replay(self, event):
        return m.replay_pair(event, self.candidate, self.fixed)

    def test_envelope_does_not_access_outcome_fields(self):
        class Guard(dict):
            def __getitem__(self, key):
                if key not in m.ENVELOPE_KEYS:
                    raise AssertionError('FUTURE_FIELD_READ')
                return super().__getitem__(key)
        r = Guard(self.entry(), labels={'future': 100}, quality={'oracle': 100})
        self.assertEqual(m.envelope(r), self.entry())

    def test_entry_id_or_price_invalid_fails_closed(self):
        for key, value in [('entryId', 'wrong'), ('price', 0), ('price', float('nan')), ('entryMinute', True)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                m.envelope(dict(self.entry(), **{key: value}))

    def test_no_entry_not_replaced_with_fill_or_zero_return(self):
        e = dict(self.entry(), entryId=None, entryMinute=None, price=None)
        out = self.replay(m.adapt(m.envelope(e), {}))
        self.assertEqual(out['candidateA'], {'status': 'NO_ENTRY', 'netPct': None})

    def test_exact_frozen_fill_price_and_time_preserved(self):
        e = self.entry()
        event = m.adapt(e, self.raw(range(570, 635)))
        self.assertEqual(event['entry'], e)
        self.assertEqual(event['fillPriceAssumption'], 100.05)
        self.assertAlmostEqual(event['future'][0]['o'], 100 * (100 / 100.05 - 1))
        wrong = dict(e, price=100)
        with self.assertRaises(ValueError):
            m.adapt(wrong, self.raw(range(570, 635)))

    def test_offgrid_containing_bar_is_not_a_full_post_entry_bar(self):
        e = self.entry(571)
        raw = self.raw(range(565, 640))
        raw['today'][7][2] = 9999  # 09:32 HIGH: before first full post-entry bar.
        a = m.adapt(e, raw)
        self.assertEqual(a['future'][0]['start'], m.stamp(e['session'], 575))
        self.assertEqual(a['initialPartialBucketMinutesNotUsed'], 4)
        self.assertLess(a['future'][0]['h'], 1)
        raw['today'][7][2] = 8888
        self.assertEqual(a, m.adapt(e, raw))

    def test_pre_entry_high_cannot_arm_protect(self):
        raw = self.raw(range(565, 635))
        raw['today'][0][2] = 9999
        a = m.adapt(self.entry(), raw)
        self.assertTrue(all(b.get('h', 0) < 3 for b in a['future']))
        self.assertNotEqual(self.replay(a)['candidateA'].get('reason'), 'PROTECT_EXIT')

    def test_missing_entry_minute_is_not_backfilled(self):
        with self.assertRaises(ValueError):
            m.adapt(self.entry(571), self.raw([570, 572, 575]))

    def test_lunch_is_calendar_gap_not_missing_bar(self):
        a = m.adapt(self.entry(689), self.raw([689, 750, 751, 752, 753, 754]))
        self.assertEqual(a['future'][0]['start'], m.stamp('2025-06-02', 750))
        self.assertEqual(a['future'][0]['minutes'], 66)
        self.assertFalse(a['future'][0]['missing'])
        self.assertFalse(any('T11:3' in b['start'] for b in a['future']))

    def test_auction_not_substituted_and_legacy_calendar_not_shortened(self):
        a = m.adapt(self.entry(870), self.raw([*range(870, 925), 930]))
        self.assertEqual(a['expectedBars'], 12)
        self.assertEqual(a['future'][-1]['start'], m.stamp('2025-06-02', 925))
        self.assertTrue(a['future'][-1]['missing'])
        r = self.replay(a)
        self.assertEqual(r['fixed12']['status'], 'CENSORED')
        self.assertTrue(r['candidateA']['capitalMustRemainLocked'])

    def test_sparse_open_timestamp_is_not_backdated(self):
        raw = self.raw([570, 571, 572, 573, 574, 577, 579])
        a = m.adapt(self.entry(), raw)
        b = a['future'][1]
        self.assertFalse(b['missing'])
        self.assertEqual(b['observedMinutes'], 2)
        self.assertEqual(b['openTimestamp'], m.stamp('2025-06-02', 577))
        self.assertEqual(b['end'], m.stamp('2025-06-02', 580))

    def test_duplicate_and_bad_ohlc_fail_closed(self):
        raw = self.raw(range(570, 575))
        raw['today'].append(raw['today'][0])
        with self.assertRaises(ValueError):
            m.adapt(self.entry(), raw)
        raw = self.raw(range(570, 575)); raw['today'][0][2] = 90
        with self.assertRaises(ValueError):
            m.adapt(self.entry(), raw)

    def test_same_arm_bar_close_cannot_signal(self):
        e = self.event([{'h': 3, 'c': 0}, {'h': 3, 'c': 2}, {'c': 2}])
        a = self.replay(e)['candidateA']
        self.assertEqual(a['candidateExitReason'], 'FIXED12_FALLBACK')

    def test_inclusive_thresholds_and_next_open_not_signal_close(self):
        e = self.event([{'h': 3, 'c': 3}, {'h': 3, 'c': 1}, {'o': 1.7, 'h': 2, 'c': .5}])
        a = self.replay(e)['candidateA']
        self.assertEqual((a['signalBar'], a['exitBar']), (2, 3))
        self.assertAlmostEqual(a['netPct'], 1.65)
        self.assertEqual(a['exitTimestamp'], e['future'][2]['openTimestamp'])

    def test_no_loss_defense_or_two_lower_close_rule(self):
        e = self.event([{'h': 0, 'c': -i} for i in range(1, 14)])
        a = self.replay(e)['candidateA']
        self.assertEqual(a['exitBar'], 12)
        self.assertEqual(a['candidateExitReason'], 'FIXED12_FALLBACK')

    def test_exact_fixed12_cap_and_cost_charged_once(self):
        e = self.event([{'h': 2, 'c': 2} for _ in range(15)])
        r = self.replay(e)
        self.assertEqual(r['fixed12']['exitBar'], 12)
        self.assertEqual(r['candidateA']['grossPct'], 2)
        self.assertAlmostEqual(r['candidateA']['netPct'], 1.95)
        self.assertEqual(r['candidateA']['exitTimestamp'], e['future'][11]['end'])

    def test_calendar_shorter_than12_uses_exact_last_close(self):
        e = self.event([{'c': 0}, {'c': 1}])
        a = self.replay(e)['candidateA']
        self.assertEqual(a['exitBar'], 2)
        self.assertEqual(a['reason'], 'CALENDAR_SESSION_CAP')

    def test_fixed12_missing_future_does_not_filter_early_candidate_exit(self):
        e = self.event([{'h': 4, 'c': 3}, {'c': 1}, {'o': .8, 'c': 1}, {'missing': True}])
        r = self.replay(e)
        self.assertEqual(r['fixed12']['status'], 'CENSORED')
        self.assertEqual(r['candidateA']['status'], 'EXIT_REFERENCE')
        self.assertAlmostEqual(r['candidateA']['netPct'], .75)

    def test_future_suffix_after_candidate_exit_cannot_change_candidate(self):
        e = self.event([{'h': 4, 'c': 3}, {'c': 1}, {'o': .8, 'c': 1}, {'c': 1}])
        before = self.replay(e)['candidateA']
        e['future'][3].update(c=-95, h=999)
        self.assertEqual(before, self.replay(e)['candidateA'])

    def test_late_observed_next_open_holding_time_is_causal(self):
        e = self.event([{'h': 4, 'c': 3}, {'c': 1}, {'o': .8, 'c': 1}])
        e['future'][2]['openTimestamp'] = m.stamp('2025-06-02', 583)
        a = self.replay(e)['candidateA']
        self.assertEqual(a['holdingClockMinutes'], 13)
        self.assertEqual(a['sparseOpenDelayMinutes'], 3)

    def test_missing_next_bucket_no_fill_no_later_backfill(self):
        e = self.event([{'h': 4, 'c': 3}, {'c': 1}, {'missing': True}, {'o': .8}])
        a = self.replay(e)['candidateA']
        self.assertEqual(a['status'], 'CENSORED')
        self.assertIsNone(a['netPct'])

    def test_exit_bar_high_not_credited_as_owned_plus5(self):
        e = self.event([{'h': 4, 'c': 3}, {'c': 1}, {'o': .8, 'h': 6, 'c': 2}])
        r = {'path': e, **self.replay(e)}
        p = m.preservation([r], 5)
        self.assertEqual(p['legacySlotPreserved'], 1)
        self.assertEqual(p['ownershipTimeCredited'], 0)
        self.assertEqual(p['exitBarHighOnlyNotCredited'], 1)

    def test_empty_population_metrics_are_null_not_zero(self):
        p = m.performance([])
        self.assertIsNone(p['netReturnPct']['mean'])
        self.assertIsNone(p['profitFactor'])
        self.assertIsNone(p['winRatePct'])

    def test_output_is_deterministic_and_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / 'a.json.gz', Path(td) / 'b.json.gz'
            value = {'safety': m.SAFETY, 'x': [1, 2, None]}
            m.write_new(a, value); m.write_new(b, value)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(m.read(a), value)
            with self.assertRaises(FileExistsError):
                m.write_new(a, value)


    def test_unselected_raw_values_not_deserialized(self):
        import gzip
        # An opaque unselected value contains a token that JSON decoding would
        # reject. Structural skipping must never deserialize that value.
        text = '{"sealed":{"future":UNREAD_PARTITION_TOKEN},"allowed":{"today":[]}}'
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'paths.json.gz'
            p.write_bytes(gzip.compress(text.encode()))
            self.assertEqual(m.read_allowlisted_paths(p, {'allowed'}), {'allowed': {'today': []}})
            with self.assertRaises(ValueError):
                m.read_allowlisted_paths(p, {'missing'})

    def test_allowlisted_reader_handles_escaped_strings_and_duplicate_ids(self):
        import gzip
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'paths.json.gz'
            obj = {'excluded': {'x': ['a}b', '"{', {'nested': 2}]}, 'allowed': {'today': []}}
            p.write_bytes(gzip.compress(json.dumps(obj).encode()))
            self.assertEqual(m.read_allowlisted_paths(p, {'allowed'}), {'allowed': {'today': []}})
            p.write_bytes(gzip.compress(b'{"allowed":{},"allowed":{}}'))
            with self.assertRaises(ValueError):
                m.read_allowlisted_paths(p, {'allowed'})

    def test_all_safety_flags_false(self):
        self.assertEqual(len(m.SAFETY), 9)
        self.assertTrue(all(v is False for v in m.SAFETY.values()))


if __name__ == '__main__':
    unittest.main()
