"""R45 synthetic boundaries and corruption tests; no Development model fitting."""
import ast
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from scripts import phase57_exit_gen3_runtime_r45 as r
from scripts.phase57_exit_gen3_facts_r45 import FactMemo,past_five,calendar
from scripts.phase57_exit_gen3_labels_r45 import utility_labels,reference_minutes,HEADS
from scripts import phase57_exit_gen3_runner_r45 as runner
from scripts import phase57_exit_gen3_scoring_r45 as scoring

DAY='2025-05-30'
P=r.load_protocol()
CANDIDATES=P['candidates']


def facts(now=571,**changes):
    values={k:None for k in P['features']['decisionFactFields']}
    values.update(currentReturnPct=0.,barsHeld=20,timeSincePeak=10,weakRun=0,
        signalTrueN=0,signalFalseN=0,signalUnknownN=6,signalLossN=0,signalRecoveryN=0,
        stateRecovery=0,failedRecovery=0,momentum5Pct=0.,range5Pct=1.,volume5=100,
        higherHigh=0,higherLow=0,lowerHigh=0,lowerLow=0,newPeak=0)
    values.update(changes)
    return dict(now=now,maxKnownAt=now,maxBarEnd=now,fresh=True,values=values)


def call(scores=(.2,.2,.2),snapshot=None,memory=None,candidate=0):
    return r.intent(list(scores),snapshot or facts(),memory or r.Memory(),CANDIDATES[candidate])


def series(scores,changes,candidate=0,times=(571,572)):
    mem=r.Memory();out=[]
    for now in times:
        a=call(scores,facts(now,**changes),mem,candidate);out.append(a);mem=r.Memory(**a['state'])
    return out


def bar(t,p=100.,volume=100):return [t,p,p,p,p,volume,volume*p]


def row(now=571,state='DROP',signals=None,fresh=True,**numeric):
    cats=dict.fromkeys(P['features']['categorical'],'UNKNOWN');cats['currentState.state']=state
    for sig in r.SIGNALS:cats[f'signal.{sig}.currentTriState']=(signals or {}).get(sig,'UNKNOWN')
    nums=dict.fromkeys(P['features']['baseNumeric'])
    defaults=dict(activeMinutesHeld=now-570,fullOwnedPrefix=1,freshClosedPrice=int(fresh),lastObservedClosedAt=now,
                  currentReturnPct=0. if fresh else None,completePrefixMfePct=1. if fresh else None,
                  completePrefixMaePct=0. if fresh else None,observedPeakGivebackPp=1.,peakConfirmedAt=570,
                  activeMinutesSincePeakConfirmation=now-570)
    defaults.update(numeric)
    for k,v in defaults.items():nums['position.'+k]=v
    return dict(session=DAY,identity=['IMMEDIATE','x|s|570',now],fresh=fresh,
                categorical=[cats[k] for k in P['features']['categorical']],numeric=[nums[k] for k in P['features']['baseNumeric']])


def prices(now=571):return past_five(DAY,now,[bar(t) for t in range(now-5,now)])


