"""Meaningful boundary tests on supplied rows, no State9/Path engine execution."""
import unittest
from recovery_floor import RecoveryLifecycle,EXIT_D
from test_local_guard import row,pivot

def armed():
    life=RecoveryLifecycle(540,900)
    life.observe(row(0,close='4',piv=pivot('L',2,0)))
    return life

class RecoveryBoundaries(unittest.TestCase):
    def test_current_confirmed_L_creates_next_bar_floor(self):
        life=armed();self.assertEqual(life.floor.level['x'],'2');self.assertEqual(life.floor.level['effective_from'],1)

    def test_equal_buffer_break_with_main_UP(self):
        life=armed();intent,meta=life.observe(row(1,close='1.5',primary='PULLBACK'))
        self.assertEqual(intent['reason'],EXIT_D);self.assertEqual(intent['context'],1)
        self.assertEqual(meta['recovery_floor_before']['x'],'2')

    def test_above_buffer_holds(self):
        life=armed();intent,_=life.observe(row(1,close='1.5000000000000000000001'))
        self.assertIsNone(intent)

    def test_no_same_bar_floor_break(self):
        life=RecoveryLifecycle(540,900);intent,meta=life.observe(row(0,close='1',piv=pivot('L',2,0)))
        self.assertIsNone(intent);self.assertIsNone(meta['recovery_floor_before'])

    def test_H_is_not_floor(self):
        life=RecoveryLifecycle(540,900);life.observe(row(0,piv=pivot('H',3,0)))
        self.assertIsNone(life.floor.level)

    def test_non_DC_L_is_not_floor(self):
        life=RecoveryLifecycle(540,900);p=pivot('L',2,0);p['generation_reason']='SEGMENT_SEED'
        life.observe(row(0,piv=p));self.assertIsNone(life.floor.level)

    def test_at_main_protection_is_not_floor(self):
        life=RecoveryLifecycle(540,900);life.observe(row(0,piv=pivot('L',0,0)))
        self.assertIsNone(life.floor.level)

    def test_floor_monotonic_and_tighten_effective_next(self):
        life=armed();life.observe(row(1,close='4',piv=pivot('L',1,1)))
        self.assertEqual(life.floor.level['x'],'2')
        _,m=life.observe(row(2,close='5',piv=pivot('L',3,2)))
        self.assertEqual(m['recovery_floor_before']['x'],'2');self.assertEqual(life.floor.level['x'],'3');self.assertEqual(life.floor.level['effective_from'],3)

    def test_A_precedes_D(self):
        life=armed();intent,_=life.observe(row(1,close='-.5',context=-1,primary='DROP',events=['STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL'],path_events=['CONTEXT_CHANGE']))
        self.assertEqual(intent['reason'],'UP_STRUCTURE_REVERSED')

    def test_B_precedes_D(self):
        life=armed();intent,_=life.observe(row(1,close='1',context=0,primary='RANGE',events=['CONTEXT_RETIRED_BY_OBSERVED_BALANCE'],path_events=['RANGE_ENTER','CONTEXT_CHANGE']))
        self.assertEqual(intent['reason'],'UP_STRUCTURE_RETIRED_BY_RANGE')

    def test_C_precedes_D(self):
        life=armed();life.guard.level={'x':'2','segment':'s1','effective_from':1,'updated_at':0,'created_at':0}
        intent,_=life.observe(row(1,close='1.5'))
        self.assertEqual(intent['reason'],'LOCAL_UP_STRUCTURE_GUARD_BROKEN')

    def test_gap_clears_then_new_confirmation_rearms_floor(self):
        life=armed();intent,m=life.observe(row(2,close='1'))
        self.assertIsNone(intent);self.assertIsNone(m['recovery_floor_before']);self.assertIsNone(life.floor.level)
        life.observe(row(3,close='4',piv=pivot('L',2,3)));self.assertEqual(life.floor.level['effective_from'],4)

    def test_segment_change_DOWN_has_no_synthetic_break(self):
        life=armed();intent,_=life.observe(row(1,close='-100',context=-1,primary='DROP',segment='s2'))
        self.assertIsNone(intent);self.assertIsNone(life.floor.level);self.assertEqual(life.base.phase,'PRE_UP_STRUCTURE')

    def test_unobserved_clears_floor(self):
        life=armed();intent,_=life.observe(row(1,observed=False))
        self.assertIsNone(intent);self.assertIsNone(life.floor.level);self.assertTrue(life.base.suspended)

    def test_PRE_cannot_establish_floor_or_sell(self):
        life=RecoveryLifecycle(540,900)
        for t,p in enumerate(['DROP','RANGE','REBOUND']):
            intent,_=life.observe(row(t,context=-1,primary=p,piv=pivot('L',2,t),close='-100'))
            self.assertIsNone(intent);self.assertIsNone(life.floor.level)

    def test_Pullback_Stop_DOWN_dwell_alone_no_sell(self):
        life=RecoveryLifecycle(540,900)
        for t,p in enumerate(['PULLBACK','RISE_STOP','PULLBACK']):
            r=row(t,primary=p,close='-100');r['state']['leg_direction']=-1
            intent,_=life.observe(r);self.assertIsNone(intent)

    def test_floor_must_remain_above_main_at_break(self):
        life=armed();intent,_=life.observe(row(1,close='1.5',protected='2'))
        self.assertIsNone(intent)

    def test_planned_close_clock_not_relabelled_D(self):
        life=armed();life.deadline=541;life.fallback.deadline=541
        intent,_=life.observe(row(1,close='1.5'));self.assertIsNone(intent)

    def test_post_exit_decisions_prohibited(self):
        life=armed();life.observe(row(1,close='1.5'))
        with self.assertRaises(RuntimeError):life.observe(row(2))

if __name__=='__main__':unittest.main()
