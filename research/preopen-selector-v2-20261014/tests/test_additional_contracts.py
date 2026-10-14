"""Meaningful optional-source, numerical, bootstrap and CLI regressions."""
from datetime import date,datetime,timedelta
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock
import numpy as np
from test_required_matrix import history,evidence,H,ROOT,watch,candidate,outcome
from ark_selector_v2.contracts import feature_names,registry,bind_provenance,FLAGS,Candle,FeatureFrame
from ark_selector_v2.calendar_phase import JST,cutoff,phase_times,dependency_history
from ark_selector_v2.exact_math import V2Error
from ark_selector_v2.features_daily import daily_features,ema
from ark_selector_v2.features_intraday import Coverage,Bar,Tick,minute_features,tick_features,reference_price
from ark_selector_v2.features_context import Peer,Financial,market_features,financial_features,state_features,assemble_features
from ark_selector_v2.evaluation import bootstrap_days,binary_diagnostics,public_suppression,summarize,exclusion_audit
from ark_selector_v2.admission import transition,metadata_audit
from ark_selector_v2.model import synthetic_factory,confirm_synthetic,synthetic_forecast_factory
from ark_selector_v2.resources import memory_preflight
from ark_selector_v2.feature_store import write_features,read_features


class AdditionalContracts(unittest.TestCase):
    def test_registry95_and_derived_histories(self):
        names=feature_names();self.assertEqual(len(set(names)),95)
        self.assertEqual([r['ordinal'] for r in registry()['columns']],list(range(1,96)))
        self.assertEqual(dependency_history(),{'g1':76,'g2':77,'ema_macd':150,'sma75_slope15':90,'sma75_up_fraction3':78,'rsi14':76})
        proposal=json.loads((ROOT/'V2_PARAM_PROPOSAL.json').read_text())
        self.assertFalse(proposal['parameters_adopted']);self.assertFalse(proposal['market_fit_allowed'])

    def test_daily51_exact_linear_independent_expectations(self):
        rows=history([F(100)+F(i,10) for i in range(150)])
        frame=daily_features(rows,rows[-1].session)
        self.assertEqual(len(frame.values),51)
        c=F('114.9');mean5=F('114.7')
        self.assertAlmostEqual(frame.values['v2_sma_distance_5'],float(100*(c/mean5-1)))
        self.assertAlmostEqual(frame.values['v2_sma_slope1_atr_75'],.05)
        self.assertAlmostEqual(frame.values['v2_sma_slopeH_atr_75'],.05)
        self.assertEqual(frame.values['v2_sma_up_fraction3_75'],1)
        self.assertEqual(frame.values['v2_price_efficiency20'],1)
        self.assertEqual(frame.values['v2_rsi14'],100)
        self.assertEqual(frame.values['v2_turnover_spike'],1)
        self.assertAlmostEqual(frame.values['v2_reference_capacity_share'],.005)
        self.assertAlmostEqual(frame.values['v2_upper_wick_ratio'],.5)
        self.assertEqual(frame.values['v2_candle_body'],0)
        self.assertEqual(frame.values['v2_downside_vol20'],0)

    def test_recursive_seed150_exact_and_optional_history(self):
        cs=[F(i+100) for i in range(150)]
        e=ema(cs,5)
        independent=sum(cs[:5])/5
        for c in cs[5:]:independent=F(1,3)*c+F(2,3)*independent
        self.assertEqual(e[-1],independent)
        frame=daily_features(history(n=77),history(n=77)[-1].session)
        self.assertIsNone(frame.values['v2_ema_distance_5'])
        self.assertIsNone(frame.values['v2_sma_slopeH_atr_75'])
        self.assertIsNone(frame.values['v2_sma_up_fraction3_75'])
        self.assertIsNotNone(frame.values['v2_sma_slope1_atr_75'])

    def test_full95_optional_source_not_joined(self):
        rows=history(n=150);frame=assemble_features(daily_features(rows,rows[-1].session))
        self.assertEqual(tuple(frame.values),feature_names())
        self.assertTrue(all(frame.values[n] is None for n in feature_names()[51:]))
        self.assertTrue(all(frame.missing[n]=='SOURCE_NOT_JOINED' for n in feature_names()[51:]))

    def test_fraction_zero_range_rsi_and_amihud(self):
        rows=history([100]*150,width=F(0));frame=daily_features(rows,rows[-1].session)
        self.assertEqual(frame.values['v2_rsi14'],50);self.assertEqual(frame.values['v2_price_efficiency20'],0)
        self.assertIsNone(frame.values['v2_close_location']);self.assertIsNone(frame.values['v2_sma_slope1_atr_5'])
        rows[-10]=replace(rows[-10],turnover=F(0))
        self.assertIsNone(daily_features(rows,rows[-1].session).values['v2_amihud20_scaled'])

    def test_reference_oldest_endpoint_five_minutes(self):
        d=date(2024,11,5);end,_=phase_times(d);when=end-timedelta(minutes=30)
        b=Bar(when-timedelta(minutes=5),when-timedelta(minutes=4),Candle.from_values(d,100,101,99,100,10,1000),'CONTINUOUS',0)
        price,meta=reference_price([b],when);self.assertEqual(price,100);self.assertEqual(meta['age_seconds_interval'],[240,300])
        older=replace(b,start=b.start-timedelta(seconds=1),end=b.end-timedelta(seconds=1))
        self.assertIsNone(reference_price([older],when)[0])

    def test_minute13_formulas_full_phase_and_gap(self):
        d=date(2024,11,5);end,auction=phase_times(d);start=datetime(2024,11,5,12,30,tzinfo=JST)
        bars=[]
        for i in range(175):
            t=start+timedelta(minutes=i);p=F(100)+F(i,100)
            bars.append(Bar(t,t+timedelta(minutes=1),Candle.from_values(d,p,p+1,p-1,p,10,p*10),'CONTINUOUS',i))
        bars.append(Bar(auction-timedelta(minutes=1),auction,Candle.from_values(d,102,102,102,102,10,1020),'AUCTION',175))
        cov=Coverage(True,True,True,True,H,'COMPLETE');f=minute_features(bars,d,cov)
        self.assertEqual(len(f.values),12);self.assertEqual(f.values['v2_pm_observed_minute_fraction'],1)
        self.assertEqual(f.values['v2_last_continuous_bar_age_seconds'],0)
        self.assertEqual(f.values['v2_pm_path_efficiency'],1)
        self.assertAlmostEqual(f.values['v2_pm_return'],float(100*(F('101.74')/100-1)))
        self.assertAlmostEqual(f.values['v2_closing_auction_gap'],float(100*(F(102)/F('101.74')-1)))
        self.assertEqual(f.metadata['last60_close_location_validN'],60)
        broken=bars[:-3]+bars[-2:]
        fb=minute_features(broken,d,Coverage(False,False,False,False,H,'PARTIAL'))
        self.assertIsNone(fb.values['v2_pm_path_efficiency'])
        self.assertIsNone(fb.values['v2_continuous_vwap_distance'])

    def test_tick7_independent_record_formulas(self):
        d=date(2024,11,5);end,_=phase_times(d);records=[]
        for i,(sec,p,size) in enumerate([(2000,99,1),(1700,100,2),(1200,102,1),(10,101,3)]):
            records.append(Tick(end-timedelta(seconds=sec),F(p),F(size),i,str(i),'CONTINUOUS'))
        f=tick_features(records,d,Coverage(True,True,True,True,H,'COMPLETE'))
        self.assertEqual(len(f.values),7);self.assertEqual(f.values['v2_tick_count30'],3)
        self.assertEqual(f.values['v2_tick_volume30'],6);self.assertEqual(f.values['v2_tick_up_ratio30'],.5)
        self.assertEqual(f.values['v2_tick_burst30'],3);self.assertEqual(f.values['v2_tick_last_trade_age'],10)
        expected=100*(F(101)/(F(605,6))-1)
        self.assertAlmostEqual(f.values['v2_tick_vwap_distance30'],float(expected))

    def test_peer_context8_and_coverage_boundary(self):
        t=date(2024,6,1);D=date(2024,6,3);e=evidence()
        peers=[Peer(str(i),'sector',t,F(i),F(i*2),e) for i in range(9)]
        expected={str(i) for i in range(10)}
        f=market_features(t,cutoff(D),'sector',expected,expected,peers,F(10),{1:F(1),5:F(2),25:F(3)},e)
        self.assertEqual(len(f.values),8);self.assertEqual(f.values['v2_sector_return_5d'],8)
        self.assertEqual(f.values['v2_relative_sector_return5'],2)
        self.assertAlmostEqual(f.values['v2_market_breadth'],800/9)
        bad=market_features(t,cutoff(D),'sector',expected,expected,peers[:-1],F(10))
        self.assertIsNone(bad.values['v2_sector_return_1d'])

    def test_financial8_asof_units_and_ambiguity(self):
        d=date(2024,6,3);e=evidence()
        row=Financial('DOC','FY','CONSOLIDATED','JPY','MILLION_JPY',F(120),F(100),F(12),F(-10),e,True)
        f=financial_features([row],d,cutoff(d),{'roe':F('.12'),'per':F(-10),'pbr':F(2)},e,True,date(2024,6,10),e)
        self.assertEqual(len(f.values),8);self.assertEqual(f.values['v2_sales_yoy'],20)
        self.assertEqual(f.values['v2_operating_profit_change'],220);self.assertEqual(f.values['v2_operating_margin'],10)
        self.assertEqual(f.values['v2_valuation_roe'],12);self.assertEqual(f.values['v2_valuation_per'],-10)
        self.assertEqual(f.values['v2_days_to_known_earnings'],7)
        future=replace(row,document_id='FUTURE',sales=F(999),evidence=replace(e,available_at=cutoff(d)+timedelta(seconds=1)))
        self.assertEqual(financial_features([row,future],d,cutoff(d)).values['v2_sales_yoy'],20)
        ambiguous=financial_features([row,replace(row,document_id='OTHER')],d,cutoff(d))
        self.assertIsNone(ambiguous.values['v2_sales_yoy'])

    def test_state9_never_carry_and_frozen_hash(self):
        t=date(2024,6,1);D=date(2024,6,3);e=evidence()
        missing=state_features('RANGE',formal_observed=False,t=t,cutoff=cutoff(D),evidence=None,rules_hash=None,profile_hash=None,normalizer_hash=None)
        self.assertTrue(all(v is None for v in missing.values.values()))
        formal=state_features('RISE',formal_observed=True,t=t,cutoff=cutoff(D),evidence=e,rules_hash=H,profile_hash=H,normalizer_hash=H)
        self.assertEqual(sum(formal.values.values()),1);self.assertEqual(formal.values['v2_previous_state_RISE'],1)
        real=replace(e,known_at_evidence_kind='OBSERVED_RECEIPT')
        with self.assertRaisesRegex(V2Error,'FROZEN_LINEAGE'):state_features('RISE',formal_observed=True,t=t,cutoff=cutoff(D),evidence=real,rules_hash=H,profile_hash=H,normalizer_hash=H,expected_lineage=('b'*64,H,H))

    def test_feature_provenance_all_fields_and_cutoff(self):
        f=FeatureFrame();f.put('v2_example',1)
        with self.assertRaises(V2Error):bind_provenance(f,{'v2_example':()},cutoff(date(2024,6,3)))
        e=evidence();bound=bind_provenance(f,{'v2_example':(e,)},cutoff(date(2024,6,3)))
        metadata=bound.metadata['column_provenance']['v2_example']['sources'][0]
        self.assertEqual(set(metadata),set(vars(e)))

    def test_all_market_cli_stages_refuse_before_request_open(self):
        for stage in ('census','train','calibrate','predict','evaluate','restore-verify'):
            p=subprocess.run([sys.executable,str(ROOT/'tools/v2_cli.py'),stage,'--request','DOES_NOT_EXIST'],capture_output=True,text=True)
            self.assertEqual(p.returncode,2);self.assertIn('AWAITING_MARKET_APPROVAL',p.stdout)
            self.assertEqual(json.loads(p.stdout)['market_numeric_reads'],0)

    def test_synthetic_certificate_rejects_relabelled_rows(self):
        fit,cal,cert=synthetic_factory();fit.x[0,0]=123456
        with self.assertRaisesRegex(V2Error,'REAL_OR_MODIFIED'):confirm_synthetic(fit,cal,cert)

    def test_memory_support_preflight_without_fit(self):
        self.assertGreater(memory_preflight(1800,600)['engineering_peak_estimate_bytes'],0)
        with self.assertRaisesRegex(V2Error,'FIT0'):memory_preflight(10000000,10000000)

    def test_state_machine_no_final_after_validation_failure(self):
        self.assertEqual(transition('VALIDATION_OPENED','FAIL'),'FAIL')
        with self.assertRaises(V2Error):transition('FAIL','FINAL_OPENED')
        with self.assertRaises(V2Error):transition('ENGINEERING_READY','FIT_ATTEMPT_STARTED')

    def test_zero_denominator_bootstrap_and_no_tail_certification(self):
        b=bootstrap_days([{'selectedN':0,'loserN':0}]*5,consecutive_window_verified=True)
        self.assertEqual(b['undefined_draws'],5000);self.assertIsNone(b['descriptive_interval'])
        b=bootstrap_days([{'selectedN':15,'loserN':0}]*40,consecutive_window_verified=True)
        self.assertEqual(b['descriptive_interval'],[0,0]);self.assertFalse(b['STATISTICAL_SUPPORT_ESTABLISHED'])
        with self.assertRaises(V2Error):bootstrap_days([{'selectedN':1,'loserN':0}],consecutive_window_verified=False)

    def test_probability_fixed_bins_and_weighted_estimand(self):
        p=np.array([.01,.05,.10,1.0]);y=np.array([0,1,0,1]);s=['a','a','b','c']
        bins=[0,.01,.025,.05,.10,.20,.50,1]
        r=binary_diagnostics(p,y,s,bins,np.array([.5,.5,1,1]))
        self.assertEqual(sum(x['N'] for x in r['bins']),4)
        self.assertEqual(r['estimand'],'DAY_UNIFORM_WEIGHTED');self.assertFalse(r['probability_tail_certified'])
        self.assertTrue(all(x['support']=='INSUFFICIENT_SUPPORT' for x in r['bins']))

    def test_public_complementary_suppression(self):
        self.assertEqual(public_suppression({'small':2,'large':100}),{'suppressed':True,'reason':'SMALL_CELL_COMPLEMENTARY_SUPPRESSION'})

    def test_metadata_monthly_union_not_permissions(self):
        days=['2024-01-01','2024-01-02']
        sources=[]
        for kind in ('DAILY','DATED_MASTER','CALENDAR'):
            for d in days:
                sources.append({'source_id':kind+d,'sha256':H,'bytes':1,'dataset':kind,'allowed_record_dates':[d],'allowed_purposes':['HISTORY'],'protected_reason':None,'latest_available_at':None,'rights_reference':'METADATA_ONLY'})
        request={'schema':'ARK_V2_METADATA_REQUEST_V1','calendar_sessions':days,'allowed_v2_sessions':days,'sources':sources,'protected_sessions':[],'exposed_sessions':[]}
        result=metadata_audit(request)
        self.assertEqual(result['metadata_eligible_requested_days'],2);self.assertEqual(result['approved_v2_teacher_days'],0)
        self.assertIsNone(result['latest_window_proposal'])

    def test_feature_sqlite_cache_hash_binding_and_stream(self):
        binding={k:H for k in ('input','code','policy','calendar','phase','schema')};binding['basis']='RAW'
        values={n:None for n in feature_names()}
        row={'session':'2030-01-01','canonical_symbol':'0001','market':'PRIME','features':values,'provenance':{'kind':'SYNTHETIC'}}
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'features.sqlite';write_features(p,iter([row]),binding)
            self.assertEqual(list(read_features(p.resolve(),binding)),[row])
            bad={**binding,'phase':'b'*64}
            with self.assertRaisesRegex(V2Error,'CACHE_HASH_DRIFT'):list(read_features(p.resolve(),bad))

    def test_whole_five_day_block_reaggregates_ratios(self):
        zero={'selectedN':0,'raw1N':0,'clean3N':0,'clean5N':0,'loser3N':0,'loser5N':0,'unknownN':0}
        rows=[{**zero,'selectedN':5,'raw1N':1,'clean3N':1,'clean5N':1,'unknownN':1},
              {**zero,'selectedN':10,'raw1N':2,'clean3N':2,'loser3N':1}]+[zero]*3
        result=bootstrap_days(rows,consecutive_window_verified=True)
        self.assertEqual(result['metrics']['raw_winner1_lower_rate']['descriptive_interval'],[.2,.2])
        self.assertEqual(result['metrics']['clean3_per_all_session']['descriptive_interval'],[.6,.6])
        self.assertEqual(result['metrics']['loser3_unknown_worst_rate']['descriptive_interval'],[2/15,2/15])

    def test_actual_gate_to_95_feature_canary(self):
        from ark_selector_v2.model import synthetic_gate_canary
        vector,receipt=synthetic_gate_canary()
        self.assertEqual(vector.shape,(95,));self.assertEqual(vector.dtype,np.float64)
        self.assertEqual([receipt[k] for k in ('g0','g1','g2')],['PASS']*3)
        self.assertEqual(receipt['optional_unjoined_columns'],44)
        self.assertEqual(synthetic_forecast_factory()[0,44],100)

    def test_watchlist_rejects_future_times_and_run_error_as_empty(self):
        from ark_selector_v2.selection import validate_watchlist,watchlist_hash
        w=watch()
        w['items'][0]['source_times']={'available_at':'2030-03-04T08:50:01+09:00'}
        w['hashes']['watchlist']=watchlist_hash(w)
        with self.assertRaisesRegex(V2Error,'INFORMATION_CUTOFF'):validate_watchlist(w)
        empty=watch([]);empty['reason']='MODEL_ERROR';empty['hashes']['watchlist']=watchlist_hash(empty)
        with self.assertRaisesRegex(V2Error,'RUN_ERROR'):validate_watchlist(empty)

    def test_raw_teacher_and_strict_boolean_source_types(self):
        from ark_selector_v2.labels import label
        from ark_selector_v2.contracts import Identity
        d=date(2024,6,3)
        row=Candle.from_values(d,100,106,96,104,basis='ADJUSTED')
        with self.assertRaisesRegex(V2Error,'RAW_JPY'):label(row)
        with self.assertRaisesRegex(V2Error,'RAW_JPY'):label(replace(row,basis='RAW',units=('USD','SHARES','JPY')))
        identity=Identity('130A','130A.T','PRIME',d,'COMMON_STOCK',100,'1')
        with self.assertRaisesRegex(V2Error,'CASH_TYPE'):replace(identity,cash='false').eligible(d)
        with self.assertRaisesRegex(V2Error,'OBSERVATION_TYPE'):state_features('RANGE',formal_observed='false',t=date(2024,6,1),cutoff=cutoff(d),evidence=evidence(),rules_hash=H,profile_hash=H,normalizer_hash=H)
        frame=FeatureFrame()
        with self.assertRaisesRegex(V2Error,'BOOLEAN'):frame.put('v2_valuation_per',True)


if __name__=='__main__':unittest.main()