class RuntimeTests(unittest.TestCase):
    def test_frozen_budget_hash(self):
        self.assertEqual(hashlib.sha256(r.PROTOCOL_PATH.read_bytes()).hexdigest(),r.PROTOCOL_SHA256)
        self.assertEqual(len(CANDIDATES),4);self.assertEqual(P['execution']['expectedModelFitCount'],24)
    def test_all_three_scores_required(self):
        for s in ([.2,.7],[None,.7,.8],[True,.7,.8],[float('nan'),.7,.8],[1.01,.7,.8]):
            self.assertEqual(call(s)['action'],'HOLD')
    def test_terminal_even_stale_and_invalid_scores(self):
        f=facts(925);f['fresh']=False;f['values']['currentReturnPct']=None
        self.assertEqual(call([None,None,None],f)['action'],'FORCE_TERMINAL')
    def test_d_wins_over_c_high(self):
        for c in range(4):
            a=series((.99,.99,.9),dict(weakRun=3,momentum5Pct=-1.,signalFalseN=2),c)
            self.assertEqual(a[0]['action'],'HOLD');self.assertEqual(a[1]['authority'],'DETERIORATION');self.assertEqual(a[1]['action'],'EXIT_INTENT')
    def test_p_independent_of_c_high(self):
        a=series((.99,.9,.2),dict(certifiedMfePct=3.,certifiedGivebackPp=1.,weakRun=2))
        self.assertEqual(a[1]['authority'],'PROTECTION');self.assertEqual(a[1]['action'],'EXIT_INTENT')
    def test_d_priority_when_both_eligible(self):
        a=series((.99,.9,.9),dict(certifiedMfePct=3.,certifiedGivebackPp=1.,weakRun=3,momentum5Pct=-1.,signalFalseN=2))
        self.assertEqual(a[-1]['authority'],'DETERIORATION')
    def test_drop_and_loss_alone_never_sell(self):
        for c in range(4):
            for v in (dict(weakRun=10),dict(currentReturnPct=-90),dict(weakRun=10,currentReturnPct=-90)):
                for a in series((.2,.9,.9),v,c,range(571,580)):self.assertEqual(a['action'],'HOLD')
    def test_single_signal_loss_alone_never_sell(self):
        for a in series((.2,.9,.9),dict(signalLossN=1),times=range(571,580)):self.assertEqual(a['action'],'HOLD')
    def test_d_missing_momentum_or_signal_evidence(self):
        for v in (dict(weakRun=3,momentum5Pct=None,signalFalseN=6),dict(weakRun=3,momentum5Pct=-3,signalFalseN=0)):
            self.assertEqual(series((.2,.2,.9),v)[-1]['action'],'HOLD')
    def test_structure_vs_failed_recovery_distinction(self):
        v=dict(weakRun=2,momentum5Pct=-1.,signalFalseN=2)
        self.assertEqual(series((.2,.2,.9),v,0)[-1]['action'],'EXIT_INTENT')
        self.assertEqual(series((.2,.2,.9),v,2)[-1]['action'],'HOLD')
    def test_failed_recovery_alternative(self):
        self.assertEqual(series((.9,.2,.9),dict(failedRecovery=1,momentum5Pct=-1.,signalLossN=1),2)[-1]['action'],'EXIT_INTENT')
    def test_hh_ll_structure_alternative(self):
        self.assertEqual(series((.9,.2,.9),dict(lowerHigh=1,lowerLow=1,momentum5Pct=-1.,signalLossN=1),0)[-1]['action'],'EXIT_INTENT')
    def test_neutral_requires_three_then_two(self):
        a=series((.2,.2,.2),dict(barsHeld=20,currentReturnPct=-1,weakRun=3,momentum5Pct=-.1,signalFalseN=2),times=(571,572,573,574))
        self.assertEqual([x['action'] for x in a],['HOLD','HOLD','HOLD','EXIT_INTENT']);self.assertEqual(a[-1]['authority'],'NEUTRAL_DETERIORATION')
    def test_neutral_does_not_override_without_full_evidence(self):
        a=series((.2,.2,.2),dict(barsHeld=20,currentReturnPct=-10),times=range(571,580))
        self.assertTrue(all(x['action']=='HOLD' for x in a))
    def test_sticky_armed_not_certificate(self):
        a=call((.9,.9,.2),facts(certifiedMfePct=2.,certifiedGivebackPp=1.,weakRun=2))
        b=call((.9,.9,.2),facts(572,weakRun=2),r.Memory(**a['state']))
        self.assertTrue(b['state']['armed']);self.assertEqual(b['state']['pCount'],0)
    def test_p_peak_age_and_giveback_threshold_inclusive(self):
        self.assertEqual(series((.2,.6,.2),dict(certifiedMfePct=1.,certifiedGivebackPp=.75,timeSincePeak=5,weakRun=2))[-1]['action'],'EXIT_INTENT')
        self.assertEqual(series((.2,.6,.2),dict(certifiedMfePct=1.,certifiedGivebackPp=.749,timeSincePeak=5,weakRun=2))[-1]['action'],'HOLD')
    def test_probation_current_and_next_fresh_only(self):
        mem=r.Memory();out=[]
        for now in (571,572,573,574):
            f=facts(now,certifiedMfePct=2.,certifiedGivebackPp=1.,weakRun=2,signalTrueN=1,momentum5Pct=.1,signalRecoveryN=int(now==571))
            a=call((.9,.9,.2),f,mem,1);mem=r.Memory(**a['state']);out.append(a)
        self.assertEqual([a['state']['pCount'] for a in out],[0,0,1,2])
        self.assertEqual(out[-1]['action'],'EXIT_INTENT')
    def test_persistent_true_is_not_new_probation(self):
        v=dict(certifiedMfePct=2.,certifiedGivebackPp=1.,weakRun=2,signalTrueN=1,momentum5Pct=.1)
        self.assertEqual(series((.9,.9,.2),v,1)[-1]['action'],'EXIT_INTENT')
    def test_d_overrides_existing_probation(self):
        f=facts(572,weakRun=3,momentum5Pct=-1.,signalFalseN=2)
        m=r.Memory(lastNow=571,armed=True,dCount=1,probationRemaining=2)
        self.assertEqual(call((.9,.9,.9),f,m,1)['authority'],'DETERIORATION')
    def test_new_certified_peak_clears_p_count(self):
        f=facts(572,certifiedMfePct=3.,certifiedGivebackPp=1.,weakRun=2,newPeak=1)
        m=r.Memory(lastNow=571,armed=True,pCount=1,probationRemaining=2)
        a=call((.9,.9,.2),f,m,1);self.assertEqual(a['state']['pCount'],0);self.assertEqual(a['state']['probationRemaining'],0)
    def test_stale_resets_counts_not_armed_or_probation(self):
        f=facts(572);f['fresh']=False;f['values']['currentReturnPct']=None
        a=call((.2,.9,.9),f,r.Memory(lastNow=571,armed=True,dCount=1,pCount=1,neutralCount=2,probationRemaining=1))
        self.assertEqual([a['state'][k] for k in ('dCount','pCount','neutralCount')],[0,0,0]);self.assertTrue(a['state']['armed']);self.assertEqual(a['state']['probationRemaining'],1)
    def test_gap_resets_probation_and_counts(self):
        a=call((.2,.2,.9),facts(573,weakRun=3,momentum5Pct=-1.,signalFalseN=2),r.Memory(lastNow=571,dCount=1,probationRemaining=1))
        self.assertEqual(a['state']['dCount'],1);self.assertEqual(a['state']['probationRemaining'],0)
    def test_lunch_is_adjacent(self):self.assertTrue(r.adjacent(690,751))
    def test_false_evidence_resets(self):
        a=call((.2,.2,.9),facts(572),r.Memory(lastNow=571,dCount=1));self.assertEqual(a['state']['dCount'],0)
    def test_no_foreign_candidate(self):
        c={**CANDIDATES[0],'threshold':.1}
        with self.assertRaises(ValueError):r.intent([.2,.2,.2],facts(),r.Memory(),c)
    def test_no_future_envelope(self):
        for k in ('maxKnownAt','maxBarEnd'):
            f=facts();f[k]=572
            with self.assertRaises(ValueError):call(snapshot=f)
    def test_no_extra_outcome_inputs(self):
        for k in ('labelAvailability','futureHigh','bucket','finalPnL','targets'):
            f=facts();f['values'][k]=1
            with self.assertRaises(ValueError):call(snapshot=f)
    def test_invalid_time_and_replayed_now(self):
        for now in (571.,True,750,930):
            with self.assertRaises(ValueError):call(snapshot=facts(now))
        with self.assertRaises(ValueError):call(snapshot=facts(),memory=r.Memory(lastNow=571))
    def test_no_target_or_model_import_in_runtime(self):
        source=Path(r.__file__).read_text();tree=ast.parse(source)
        imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any(any(k in name for k in ('label','_data_','runner','numpy','sklearn','evaluat','scoring')) for name in imports))


