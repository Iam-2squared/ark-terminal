"""Synthetic DEFINITION tests only. No repository market files are loaded."""
import copy
import hashlib
import inspect
import json
from pathlib import Path
import random
import unittest
from fractions import Fraction as F
import reference as r

ROOT = Path(__file__).parent
DAY, PREV = '2025-06-02', '2025-05-30'
CAL = ['2025-05-26','2025-05-27','2025-05-28','2025-05-29',PREV,DAY]
ENDS = tuple(range(541,691))+tuple(range(751,926))


def bars(prices, start=541, spread=0, activity=100):
    return tuple(r.Bar(start+i,p,F(p)+F(spread),F(p)-F(spread),p,activity,
                       None if activity is None else F(p)*activity,start+i)
                 for i,p in enumerate(prices))


def series(prices, start=541):
    return r.Session(DAY,'SYNTHETIC','RAW-SYNTHETIC',ENDS,bars(prices,start))


def previous(flat=False, missing=False):
    ps = [100] * 30 if flat else [F(100)+F(i%5,4) for i in range(30)]
    bs = bars(ps)
    if missing: bs=bs[:-1]
    return r.Session(PREV,'SYNTHETIC','RAW-SYNTHETIC',ENDS,bs)


def dailies(down=False):
    return [dict(date=d,security='SYNTHETIC',basis='RAW-SYNTHETIC',
                 o=100-i if down else 100+i,h=102-i if down else 102+i,
                 l=98-i if down else 98+i,c=99-i if down else 101+i,volume=1000,value=100000)
            for i,d in enumerate(CAL[:-1])]


class ContractTests(unittest.TestCase):
    def test_version_and_scope(self):
        c=json.loads((ROOT/'contract.json').read_text())
        self.assertEqual(c['version'],r.VERSION)
        self.assertEqual(c['authorized_scope'],'DEFINITION_AND_SYNTHETIC_TESTS_ONLY')
    def test_parameter_lock(self):
        c=json.loads((ROOT/'contract.json').read_text())
        self.assertEqual(c['cycle_active_minutes'],r.CYCLE)
        self.assertEqual(c['reference_scale']['minimum_complete_blocks'],r.MIN_SCALE_BLOCKS)
        self.assertEqual(F(c['swing']['reversal_scale_multiple']),r.SWING_MULTIPLE)
        self.assertEqual(c['range']['complete_minutes'],r.RANGE_MINUTES)
        for key,value in [('max_width_scale',r.RANGE_MAX_WIDTH),('max_efficiency',r.RANGE_MAX_EFFICIENCY),('touch_band_scale',r.TOUCH_BAND)]:
            self.assertEqual(F(c['range'][key]),value)
        self.assertEqual(c['range']['minimum_distinct_blocks_per_side'],r.TOUCH_BLOCKS)
        self.assertEqual(c['attributes']['chop_min_close_direction_changes'],r.CHOP_CHANGES)
        self.assertEqual(F(c['attributes']['chop_max_efficiency']),r.CHOP_MAX_EFFICIENCY)
        self.assertEqual(F(c['attributes']['chop_min_envelope_scale']),r.CHOP_MIN_WIDTH)
        self.assertEqual(F(c['attributes']['expansion_ratio']),r.EXPANSION)
        self.assertEqual(F(c['attributes']['compression_ratio']),r.COMPRESSION)
        self.assertEqual(c['oracle']['future_active_minutes'],r.ORACLE_HORIZON)
    def test_safety(self):
        c=json.loads((ROOT/'contract.json').read_text())
        self.assertEqual(c['safety'],r.SAFETY)
        self.assertEqual(len(r.SAFETY),9)
        self.assertTrue(all(v is False for v in r.SAFETY.values()))
    def test_no_legacy_model_signal_import(self):
        s=(ROOT/'reference.py').read_text()
        import ast
        imports=[]
        for x in ast.walk(ast.parse(s)):
            if isinstance(x,ast.Import): imports += [a.name for a in x.names]
            if isinstance(x,ast.ImportFrom): imports += [x.module]
        self.assertFalse(any(x and ('scripts' in x or 'requests' in x or 'sklearn' in x) for x in imports))
    def test_causal_interface_no_future_argument(self):
        self.assertEqual(list(inspect.signature(r.snapshot).parameters),['prefix','ends','asof','scale'])


