"""CCMG frozen checkpoint contract: 30 focused causal and execution checks."""
import copy
import unittest

from scripts import phase57_ccmg_guard as guard
from scripts import phase57_exit_checkpoints_v1 as cp


DAY = '2025-08-01'
ENTRY = {'opportunity': f'{DAY}|1234', 'session': DAY, 'symbol': '1234',
         'entryId': f'{DAY}|1234|540', 'entryMinute': 540,
         'effectiveEntryPrice': 100.0}


def bar(minute, close, *, high=None, opened=None):
    opened = close if opened is None else opened
    return [minute, opened, max(opened, close, high if high is not None else close),
            min(opened, close), close, 100, 10000]


def state_at(start_index=0, highest=0, streak=0):
    s = guard.State.create({'opportunity':ENTRY['opportunity'],'session':DAY,
        'symbol':'1234','entryId':ENTRY['entryId'],'entryMinute':540,'price':100.0})
    s.index, s.highest, s.breach_streak = start_index, highest, streak
    return s


def step(s, close=None, *, now=None, prefix=(), high=None, control=925):
    now = s.grid[s.index] if now is None else now
    if close is not None:
        prefix += cp.closed_prefix(DAY, now, (bar(now-1, close, high=high),))
    return s.checkpoint(now, prefix, control_now=control), prefix


def path(close1=101, close2=99, close3=99, fill=98.5):
    result={540:bar(540, close1),541:bar(541, close2),542:bar(542, close3)}
    if fill is not None:result[543]=bar(543, 99, opened=fill)
    return result


def control(now=545, price=98, exit_minute=546):
    return {'decisionNow':now,'exitPrice':price,'exitMinute':exit_minute}