class LabelTests(unittest.TestCase):
    def label(self,values,now=571,mfe=2,fresh=True,entry=100):
        anchor,samples,_,_=reference_minutes(DAY,now)
        index={t:bar(t,v) for t,v in zip([anchor]+samples,values)}
        return utility_labels(DAY,now,entry,fresh,mfe,index)
    def test_persistent_positive(self):self.assertEqual(self.label([100,101,100.2,100.5])['targets'],dict(zip(HEADS,(1,0,0))))
    def test_persistent_negative(self):self.assertEqual(self.label([100,99,100.2,99.5])['targets'],dict(zip(HEADS,(0,1,1))))
    def test_single_positive_touch_not_continuation(self):self.assertEqual(self.label([100,99,99,101])['targets']['CONTINUATION'],0)
    def test_single_negative_touch_not_deterioration(self):self.assertEqual(self.label([100,101,101,99])['targets']['DETERIORATION'],0)
    def test_protection_not_eligible_is_null_not_zero(self):
        a=self.label([100,99,99,99],mfe=None);self.assertIsNone(a['targets']['PROTECTION']);self.assertEqual(a['reasonCode']['PROTECTION'],'PROTECTION_NOT_ELIGIBLE')
    def test_mfe_eligibility_inclusive(self):self.assertIsNotNone(self.label([100,99,99,99],mfe=1)['targets']['PROTECTION'])
    def test_entry_denominator_not_anchor(self):
        a=self.label([200,199,199,199],entry=100);self.assertEqual(a['futureUtility'],[-1,-1,-1])
    def test_references_lunch(self):self.assertEqual(reference_minutes(DAY,690),(750,[755,760,765],15,None))
    def test_last_three_uses_auction(self):
        a=self.label([100,101,102,103],now=922);self.assertEqual(a['sampleReferenceMinutes'],[923,924,930]);self.assertEqual(a['knownAt']['CONTINUATION'],930)
    def test_minimum_remaining(self):
        for now in (923,924,925):self.assertTrue(all(x is None for x in utility_labels(DAY,now,100,True,2,{})['targets'].values()))
    def test_missing_no_forward_search(self):
        ix={t:bar(t) for t in (571,576,581,587)}
        a=utility_labels(DAY,571,100,True,2,ix);self.assertTrue(all(x is None for x in a['targets'].values()))
    def test_nonpositive_required_ref_censors(self):self.assertTrue(all(x is None for x in self.label([100,0,99,99])['targets'].values()))
    def test_stale_no_targets(self):self.assertTrue(all(x is None for x in self.label([100,99,99,99],fresh=False)['targets'].values()))
    def test_invalid_auction(self):
        ix={t:bar(t) for t in (922,923,924,930)};ix[930][2]=101
        a=utility_labels(DAY,922,100,True,2,ix);self.assertEqual(set(a['reasonCode'].values()),{'INVALID_AUCTION'})
    def test_unsampled_gaps_are_allowed_not_complete_path_claim(self):
        a=self.label([100,101,102,103]);self.assertEqual(a['targets']['CONTINUATION'],1)
    def test_c_d_mutually_exclusive_property(self):
        rng=np.random.default_rng(4)
        for vals in rng.uniform(98,102,(200,4)):
            a=self.label(vals.tolist());self.assertFalse(a['targets']['CONTINUATION'] and a['targets']['DETERIORATION'])
    def test_offsets_unique_future_for_all_epochs(self):
        for now in r.ENDPOINTS:
            a,s,h,reason=reference_minutes(DAY,now)
            if not reason:self.assertEqual(len(set(s)),3);self.assertTrue(min(s)>now);self.assertLessEqual(max(s),930)