class ObservationTests(unittest.TestCase):
    def test_invalid_ohlc(self):
        with self.assertRaisesRegex(ValueError,'INVALID_OHLC'): r.Bar(541,100,99,98,100)
    def test_nan_rejected(self):
        with self.assertRaisesRegex(ValueError,'NONFINITE'): r.q(float('nan'))
    def test_boolean_price_rejected(self):
        with self.assertRaisesRegex(ValueError,'BOOLEAN'): r.q(True)
    def test_negative_volume(self):
        with self.assertRaisesRegex(ValueError,'NEGATIVE_ACTIVITY'): r.Bar(541,100,100,100,100,-1)
    def test_duplicate_rejected(self):
        b=bars([100])[0]
        with self.assertRaisesRegex(ValueError,'DUPLICATE'): r.snapshot([b,b],ENDS,541,F(1))
    def test_future_rejected(self):
        with self.assertRaisesRegex(ValueError,'FUTURE'): r.snapshot(bars([100]*6),ENDS,545,F(1))
    def test_delayed_received_rejected(self):
        b=r.Bar(541,100,100,100,100,available_at=543)
        with self.assertRaisesRegex(ValueError,'NOT_YET'): r.snapshot([b],ENDS,542,F(1))
    def test_explicit_no_knownat_claim(self):
        b=r.Bar(541,100,100,100,100)
        z=r.snapshot([b],ENDS,541,None)
        self.assertEqual(z['availability'],'HISTORICAL_CLOSED_RECONSTRUCTION')
    def test_exact_5(self):
        self.assertEqual(r.window(bars([100]*5),ENDS,545)['status'],'COMPLETE')
    def test_missing_not_retimed(self):
        bs=bars([100]*5)
        z=r.window(bs[:2]+bs[3:],ENDS,545)
        self.assertEqual(z['missingEnds'],[543])
        self.assertEqual(z['expectedEnds'],[541,542,543,544,545])
    def test_current_missing_not_forward_filled(self):
        z=r.snapshot(bars([100]*4),ENDS,545,F(1))
        self.assertIsNone(z['state']['structure'])
        self.assertEqual(z['state']['identificationStatus'],'CURRENT_BAR_UNAVAILABLE')
    def test_initial_no_forced_wait(self):
        self.assertEqual(r.grid(570,ENDS)['checkpoints'][:3],[570,575,580])
        z=r.snapshot(bars([100]*30),ENDS,570,F(1))
        self.assertEqual(z['observation']['status'],'COMPLETE')
    def test_1500_is_valid(self):
        self.assertEqual(r.grid(900,ENDS)['checkpoints'],[900,905,910,915,920,925])
        self.assertEqual(r.snapshot(bars([100]*5,start=896),ENDS,900,F(1))['observation']['status'],'COMPLETE')
    def test_auction_not_five_fake_bars(self):
        self.assertNotIn(930,r.grid(900,ENDS)['checkpoints'])
    def test_lunch_grid(self):
        self.assertEqual(r.grid(688,ENDS)['checkpoints'][1],753)
    def test_lunch_window_segmented(self):
        bs=bars([100]*2,start=689)+bars([101]*3,start=751)
        self.assertIn('SESSION_BOUNDARY',r.window(bs,ENDS,753)['reasons'])
    def test_open_short_history(self):
        self.assertIn('SHORT_SESSION_HISTORY',r.window(bars([100]*2),ENDS,542)['reasons'])
    def test_no_relabel_at_reopen_without_new_bar(self):
        z=r.window(bars([100],start=690),ENDS,750)
        self.assertIn('CURRENT_BAR_UNAVAILABLE',z['reasons'])
    def test_tail_not_invented(self):
        self.assertEqual(r.grid(922,ENDS)['tailEnds'],[923,924,925])
    def test_window_generator(self):
        self.assertEqual(r.window(bars([100]*5),(e for e in ENDS),545)['status'],'COMPLETE')


