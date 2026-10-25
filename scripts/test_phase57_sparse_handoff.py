import copy
import datetime as dt
import json
import os
import tempfile
from pathlib import Path
import unittest
import numpy as np
from scripts import phase57_behavior_reader_v2 as r
from scripts import phase57_sparse_handoff as s

class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.day='2025-08-25'
        self.cal=[(dt.date(2025,8,10)+dt.timedelta(days=n)).isoformat() for n in range(16)]
        self.previous={'Date':self.cal[-2],'Code':'10000','O':100.,'H':102.,'L':98.,'C':100.,'Vo':10.,'Va':1000.}
        self.hist=[{'daily':{**self.previous,'Date':d},'tr':.01,'barValue':{t:5000. for t in range(545,926,5)},'barVolumes':{t:50. for t in range(545,926,5)}} for d in self.cal[-11:-1]]
    def rows(self,end=570,start=540):
        return [{'Date':self.day,'Code':'10000','Time':'%02d:%02d'%divmod(t,60),'O':100.,'H':101.,'L':99.,'C':100.,'Vo':10.,'Va':1000.} for t in range(start,end) if 540<=t<690 or 750<=t<925]
    def context(self,at=570,rows=None,**kw):
        return r.context(self.day,at,self.rows(at) if rows is None else rows,kw.get('previous',self.previous),kw.get('history',self.hist),kw.get('calendar',self.cal),kw.get('personality'))
    def test_history_adapter(self):
        h=r.history_adapter(self.hist,self.day);self.assertEqual(h[-1]['session'],self.cal[-2]);self.assertEqual(h[-1]['barValues'][570],5000.)
    def test_adapter_roundtrip(self):
        a=r.history_adapter(self.hist,self.day);self.assertEqual(r.history_adapter(a,self.day),a)
    def test_bad_history(self):
        for h in [[{}],self.hist+self.hist[-1:],list(reversed(self.hist))]:
            with self.assertRaises(ValueError):r.history_adapter(h,self.day)
    def test_future_history(self):
        with self.assertRaises(ValueError):r.history_adapter([{'session':self.day}],self.day)
    def test_adapter_ambiguous(self):
        h=copy.deepcopy(self.hist);h[0]['barValues']={}
        with self.assertRaises(ValueError):r.history_adapter(h,self.day)
    def test_fresh_closed_bar(self):
        x=self.context();self.assertEqual(x['status'],'RESEARCH_CONTEXT_AVAILABLE');self.assertEqual(x['lastCompletedBar'],570);self.assertEqual(x['stalenessMinutes'],0)
    def test_four_minutes_allowed(self):
        self.assertEqual(self.context(574)['stalenessMinutes'],4)
    def test_five_minutes_old_not_allowed(self):
        self.assertEqual(self.context(575,self.rows(570))['missingReason'],'MISSING_CURRENT_BAR')
    def test_missing_last_minute(self):
        self.assertEqual(self.context(rows=self.rows()[:-1])['status'],'UNAVAILABLE')
    def test_missing_internal_minute(self):
        rows=self.rows();del rows[-3];self.assertEqual(self.context(rows=rows)['status'],'UNAVAILABLE')
    def test_future_poison_rejected(self):
        with self.assertRaises(ValueError):self.context(rows=self.rows(571))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):self.context(rows=self.rows()+self.rows()[-1:])
    def test_unsorted_rejected(self):
        with self.assertRaises(ValueError):self.context(rows=list(reversed(self.rows())))
    def test_mixed_security(self):
        rows=self.rows();rows[0]['Code']='OTHER'
        with self.assertRaises(ValueError):self.context(rows=rows)
    def test_previous_security_mismatch(self):
        with self.assertRaises(ValueError):self.context(previous={**self.previous,'Code':'OTHER'})
    def test_wrong_previous_day(self):
        self.assertEqual(self.context(previous={**self.previous,'Date':self.cal[-3]})['status'],'UNAVAILABLE')
    def test_stale_history(self):
        self.assertEqual(self.context(history=self.hist[:-1])['missingReason'],'HISTORY_NOT_CURRENT')
    def test_scale_missing(self):
        self.assertEqual(self.context(history=self.hist[-2:])['status'],'UNAVAILABLE')
    def test_corporate_action(self):
        self.assertEqual(self.context(previous={**self.previous,'AdjFactor':.5})['status'],'UNAVAILABLE')
    def test_session_boundaries(self):
        for minute in [540,544,691,720,750,754,926,930]:self.assertEqual(self.context(minute)['status'],'UNAVAILABLE')
        for minute in [545,690,755,925]:self.assertEqual(self.context(minute)['status'],'RESEARCH_CONTEXT_AVAILABLE')
    def test_morning_not_afternoon(self):
        self.assertEqual(self.context(755,self.rows(690))['status'],'UNAVAILABLE')
    def test_missing_morning_vwap_null(self):
        x=self.context(755,self.rows(755,750));self.assertEqual(x['status'],'RESEARCH_CONTEXT_AVAILABLE');self.assertIsNone(x['features']['cumulative_vwap'])
    def test_vwap_and_opening_range(self):
        f=self.context()['features'];self.assertEqual(f['cumulative_vwap'],100);self.assertEqual(f['opening_range_high'],101);self.assertEqual(f['rvol_volume'],1);self.assertEqual(f['rvol_trading_value'],1)
    def test_opening_range_unconfirmed(self):
        self.assertIsNone(self.context(565)['features']['opening_range_high'])
    def test_no_rvol_zero_fill(self):
        h=copy.deepcopy(self.hist)
        for row in h:row['barValue']={};row['barVolumes']={}
        f=self.context(history=h)['features'];self.assertIsNone(f['rvol_volume']);self.assertIsNone(f['rvol_trading_value'])
    def test_pre_change_close(self):
        day='2024-11-01';prev={**self.previous,'Date':'2024-10-31'};hist=[{**h,'daily':{**h['daily'],'Date':f'2024-10-{22+i:02d}'}} for i,h in enumerate(self.hist)]
        rows=[{**x,'Date':day} for x in self.rows(900)]
        x=r.context(day,900,rows,prev,hist,[h['daily']['Date'] for h in hist]+[day]);self.assertEqual(x['status'],'RESEARCH_CONTEXT_AVAILABLE')
        self.assertEqual(r.context(day,905,rows,prev,hist,[day])['status'],'UNAVAILABLE')
    def test_price_scale_invariance(self):
        base=self.context();rows=copy.deepcopy(self.rows());prev=copy.deepcopy(self.previous);hist=copy.deepcopy(self.hist)
        for row in rows+[prev]+[h['daily'] for h in hist]:
            for key in ['O','H','L','C','Va']:row[key]*=10
        for h in hist:h['barValue']={k:x*10 for k,x in h['barValue'].items()}
        x=self.context(rows=rows,previous=prev,history=hist)
        for key in ['body_s','range_s','close_pdh_s','rvol_trading_value']:self.assertAlmostEqual(x['features'][key],base['features'][key])
    def test_forming_five_minute_not_used(self):
        a=self.context(573);rows=self.rows(573)
        for row in rows[-3:]:row.update(O=900.,H=999.,L=800.,C=900.)
        b=self.context(573,rows);self.assertEqual(a['features'],b['features'])