class FactTests(unittest.TestCase):
    def test_exact_fact_width(self):self.assertEqual(len(FactMemo().update(DAY,row(),prices())['values']),21)
    def test_drop_count_capped(self):
        m=FactMemo()
        for now in range(571,585):out=m.update(DAY,row(now),prices(now))
        self.assertEqual(out['values']['weakRun'],10)
    def test_pullback_not_weak_under_frozen_contract(self):self.assertEqual(FactMemo().update(DAY,row(state='PULLBACK'),prices())['values']['weakRun'],0)
    def test_actual_state_recovery(self):
        m=FactMemo();m.update(DAY,row(),prices());o=m.update(DAY,row(572,state='REBOUND'),prices(572));self.assertEqual(o['values']['stateRecovery'],1)
    def test_failed_recovery_sequences(self):
        for states in [('DROP','REBOUND','DROP'),('RISE','DROP','DROP')]:
            m=FactMemo()
            for n,s in zip((571,572,573),states):out=m.update(DAY,row(n,state=s),prices(n))
            self.assertEqual(out['values']['failedRecovery'],1)
    def test_unknown_never_inferred_recovery(self):
        m=FactMemo()
        for n,s in zip((571,572,573),('DROP','UNKNOWN','REBOUND')):out=m.update(DAY,row(n,state=s),prices(n))
        self.assertEqual(out['values']['stateRecovery'],0)
    def test_signal_unknown_not_loss(self):
        m=FactMemo()
        for n,s in zip((571,572,573),('TRUE','UNKNOWN','FALSE')):
            o=m.update(DAY,row(n,signals={'BREAKOUT':s}),prices(n));self.assertEqual(o['values']['signalLossN'],0)
    def test_actual_signal_change_only(self):
        m=FactMemo();m.update(DAY,row(signals={'BREAKOUT':'FALSE'}),prices());o=m.update(DAY,row(572,signals={'BREAKOUT':'TRUE'}),prices(572));self.assertEqual(o['values']['signalRecoveryN'],1)
        o=m.update(DAY,row(573,signals={'BREAKOUT':'TRUE'}),prices(573));self.assertEqual(o['values']['signalRecoveryN'],0)
    def test_gap_resets_state_and_signals(self):
        m=FactMemo();m.update(DAY,row(signals={'BREAKOUT':'TRUE'}),prices())
        o=m.update(DAY,row(573,state='REBOUND',signals={'BREAKOUT':'FALSE'}),prices(573));self.assertEqual(o['values']['signalLossN'],0);self.assertEqual(o['values']['stateRecovery'],0)
    def test_stale_resets_histories(self):
        m=FactMemo();m.update(DAY,row(),prices());m.update(DAY,row(572,fresh=False),prices(572));o=m.update(DAY,row(573,state='REBOUND'),prices(573));self.assertEqual(o['values']['stateRecovery'],0)
    def test_uncertified_giveback_null(self):
        o=FactMemo().update(DAY,row(fullOwnedPrefix=0,completePrefixMfePct=None,completePrefixMaePct=None),prices())
        self.assertIsNone(o['values']['certifiedGivebackPp']);self.assertIsNone(o['values']['certifiedMfePct'])
    def test_future_peak_rejected(self):
        with self.assertRaises(ValueError):FactMemo().update(DAY,row(peakConfirmedAt=580),prices())
    def test_entry_local_history(self):
        m=FactMemo();m.update(DAY,row(),prices());z=row(572);z['identity'][1]='different'
        with self.assertRaises(ValueError):m.update(DAY,z,prices(572))
    def test_strict_new_peak_not_equal_tie(self):
        m=FactMemo();m.update(DAY,row(),prices());o=m.update(DAY,row(572,completePrefixMfePct=1.),prices(572));self.assertEqual(o['values']['newPeak'],0)
        o=m.update(DAY,row(573,completePrefixMfePct=2.),prices(573));self.assertEqual(o['values']['newPeak'],1)
    def test_unclosed_bar_forbidden(self):
        with self.assertRaises(ValueError):past_five(DAY,571,[bar(571)])
    def test_gap_no_forward_fill(self):
        o=past_five(DAY,571,[bar(i) for i in (566,568,569,570)])
        self.assertIsNone(o['momentum5Pct']);self.assertIsNone(o['volume5']);self.assertEqual(o['higherHigh'],0)
    def test_volume_independent_of_invalid_price(self):
        b=[bar(i) for i in range(566,571)];b[0][2]=None;o=past_five(DAY,571,b)
        self.assertEqual(o['volume5'],500);self.assertIsNone(o['momentum5Pct'])
    def test_five_bar_momentum_and_structure(self):
        o=past_five(DAY,571,[bar(i,100+j) for j,i in enumerate(range(566,571))]);self.assertAlmostEqual(o['momentum5Pct'],4);self.assertEqual(o['higherHigh'],1)
    def test_lunch_uses_scheduled_completed_bars(self):
        o=past_five(DAY,751,[bar(i) for i in (686,687,688,689,750)]);self.assertEqual(o['volume5'],500)
    def test_calendar_not_observation_availability(self):self.assertEqual(calendar(DAY,922),[3,3])