class ScaleDirectionTests(unittest.TestCase):
    def test_scale_uses_previous_six_complete_blocks(self):
        z=r.scale_from_previous(previous(),DAY,PREV,'SYNTHETIC','RAW-SYNTHETIC')
        self.assertEqual(z['scale'],1)
        self.assertEqual(z['blockN'],6)
    def test_scale_insufficient(self):
        z=r.scale_from_previous(previous(missing=True),DAY,PREV,'SYNTHETIC','RAW-SYNTHETIC')
        self.assertEqual(z['status'],'SCALE_INSUFFICIENT')
    def test_scale_zero_not_replaced(self):
        z=r.scale_from_previous(previous(flat=True),DAY,PREV,'SYNTHETIC','RAW-SYNTHETIC')
        self.assertEqual(z['status'],'SCALE_ZERO')
        self.assertIsNone(z['scale'])
    def test_wrong_previous_not_substituted(self):
        with self.assertRaisesRegex(ValueError,'ACTUAL_PREVIOUS'): r.scale_from_previous(previous(),DAY,'2025-05-29','SYNTHETIC','RAW-SYNTHETIC')
    def test_basis_mismatch(self):
        self.assertEqual(r.scale_from_previous(previous(),DAY,PREV,'SYNTHETIC','ADJUSTED')['status'],'PRICE_BASIS_UNVERIFIED')
    def test_small_positive_not_flat(self):
        self.assertEqual(r.metrics(bars([F(100),F(100),F(100),F(100),F(1000001,10000)]))['direction'],'UP')
    def test_flat_close_big_range_not_no_movement(self):
        z=r.metrics(bars([100,101,99,101,100]))
        self.assertEqual(z['direction'],'UNCHANGED')
        self.assertEqual(z['width'],2)
        self.assertEqual(z['directionChanges'],3)
    def test_efficiency_zero_motion_null(self):
        self.assertIsNone(r.metrics(bars([100]*5))['efficiency'])
    def test_missing_activity_not_zero(self):
        self.assertIsNone(r.metrics(bars([100]*5,activity=None))['volume'])


class SwingStructureTests(unittest.TestCase):
    def test_exact_swing_threshold(self):
        ps=r.pivots(bars([100,101,100]),F(1))
        self.assertEqual([p['kind'] for p in ps],['LOW','HIGH'])
    def test_subthreshold_not_pivot(self):
        self.assertEqual(r.pivots(bars([100,F(1009,10),100]),F(1)),[])
    def test_equal_extreme_earliest(self):
        ps=r.pivots(bars([100,102,102,101]),F(1))
        self.assertEqual(ps[-1]['effectiveAt'],542)
        self.assertEqual(ps[-1]['confirmedAt'],544)
    def test_no_pivot_through_gap(self):
        self.assertEqual(r.pivots(bars([100])+bars([200],start=550),F(1)),[])
    def test_up_structure(self):
        z=r.snapshot(bars([100,102,101,103,102,104]),ENDS,546,F(1))
        self.assertEqual(z['state']['structure']['kind'],'UP_STRUCTURE')
        self.assertEqual(z['state']['structure']['protected'],102)
    def test_down_structure(self):
        z=r.snapshot(bars([104,102,103,101,102,100]),ENDS,546,F(1))
        self.assertEqual(z['state']['structure']['kind'],'DOWN_STRUCTURE')
    def test_lower_high_only_not_down(self):
        z=r.snapshot(bars([100,104,101,103,102]),ENDS,545,F(1))
        self.assertIsNone(z['state']['structure'])
    def test_invalidated_structure_not_resurrected(self):
        z=r.snapshot(bars([100,102,101,103,102,100,100]),ENDS,547,F(1))
        self.assertIsNone(z['state']['structure'])
        self.assertIn('RESTRUCTURING',z['state']['phase'])
    def test_equal_protected_not_break(self):
        z=r.snapshot(bars([100,102,101,103,102,101]),ENDS,546,F(1))
        self.assertEqual(z['state']['structure']['kind'],'UP_STRUCTURE')
    def test_gap_does_not_forwardfill_structure(self):
        bs=bars([100,102,101,103,102])+bars([103],start=550)
        self.assertIsNone(r.snapshot(bs,ENDS,550,F(1))['state']['structure'])
    def test_low_recovery(self):
        z=r.snapshot(bars([103,102,101,100,101]),ENDS,545,F(1))
        self.assertIn('RECOVERY',z['state']['phase'])
        self.assertEqual(z['state']['recoveredFraction'],F(1,3))
    def test_recovery_complete_not_automatic_uptrend(self):
        z=r.snapshot(bars([103,102,100,101,103]),ENDS,545,F(1))
        self.assertNotIn('RECOVERY',z['state']['phase'])
        self.assertIsNone(z['state']['structure'])
        self.assertIn('RECOVERY_COMPLETE',[e['kind'] for e in z['state']['events']])
    def test_failed_recovery(self):
        z=r.snapshot(bars([103,100,101,99,99]),ENDS,545,F(1))
        self.assertIn('RECOVERY_INVALIDATED',[e['kind'] for e in z['state']['events']])
    def test_correction_and_recovery_can_coexist(self):
        z=r.snapshot(bars([104,102,103,100,101]),ENDS,545,F(1))
        self.assertEqual(z['state']['structure']['kind'],'DOWN_STRUCTURE')
        self.assertEqual(set(z['state']['phase']),{'CORRECTION','RECOVERY'})


