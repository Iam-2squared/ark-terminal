"""Boundary probes of the requested lifecycle; no market fits or policy search."""
import unittest
from lifecycle import Lifecycle
from replay import fill_from_source

def row(m,context,primary='RISE',segment='w:S0001',observed=True,events=(),path_events=(),activity='LIVE'):
    t=m-540
    s={'as_of':t,'observed_at':t if observed else None,'current_semantics_observed':observed,'numeric_status':'ACCEPTED' if observed else 'NOT_AVAILABLE','primary':primary,'context':context,'activity':activity,'context_established_at':t,'events':list(events),'protected_before':'2','protected_after_effective_next':'2','protected_effective_from':t+1,'close_u':'1','balance':{'established_at':t} if primary=='RANGE' else None}
    p={'Primary_or_null':primary if observed else None,'causal_segment_id':segment,'run_id':f'{segment}:{primary}','dwell_observed_bars':1}
    return {'bar_end_minute':m,'state':s,'path':p,'path_events':[{'event_type':x} for x in path_events],'slot':{'bar_end':str(m)}}

class LifecycleBoundaries(unittest.TestCase):
    def test_pre_ignores_down_range_loss_and_time(self):
        life=Lifecycle(600)
        for i,p in enumerate(['DROP','SHARP_DROP','REBOUND','RANGE']):
            self.assertIsNone(life.observe(row(600+i,-1 if p!='RANGE' else 0,p)))
        self.assertIsNone(life.observe(row(750,None,None,observed=False)))
        self.assertIsNone(life.first_arm_minute)

    def test_arm_first_up_without_rejecting_entry(self):
        life=Lifecycle(600);life.observe(row(600,-1,'DROP'));life.observe(row(601,1))
        self.assertEqual(life.first_arm_minute,601);self.assertFalse(life.arm_at_entry)

    def test_pullback_stop_and_tighten_hold(self):
        life=Lifecycle(600);life.observe(row(600,1))
        self.assertIsNone(life.observe(row(601,1,'PULLBACK')))
        self.assertIsNone(life.observe(row(602,1,'RISE_STOP',activity='STOPPED')))
        self.assertIsNone(life.observe(row(603,1,events=['PROTECTED_LEVEL_TIGHTENED_EFFECTIVE_NEXT_BAR'])))
        self.assertEqual(len(life.tighten_events),1)

    def test_adjacent_reversal_and_lock(self):
        life=Lifecycle(600);life.observe(row(600,1))
        trigger=life.observe(row(601,-1,'DROP',events=['STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL'],path_events=['CONTEXT_CHANGE']))
        self.assertEqual(trigger['reason'],'UP_STRUCTURE_REVERSED')
        with self.assertRaises(RuntimeError):life.observe(row(602,1))

    def test_range_retirement(self):
        life=Lifecycle(600);life.observe(row(600,1))
        trigger=life.observe(row(601,0,'RANGE',events=['CONTEXT_RETIRED_BY_OBSERVED_BALANCE'],path_events=['RANGE_ENTER','CONTEXT_CHANGE'],activity='BALANCED'))
        self.assertEqual(trigger['reason'],'UP_STRUCTURE_RETIRED_BY_RANGE')

    def test_null_then_down_not_synthetic_reversal(self):
        life=Lifecycle(600);life.observe(row(600,1));life.observe(row(601,None,None,observed=False))
        self.assertIsNone(life.observe(row(602,-1,'DROP',segment='w:S0002')))
        self.assertEqual(life.phase,'PRE_UP_STRUCTURE');self.assertEqual(len(life.suspensions),1)

    def test_segment_and_ordinal_gap_cannot_sell(self):
        for m,seg in [(601,'w:S0002'),(605,'w:S0001')]:
            life=Lifecycle(600);life.observe(row(600,1))
            self.assertIsNone(life.observe(row(m,-1,'DROP',segment=seg)))

    def test_rearm_does_not_overwrite_first_arm(self):
        life=Lifecycle(600);life.observe(row(600,1));life.observe(row(601,None,None,observed=False));life.observe(row(602,1,segment='w:S0002'))
        self.assertEqual(life.first_arm_minute,600);self.assertEqual(len(life.arm_events),2)

    def test_lunch_next_regular_open_and_sell_adjustment(self):
        e={'session':'2025-01-06','fill_minute':685}
        bars=[[680,100,101,99,100,10,1000],[690,99,99,99,99,10,990],[750,98,99,97,98,10,980],[751,97,98,96,97,10,970],[930,96,96,96,96,10,960]]
        f=fill_from_source(e,{'minute':690,'reason':'UP_STRUCTURE_REVERSED'},bars)
        self.assertEqual(f['sell_minute'],751);self.assertAlmostEqual(f['sell_price'],97*.9995)

    def test_session_close_exact_print_and_missing_unresolved(self):
        e={'session':'2025-01-06','fill_minute':800};a=[924,100,101,99,100,1,100]
        self.assertEqual(fill_from_source(e,None,[a])['sell_status'],'UNRESOLVED')
        f=fill_from_source(e,None,[a,[930,90,90,90,90,1,90]])
        self.assertEqual(f['sell_source'],'PLANNED_TERMINAL_AUCTION_CLOSE');self.assertAlmostEqual(f['sell_price'],90*.9995)

if __name__=='__main__':unittest.main()