class SupportAndSelectionTests(unittest.TestCase):
    def synthetic(self):
        days=sorted(set(s for f in P['split']['folds'] for k in ('train','score','purge') for s in f[k]))
        ids=[(i,a,k) for i in range(len(days)) for a in range(2) for k in range(20)]
        return SimpleNamespace(session_names=days,sessions=np.array([v[0] for v in ids]),arms=np.array([v[1] for v in ids]),entries=np.arange(len(ids)),entry_ids=list(range(len(ids))),now=np.full(len(ids),600),fresh=np.ones(len(ids),dtype=bool),targets=np.array([[v[2]%2]*3 for v in ids],dtype=float))
    def test_all_24_support_slices(self):self.assertEqual(len(runner.support_slices(self.synthetic(),P)[0]),24)
    def test_single_class_fails_before_any_fit(self):
        d=self.synthetic();d.targets[:,1]=0
        with self.assertRaisesRegex(ValueError,'CLASS_SUPPORT'):runner.support_slices(d,P)
    def test_stale_target_never_trains(self):
        d=self.synthetic();d.fresh[::3]=False
        slices,_=runner.support_slices(d,P)
        for _,_,_,train,_ in slices:self.assertTrue(np.all(d.fresh[train]))
    def test_support_cache_cannot_fit(self):
        with tempfile.TemporaryDirectory() as t, self.assertRaisesRegex(ValueError,'SUPPORT_ONLY_CACHE'):
            runner.fit_predictions(self.synthetic(),Path(t),P)
    def gate_rows(self,passed=False):
        return [{'candidateId':c['candidateId'],'gate':{'pass':passed,'capabilityMargins':dict(winner=1.,retention=1.,loss=1.)}} for c in CANDIDATES]
    def test_no_selection_all_fail(self):self.assertEqual(scoring.select_from_gates(self.gate_rows())['outcome'],'NO_SELECTION_STOP')
    def test_no_missing_candidate(self):
        with self.assertRaises(ValueError):scoring.select_from_gates(self.gate_rows()[:-1])
    def test_no_tie_pick(self):self.assertEqual(scoring.select_from_gates(self.gate_rows(True))['outcome'],'NO_SELECTION_STOP')
    def test_one_pass_select(self):
        rows=self.gate_rows();rows[2]['gate']['pass']=True;self.assertEqual(scoring.select_from_gates(rows)['selectedCandidateId'],CANDIDATES[2]['candidateId'])
    def test_no_c_f_label_import_runtime(self):
        for module in (r,):
            tree=ast.parse(Path(module.__file__).read_text());mods=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
            self.assertFalse(any('label' in m or 'scoring' in m for m in mods))
    def test_float32_peak_native_conversion(self):
        data=SimpleNamespace(numeric_names=['position.observedRunningHigh'],numeric=np.array([[101.]],dtype=np.float32));self.assertIs(type(runner.position(data,0)['observedRunningHigh']),float)