class RangeEventTests(unittest.TestCase):
    def test_range_positive_evidence(self):
        self.assertIsNotNone(r.range_candidate(bars([100,101,100,101,100]*6),F(1)))
    def test_flatline_not_range(self):
        self.assertIsNone(r.range_candidate(bars([100]*30),F(1)))
    def test_short_window_not_range(self):
        self.assertIsNone(r.range_candidate(bars([100,101,100]*9),F(1)))
    def test_trending_not_range(self):
        self.assertIsNone(r.range_candidate(bars([F(100)+F(i,100) for i in range(30)]),F(1)))
    def test_range_exit_not_automatic_up(self):
        z=r.snapshot(bars([100,101,100,101,100]*6+[102]),ENDS,571,F(1))
        self.assertIsNone(z['state']['structure'])
        self.assertIn('RANGE_CLOSE_EXIT',[e['kind'] for e in z['state']['events']])
    def test_chop_coexists_with_up_direction(self):
        z=r.attributes(bars([100,101,100,101,F(201,2)]),[],F(1))
        self.assertIn('CHOPPINESS',z['tags'])
        self.assertEqual(z['descriptors']['direction'],'UP')
    def test_chop_not_zero_width(self):
        self.assertNotIn('CHOPPINESS',r.attributes(bars([100]*5),[],F(1))['tags'])
    def test_cross_level_identity(self):
        e=r.level_events(bars([99,100,101,102,103]),F(100),'PDH',540,540,545)
        self.assertTrue(any(x['kind']=='CLOSE_CROSS_UP' and x['levelId']=='PDH' for x in e))
    def test_wick_not_close_cross(self):
        bs=(r.Bar(541,99,99,99,99),r.Bar(542,99,102,98,99))
        kinds=[e['kind'] for e in r.level_events(bs,F(100),'PDH',540,540,542)]
        self.assertIn('WICK_ABOVE',kinds)
        self.assertNotIn('CLOSE_CROSS_UP',kinds)
    def test_samebar_order_explicit(self):
        bs=(r.Bar(541,99,99,99,99),r.Bar(542,99,102,98,101))
        self.assertIn('INTRABAR_ORDER_UNRESOLVED',[e['kind'] for e in r.level_events(bs,F(100),'PDH',540,540,542)])
    def test_reclaim_has_history(self):
        e=r.level_events(bars([101,99,101]),F(100),'PDH',540,540,543)
        self.assertIn('RECLAIM_UP',[x['kind'] for x in e])
    def test_gap_cross_not_invented(self):
        e=r.level_events(bars([99])+bars([101],start=550),F(100),'PDH',540,540,550)
        self.assertFalse(any(x['kind']=='CLOSE_CROSS_UP' for x in e))
    def test_future_level_rejected(self):
        with self.assertRaisesRegex(ValueError,'UNFIXED'): r.level_events(bars([100]),F(100),'PDH',542,540,541)
    def test_two_close_confirmation(self):
        e={'kind':'CLOSE_CROSS_UP','eventAt':542,'level':F(100)}
        z=r.confirmation(e,bars([99,101,102,103]),ENDS,544)
        self.assertEqual(z['status'],'HELD_TWO_CLOSES')
    def test_confirmation_missing_not_failure(self):
        e={'kind':'CLOSE_CROSS_UP','eventAt':542,'level':F(100)}
        self.assertEqual(r.confirmation(e,bars([99,101]),ENDS,544)['status'],'OBSERVATION_INSUFFICIENT')
    def test_confirmation_close_boundary(self):
        e={'kind':'CLOSE_CROSS_UP','eventAt':924,'level':F(100)}
        self.assertEqual(r.confirmation(e,[],ENDS,925)['status'],'RIGHT_CENSORED')


