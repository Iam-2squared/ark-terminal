"""72 named R1 requirements; only generated values, independent exact oracles."""
from __future__ import annotations
from dataclasses import replace
from datetime import date,datetime,timedelta
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tools"))
from ark_selector_v2.exact_math import V2Error,rational,median
from ark_selector_v2.contracts import Candle,Identity,SourceEvidence,FLAGS,digest,code_hash,configuration_hash,registry,forbid_outcomes
from ark_selector_v2.calendar_phase import ExchangeCalendar,JST,cutoff,phase_times,tick_in_window
from ark_selector_v2.gates import g0,g1,g2,atr_pre
from ark_selector_v2.labels import label
from ark_selector_v2.features_daily import daily_features
from ark_selector_v2.features_intraday import Tick,Bar,Coverage,tick_features,ordered_ticks,path_first_hit,remaining_high
from ark_selector_v2.model import TrainingData,partition,teacher_support,synthetic_factory,fit_synthetic_bundle,ModelBundle,oracle_supply
from ark_selector_v2.weights import common_weights,used_columns,check_cal_support
from ark_selector_v2.calibration import temperature,fit_temperature,Temperature
from ark_selector_v2.selection import joint,qualified,rank_candidates,make_watchlist,validate_watchlist,watchlist_hash
from ark_selector_v2.evaluation import summarize,capture
from ark_selector_v2.admission import Admission,Mode,ApprovalPins,validate_approval,admitted_open
from ark_selector_v2.experiment_ledger import ExperimentLedger,EVENTS
from ark_selector_v2.artifact_io import exclusive_bytes,load_model,safe_path,restore_zip,sha_file
from protection_audit import audit_repo

H="a"*64


def history(values=None,n=90,width=F(2),va=F(200000000)):
    cs=[F(100+i) for i in range(n)] if values is None else [F(x) for x in values]
    start=date(2024,1,2)
    return [Candle(start+timedelta(days=i),c,c+width/2,c-width/2,c,F(1000000),va) for i,c in enumerate(cs)]


def set_last(rows,o=None,c=None,va=None):
    old=rows[-1]
    o=old.open if o is None else F(o);c=old.close if c is None else F(c)
    assert o is not None and c is not None
    return rows[:-1]+[replace(old,open=o,close=c,high=max(o,c)+1,low=min(o,c)-1,turnover=old.turnover if va is None else F(va))]


def evidence(d=date(2024,6,1),at=None):
    t=at or datetime(2024,6,1,16,30,tzinfo=JST)
    return SourceEvidence("synthetic",H,"1","record1",t,t,t,t,d,"JPY","RAW","1",0,77,H,"SYNTHETIC",None,"NOT_CERTIFIED")


def candidate(code="0001",q=None):
    return {"canonical_symbol":code,"rss_symbol":code+".T","market":"PRIME","q":q or [.5,.5,.375,.375,.25],"p3":.03125,"p5":.0078125,"g1":"PASS","g2":"PASS","first_reason":None,"all_reason_codes":[],"source_times":{},"missing_map":{},"feature_hash":H}


def watch(rows=None):
    rows=[candidate()] if rows is None else rows
    counts={k:len(rows) for k in ("master","price","g0","g1","g2","prob")}
    hashes={k:H for k in ("config","input","split","risk_model","opportunity_model","calibration")}
    return make_watchlist(date(2030,3,4),rows,counts,hashes)


def outcome(up=2,adverse=1):
    return label(Candle.from_values(date(2030,3,4),100,str(100+up),str(100-adverse),100))