class ReplayTests(unittest.TestCase):
    def synthetic(self):
        day=P['split']['folds'][0]['score'][0];oid=day+'|S';eid=oid+'|570';key='IMMEDIATE::'+eid
        times=(571,572,573,574,925)
        v=[facts(t,weakRun=3,momentum5Pct=-1.,signalFalseN=2)['values'] for t in times]
        fv=np.array([[np.nan if x[k] is None else x[k] for k in P['features']['decisionFactFields']] for x in v],dtype=float)
        nums=np.array([[101.,float(t),1.] for t in times],dtype=np.float32)
        entry=dict(entryId=eid,opportunity=oid,session=day,entryMinute=570,price=100.,symbol='S',entryArm='IMMEDIATE')
        return SimpleNamespace(session_names=[day],sessions=np.zeros(5,dtype=int),arms=np.zeros(5,dtype=int),entries=np.zeros(5,dtype=int),entry_ids=[key],entry_rows={key:entry},
            now=np.array(times),fresh=np.ones(5,dtype=bool),fact_values=fv,numeric=nums,numeric_names=['position.observedRunningHigh','position.peakConfirmedAt','position.fullOwnedPrefix'],
            raw={oid:{'today':[bar(t) for t in (570,571,573,574,930)]}},opportunity_records={oid:{}})
    def replay(self,d,scores):
        with patch.object(runner.r36,'_ordered_geometry',return_value=None),patch.object(runner.r36,'_post_entry_high',return_value=None):
            return runner.replay_candidate(d,scores,CANDIDATES[0],P)
    def test_missing_open_intent_cancel_not_forward_fill(self):
        d=self.synthetic();scores=np.tile([.2,.2,.9],(5,1));scores[2]=[.9,.2,.2]
        out=self.replay(d,scores)[0]
        self.assertEqual(out['missingOrdinaryReferences'],1);self.assertEqual(out['exitMinute'],930)
        self.assertEqual(out['exitKind'],'FORCED_TERMINAL')
    def test_missing_open_reevaluate_and_exit_when_evidence_remains(self):
        d=self.synthetic();out=self.replay(d,np.tile([.2,.2,.9],(5,1)))[0]
        self.assertEqual(out['missingOrdinaryReferences'],1);self.assertEqual(out['exitMinute'],573)
    def test_missing_terminal_stays_unresolved(self):
        d=self.synthetic();oid=next(iter(d.raw));d.raw[oid]['today']=[bar(570)]
        out=self.replay(d,np.tile([.9,.2,.2],(5,1)))[0]
        self.assertEqual(out['exitStatus'],'UNRESOLVED_TERMINAL_EXIT');self.assertIsNone(out['exitPrice'])
    def test_execution_high_cannot_change_intent(self):
        a=self.synthetic();b=copy.deepcopy(a);oid=next(iter(b.raw));b.raw[oid]['today'][2][2]=999
        scores=np.tile([.2,.2,.9],(5,1));x=self.replay(a,scores)[0];y=self.replay(b,scores)[0]
        self.assertEqual(x['decisionNow'],y['decisionNow']);self.assertEqual(x['exitPrice'],y['exitPrice'])
    def test_sell_cost_once_and_native_owned_peak(self):
        d=self.synthetic();o=self.replay(d,np.tile([.2,.2,.9],(5,1)))[0]
        self.assertAlmostEqual(o['netReturnPctBySellCost']['0.05'],-.05)
        self.assertIsNotNone(o['metrics']['ownedPeakGivebackPp'])

