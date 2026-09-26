"""Synthetic runtime boundary tests; no estimator fits or candidate results."""
import ast
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from scripts.phase57_exit_core_runtime_r35 import CoreEncoder, SIGNALS, exit_intent, tri_state
from scripts.phase57_exit_hold_targets_r35 import hold_targets


def fixture():
    def state(t):
        return dict(asOf=t, inputCutoff=t, maxSourceBarEnd=t,
                    maxSourceBarStart=t-1, lastPriceTime=t,
                    state='DROP', dataQuality='OK', confidence='HIGH', reasonCodes=['B','A'])
    h = {str(w):dict(stateChanges=0,stateKnown=1,stateKnownAdjacentPairs=0,
                     signals={s:dict(true=0,false=0,unknown=1) for s in SIGNALS}) for w in (3,5,10)}
    h.update(bullishStateDisappeared=dict.fromkeys(SIGNALS),stateRunObservedSamplesCapped10=1)
    pos = dict(clockMinutesHeld=1, activeMinutesHeld=1, observedOwnedBars=1, missingOwnedBars=0,
               fullOwnedPrefix=True,freshClosedPrice=True,lastObservedClose=100.0,lastObservedClosedAt=571,
               currentReturnPct=0.0, observedRunningHigh=101.0,observedRunningLow=99.0,
               observedMfePct=1.0,observedMaePct=-1.0,completePrefixMfePct=1.0,
               completePrefixMaePct=-1.0,observedPeakGivebackPp=1.0,peakConfirmedAt=571,
               activeMinutesSincePeakConfirmation=0)
    return dict(availabilitySemantics='HISTORICAL_BAR_END_PROXY_NOT_PROVIDER_PUBLICATION_TIME',
                entry=dict(entryId='SYNTH|S1|570',session='2025-05-30',entryMinute=570,
                           symbol='S1',price=100.,opportunity='SYNTH|S1'),
                entryPolicy='IMMEDIATE',entryState=state(570),entryToCurrentState=['DROP','DROP'],
                history=h,inputMaxBarEnd=571,inputMaxKnownAt=571,now=571,position=pos,
                recognition=dict(state=state(571),signals={s:dict(state=None) for s in SIGNALS}),
                schemaVersion='phase57-exit-checkpoint-r20',stateDwellObservedActiveMinutes=1)


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=Path(os.environ['R33_FIT_CONTRACT'])
        cls.encoder=CoreEncoder(cls.path)

    def test_exact_feature_width_and_metadata_isolation(self):
        out=self.encoder.encode(fixture())
        self.assertEqual(len(out['categorical']),21)
        self.assertEqual(len(out['numeric']),83)
        self.assertEqual(set(out),{'identity','session','fresh','categorical','numeric'})
        self.assertNotIn('entryId',self.encoder.categorical_names)

    def test_contract_hash_required(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'changed.json');p.write_bytes(self.path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'CONTRACT_HASH'):
                CoreEncoder(p)

    def test_tristate_distinct(self):
        self.assertEqual([tri_state(v) for v in (True,False,None)],['TRUE','FALSE','UNKNOWN'])
        for v in (0,1,'FALSE','UNKNOWN'):
            with self.assertRaises(ValueError):tri_state(v)

    def test_unknown_and_false_produce_different_categories(self):
        a=fixture();b=copy.deepcopy(a);b['recognition']['signals']['BREAKOUT']['state']=False
        self.assertNotEqual(self.encoder.encode(a)['categorical'],self.encoder.encode(b)['categorical'])

    def test_state_transition_pair_is_one_categorical_level(self):
        r=fixture();out=self.encoder.encode(r)
        idx=self.encoder.categorical_names.index('entryToCurrentState')
        self.assertEqual(out['categorical'][idx],'["DROP","DROP"]')
        r['entryToCurrentState']=None
        self.assertEqual(self.encoder.encode(r)['categorical'][idx],'UNKNOWN')

    def test_reason_codes_sort_without_refit(self):
        a=fixture();b=copy.deepcopy(a);b['entryState']['reasonCodes'].reverse()
        self.assertEqual(self.encoder.encode(a),self.encoder.encode(b))

    def test_unknown_history_not_failure(self):
        r=fixture();out=self.encoder.encode(r)
        i=self.encoder.categorical_names.index('signal.BREAKOUT.observedTrueToFalseTriState')
        self.assertEqual(out['categorical'][i],'UNKNOWN')

    def test_future_source_and_now_rejected(self):
        for key in ('inputMaxKnownAt','inputMaxBarEnd'):
            r=fixture();r[key]=572
            with self.assertRaisesRegex(ValueError,'FUTURE_'):self.encoder.encode(r)
        for now in (571.0,True,691,750,930):
            r=fixture();r['now']=now
            with self.assertRaises(ValueError):self.encoder.encode(r)

    def test_state_cannot_be_backdated_or_use_unclosed_bar(self):
        r=fixture();r['recognition']['state']['asOf']=572
        with self.assertRaisesRegex(ValueError,'ASOF_DRIFT'):self.encoder.encode(r)
        r=fixture();r['recognition']['state']['maxSourceBarStart']=571
        with self.assertRaisesRegex(ValueError,'UNCLOSED_BAR'):self.encoder.encode(r)

    def test_incomplete_path_preserves_observed_only(self):
        r=fixture();p=r['position'];p.update(fullOwnedPrefix=False,missingOwnedBars=1,
                                          completePrefixMfePct=None,completePrefixMaePct=None)
        out=self.encoder.encode(r)
        self.assertIsNone(out['numeric'][self.encoder.numeric_names.index('position.completePrefixMfePct')])
        self.assertEqual(out['numeric'][self.encoder.numeric_names.index('position.observedRunningHigh')],101.)
        p['completePrefixMfePct']=1.
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_PATH'):self.encoder.encode(r)

    def test_no_stale_current_return(self):
        r=fixture();r['position']['freshClosedPrice']=False
        with self.assertRaisesRegex(ValueError,'STALE_PRICE'):self.encoder.encode(r)
        r['position'].update(currentReturnPct=None,lastObservedClosedAt=570)
        self.assertFalse(self.encoder.encode(r)['fresh'])

    def test_future_peak_rejected(self):
        r=fixture();r['position']['peakConfirmedAt']=572
        with self.assertRaisesRegex(ValueError,'FUTURE_'):self.encoder.encode(r)

    def test_evaluator_root_rejected(self):
        for key in ('bucket','finalPnl','targetsPp','futureHigh'):
            r=fixture();r[key]=999
            with self.assertRaisesRegex(ValueError,'ROOT_ALLOWLIST'):self.encoder.encode(r)

    def test_unselected_context_never_enters_features(self):
        a=fixture();b=copy.deepcopy(a);b['recognition']['signalContext']={'unused':99999}
        self.assertEqual(self.encoder.encode(a),self.encoder.encode(b))

    def test_core_has_no_target_or_evaluator_import(self):
        import scripts.phase57_exit_core_runtime_r35 as module
        tree=ast.parse(Path(module.__file__).read_text())
        imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any('target' in n or 'evaluator' in n or 'capture' in n for n in imports))