class ContextOracleTests(unittest.TestCase):
    def test_all_four_scopes(self):
        z=r.assemble(series([100,102,101,103,102]),previous(),CAL,dailies(),545)
        self.assertEqual(z['contexts']['recentDaily']['fiveDayDirection'],'UP')
        self.assertIsNotNone(z['contexts']['previousDay'])
        self.assertEqual(z['contexts']['scale']['scale'],1)
        self.assertEqual(z['descriptors']['direction'],'UP')
        self.assertEqual(z['scope'],'TODAY')
    def test_daily_conflict_not_overwrite_today(self):
        z=r.assemble(series([100,102,101,103,102]),previous(),CAL,dailies(down=True),545)
        self.assertEqual(z['contexts']['recentDaily']['fiveDayDirection'],'DOWN')
        self.assertEqual(z['state']['structure']['kind'],'UP_STRUCTURE')
    def test_missing_previous_does_not_remove_direction(self):
        z=r.assemble(series([100,101,102,103,104]),None,CAL,dailies(),545)
        self.assertEqual(z['descriptors']['direction'],'UP')
        self.assertIsNone(z['state']['structure'])
    def test_missing_daily_not_substitute(self):
        self.assertFalse(r.daily_context(DAY,CAL,dailies()[:-1],'SYNTHETIC','RAW-SYNTHETIC')['complete5'])
    def test_future_daily_rejected(self):
        rows=dailies();rows[-1]['date']=DAY
        with self.assertRaisesRegex(ValueError,'EXACT_LAGS'): r.daily_context(DAY,CAL,rows,'SYNTHETIC','RAW-SYNTHETIC')
    def test_security_identity_rejected(self):
        rows=dailies();rows[0]['security']='OTHER'
        with self.assertRaisesRegex(ValueError,'SECURITY_MISMATCH'): r.daily_context(DAY,CAL,rows,'SYNTHETIC','RAW-SYNTHETIC')
    def test_corporate_action_cross_basis_blocked(self):
        rows=dailies();rows[0]['actionUnverified']=True
        z=r.daily_context(DAY,CAL,rows,'SYNTHETIC','RAW-SYNTHETIC')
        self.assertFalse(z['complete5'])
    def test_effective_and_confirmed_separate(self):
        bs=bars([100,102,101,103,102,104])
        a=r.reference_at(bs,ENDS,544,F(1))
        self.assertGreater(a['futureConfirmation']['lateConfirmedPivotN'],0)
        self.assertNotEqual(r.canonical(a['state']),r.canonical(r.snapshot(bs[:4],ENDS,544,F(1))['state']))
    def test_end_censor_does_not_remove_direction(self):
        z=r.reference_at(bars([100,101,102,103,104],start=921),ENDS,925,F(1))
        self.assertEqual(z['futureConfirmation']['status'],'RIGHT_CENSORED')
        self.assertEqual(z['descriptors']['direction'],'UP')
    def test_oracle_after_horizon_invariant(self):
        a=bars([100,102,101,103,102]*8)
        b=a[:15]+bars([1000]*25,start=556)
        self.assertEqual(r.canonical(r.reference_at(a,ENDS,545,F(1))),r.canonical(r.reference_at(b,ENDS,545,F(1))))
    def test_causal_suffix_invariant(self):
        a=bars([100,102,101,103,102]*8)
        b=a[:5]+bars([1000]*35,start=546)
        self.assertEqual(r.canonical(r.snapshot(a[:5],ENDS,545,F(1))),r.canonical(r.snapshot(b[:5],ENDS,545,F(1))))
    def test_no_caller_input_mutation(self):
        a=bars([100,102,101,103,102]*8)
        digest=r.canonical(a)
        r.reference_at(a,ENDS,545,F(1))
        self.assertEqual(r.canonical(a),digest)
    def test_transition_is_not_economic_claim(self):
        a=r.snapshot(bars([100]*5),ENDS,545,F(1))
        b=r.snapshot(bars([100]*10),ENDS,550,F(1))
        self.assertFalse(r.transition(a,b)['isEconomicReversalClaim'])
    def test_transition_identity_guard(self):
        a=r.snapshot(bars([100]*5),ENDS,545,F(1)); b=copy.deepcopy(a); b['asOf']=550; b['scope']='OTHER'
        with self.assertRaisesRegex(ValueError,'IDENTITY'): r.transition(a,b)
    def test_scale_invariance(self):
        ps=[100,102,101,103,102,104,101,103,104]
        a=r.snapshot(bars(ps),ENDS,549,F(1))
        b=r.snapshot(bars([p*10 for p in ps]),ENDS,549,F(10))
        self.assertEqual(a['state']['identificationStatus'],b['state']['identificationStatus'])
        self.assertEqual(a['state']['phase'],b['state']['phase'])
        self.assertEqual(a['descriptors']['direction'],b['descriptors']['direction'])
    def test_randomized_replay_determinism(self):
        gen=random.Random(587)
        for _ in range(25):
            ps=[F(100)]
            for i in range(49): ps.append(ps[-1]+F(gen.choice([-3,-2,-1,0,1,2,3]),2))
            bs=bars(ps)
            a=r.canonical(r.snapshot(bs,ENDS,590,F(1)))
            b=r.canonical(r.snapshot(bs,ENDS,590,F(1)))
            self.assertEqual(hashlib.sha256(a.encode()).hexdigest(),hashlib.sha256(b.encode()).hexdigest())