class CheckpointGuardTests(unittest.TestCase):
    def test_01_grid_parity(self):
        self.assertEqual(state_at().grid, cp.checkpoint_grid(DAY,540))

    def test_02_future_bar_rejected(self):
        s=state_at()
        future=cp.closed_prefix(DAY,541,(bar(541,110),))
        self.assertEqual(future,())
        r,_=step(s,prefix=future)
        self.assertIsNone(r['highestCertifiedMilestone'])
        with self.assertRaisesRegex(ValueError,'FUTURE_IN_DECISION'):
            s2=state_at()
            s2.checkpoint(541,(cp.KnownBar(540,101,101,101,101,1,1,542),),control_now=925)

    def test_03_stale_close_not_current(self):
        s=state_at();_,p=step(s,101)
        r,_=step(s,prefix=p)
        self.assertFalse(r['freshClosedPrice']);self.assertIsNone(r['currentReturnPct'])

    def test_04_plus_one(self):
        r,_=step(state_at(),101)
        self.assertEqual((r['highestCertifiedMilestone'],r['floorPct']),(1,0))

    def test_05_plus_two(self):
        r,_=step(state_at(),102)
        self.assertEqual((r['highestCertifiedMilestone'],r['floorPct']),(2,1))

    def test_06_plus_three(self):
        r,_=step(state_at(),103)
        self.assertEqual((r['highestCertifiedMilestone'],r['floorPct']),(3,2))

    def test_07_plus_five(self):
        r,_=step(state_at(),105)
        self.assertEqual((r['highestCertifiedMilestone'],r['floorPct']),(5,3))

    def test_08_plus_ten(self):
        r,_=step(state_at(),110)
        self.assertEqual((r['highestCertifiedMilestone'],r['floorPct']),(10,5))

    def test_09_multi_step_close(self):
        r,_=step(state_at(),111)
        self.assertEqual(r['highestCertifiedMilestone'],10)

    def test_10_milestone_monotone(self):
        s=state_at();_,p=step(s,110);r,_=step(s,99,prefix=p)
        self.assertEqual(r['highestCertifiedMilestone'],10)

    def test_11_floors(self):
        self.assertEqual(guard.FLOOR,{1:0,2:1,3:2,5:3,10:5})

    def test_12_promotion_resets_old_alert(self):
        s=state_at(highest=1,streak=1)
        r,_=step(s,102)
        self.assertEqual((r['event'],r['breachStreak'],r['state']),('PROMOTION',0,'ACTIVE'))

    def test_13_first_breach(self):
        r,_=step(state_at(highest=1),99)
        self.assertEqual((r['state'],r['breachStreak']),('ALERT_1',1))

    def test_14_recovery(self):
        s=state_at(highest=1,streak=1)
        r,_=step(s,100)
        self.assertEqual((r['event'],r['state'],r['breachStreak']),('RECOVERY','ACTIVE',0))

    def test_15_second_adjacent_fresh(self):
        s=state_at(highest=1);_,p=step(s,99);r,_=step(s,99,prefix=p)
        self.assertEqual((r['event'],r['candidateIntent']),('BREACH_2',True))

    def test_16_gap_resets_streak(self):
        s=state_at(highest=1);_,p=step(s,99);r,p=step(s,prefix=p)
        self.assertEqual((r['event'],r['breachStreak']),('DATA_GAP_RESET',0))
        r,_=step(s,99,prefix=p)
        self.assertEqual(r['state'],'ALERT_1')

    def test_17_lunch_adjacent_on_grid(self):
        s=state_at(state_at().grid.index(690),highest=1)
        r,p=step(s,99)
        self.assertEqual(r['now'],690)
        r,_=step(s,99,prefix=p)
        self.assertEqual((r['now'],r['event']),(751,'BREACH_2'))

    def test_18_new_milestone_while_alert(self):
        s=state_at(highest=1,streak=1);r,_=step(s,105)
        self.assertEqual((r['highestCertifiedMilestone'],r['breachStreak']),(5,0))

    def test_19_preprofit_delegates_control(self):
        r=guard.run_entry(ENTRY,control(541,99,542),{540:bar(540,99)})
        self.assertEqual(r['terminalReason'],'CONTROL_FIRST')

    def test_20_potential_ignored(self):
        extra=dict(ENTRY,potentialProbability=0.0,holdVeto=True)
        self.assertEqual(guard.run_entry(extra,control(),path()),guard.run_entry(ENTRY,control(),path()))

    def test_21_old_model_ignored(self):
        extra=dict(ENTRY,D=100,WPSDDamage=100,R54Sell=True)
        self.assertEqual(guard.run_entry(extra,control(),path()),guard.run_entry(ENTRY,control(),path()))

    def test_22_control_earlier(self):
        r=guard.run_entry(ENTRY,control(542,99,543),path())
        self.assertEqual((r['terminalReason'],r['decisionNow']),('CONTROL_FIRST',542))

    def test_23_candidate_earlier(self):
        r=guard.run_entry(ENTRY,control(),path())
        self.assertEqual((r['terminalReason'],r['decisionNow']),('CANDIDATE_FIRST',543))

    def test_24_simultaneous_reason(self):
        r=guard.run_entry(ENTRY,control(543,98,544),path())
        self.assertEqual(r['terminalReason'],'BOTH_TRIGGER_SAME_CHECKPOINT')

    def test_25_confirmed_next_open(self):
        r=guard.run_entry(ENTRY,control(),path())
        self.assertEqual((r['fillStatus'],r['exitMinute'],r['exitPrice']),
                         ('RESOLVED_NEXT_SCHEDULED_OPEN',543,98.5))

    def test_26_missing_next_open_null(self):
        r=guard.run_entry(ENTRY,control(),path(fill=None))
        self.assertIsNone(r['exitPrice']);self.assertEqual(r['fillNullReason'],'MISSING_EXECUTION_REFERENCE')

    def test_27_control_ceiling(self):
        r=guard.run_entry(ENTRY,control(542,99,543),path())
        self.assertTrue(all(t['now']<=r['controlCeilingNow'] for t in r['checkpointTrace']))

    def test_28_deterministic_trace(self):
        self.assertEqual(guard.run_entry(ENTRY,control(),path()),guard.run_entry(copy.deepcopy(ENTRY),control(),copy.deepcopy(path())))

    def test_29_gross_vs_net(self):
        r=guard.run_entry(ENTRY,control(),path())
        self.assertAlmostEqual(r['checkpointTrace'][0]['currentReturnPct'],1.)
        self.assertEqual(str(guard.corrected_pnl_jpy({'quantity':100,'notionalJpy':10005},r['exitPrice'])),
                         '-159.92500')

    def test_30_safety(self):
        self.assertEqual(len(guard.SAFETY),9)
        self.assertTrue(all(value is False for value in guard.SAFETY.values()))


if __name__ == '__main__':unittest.main()
