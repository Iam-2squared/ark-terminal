import copy, datetime as dt, json, subprocess, unittest
import numpy as np
import pandas as pd
from scripts import phase57_selector_path_anatomy as m

def path(date='2024-11-06',time='09:30',n=60):
    start=m.old.timestamp(f'{date}T{time}:00+09:00');end=start.replace(hour=15,minute=30 if date>='2024-11-05' else 0)
    bars=[]
    for i,t in enumerate(m.regular_slots(start,end)[:n]):
        bars.append({'start':t.isoformat(),'end':(t+dt.timedelta(minutes=5)).isoformat(),'missing':False,'o':0,'h':2,'l':-1,'c':1,'observedMinutes':5})
    return {'selectorEventId':f'{date}|{time}|TEST','sessionDate':date,'symbol':'TEST','decisionTimestamp':start.isoformat(),'decisionPrice':100,'future':bars}

class Anatomy(unittest.TestCase):
    def test_protocol_safety_and_pins(self):m.protocol()
    def test_exact_horizon_and_zero(self):
        e=m.evaluate(path());self.assertEqual(e['outcomes']['0'],{'status':'REFERENCE_ONLY','gross':0});self.assertEqual(e['outcomes']['120']['barCount'],24)
    def test_excursions_ties_order_and_giveback(self):
        r=m.evaluate(path())['outcomes']['30'];self.assertAlmostEqual(r['MFE'],2);self.assertAlmostEqual(r['MAE'],-1);self.assertAlmostEqual(r['giveback'],1);self.assertEqual(r['peakInterval'],[0,5]);self.assertEqual(r['ordering'],'UNKNOWN_INTRABAR_ORDER')
    def test_entry_open_not_decision(self):
        p=path();p['future'][0].update(o=1);r=m.evaluate(p)['outcomes']['5'];self.assertAlmostEqual(r['gross'],0);self.assertAlmostEqual(r['MFE'],100*(102/101-1))
    def test_missing_start_no_skip(self):
        p=path();p['future'][0]['missing']=True;self.assertEqual(m.evaluate(p)['outcomes']['30']['status'],'FIRST_ELIGIBLE_BAR_MISSING')
    def test_missing_middle_fails_closed(self):
        p=path();p['future'][2]['missing']=True;e=m.evaluate(p);self.assertEqual(e['outcomes']['10']['status'],'AVAILABLE');self.assertEqual(e['outcomes']['30']['status'],'INCOMPLETE_PATH')
    def test_absent_slot_not_interpolated(self):
        p=path();del p['future'][0];self.assertEqual(m.evaluate(p)['outcomes']['30']['status'],'INCOMPLETE_PATH')
    def test_lunch_and_session_end(self):
        e=m.evaluate(path(time='11:00'));self.assertEqual(e['outcomes']['30']['status'],'AVAILABLE');self.assertEqual(e['outcomes']['60']['status'],'LUNCH_BREAK');self.assertEqual(e['outcomes']['SESSION_END']['barCount'],42)
    def test_old_close(self):
        e=m.evaluate(path(date='2024-11-01',time='14:30'));self.assertEqual(e['outcomes']['SESSION_END']['elapsedMinutes'],30);self.assertEqual(e['outcomes']['60']['status'],'SESSION_END')
    def test_zero_excursion_has_no_timing(self):
        p=path();[b.update(o=0,h=0,l=0,c=0) for b in p['future']];r=m.evaluate(p)['outcomes']['30'];self.assertIsNone(r['peakInterval']);self.assertIsNone(r['troughInterval'])
    def test_threshold_first_hit_and_sparse(self):
        p=path();p['future'][1].update(h=5,observedMinutes=2);r=m.evaluate(p)['outcomes']['30'];self.assertEqual(r['firstHitIntervals']['5'],[5,10]);self.assertEqual(r['sparseBars'],1)
    def test_common_identity_and_pair_full5(self):
        events={};a=[];b=[]
        for arm,ids in [('a',a),('b',b)]:
            for i in range(5):
                p=path();p['selectorEventId']=arm+str(i);events[p['selectorEventId']]=m.evaluate(p);ids.append(p['selectorEventId'])
        self.assertEqual(m.common_ids(events,a,120),a);self.assertEqual(len(m.matched_ids(events,a,b)[0]),5)
        events[b[-1]]['outcomes']['120']={'status':'INCOMPLETE_PATH'}
        self.assertEqual(len(m.matched_ids(events,m.common_ids(events,a,120),m.common_ids(events,b,120))[0]),0)
    def test_null_parity(self):
        e=m.evaluate(path());events={e['selectorEventId']:e};ids=list(events)*5
        r=m.pair(events,ids,ids,30);self.assertAlmostEqual(r['differences']['net']['sessionEqualMean'],0)
    def test_tail_excludes_only_positive(self):
        rows=[{'net':v,'selectorEventId':str(i),'sessionDate':'s'} for i,v in enumerate([-3,-2,-1,0,10])];r=m.tails(rows);self.assertEqual(r['top1Excluded']['removedN'],1);self.assertEqual(r['top5Excluded']['remaining']['mean'],-1.5)
    def test_cluster_not_row_bootstrap(self):
        r=m.cluster({'a':0,'b':1,'c':2},7);self.assertEqual(r,m.cluster({'a':0,'b':1,'c':2},7));self.assertEqual(r['clusters'],3);self.assertLessEqual(r['simultaneousCI95'][0],r['clusterCI95'][0])
    def test_pit_ranks_future_invariance(self):
        f=pd.DataFrame({'savedV1Score':[1,2,3,3],'decisionVolatilityPct':[1,2,3,np.nan],'future':[0,1,2,3]});a=m.pit_ranks(f);f.future=[100,-100,5,6];b=m.pit_ranks(f);self.assertEqual(a.scoreDecile.tolist(),b.scoreDecile.tolist());self.assertEqual(a.volatilityStratum.tolist(),['LOW','MID','HIGH','UNKNOWN'])
    def test_price_decimal_bands(self):
        self.assertEqual(m.band(100),'(75,100]');self.assertEqual(m.band(100.01),'(100,200]');self.assertEqual(m.band(75.1),'(75,100]')
    def test_future_change_preserves_earlier_outcome(self):
        p=path();a=m.evaluate(p);p['future'][12]['h']=20;b=m.evaluate(p);self.assertEqual(a['outcomes']['30'],b['outcomes']['30'])
    def test_post_peak_excludes_earlier_endpoints(self):
        p=path();p['future'][20]['h']=6;e=m.evaluate(p);out=m.translation({e['selectorEventId']:e},[e['selectorEventId']]);self.assertEqual(out['winner5']['horizons']['30']['postFullDayPeakGiveback']['n'],0);self.assertEqual(out['winner5']['horizons']['120']['postFullDayPeakGiveback']['n'],1)
    def test_score_projector_python_parity(self):
        p=path();code="import {scoreWindow} from './scripts/phase57_selector_path_scores.mjs'; const map=new Map();for(let m=570;m<690;m+=5)map.set(m,{open:100,high:102,low:99,close:101,availableAtJst:'2024-11-06T'+String(Math.floor((m+5)/60)).padStart(2,'0')+':'+String((m+5)%60).padStart(2,'0')+':00+09:00'}); console.log(JSON.stringify([scoreWindow(map,570,120,'2024-11-06'),scoreWindow(map,660,60,'2024-11-06')]));"
        a,b=json.loads(subprocess.check_output(['node','--input-type=module','-e',code],cwd=m.ROOT));self.assertIsNone(b);r=m.evaluate(p)['outcomes']['120'];self.assertAlmostEqual(a['gross'],r['gross']);self.assertAlmostEqual(a['MFE'],r['MFE']);self.assertAlmostEqual(a['MAE'],r['MAE'])
if __name__=='__main__':unittest.main()
