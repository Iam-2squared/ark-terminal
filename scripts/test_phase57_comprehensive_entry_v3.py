import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import phase57_comprehensive_entry_v3 as v


def fixture(closes=(-2,-4,-4,-2,-1,0,1,2,3,4,5,6), start=540):
    session='2024-09-17'; stamp=lambda t:v.c.stamp(session,t)
    op={'anchorId':'a','eventType':v.q.INITIAL,'opportunityTimestamp':stamp(start),
        'referenceTimestamp':stamp(start),'referencePrice':100.,'referenceStatus':'REFERENCE_OPEN'}
    x={'id':'a|'+v.q.INITIAL,'op':op,'session':session,'symbol':'TEST','breadth':1}
    bars=[]; prev=0.
    for i,close in enumerate(closes):
        bars.append({'start':stamp(start+5*i),'end':stamp(start+5*(i+1)),
            'o':prev,'h':max(prev,close)+.4,'l':min(prev,close)-.4,'c':float(close),'observedMinutes':5,'missing':False})
        prev=float(close)
    path={'decisionTimestamp':stamp(start),'decisionPrice':100.,'sessionDate':session,
        'sessionEndMinute':900,'future':bars}
    return x,path,{'newEligibleRank':1,'savedV1Score':.1}


class EventTests(unittest.TestCase):
    def states(self,fixture_args=()):
        x,p,s=fixture(*fixture_args);return x,p,s,v.reconstruct(x,p,s,{})

    def test_protocol_upstream_and_split_identity(self):
        p,ops,paths,selectors,legacy=v.sources()
        self.assertEqual(len(ops),1760)
        self.assertEqual(len({x['session'] for x in ops}),38)
        self.assertTrue(all(x['session'] in p['split']['TRAIN'] for x in ops))
        self.assertEqual(len({x['id'] for x in ops}),1760)
        self.assertEqual(set(x['op']['eventType'] for x in ops),{v.q.INITIAL,v.q.DIP})
        self.assertEqual(p['budget']['supervisedFits'],0)
        self.assertEqual(len(p['safety']),9)
        self.assertTrue(all(x is False for x in p['safety'].values()))

    def test_sealed_partitions_rejected(self):
        for partition in ('VALIDATION','DEVELOPMENT_TEST','OOS'):
            with self.assertRaisesRegex(RuntimeError,'SEALED_PARTITION'):v.sources(partition)

    def test_state_grid_and_completed_semantics(self):
        _,_,_,states=self.states()
        self.assertEqual([s['delay'] for s in states],list(range(0,31,5)))
        for s in states:
            self.assertEqual(len(s['bars']),s['delay']//5)
            self.assertTrue(all(b['end']<=s['timestamp'] for b in s['bars']))

    def test_future_mutation_cannot_change_known_states(self):
        x,p,s,states=self.states();changed=copy.deepcopy(p)
        for b in changed['future'][3:]:b.update(o=111,h=999,l=-99,c=200)
        self.assertEqual(states[:4],v.reconstruct(x,changed,s,{})[:4])

    def test_no_evaluator_in_state_or_event(self):
        x,p,s=fixture()
        with patch.object(v.v2,'evaluate',side_effect=AssertionError('NO_LABELS')),patch.object(v.m,'path_class',side_effect=AssertionError('NO_CLASSES')):
            self.assertIn('S1_P_S_R',v.detect(v.reconstruct(x,p,s,{})))

    def test_pullback_not_oracle_bottom(self):
        _,_,_,states=self.states();events=v.detect(states)
        self.assertEqual(events['E1_PULLBACK']['delay'],5)
        self.assertEqual(events['S1_P_S_R']['delay'],20)
        self.assertEqual(events['S1_P_S_R']['sequenceDelays'],[5,15,20])

    def test_momentum_turn_sequence(self):
        _,_,_,states=self.states()
        self.assertEqual(v.detect(states)['S3_P_S_M']['sequenceDelays'],[5,15,20])

    def test_failed_breakdown_sequence(self):
        x,p,s=fixture();p['future'][2]['l']=-5
        z=v.detect(v.reconstruct(x,p,s,{}))
        self.assertEqual(z['E5_FAILED_BREAKDOWN']['delay'],15)
        self.assertEqual(z['S2_P_F_R']['sequenceDelays'],[5,15,20])

    def test_continuation_requires_two_changes(self):
        x,p,s=fixture((1,2,3,4,5,6,7,8,9,10,11,12));z=v.detect(v.reconstruct(x,p,s,{}))
        self.assertEqual(z['E6_CONTINUATION']['delay'],15)
        self.assertNotIn('E1_PULLBACK',z)

    def test_sequence_never_two_stages_same_bar(self):
        _,_,_,states=self.states()
        for event in v.detect(states).values():
            self.assertEqual(event['sequenceDelays'],sorted(set(event['sequenceDelays'])))

    def test_signal_to_next_open_not_low(self):
        x,p,s,states=self.states();ev=v.detect(states)['S1_P_S_R'];d=v.decision(x,p,states,ev)
        self.assertAlmostEqual(d['executionPrice'],98.)
        self.assertEqual(d['delay'],20)
        self.assertNotEqual(d['executionPrice'],95.6)

    def test_execution_signal_high_low_close_do_not_choose_fill(self):
        x,p,s,states=self.states();event=v.detect(states)['E1_PULLBACK'];d=v.decision(x,p,states,event)
        for k in ('h','l','c'):p['future'][1][k]=None
        self.assertEqual(d,v.decision(x,p,states,event))

    def test_missing_open_unknown_no_later_substitution(self):
        x,p,s,states=self.states();event=v.detect(states)['E1_PULLBACK'];p['future'][1]['o']=None
        d=v.decision(x,p,states,event);self.assertEqual(d['status'],'UNKNOWN_EXECUTION');self.assertIsNone(d['delay'])

    def test_missing_prefix_terminal_no_resurrection(self):
        x,p,s=fixture();p['future'][1]['missing']=True;states=v.reconstruct(x,p,s,{})
        self.assertEqual([z['status'] for z in states[2:]],['UNKNOWN_PREFIX']*5)
        self.assertNotIn('S1_P_S_R',v.detect(states))

    def test_gap_in_prefix_fails_closed(self):
        x,p,s=fixture();p['future'].pop(0)
        states=v.reconstruct(x,p,s,{})
        self.assertEqual(states[1]['status'],'UNKNOWN_PREFIX')

    def test_unknown_reference_all_states_terminal(self):
        x,p,s=fixture();x['op']['referenceStatus']='UNKNOWN_REFERENCE_OPEN'
        states=v.reconstruct(x,p,s,{})
        self.assertEqual(set(z['status'] for z in states),{'UNKNOWN_REFERENCE'})
        self.assertEqual(v.detect(states),{})

    def test_segment_boundary_does_not_cross_lunch(self):
        x,p,s=fixture(start=680);states=v.reconstruct(x,p,s,{})
        self.assertEqual(states[2]['status'],'EXPIRED_BOUNDARY')
        self.assertNotIn('S1_P_S_R',v.detect(states))

    def test_no_event_is_not_skip(self):
        x,p,s=fixture((0,)*12);states=v.reconstruct(x,p,s,{})
        d=v.decision(x,p,states,None)
        self.assertEqual(d['status'],'NO_EVENT')
        self.assertNotIn('SKIP',str(d))

    def test_intrabar_order_remains_unknown(self):
        _,_,_,states=self.states()
        self.assertEqual({z['intrabarOrder'] for z in states},{'UNKNOWN_INTRABAR_ORDER'})
        x,p,s=fixture((3,)*12);p['future'][0]['l']=-2
        self.assertEqual(v.m.path_class(x,p),'INCONCLUSIVE')

    def test_initial_dip_independent_identity(self):
        x,p,s=fixture();x2=copy.deepcopy(x);x2['op']['eventType']=v.q.DIP;x2['id']='a|'+v.q.DIP
        a=v.reconstruct(x,p,s,{});b=v.reconstruct(x2,p,s,{})
        self.assertEqual(v.detect(a),v.detect(b))
        self.assertNotEqual(a[0]['features']['isDip'],b[0]['features']['isDip'])

    def test_deterministic_sequence(self):
        x,p,s=fixture();a=v.reconstruct(x,p,s,{})
        self.assertEqual(a,v.reconstruct(x,p,s,{}));self.assertEqual(v.detect(a),v.detect(copy.deepcopy(a)))

    def test_state_schema_has_no_outcome(self):
        _,_,_,states=self.states()
        self.assertNotIn('mfe',str(states).lower());self.assertNotIn('mae',str(states).lower())
        self.assertNotIn('pathClass',str(states));self.assertNotIn('candidateA',str(states))

    def test_first_event_only(self):
        x,p,s,states=self.states();a=v.detect(states)['E1_PULLBACK']
        self.assertEqual(a['delay'],5)
        self.assertEqual(v.detect(states[:2])['E1_PULLBACK'],a)

    def test_output_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):v.run(d)

    def test_zero_denominators_never_pass(self):
        p=v.protocol();z=v.basic_mechanic([],p['mechanicKeepGate'])
        self.assertFalse(any(z['gates'].values()))

    def test_better_entry_risk_separate_from_nonentry(self):
        x,p,s,states=self.states();r=v.outcome_row(x,p,v.decision(x,p,states,None))
        z=v.cohort_metrics([r])
        for risk in z['riskDecomposition'].values():
            self.assertEqual(risk['RISK_REDUCTION_BY_BETTER_ENTRY'],0)
            self.assertEqual(risk['baselineAll'],risk['RISK_NOT_ENTERED_NOT_AN_ADOPTED_SKIP_POLICY'])


if __name__=='__main__':unittest.main()