class PullbackTests(unittest.TestCase):
    def bars(self,values,start=545):return [{'t':start+5*i,'C':x} for i,x in enumerate(values)]
    def test_up_down_pair_confirmed(self):
        ev=r.pullback_events(self.bars([100,101,102,101,100.5,101.5]),1)
        self.assertEqual(len(ev),1);self.assertEqual(ev[0]['value'],.75);self.assertEqual(ev[0]['availableAt'],570)
    def test_no_terminal_unconfirmed(self):self.assertEqual(r.pullback_events(self.bars([100,101,102,101,100.5]),1),[])
    def test_lunch_not_paired(self):
        bars=self.bars([100,102,101],675)+self.bars([101,99,100],755)
        self.assertEqual(r.pullback_events(bars,1),[])
    def test_missing_not_paired(self):
        bars=self.bars([100,102,101])+self.bars([101,99,100],565)
        self.assertEqual(r.pullback_events(bars,1),[])
    def test_above_one_not_clipped(self):
        ev=r.pullback_events(self.bars([100,101,100,99,100]),1);self.assertEqual(ev[0]['value'],2)
    def test_future_extension_cannot_change_events(self):
        a=self.bars([100,101,102,101,100.5,101.5]);ev=r.pullback_events(a,1)
        self.assertEqual(ev,[x for x in r.pullback_events(a+self.bars([103,105,104],575),1) if x['availableAt']<=570])