class AdditionalBoundaryTests(unittest.TestCase):
    def test_range_at_exact_width_boundary(self):
        self.assertIsNotNone(r.range_candidate(bars([100,102,100,102,100]*6),F(1)))
    def test_range_beyond_width_boundary(self):
        self.assertIsNone(r.range_candidate(bars([100,F(10201,100),100,F(10201,100),100]*6),F(1)))
    def test_outside_schedule_rejected(self):
        with self.assertRaisesRegex(ValueError,'OUTSIDE_SCHEDULE'):
            r.window(bars([100],start=700),ENDS,700)
    def test_mixed_basis_direction_survives(self):
        today=r.Session(DAY,'SYNTHETIC','ADJUSTED',ENDS,bars([100,101,102,103,104]))
        z=r.assemble(today,previous(),CAL,dailies(),545)
        self.assertEqual(z['descriptors']['direction'],'UP')
        self.assertIsNone(z['contexts']['previousDay'])
        self.assertEqual(z['levelSnapshotAtWindowStart'],{})
    def test_no_volume_derived_from_price(self):
        bs=[r.Bar(541+i,100,100,100,100,100,None) for i in range(5)]
        self.assertIsNone(r.metrics(bs)['observedVWAP'])
    def test_wick_at_segment_start_is_observed(self):
        b=r.Bar(541,99,102,98,99)
        kinds=[e['kind'] for e in r.level_events([b],100,'LEVEL',540,540,541)]
        self.assertIn('WICK_ABOVE',kinds)
        self.assertNotIn('CLOSE_CROSS_UP',kinds)
    def test_confirmation_rejects_wick_event(self):
        with self.assertRaisesRegex(ValueError,'NOT_A_CLOSE_CROSS'):
            r.confirmation({'kind':'WICK_ABOVE','eventAt':541,'level':F(100)},[],ENDS,545)
    def test_zero_denominator_ratio_is_null(self):
        z=r.attributes(bars([100]*5,start=546),bars([100]*5,activity=0),F(1))
        self.assertIsNone(z['ratios']['volume'])
        self.assertIsNone(z['ratios']['width'])
    def test_at_oracle_low_not_yet_recovering(self):
        bs=bars([103,102,100,101,102])
        z=r.reference_at(bs,ENDS,543,F(1))
        self.assertNotIn('RECOVERY',z['state']['phase'])
    def test_vwap_dynamic_cross(self):
        z=r.vwap_events(bars([100,99,101]),ENDS,540,543)
        self.assertEqual(z['status'],'AVAILABLE')
        self.assertIn('VWAP_RELATION_CROSS_UP',[e['kind'] for e in z['events']])
    def test_vwap_missing_cannot_claim_full_prefix(self):
        z=r.vwap_events(bars([100],start=542),ENDS,540,542)
        self.assertEqual(z['status'],'PARTIAL_OBSERVATION')
    def test_oracle_gap_does_not_make_pivot(self):
        bs=bars([100],start=545)+bars([103],start=550)
        z=r.reference_at(bs,ENDS,545,F(1))
        self.assertEqual(z['futureConfirmation']['lateConfirmedPivotN'],0)
    def test_price_scaling_property_25_paths(self):
        gen=random.Random(2155)
        for _ in range(25):
            ps=[F(100)]
            for i in range(29): ps.append(ps[-1]+F(gen.choice([-2,-1,0,1,2]),2))
            a=r.snapshot(bars(ps),ENDS,570,F(1))
            b=r.snapshot(bars([p*7 for p in ps]),ENDS,570,F(7))
            self.assertEqual(a['state']['identificationStatus'],b['state']['identificationStatus'])
            self.assertEqual(a['state']['phase'],b['state']['phase'])
            self.assertEqual([p['kind'] for p in a['state'].get('pivots',[])],
                             [p['kind'] for p in b['state'].get('pivots',[])])


if __name__=='__main__':
    unittest.main(verbosity=2)
