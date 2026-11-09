"""Read-only strict dual-session RSS log source regression.

Friday historical 4328 and Monday 142 G1/1M capture share one child log; the
original daily-cycle parser treated expected Friday/Monday markers as duplicates.
This suite never writes or fabricates market receipts, never sends orders.
"""
import sys
from pathlib import Path
import types
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import daily_cycle
import no11_circuit_repair
import no11_combined_nightly_parser as fix


def patched_cycle():
    raw=no11_circuit_repair.transform('cycle',(HERE/'daily_cycle.py').read_bytes())
    changed=fix.transform(raw)
    obj=types.ModuleType('test_patched_cycle')
    obj.__file__=str(HERE/'daily_cycle.py')
    exec(compile(changed.decode('utf-8-sig'),str(HERE/'daily_cycle.py'),'exec'),obj.__dict__)
    return obj,changed


def live_like():
    return '''NO11_WEEKLY_NIGHTLY_ASOF=2026-11-09
NO11_WEEKLY_NIGHTLY_NEXT_SESSION=2026-11-10
NO11_WEEKLY_NIGHTLY_MODE=WEEKLY_POOL_CANDIDATES_ONLY
NO11_WEEKLY_RECOVER_MISSING_FRIDAY=REAL_RSS_FULL_4328|ASOF_2026-11-06
NO11_NIGHTLY_HISTORICAL_FRIDAY_OBSERVED_NOW=2026-11-06
NO11_DAILY_TARGET=2026-11-06
NO11_DAILY_PROGRESS=4328/4328|WAVE_OBSERVED=4|WAVE_FULL76=3
NO11_DAILY_TREND_CENSUS=COMPLETE_OBSERVED_STRUCTURE_ONLY
NO11_PREVIOUS_ARCHIVE_STAGE=C:\\private\\previous-source\\2026-11-09\\previous-archive-stage-friday.json
NO11_PREVIOUS_CAPTURE_DIR=C:\\private\\previous-source\\2026-11-09\\rss-friday
NO11_NIGHTLY_DAILY_RUN=C:\\private\\daily-2026-11-06
NO11_NIGHTLY_MASK=C:\\private\\pass-friday.json
NO11_NIGHTLY_CHART50=C:\\private\\chart-friday.json
NO11_WEEKLY_RECOVER_MISSING_FRIDAY=D100_AND_PREVIOUS_DONE|ASOF_2026-11-06
NO11_WEEKLY_NIGHTLY_POOL_SOURCE=C:\\private\\daily-2026-11-06
NO11_DAILY_TARGET=2026-11-09
NO11_DAILY_PROGRESS=142/142|WAVE_OBSERVED=1|WAVE_FULL76=1
NO11_WEEKLY_REFRESH_CAPTURES=142/142
NO11_WEEKLY_REFRESH_PASS=123
NO11_WEEKLY_NIGHTLY_CURRENT_MASK=C:\\private\\pass-monday.json
NO11_WEEKLY_NIGHTLY_CURRENT_CHART50=C:\\private\\chart-monday.json
NO11_PREVIOUS_ARCHIVE_STAGE=C:\\private\\previous-source\\2026-11-10\\previous-archive-stage-monday.json
NO11_PREVIOUS_CAPTURE_DIR=C:\\private\\previous-source\\2026-11-10\\rss-monday
NO11_WEEKLY_NIGHTLY_REFRESH_RUN=C:\\private\\weekly-refresh-2026-11-09
NO11_WEEKLY_NIGHTLY_STAGE=CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE
ORDER_TRANSMISSION=False
'''.encode('utf-8')


class CombinedCaptureParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cycle,cls.transformed=patched_cycle()

    def test_original_installed_parser_fails_on_two_valid_archive_markers(self):
        original=no11_circuit_repair.transform('cycle',(HERE/'daily_cycle.py').read_bytes())
        c=types.ModuleType('installed_old')
        exec(compile(original.decode('utf-8-sig'),'old.py','exec'),c.__dict__)
        with self.assertRaisesRegex(ValueError,'NO11_DAILY_CYCLE_NIGHTLY_LOG_MARKER_NO11_PREVIOUS_ARCHIVE_STAGE_'):
            c.parse_nightly(live_like())

    def test_real_2026_11_06_to_11_09_combined_log_selects_final_monday_only(self):
        data=self.cycle.parse_nightly(live_like())
        self.assertEqual(data['previousSession'],'2026-11-09')
        self.assertEqual(data['sessionDate'],'2026-11-10')
        self.assertEqual(data['historicalFridayRecoveryAsOf'],'2026-11-06')
        self.assertEqual(data['weekly'],r'C:\private\daily-2026-11-06')
        self.assertEqual(data['run'],r'C:\private\weekly-refresh-2026-11-09')
        self.assertEqual(data['chart'],r'C:\private\chart-monday.json')
        self.assertEqual(data['mask'],r'C:\private\pass-monday.json')
        self.assertEqual(data['stage'],r'C:\private\previous-source\2026-11-10\previous-archive-stage-monday.json')
        self.assertEqual(data['capture'],r'C:\private\previous-source\2026-11-10\rss-monday')
        self.assertFalse(data['stage'].endswith('friday.json'))

    def test_partial_or_unproven_friday_recovery_rejected(self):
        base=live_like().decode()
        mutations=[
            ('NO11_WEEKLY_RECOVER_MISSING_FRIDAY=D100_AND_PREVIOUS_DONE|ASOF_2026-11-06',''),
            ('NO11_WEEKLY_RECOVER_MISSING_FRIDAY=REAL_RSS_FULL_4328|ASOF_2026-11-06',''),
            ('NO11_WEEKLY_RECOVER_MISSING_FRIDAY=D100_AND_PREVIOUS_DONE|ASOF_2026-11-06',
             'NO11_WEEKLY_RECOVER_MISSING_FRIDAY=D100_AND_PREVIOUS_DONE|ASOF_2026-10-30'),
            ('NO11_WEEKLY_NIGHTLY_CURRENT_CHART50=C:\\private\\chart-monday.json',''),
            ('NO11_PREVIOUS_ARCHIVE_STAGE=C:\\private\\previous-source\\2026-11-10\\previous-archive-stage-monday.json',''),
            ('NO11_WEEKLY_NIGHTLY_STAGE=CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE',
             'NO11_WEEKLY_NIGHTLY_STAGE=BLOCKED'),
            ('NO11_WEEKLY_NIGHTLY_ASOF=2026-11-09','NO11_WEEKLY_NIGHTLY_ASOF=2026-11-09\nNO11_WEEKLY_NIGHTLY_ASOF=2026-11-09')
        ]
        for old,new in mutations:
            with self.subTest(old=old):
                with self.assertRaises(ValueError):
                    self.cycle.parse_nightly(base.replace(old,new,1).encode())

    def test_unexpected_duplicate_weekday_marker_rejected(self):
        original=live_like()
        edited=original+b'NO11_PREVIOUS_ARCHIVE_STAGE=C:\\private\\new-staged.json\n'
        with self.assertRaisesRegex(ValueError,'NIGHTLY_LOG_MARKER_NO11_PREVIOUS_ARCHIVE_STAGE_'):
            self.cycle.parse_nightly(edited)

    def test_regular_friday_and_weekday_regression(self):
        import test_daily_cycle as oldtest
        test=oldtest.DailyCycleTests()
        for friday in (True,False):
            record=self.cycle.parse_nightly(test.example(friday))
            self.assertEqual(record['sessionDate'],'2026-11-09' if friday else '2026-11-05')
        with self.assertRaisesRegex(ValueError,'NIGHTLY_LOG_MARKER_'):
            self.cycle.parse_nightly(test.example()+b'NO11_WEEKLY_NIGHTLY_NEXT_SESSION=2026-11-06\n')

    def test_transformation_one_byte_scoped_and_idempotent(self):
        old=no11_circuit_repair.transform('cycle',(HERE/'daily_cycle.py').read_bytes())
        new=self.transformed
        self.assertEqual(new,fix.transform(new))
        self.assertIn(fix.MARK.encode(),new)
        a=old.decode('utf-8-sig')
        b=new.decode('utf-8-sig')
        self.assertEqual(a[:a.index('def parse_nightly(raw):')],b[:b.index('def parse_nightly(raw):')])
        self.assertEqual(a[a.index('def verified_sources('):],b[b.index('def verified_sources('):])
        self.assertIn('not stage.get("omittedSymbols")',b)
        self.assertIn('"PREVIOUS_MINUTES_INCOMPLETE"',b)
        self.assertIn('productionReady=False',b)

if __name__=='__main__':
    unittest.main(verbosity=2)
