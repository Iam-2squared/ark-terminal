"""Boundary tests on synthetic supplied trace rows, without running State9/Path engines."""
import unittest
from local_guard import GuardedLifecycle, EXIT_C

def pivot(kind,x,t):return {'kind':kind,'x':str(x),'extremum_t':t,'confirmed_at':t,'generation_reason':'DC_CONFIRMED'}

def row(t,close='3.5',context=1,primary='RISE',segment='s1',observed=True,piv=None,events=(),path_events=(),protected='0'):
    minute=540+t
    return {'bar_end_minute':minute,'slot':{'bar_end':f'2025-06-01T{minute//60:02}:{minute%60:02}:00+09:00'},'state':{'as_of':t,'observed_at':t if observed else None,'current_semantics_observed':observed,'numeric_status':'ACCEPTED' if observed else 'NOT_AVAILABLE','context':context,'context_established_at':0,'primary':primary,'activity':'BALANCED' if primary=='RANGE' else 'RUNNING','close_u':str(close),'protected_before':protected,'protected_after_effective_next':protected,'protected_effective_from':0,'local_pivot_confirmed':piv,'events':list(events),'balance':{'established_at':t} if primary=='RANGE' else None,'_structure_pivots':[],'_context_extreme':str(close),'stop':{'count':999},'leg_direction':1},'path':{'Primary_or_null':primary if observed else None,'causal_segment_id':segment,'run_id':primary+'-run','dwell_observed_bars':999},'path_events':[{'event_type':e} for e in path_events]}

def seeded():
    life=GuardedLifecycle(543,900)
    for t,p in enumerate([pivot('L',0,0),pivot('H',3,1),pivot('L',1,2)]):life.prefix(row(t,piv=p))
    return life

class GuardBoundaries(unittest.TestCase):
    def test_previous_confirmations_create_next_bar_guard(self):
        life=seeded();intent,r=life.observe(row(3))
        self.assertIsNone(intent);self.assertIsNone(r['local_guard_before'])
        self.assertEqual(r['local_guard_after_effective_next']['effective_from'],4)
        self.assertEqual(r['local_guard_after_effective_next']['x'],'1')

    def test_equality_break_while_main_still_UP(self):
        life=seeded();life.observe(row(3));intent,r=life.observe(row(4,close='.5',primary='PULLBACK'))
        self.assertEqual(intent['reason'],EXIT_C);self.assertEqual(intent['context'],1)
        with self.assertRaises(RuntimeError):life.observe(row(5))

    def test_main_A_precedence(self):
        life=seeded();life.observe(row(3))
        intent,_=life.observe(row(4,close='-.5',context=-1,primary='DROP',events=['STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL'],path_events=['CONTEXT_CHANGE']))
        self.assertEqual(intent['reason'],'UP_STRUCTURE_REVERSED')

    def test_main_B_precedence(self):
        life=seeded();life.observe(row(3))
        intent,_=life.observe(row(4,context=0,primary='RANGE',events=['CONTEXT_RETIRED_BY_OBSERVED_BALANCE'],path_events=['RANGE_ENTER','CONTEXT_CHANGE']))
        self.assertEqual(intent['reason'],'UP_STRUCTURE_RETIRED_BY_RANGE')

    def test_current_confirmation_not_eligible_same_bar(self):
        life=GuardedLifecycle(542,900)
        life.prefix(row(0,piv=pivot('L',0,0)));life.prefix(row(1,piv=pivot('H',3,1)))
        _,r=life.observe(row(2,piv=pivot('L',1,2)))
        self.assertIsNone(r['local_guard_after_effective_next'])
        _,r=life.observe(row(3));self.assertEqual(r['local_guard_after_effective_next']['effective_from'],4)

    def test_gap_resets_guard_and_rearms(self):
        life=seeded();life.observe(row(3));intent,r=life.observe(row(5,close='.5'))
        self.assertIsNone(intent);self.assertIsNone(r['local_guard_before']);self.assertIsNone(life.guard.level)
        self.assertEqual(len(life.base.arm_events),2)

    def test_new_segment_DOWN_not_synthetic_A(self):
        life=seeded();life.observe(row(3));intent,_=life.observe(row(4,close='-10',context=-1,primary='DROP',segment='s2'))
        self.assertIsNone(intent);self.assertEqual(life.base.phase,'PRE_UP_STRUCTURE');self.assertIsNone(life.guard.level)

    def test_observation_lost_resets_guard(self):
        life=seeded();life.observe(row(3));intent,_=life.observe(row(4,observed=False))
        self.assertIsNone(intent);self.assertTrue(life.base.suspended);self.assertIsNone(life.guard.level)

    def test_PRE_and_primary_dwell_stop_alone_no_SELL(self):
        life=GuardedLifecycle(540,900)
        for t,primary in enumerate(['DROP','RANGE','REBOUND']):
            intent,_=life.observe(row(t,context=-1 if primary!='RANGE' else 0,primary=primary,close='-999'))
            self.assertIsNone(intent)
        for t,primary in enumerate(['PULLBACK','RISE_STOP'],3):
            intent,_=life.observe(row(t,primary=primary));self.assertIsNone(intent)

    def test_guard_must_exceed_main_level(self):
        life=seeded();life.observe(row(3));intent,_=life.observe(row(4,close='.5',protected='1'))
        self.assertIsNone(intent)

    def test_guard_never_lowers(self):
        life=seeded();life.observe(row(3));life.guard.level={**life.guard.level,'x':'2'}
        _,r=life.observe(row(4,close='3.5'));self.assertEqual(life.guard.level['x'],'2')

    def test_C_does_not_relabel_planned_close_deadline(self):
        life=seeded();life.deadline=544;life.observe(row(3));intent,_=life.observe(row(4,close='.5'))
        self.assertIsNone(intent)

if __name__=='__main__':unittest.main()
