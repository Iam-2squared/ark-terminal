"""Arrival/restart regressions with actual original feature code, fake scorer."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_no11_frozen_p1_rss_state_stream as t
r, f, feature = t.r, t.f, t.feature


class AlwaysWait(t.RecordingScorer):
    def score(self, numeric, categorical):
        result = super().score(numeric, categorical)
        return dict(result, score=.2)


class ArrivalOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = feature.load_feature_runtime(f.REPO)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'private.sqlite'
        self.scorer = AlwaysWait()
        self.session = f.ForwardP1Session(self.db, self.scorer)

    def tearDown(self):
        self.session.close()
        self.temp.cleanup()

    def run_feed(self, data, events):
        return r.consume_received_feed(self.runtime, self.session, data, events, t.previous(),
                                       previous_session=t.PRIOR, through=t.at(610, 0))

    def test_bar_arrives_before_first_selector_same_clock_not_delayed_one_minute(self):
        events = t.selectors()
        events[0]['receivedAtJst'] = t.at(570, 10)
        result = self.run_feed(t.feed(), events)
        self.assertEqual(result['counts']['p1FeatureRows'], 6)
        stored = self.session.db.execute('SELECT result_json FROM evaluations ORDER BY bar_end LIMIT 1').fetchone()
        first = json.loads(stored[0])
        self.assertEqual(first['barEndJst'], t.at(570, 0))
        self.assertEqual(first['evaluatedAtJst'], t.at(570, 10))
        self.assertFalse(first['orderAuthorized'])

    def test_late_refresh_never_leaks_backwards_on_restart(self):
        events = t.selectors() + [{'kind': 'selector', 'receivedAtJst': t.at(600, 10),
                                  'payload': t.base.selector('10:00:00', kind='WATCH_REFRESH')}]
        result = self.run_feed(t.feed(65), events)
        self.assertEqual(result['counts']['p1FeatureRows'], 36)
        index = self.runtime.feature['P1_numeric'].index('knownRefreshCount')
        # 10:00 bar received at :08; refresh arrives at :10, so only 10:01 sees it.
        self.assertEqual(self.scorer.captured[30][0][index], 0)
        self.assertEqual(self.scorer.captured[31][0][index], 1)
        self.session.close()
        self.session = f.ForwardP1Session(self.db, self.scorer)
        again = self.run_feed(t.feed(65), events)
        self.assertEqual(again['counts']['idempotentDecisions'], 36)
        self.assertEqual(self.scorer.calls, 36)

    def test_changed_received_minute_cannot_rewrite_previous_state_or_candidates(self):
        data = t.feed()
        self.run_feed(data, t.selectors())
        revised = deepcopy(data)
        revised['rows'][0]['Va'] += 1
        with self.assertRaisesRegex(ValueError, 'MINUTE_CHANGED_ON_RESTART'):
            self.run_feed(revised, t.selectors())

    def test_duplicate_selector_envelope_does_not_refresh_or_double_evaluate(self):
        events = t.selectors()
        result = self.run_feed(t.feed(), events + deepcopy(events))
        self.assertEqual(result['counts']['p1FeatureRows'], 6)
        self.assertEqual(self.session.watch_context(t.CODE)['refresh_minutes'], [])

    def test_cli_consumes_private_files_with_original_features_and_no_orders(self):
        root = Path(self.temp.name) / 'cli'
        root.mkdir()
        for name, value in [('feed.json', t.feed()), ('selectors.json', t.selectors()),
                            ('previous.json', t.previous())]:
            (root / name).write_text(json.dumps(value), encoding='utf-8')
        output = io.StringIO()
        with patch.object(f, 'FrozenP1Scorer', return_value=t.RecordingScorer()), redirect_stdout(output):
            r.main(['--session', t.DAY, '--through', t.at(580, 0),
                    '--minute-feed', str(root / 'feed.json'),
                    '--selector-events', str(root / 'selectors.json'),
                    '--previous-context', str(root / 'previous.json'),
                    '--runtime-root', str(root / 'SYNTHETIC_SCORER_NO_PRIVATE_MODELS'),
                    '--private-root', str(root / 'out')])
        report_files = list((root / 'out').glob('rss-state9-p1-*.json'))
        self.assertEqual(len(report_files), 1)
        report = json.loads(report_files[0].read_text(encoding='utf-8'))
        self.assertEqual(report['counts']['p1FeatureRows'], 6)
        self.assertEqual(report['p1Session']['firstEntryCandidates'], 1)
        self.assertFalse(report['privateModelsExecuted'])
        self.assertFalse(report['orderTransmission'])
        self.assertIn('ORDER_TRANSMISSION=False', output.getvalue())


if __name__ == '__main__':
    unittest.main()