class ActionTests(unittest.TestCase):
    def test_maximum_horizon_not_average(self):
        self.assertEqual(exit_intent([-1.,-1.,0.5],True,0,0.,1)['action'],'HOLD_NO_ACTION')

    def test_threshold_inclusive_and_persistence(self):
        a=exit_intent([0.10,0.,-1.],True,0,0.10,2)
        self.assertEqual(a['action'],'HOLD_NO_ACTION')
        b=exit_intent([0.10,0.,-1.],True,a['consecutive'],0.10,2)
        self.assertEqual(b['action'],'EXIT_INTENT')

    def test_missing_or_stale_does_not_advance(self):
        for predicted,fresh in (([None,0.,0.],True),([float('nan'),0.,0.],True),([-1.,-1.,-1.],False)):
            out=exit_intent(predicted,fresh,1,0.,2)
            self.assertEqual(out['action'],'HOLD_NO_ACTION');self.assertEqual(out['consecutive'],1)

    def test_fresh_false_condition_resets(self):
        self.assertEqual(exit_intent([0.,1.,0.],True,1,0.,2)['consecutive'],0)

    def test_no_unregistered_policy_mapping(self):
        for threshold,persistence in ((0.5,1),(0.,3),(True,1)):
            with self.assertRaises(ValueError):exit_intent([-1.,-1.,-1.],True,0,threshold,persistence)


class LabelTests(unittest.TestCase):
    starts=tuple(range(540,690))+tuple(range(750,925))
    @staticmethod
    def bar(t,p):return [t,p,p,p,p,1,1]

    def test_three_exact_labels(self):
        r=hold_targets(571,self.starts,[self.bar(t,p) for t,p in ((571,100),(576,101),(586,102),(930,103))])
        self.assertAlmostEqual(r['targetsPp']['HOLD5'],1.)
        self.assertAlmostEqual(r['targetsPp']['HOLD15'],2.)
        self.assertAlmostEqual(r['targetsPp']['HOLD_TERMINAL'],3.)
        self.assertTrue(r['labelSideOnly'])

    def test_lunch_uses_scheduled_not_observed_clock(self):
        r=hold_targets(690,self.starts,[self.bar(750,100),self.bar(755,102),self.bar(765,103)])
        self.assertEqual(r['referenceMinutes']['exitNow'],750)
        self.assertEqual(r['referenceMinutes']['HOLD5'],755)

    def test_no_forward_search_for_missing_base(self):
        r=hold_targets(571,self.starts,[self.bar(572,100),self.bar(576,101),self.bar(930,103)])
        self.assertTrue(all(v is None for v in r['targetsPp'].values()))

    def test_per_head_missing_not_complete_case(self):
        r=hold_targets(571,self.starts,[self.bar(571,100),self.bar(577,101),self.bar(586,102),self.bar(930,103)])
        self.assertIsNone(r['targetsPp']['HOLD5'])
        self.assertIsNotNone(r['targetsPp']['HOLD15'])
        self.assertIsNotNone(r['targetsPp']['HOLD_TERMINAL'])

    def test_terminal_missing_no_previous_close_substitute(self):
        r=hold_targets(924,self.starts,[self.bar(924,100),self.bar(925,101)])
        self.assertIsNone(r['targetsPp']['HOLD_TERMINAL'])

    def test_no_horizon_crosses_next_day(self):
        r=hold_targets(925,self.starts,[self.bar(930,105)])
        self.assertTrue(all(v is None for v in r['targetsPp'].values()))
        self.assertIsNone(r['referenceMinutes']['exitNow'])

    def test_duplicate_and_invalid_auction_rejected(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):
            hold_targets(571,self.starts,[self.bar(571,100),self.bar(571,101)])
        bad=self.bar(930,100);bad[2]=101
        with self.assertRaisesRegex(ValueError,'AUCTION'):
            hold_targets(571,self.starts,[bad])


if __name__=='__main__':unittest.main()