class LaunchTests(unittest.TestCase):
    def fixture(self):
        from scripts import phase57_exit_gen3_preflight_r45 as f
        execution='1'*40;trigger='2'*40;research='3'*40;branch='research/phase57-gen3-r45-launch-test'
        current=dict(status='GEN3_PREFLIGHT_CONTRACT_PASS_NOT_PERFORMANCE_PASS',executionSha=execution,runId='10',sourceSha256={'source':'hash'},protocolSha256=f.PROTOCOL_SHA256,candidateCount=4,expectedModelFitCount=24)
        prior={**current,'support':{'status':'GEN3_SUPPORT_AND_INDEPENDENT_LABELS_PASS','independentLabelCheck':{'rowsChecked':656247,'mismatches':0}}}
        marker=dict(schemaVersion='phase57-gen3-launch-r45-v1',authorizedByUser=True,executionSha=execution,researchHead=research,triggerBranch=branch,contractRunId=10,protocolSha256=f.PROTOCOL_SHA256,candidateCount=4,expectedModelFitCount=24)
        def get(path):
            if path=='/git/ref/heads/'+branch:return {'object':{'sha':trigger}}
            if path=='/git/ref/heads/'+f.RESEARCH:return {'object':{'sha':research}}
            if path=='/actions/runs/10':return dict(head_sha=execution,path=f.CONTRACT_WORKFLOW,status='completed',conclusion='success')
            if path=='/actions/runs/20':return dict(head_sha=trigger,path=f.FINITE_WORKFLOW,workflow_id=42)
            if path.startswith('/compare/'):
                return dict(status='ahead',behind_by=0,files=[{'filename':f.LAUNCH_PATH}] if path.endswith(trigger) else [{'filename':f.CLOSURE_PATH}])
            if path=='/actions/artifacts/'+str(f.R35_ID):return dict(workflow_run={'id':f.R35_RUN},expired=False,digest='sha256:'+f.R35_HASH)
            if path.startswith('/actions/workflows/'):return {'workflow_runs':[{'id':20}]}
            if path.startswith('/actions/runs?'):return {'workflow_runs':[]}
            raise AssertionError(path)
        env=dict(GITHUB_SHA=trigger,GITHUB_RUN_ID='20',GITHUB_REPOSITORY=f.REPOSITORY,GITHUB_REF='refs/heads/'+branch,GITHUB_RUN_ATTEMPT='1')
        return f,current,prior,marker,get,env
    def run_check(self,mutator=None):
        import os
        f,current,prior,marker,get,env=self.fixture()
        if mutator:mutator(prior,marker,env)
        with patch.dict(os.environ,env),patch.object(f,'contract_receipt',return_value=current),patch.object(f.subprocess,'check_output',return_value=marker['executionSha']+'\n'):
            return f.validate_launch(Path('.'),marker,prior,get)
    def test_exact_launch_allowed(self):self.assertEqual(self.run_check()['status'],'GEN3_LAUNCH_VERIFIED')
    def test_no_second_attempt(self):
        with self.assertRaises(ValueError):self.run_check(lambda a,b,e:e.update(GITHUB_RUN_ATTEMPT='2'))
    def test_no_unapproved_launch(self):
        with self.assertRaises(ValueError):self.run_check(lambda a,b,e:b.update(authorizedByUser=False))
    def test_mismatched_tested_source(self):
        with self.assertRaises(ValueError):self.run_check(lambda a,b,e:a.update(sourceSha256={'wrong':'hash'}))
    def test_support_required(self):
        with self.assertRaises(ValueError):self.run_check(lambda a,b,e:a.update(support={}))
    def test_different_protocol(self):
        with self.assertRaises(ValueError):self.run_check(lambda a,b,e:b.update(protocolSha256='0'*64))

if __name__ == "__main__":
    unittest.main()