class RequiredMatrix(unittest.TestCase):
    def test_01_calendar_non_sessions(self):
        cal=ExchangeCalendar((date(2024,10,11),date(2024,10,15)),H,"SYNTHETIC")
        for d in (date(2024,10,12),date(2024,10,13),date(2024,10,14)):
            with self.assertRaisesRegex(V2Error,"NON_EXCHANGE_SESSION"):cal.previous(d)

    def test_02_previous_is_exchange_session(self):
        cal=ExchangeCalendar((date(2024,10,11),date(2024,10,15)),H,"SYNTHETIC")
        self.assertEqual(cal.previous(date(2024,10,15)),date(2024,10,11))
        self.assertNotEqual(cal.previous(date(2024,10,15)),date(2024,10,14))

    def test_03_source_after_cutoff(self):
        e=evidence(at=datetime(2024,6,3,8,50,1,tzinfo=JST))
        with self.assertRaisesRegex(V2Error,"SOURCE_NOT_KNOWN"):e.validate(cutoff(date(2024,6,3)))

    def test_04_current_outcome_keys_rejected(self):
        for key in ("label","outcome","current_day_OHLC","today_State","future_close"):
            with self.assertRaisesRegex(V2Error,"OUTCOME"):forbid_outcomes({"nested":{key:1}})

    def test_05_poison_future_invariant(self):
        rows=history(n=150);t=rows[-1].session
        poisoned=rows+[replace(rows[-1],session=t+timedelta(days=1),close=F(999999999),high=F(999999999))]
        self.assertEqual(daily_features(rows,t).values,daily_features(poisoned,t).values)
        e=evidence(at=datetime(2024,6,4,1,tzinfo=JST))
        with self.assertRaises(V2Error):e.validate(cutoff(date(2024,6,3)))

    def test_06_basis_split_units(self):
        rows=history();D=rows[-1].session+timedelta(days=1)
        cal=ExchangeCalendar(tuple(r.session for r in rows)+(D,),H,"SYNTHETIC")
        ident=Identity("130A","130A.T","PRIME",D,"COMMON_STOCK",100,"1")
        for r in (replace(rows[-1],basis="ADJUSTED"),replace(rows[-1],units=("JPY","UNKNOWN","JPY"))):
            with self.assertRaises(V2Error):g0(rows[:-1]+[r],ident,D,cal)
        split=rows[:-1]+[replace(rows[-1],comparable_suffix="AFTER_SPLIT")]
        self.assertEqual(g0(split,ident,D,cal).state,"UNKNOWN")

    def test_07_security_kind_and_alpha_identity(self):
        D=date(2024,6,3)
        i=Identity("130A","130A.T","GROWTH",D,"COMMON_STOCK",100,"RULE_V1")
        self.assertTrue(i.eligible(D))
        for kind in ("ETF","REIT","PREFERRED_STOCK"):
            self.assertFalse(replace(i,security_kind=kind).eligible(D))
        with self.assertRaises(V2Error):replace(i,effective_session=D-timedelta(days=1)).eligible(D)

    def test_08_no_trade_partial_null(self):
        row=Candle.from_values(date(2024,6,1),None,None,None,None,status="NO_TRADE")
        self.assertEqual(label(row).status,"NO_TRADE")
        with self.assertRaisesRegex(V2Error,"PARTIAL"):Candle.from_values(row.session,100,None,99,100)
        for v in (True,"NaN","Infinity",100.0):
            with self.assertRaises(V2Error):rational(v)

    def test_09_master_missing_is_data_blocked(self):
        rows=history();D=rows[-1].session+timedelta(days=1)
        cal=ExchangeCalendar(tuple(r.session for r in rows)+(D,),H,"SYNTHETIC")
        i=Identity("0001","0001.T","PRIME",D,"COMMON_STOCK",100,"1")
        with self.assertRaisesRegex(V2Error,"DATA_BLOCKED"):g0(rows,i,D,cal,master_present=False)

    def test_10_76_vs_77_closes(self):
        rows=history(n=76)
        self.assertTrue(g1(rows).passed)
        self.assertIsNone(atr_pre(rows))
        self.assertEqual(g2(rows).state,"UNKNOWN")

    def test_11_all_up_pass(self):self.assertTrue(g1(history()).passed)

    def test_12_all_nonup_reject(self):
        self.assertEqual(g1(history([100]*90)).reasons,("REJECT_NO_UP_AXIS",))

    def test_13_short_nonup_wait(self):
        rows=history();rows=set_last(rows,c=185)
        result=g1(rows)
        self.assertEqual(result.state,"WAIT");self.assertFalse(result.values["axes"]["short"])
        self.assertTrue(result.values["axes"]["medium"])

    def test_14_medium_flat_wait(self):
        values=[100]*90;values[-16]=143;values[-26]=143
        values[-5:]=[139,140,141,142,143]
        result=g1(history(values))
        self.assertEqual(result.state,"WAIT");self.assertFalse(result.values["axes"]["medium"])
        self.assertTrue(result.values["axes"]["long"]);self.assertTrue(result.values["axes"]["short"])

    def test_15_medium_both_required(self):
        values=list(range(100,190));values[-26]=190
        result=g1(history(values))
        self.assertTrue(result.values["15"]["up"]);self.assertFalse(result.values["25"]["up"])
        self.assertFalse(result.values["axes"]["medium"])

    def test_16_equalities_not_up(self):
        result=g1(history([100]*90))
        for n in (5,15,25,75):
            self.assertEqual(result.values[str(n)]["delta"],0);self.assertFalse(result.values[str(n)]["up"])

    def test_17_tiny_exact_sign(self):
        tiny=F(1,10**30)
        self.assertTrue(g1(history([F(100)]*89+[F(100)+tiny])).passed)
        self.assertEqual(g1(history([F(100)]*89+[F(100)-tiny])).state,"REJECT")

    def test_18_independent_ma_equation(self):
        values=[F(100)+F(i*i,13) for i in range(90)]
        result=g1(history(values))
        for n in (5,15,25,75):
            independent=(sum(values[-n:])-sum(values[-n-1:-1]))/n
            self.assertEqual(independent,(values[-1]-values[-n-1])/n)
            self.assertEqual(result.values[str(n)]["delta"],independent)

    def test_19_perfect_order_not_required(self):
        values=[150]*65+[160]*15+[130]*9+[180]
        r=g1(history(values))
        self.assertTrue(r.passed);self.assertLess(r.values["5"]["sma"],r.values["15"]["sma"])

    def test_20_unknown_not_flat(self):
        rows=history();rows[-76]=replace(rows[-76],open=None,high=None,low=None,close=None,status="NO_TRADE")
        r=g1(rows);self.assertEqual(r.state,"UNKNOWN");self.assertIsNone(r.values["75"]["delta"])

    def test_21_cc_exact_minus5(self):
        rows=history([100]*77)
        self.assertIn("DAMAGE_CC",g2(set_last(rows,o=97,c=95)).reasons)
        self.assertNotIn("DAMAGE_CC",g2(set_last(rows,o=97,c=F(95)+F(1,10**20))).reasons)

    def test_22_body_and_gap_independent(self):
        body=g2(set_last(history([98]*77,width=F(4)),o=100,c=95))
        self.assertIn("DAMAGE_BODY",body.reasons);self.assertNotIn("DAMAGE_CC",body.reasons)
        gap=g2(set_last(history([100]*77),o=95,c=100))
        self.assertIn("DAMAGE_GAP",gap.reasons);self.assertNotIn("DAMAGE_BODY",gap.reasons)

    def test_23_exact_three_atr(self):
        rows=history([100]*77,width=F(1))
        self.assertEqual(atr_pre(rows),1)
        self.assertIn("DAMAGE_ATR",g2(set_last(rows,o=97,c=97)).reasons)
        self.assertNotIn("DAMAGE_ATR",g2(set_last(rows,o=97,c=F(97)+F(1,10**20))).reasons)

    def test_24_atr_excludes_t_crash(self):
        rows=history([100]*77)
        rows[-1]=replace(rows[-1],high=F(200),low=F(1),close=F(95))
        self.assertEqual(atr_pre(rows),2)
        wrong=(13*F(2)+F(199))/14
        self.assertNotEqual(atr_pre(rows),wrong)

    def test_25_atr_independent_seed_updates(self):
        rows=history([100]*77)
        for i in range(1,76):rows[i]=replace(rows[i],high=F(100)+F(i,2),low=F(100)-F(i,2))
        expected=sum((F(i) for i in range(1,15)),F())/14
        for i in range(15,76):expected=(13*expected+F(i))/14
        self.assertEqual(atr_pre(rows),expected)

    def test_26_zero_atr_no_drop_vs_drop(self):
        rows=history([100]*77,width=F(0))
        self.assertTrue(g2(rows).passed);self.assertEqual(g2(rows).values["z_loss"],0)
        result=g2(set_last(rows,o=100,c=99))
        self.assertIn("DAMAGE_ATR",result.reasons);self.assertEqual(result.values["atr_zero_reason"],"ATR_ZERO_WITH_POSITIVE_DROP")
        self.assertIsNone(result.values["z_loss"])

    def test_27_gap_recovery_still_rejected(self):
        result=g2(set_last(history([100]*77),o=95,c=F('99.8')))
        self.assertEqual(result.first_reason,"DAMAGE_GAP")

    def test_28_minus4_candle_can_pass(self):
        self.assertTrue(g2(set_last(history([100]*77,width=F(10)),o=100,c=96)).passed)

    def test_29_median_spike_decline(self):
        self.assertEqual(median([F(1),F(2),F(3),F(4)]),F(5,2))
        rows=history([100]*77,va=F(50000000))
        self.assertIn("CAPACITY",g2(set_last(rows,va=500000000)).reasons)
        self.assertIn("CAPACITY",g2(set_last(history([100]*77),va=90000000)).reasons)

    def test_30_capacity_equal_and_above(self):
        rows=history([100]*77,va=F(100000000))
        self.assertTrue(g2(rows).passed)
        self.assertIn("CAPACITY",g2(set_last(rows,va=F(100000000)-1)).reasons)

    def test_31_price_lot_equality(self):
        rows=history([10000]*77)
        self.assertTrue(g2(rows).passed)
        self.assertIn("PRICE_LOT",g2(set_last(rows,c=F(10000)+F(1,1000000))).reasons)

    def test_32_all_and_first_reasons(self):
        result=g2(set_last(history([12000]*77,width=F(1)),o=11000,c=10500,va=10))
        self.assertEqual(result.first_reason,"PRICE_LOT")
        self.assertEqual(result.reasons,("PRICE_LOT","DAMAGE_CC","DAMAGE_GAP","DAMAGE_ATR","CAPACITY"))

    def test_33_exact_up_buckets(self):
        for k in range(1,6):
            l=outcome(up=k);self.assertEqual(l.b,k);self.assertTrue(l.raw_winner[k-1])
            less=label(Candle.from_values(date(2030,3,4),100,F(100+k)-F(1,10**20),99,100))
            self.assertEqual(less.b,k-1)

    def test_34_exact_risk_boundaries(self):
        self.assertEqual(outcome(adverse=3).r,1);self.assertEqual(outcome(adverse=5).r,2)
        l=label(Candle.from_values(date(2030,3,4),100,101,F(97)+F(1,10**20),100))
        self.assertEqual(l.r,0)

    def test_35_raw_bigwinner_and_loser(self):
        l=outcome(up=6,adverse=4)
        self.assertEqual((l.b,l.r),(5,1));self.assertTrue(l.raw_winner[4]);self.assertTrue(l.raw_loser[2]);self.assertFalse(l.clean_winner[4])

    def test_36_r0_b0_not_positive(self):
        l=outcome(up=.4,adverse=.2)
        self.assertEqual((l.r,l.b,l.utility),(0,0,0))

    def test_37_exact_zero_inside_b0(self):
        l=outcome(up=0);self.assertEqual(l.b,0);self.assertTrue(l.exact_zero)

    def test_38_unknown_not_r0_b0(self):
        l=label(Candle.from_values(date(2030,3,4),None,None,None,None,status="NO_TRADE"))
        self.assertIsNone(l.r);self.assertIsNone(l.b);self.assertIsNone(l.utility)

    def test_39_invalid_ohlc_stops(self):
        for args in [(100,99,98,99),(100,102,101,101)]:
            with self.assertRaises(V2Error):Candle.from_values(date(2030,3,4),*args)

    def test_40_same_bar_ambiguous(self):
        d=date(2024,11,5);end,_=phase_times(d)
        b=Bar(end-timedelta(minutes=1),end,Candle.from_values(d,100,106,94,100),"CONTINUOUS",0)
        self.assertEqual(path_first_hit([b],F(100),3,3),"AMBIGUOUS")

    def test_41_past_bar_high_not_reused(self):
        d=date(2024,11,5);end,_=phase_times(d)
        past=Bar(end-timedelta(minutes=2),end-timedelta(minutes=1),Candle.from_values(d,100,120,99,100),"CONTINUOUS",0)
        future=Bar(end-timedelta(minutes=1),end,Candle.from_values(d,100,101,99,100),"CONTINUOUS",1)
        self.assertEqual(remaining_high([past,future],future.start),101)

    def test_42_independent_integer_ratio_recount(self):
        counts=[0]*6
        for j in range(0,700,7):
            o=F(137,10);h=o*F(10000+j,10000)
            l=label(Candle.from_values(date(2030,3,4),o,h,o,o))
            independent=sum(100*h>=(100+k)*o for k in range(1,6))
            self.assertEqual(l.b,independent);counts[independent]+=1
        self.assertEqual(sum(counts),100)

    def test_43_risk_keeps_failures(self):
        fit,_,_=synthetic_factory();known,r0,w,c=partition(fit)
        self.assertEqual(set(fit.risk[known]),{0,1,2});self.assertEqual(int(known.sum()),len(fit.x)-int((fit.risk<0).sum()))

    def test_44_opportunity_r0_including_b0(self):
        fit,_,_=synthetic_factory();known,r0,w,c=partition(fit)
        self.assertTrue(np.all(fit.risk[r0]==0));self.assertEqual(set(fit.opportunity[r0]),set(range(6)))

    def test_45_common_scaling_and_inheritance(self):
        sessions=["a"]*100+["b"]*50
        w,c=common_weights(sessions,[True]*150)
        self.assertEqual(c,75);np.testing.assert_array_equal(w[:100],np.full(100,.75));np.testing.assert_array_equal(w[100:],np.full(50,1.5))
        self.assertEqual(float(w.mean()),1);subset=np.array([0,1,100,102]);np.testing.assert_array_equal(w[subset],[.75,.75,1.5,1.5])

    def test_46_missing_class_fit0(self):
        fit,cal,cert=synthetic_factory();fit.risk[fit.risk==2]=1
        spy=Mock()
        with tempfile.TemporaryDirectory() as t:
            ledger=ExperimentLedger(Path(t)/"ledger",mode="SYNTHETIC");binding={"test":1};ledger.reserve(Path(t)/"run","SYNTHETIC_V2_ENGINEERING",binding)
            with patch("ark_selector_v2.model.confirm_synthetic",return_value=None):
                with self.assertRaisesRegex(V2Error,"INSUFFICIENT_TEACHER_SUPPORT"):fit_synthetic_bundle(fit,cal,cert,ledger,binding,estimator_factory=spy)
            spy.assert_not_called()

    def test_47_estimator_specific_fit_columns(self):
        x=np.array([[1,1,np.nan],[2,1,np.nan],[3,2,np.nan],[4,2,np.nan]],dtype=np.float64)
        allc,_=used_columns(x);subset,_=used_columns(x[:2])
        self.assertEqual(allc,(0,1));self.assertEqual(subset,(0,))

    def test_48_cal_cannot_choose_columns(self):
        x=np.array([[1,2],[2,3]],dtype=np.float64);cols,_=used_columns(x)
        cal=np.array([[9,np.nan],[10,np.nan]],dtype=np.float64)
        with self.assertRaisesRegex(V2Error,"FEATURE_SUPPORT_SHIFT"):check_cal_support(cal,cols)
        self.assertEqual(cols,(0,1))

    def test_49_wrong_model_class_order(self):
        from ark_selector_v2.model import MODEL_PARAMS
        receipt={"code_hash":code_hash(),"schema_hash":digest(registry()),"config_hash":configuration_hash()}
        dummy=Temperature(1,0,0,1,1,"TEST")
        bundle=ModelBundle(SimpleNamespace(classes_=np.array([1,0,2])),SimpleNamespace(classes_=np.arange(6)),(0,),(0,),dummy,dummy,receipt)
        with self.assertRaisesRegex(V2Error,"CLASS_ORDER"):bundle.validate_identity()

    def test_50_joint_inclusion_and_example_h(self):
        q,p3,p5=joint(np.array([[.96,.035,.005]]),np.array([[.20,.10,.10,.15,.15,.30]]))
        np.testing.assert_allclose(q[0],[.768,.672,.576,.432,.288],atol=1e-15)
        self.assertAlmostEqual(float(q.sum()),2.736);self.assertAlmostEqual(float(p3[0]),.04);self.assertAlmostEqual(float(p5[0]),.005)
        self.assertTrue(np.all(np.diff(q,axis=1)<=0))

    def test_51_beta_one_and_independent_softmax(self):
        p=np.array([[.2,.3,.5]])
        np.testing.assert_allclose(temperature(p,1),p,atol=1e-15)
        expected=p**.7/(p**.7).sum(axis=1,keepdims=True)
        np.testing.assert_allclose(temperature(p,.7),expected,atol=1e-15)

    def test_52_calibration_failure_bounds_flat(self):
        p=np.array([[.8,.1,.1],[.2,.3,.5]]);y=np.array([0,2]);w=np.ones(2)
        for result in (SimpleNamespace(x=1,fun=1,success=False),SimpleNamespace(x=20,fun=1,success=True),SimpleNamespace(x=float('nan'),fun=1,success=True)):
            with self.assertRaisesRegex(V2Error,"CALIBRATION_REVIEW_REQUIRED"):fit_temperature(p,y,w,optimizer=Mock(return_value=result))
        with self.assertRaisesRegex(V2Error,"FLAT"):fit_temperature(np.full((2,3),1/3),y,w)

    def test_53_calibration_never_estimator_fit(self):
        p=np.array([[.8,.1,.1],[.2,.3,.5]]);y=np.array([0,2]);w=np.ones(2)
        optimizer=Mock(return_value=SimpleNamespace(x=1,fun=1,success=True,nfev=1))
        with patch('sklearn.ensemble.HistGradientBoostingClassifier.fit') as spy:
            fit_temperature(p,y,w,optimizer=optimizer);spy.assert_not_called()
        self.assertEqual(optimizer.call_count,1)

    def test_54_budget_2fit_2cal_no_retry(self):
        with tempfile.TemporaryDirectory() as t:
            ledger=ExperimentLedger(Path(t)/"ledger",mode="SYNTHETIC");binding={"code":H};ledger.reserve(Path(t)/"run","C",binding)
            for event in EVENTS[1:9]:ledger.append(event,"C",binding)
            rows=ledger.rows();self.assertEqual(sum(r['event'].endswith('FIT_STARTED') for r in rows),2);self.assertEqual(sum(r['event'].endswith('CAL_STARTED') for r in rows),2)
            with self.assertRaisesRegex(V2Error,"NO_RETRY"):ledger.append("RISK_FIT_STARTED","C",binding)

    def test_55_selection_thresholds_and_ties(self):
        self.assertTrue(qualified([.5,.4,.3,.2,.1],.05,.01))
        self.assertFalse(qualified([np.nextafter(.5,0),.4,.3,.2,.1],.05,.01))
        rows=[candidate("0003"),candidate("0002",[.5,.375,.375,.375,.375]),candidate("0001",[.5,.375,.375,.375,.375])]
        self.assertEqual([r["canonical_symbol"] for r in rank_candidates(rows)],["0001","0002","0003"])

    def test_56_0_2_15_and_duplicate(self):
        for n in (0,2,15,16):self.assertEqual(len(rank_candidates([candidate(f'{i:04d}') for i in range(n)])),min(15,n))
        with self.assertRaises(V2Error):rank_candidates([candidate(),candidate()])

    def test_57_unknown_labels_cannot_replace_selection(self):
        rows=[candidate("0002"),candidate("0001")];before=rank_candidates(rows)
        labels={"0001":None,"0002":outcome(5)}
        self.assertEqual(rank_candidates(rows),before)
        with self.assertRaises(V2Error):rank_candidates([{**rows[0],"label":labels["0002"]}])

    def test_58_zero_day_in_supply_denominator(self):
        key=("2030-03-04","0001","PRIME")
        result=summarize(["2030-03-04","2030-03-05"],[key],{key:outcome(5)})
        self.assertEqual(result["zero_candidate_days"],1);self.assertEqual(result["clean_winner_per_all_session"][4],.5)

    def test_59_unknown_worst_case_loser(self):
        keys=[("2030-03-04",f'{i:04d}',"PRIME") for i in range(10)]
        result=summarize(["2030-03-04"],keys,{k:outcome(2) for k in keys[:8]})
        self.assertEqual(result["loser_known_rates"][2],0);self.assertEqual(result["loser_unknown_worst_upper_rates"][2],.2)
        self.assertFalse(result["POINT_TARGETS_MET"])

    def test_60_capture_and_zero_denominator(self):
        keys={("2030-03-04",str(i),"PRIME") for i in range(3)};one={sorted(keys)[0]}
        labels={k:outcome(5) for k in keys}
        result=capture({"g0":keys,"g2":one,"selected":one},labels)
        self.assertEqual(result["5"]["GateRetention"],1/3);self.assertEqual(result["5"]["ModelCapture"],1)
        empty=capture({"g0":set(),"g2":set(),"selected":set()},{})
        self.assertIsNone(empty["5"]["GateRetention"])

    def test_61_fit_oracle_upper_stops_fit0(self):
        sessions=[f'{i:03d}' for i in range(120)]
        with patch('sklearn.ensemble.HistGradientBoostingClassifier.fit') as spy:
            with self.assertRaisesRegex(V2Error,"ORACLE_SUPPLY_FIT0"):oracle_supply(sessions,{sessions[0]:(20,20)})
            spy.assert_not_called()

    def test_62_phase_change_all_windows(self):
        for d in (date(2024,11,1),date(2024,11,5)):
            end,auction=phase_times(d)
            for n in (1,5,15,30,60):
                self.assertTrue(tick_in_window(end-timedelta(minutes=n),d,n,"CONTINUOUS"))
                self.assertFalse(tick_in_window(end,d,n,"CONTINUOUS"));self.assertFalse(tick_in_window(auction,d,n,"AUCTION"))
            with self.assertRaisesRegex(V2Error,"PHASE_UNKNOWN"):tick_in_window(end,d,30,"UNKNOWN")

    def test_63_no_trade_zero_vs_missing(self):
        d=date(2024,11,5)
        complete=Coverage(True,True,True,True,H,"COMPLETE");missing=Coverage(False,False,False,False,H,"SOURCE_NOT_JOINED")
        zero=tick_features([],d,complete);unknown=tick_features([],d,missing)
        self.assertEqual(zero.values["v2_tick_count30"],0);self.assertEqual(zero.values["v2_tick_volume30"],0)
        self.assertIsNone(zero.values["v2_tick_vwap_distance30"]);self.assertIsNone(unknown.values["v2_tick_count30"])

    def test_64_equal_timestamp_distinct_transactions(self):
        d=date(2024,11,5);end,_=phase_times(d)
        a=Tick(end-timedelta(seconds=10),F(100),F(1),0,"TX_A","CONTINUOUS")
        b=replace(a,ordinal=1,transaction_id="TX_B")
        self.assertEqual(len(ordered_ticks([a,b])),2)
        with self.assertRaisesRegex(V2Error,"DUPLICATE_TICK"):ordered_ticks([a,replace(b,transaction_id="TX_A")])

    def test_65_forbidden_descriptor_no_open(self):
        adm=Admission(Mode.MARKET,H,"FIT_TEACHER",frozenset({"2030-03-04"}),H,"C")
        d={"role":"FIT","purpose":"FIT_TEACHER","session":"2030-03-04","source_sha256":H,"bytes":0,"protected":False,"path":"never"}
        opener=Mock()
        with self.assertRaisesRegex(V2Error,"FORBIDDEN_DESCRIPTOR"):admitted_open([d,{**d,"role":"FINAL"}],permitted_roles={"FIT","CAL"},admission=adm,opener=opener)
        opener.assert_not_called()

    def test_66_fake_approval_and_sealed_dates(self):
        req={"schema":"ARK_SELECTOR_V2_OWNER_APPROVAL_V1","design_id":"ARK_PREOPEN_V2_TREND_CONTINUATION_CASCADE","candidate_id":"PREOPEN_V2_TC_C01","mode":Mode.MARKET.value,"owner_evidence_reference":"self","owner_evidence_sha256":H,"owner_approved_at":"2026-01-01T00:00:00+09:00","parent_approval_sha256":H,"purpose":"FIT_TEACHER","manifest_sha256":H,"precommit_sha256":H,"exact_session_allowlists":{"FIT_TEACHER":["2024-10-01"]},"budget":{"candidates":1,"base_fits":2,"calibration_optimizations":2},**{f:False for f in FLAGS}}
        with self.assertRaisesRegex(V2Error,"SELF_DECLARED"):validate_approval(req,ApprovalPins(),purpose="FIT_TEACHER",mode=Mode.MARKET,manifest_hash=H)
        adm=Admission(Mode.MARKET,H,"FIT_TEACHER",frozenset({"2024-10-01"}),H,"C")
        desc={"role":"FIT","purpose":"FIT_TEACHER","session":"2024-10-01","source_sha256":H,"bytes":0,"protected":True,"path":"never"}
        opener=Mock()
        with self.assertRaisesRegex(V2Error,"PROTECTED"):admitted_open([desc],permitted_roles={"FIT"},admission=adm,opener=opener)
        opener.assert_not_called()

    def test_67_no_artifact_or_ledger_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"sealed";exclusive_bytes(p,b"original")
            with self.assertRaises(FileExistsError):exclusive_bytes(p,b"changed")
            self.assertEqual(p.read_bytes(),b"original")
            ledger=ExperimentLedger(Path(t)/"ledger",mode="SYNTHETIC");ledger.reserve(Path(t)/"run","C",{})
            with self.assertRaises(FileExistsError):ledger.reserve(Path(t)/"run","C",{})

    def test_68_untrusted_pickle_refused_before_load(self):
        with patch('joblib.load') as spy:
            with self.assertRaisesRegex(V2Error,"UNTRUSTED_PICKLE"):load_model(Path("never-open"),trusted=None,independently_pinned_receipts=frozenset({H}))
            spy.assert_not_called()

    def test_69_restore_traversal_symlink_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"out"
            with self.assertRaisesRegex(V2Error,"PATH_TRAVERSAL"):safe_path(root,"../escape")
            root.mkdir();(root/"link").symlink_to(Path(t),target_is_directory=True)
            with self.assertRaisesRegex(V2Error,"SYMLINK_ESCAPE"):safe_path(root,"link/escape")
            z=Path(t)/"bad.zip"
            with zipfile.ZipFile(z,'w') as f:f.writestr('x',b'changed')
            with self.assertRaisesRegex(V2Error,"ENTRY_HASH_MISMATCH"):restore_zip(z,Path(t)/"restored",{"x":{"bytes":7,"sha256":H}},archive_hash=sha_file(z)[0],max_bytes=100)

    def test_70_all_false_flags_header_and_item(self):
        for field in FLAGS:
            w=watch();w[field]=True
            with self.assertRaises(V2Error):validate_watchlist(w)
            w=watch();del w["items"][0][field]
            with self.assertRaises(V2Error):validate_watchlist(w)

    def test_71_sealed_forecast_and_code_drift(self):
        w=watch();w["items"][0]["q"][0]=.6
        with self.assertRaises(V2Error):validate_watchlist(w)
        from ark_selector_v2.model import MODEL_PARAMS
        dummy=Temperature(1,0,0,1,1,"TEST")
        bundle=ModelBundle(None,None,(),(),dummy,dummy,{"code_hash":"b"*64,"schema_hash":digest(registry()),"config_hash":digest(MODEL_PARAMS)})
        with self.assertRaisesRegex(V2Error,"NO_REFIT"):bundle.validate_identity()

    def test_72_v1_frozen_whole_tree_unchanged(self):
        result=audit_repo(ROOT.parents[1],"4b02c4eb6fed0b75bfc7a6e8afc49d7868696159")
        self.assertEqual(result["status"],"PASS");self.assertTrue(result["protected_tree_unchanged"])


if __name__=="__main__":unittest.main()