class SparseTests(unittest.TestCase):
    def profile(self):
        at='2025-08-22T15:30:00+09:00'
        cell={'symbol':'10000','trait_id':'test','computedThrough':at,'peerArtifactThrough':at,'normalizationThrough':at,'referenceScaleThrough':at,'definitionHash':'fixed','globalStatus':'USABLE','sampleConfidence':'HIGH','temporalReliability':{'status':'PASS'},'drift':False,'identityStatus':'DATED_MASTER_CODE_RESEARCH_ONLY'}
        return {'symbol':'10000','asOf':at,'researchOnly':True,'traits':[cell]}
    def test_dispatch(self):self.assertEqual(len(r.dispatch(self.profile(),'2025-08-25T09:05:00+09:00')),1)
    def test_sample_not_temporal(self):
        p=self.profile();p['traits'][0]['temporalReliability']['status']='INSUFFICIENT';self.assertEqual(r.dispatch(p,'2025-08-25T09:05:00+09:00'),[])
    def test_watch_never_dispatch(self):
        p=self.profile();p['traits'][0]['globalStatus']='WATCH';self.assertEqual(r.dispatch(p,'2025-08-25T09:05:00+09:00'),[])
    def test_low_never_dispatch(self):
        p=self.profile();p['traits'][0]['sampleConfidence']='LOW';self.assertEqual(r.dispatch(p,'2025-08-25T09:05:00+09:00'),[])
    def test_drift_never_dispatch(self):
        p=self.profile();p['traits'][0]['drift']=True;self.assertEqual(r.dispatch(p,'2025-08-25T09:05:00+09:00'),[])
    def test_equal_or_future_asof_rejected(self):
        for t in ['2025-08-22T15:30:00+09:00','2025-08-21T15:30:00+09:00']:
            with self.assertRaises(ValueError):r.dispatch(self.profile(),t)
    def test_mixed_asof_rejected(self):
        p=self.profile();p['traits'][0]['normalizationThrough']='2025-08-23T15:30:00+09:00'
        with self.assertRaises(ValueError):r.dispatch(p,'2025-08-25T09:05:00+09:00')
    def test_naive_timezone_rejected(self):
        with self.assertRaises(ValueError):r.dispatch(self.profile(),'2025-08-25T09:05:00')
    def test_research_namespace_required(self):
        p=self.profile();p['researchOnly']=False
        with self.assertRaises(ValueError):r.dispatch(p,'2025-08-25T09:05:00+09:00')
    def test_three_folds_required(self):
        p=s.read(s.BASE/'protocol.json')['temporalPolicy'];self.assertEqual(s.temporal_summary([{'eligible':False}],p)['status'],'INSUFFICIENT')
    def test_temporal_pass_and_failure(self):
        p=s.read(s.BASE/'protocol.json')['temporalPolicy'];good=[{'eligible':True,'x':x,'y':x,'posteriorChange':0} for x in [-1,.2,1]]
        self.assertEqual(s.temporal_summary(good,p)['status'],'PASS')
        for q in good:q['y']=-q['x']
        self.assertEqual(s.temporal_summary(good,p)['status'],'FAIL')
    def test_unidentifiable_calibration_fails(self):
        p=s.read(s.BASE/'protocol.json')['temporalPolicy'];rows=[{'eligible':True,'x':1,'y':1,'posteriorChange':0}]*3
        self.assertEqual(s.temporal_summary(rows,p)['status'],'FAIL')
    def test_calendar_embargo(self):
        p=s.admission.plan();cal=s.calendar();fs=s.folds(cal,p)
        self.assertEqual(len(fs),3)
        for f in fs:self.assertGreater(f['test'][0],f['end']+5);self.assertLess(max(f['train']),min(f['test']))
    def test_mapping_asof(self):
        fs=s.folds(s.calendar(),s.admission.plan())
        self.assertFalse(s.calibration_available(fs[0]['testEnd'],fs[1]['anchor']))
        self.assertTrue(s.calibration_available(fs[0]['testEnd'],fs[2]['anchor']))
    def test_causal_fit_ignores_future_poison(self):
        rng=np.random.default_rng(8);data=rng.normal(size=(90,150));cov=rng.normal(size=(90,150,4));eligible=np.ones((90,150),bool);item={'id':'x','transform':'identity'};ix=np.arange(60)
        a=s.snapshot(data,cov,eligible,item,ix);data[60:]=1e10;cov[60:]=-1e10;b=s.snapshot(data,cov,eligible,item,ix)
        np.testing.assert_equal(a['post'],b['post']);np.testing.assert_equal(a['fit']['beta'],b['fit']['beta'])
    def test_sample_reference_not_frozen_future(self):
        self.assertIn('recomputed only',s.read(s.BASE/'protocol.json')['sampleConfidence'])
    def test_old_sources_unchanged(self):s.invariants()
    def test_synthetic_end_to_end_regeneration(self):
        # Entire evaluation/serialization path, synthetic values only; never real payloads.
        p=s.admission.plan();allowed=set(p['dailyDevelopment'])|set(p['intradayDevelopment']);days=[d for d in s.calendar() if min(allowed)<=d<=max(allowed)];n=105;nt=len(days)
        rng=np.random.default_rng(12);codes=[str(10000+i) for i in range(n)];catalog=s.targets()
        ts={'daily':[next(x for x in catalog['daily'] if x['id']=='amihud')],'intraday':[catalog['intraday'][-1]]}
        daily=rng.lognormal(-20,.1,(nt,n,1));minute=rng.uniform(.5,1.5,(nt,n,1));cov=rng.normal(size=(nt,n,4));eligible=np.ones((nt,n,2),bool)
        for i,d in enumerate(days):
            if d not in allowed:daily[i]=np.nan;cov[i]=np.nan;eligible[i]=False
            if d not in p['intradayDevelopment']:minute[i]=np.nan;eligible[i,:,1]=False
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);matrix=root/'matrix';matrix.mkdir()
            np.savez_compressed(matrix/'matrix.npz',daily=daily,intraday=minute,cov=cov,intraCoverage=np.ones((nt,n)),eligible=eligible,eventcounts=np.zeros((nt,n),int))
            s.write(matrix/'metadata.json',{'sessions':days,'codes':codes,'targets':ts,'lastMaster':codes,'hashes':s.invariants(),'readerCounts':{},'readerExamples':[],'eventExamples':[],'inputLedger':[],'excludedNoPayloadRead':[]})
            s.gzwrite(matrix/'pullback-comparison.json.gz',[])
            s.evaluate(matrix,root/'a');s.evaluate(matrix,root/'b')
            self.assertEqual((root/'a/manifest.json').read_bytes(),(root/'b/manifest.json').read_bytes())
            for profile in s.read(root/'a/06_sparse_profiles.json.gz'):
                self.assertTrue(r.validate_snapshot(profile,days[-1]+'T15:31:00+09:00'))

if __name__=='__main__':unittest.main()
