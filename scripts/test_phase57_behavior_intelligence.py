"""Regression for causal boundaries, denominator integrity and absent-trait safety."""
import copy,unittest
from unittest.mock import patch
import numpy as np
from scripts import phase57_behavior_intelligence as b

class BehaviorTests(unittest.TestCase):
    def rows(self,n=5):
        return [{'member':{'selectorEventId':str(i),'decisionTimestamp':'2024-11-20T10:00:00+09:00','sessionDate':'2024-11-20','symbol':str(i)},'WHO':[{'availability':'UNAVAILABLE'}]} for i in range(n)]
    def history(self):
        return [{'session':f'2024-11-{i:02d}','daily':{'Date':f'2024-11-{i:02d}','Code':'11110','O':100,'H':103,'L':98,'C':101,'Vo':10,'Va':1000},'tr':.03,'barValues':{},'barVolumes':{}} for i in range(11,17)]
    def test_unavailable_never_drops_who(self):
        rows=self.rows();keep,f=b.retain(rows,np.arange(5),.4,'S1');self.assertEqual(keep,set(range(5)));self.assertEqual(f,5)
    def test_allcombined_not_filtered_by_dict(self):
        keep,_=b.retain(self.rows(),[3,1,5,2,4],.8,'S4');self.assertEqual(keep,{0,1,3,4})
    def test_no_outcome_access_ranking(self):
        rows=self.rows();a=b.retain(rows,[2,4,1,5,3],.6,'S2');rows[0]['futureLabel']=100000;self.assertEqual(a,b.retain(rows,[2,4,1,5,3],.6,'S2'))
    def test_stable_ties(self):
        self.assertEqual(b.retain(self.rows(),[1]*5,.4,'S2')[0],{0,1})
    def test_zero_and_missing_preserved(self):
        x={'RECENT':{'features':{'gap':0}}};v=b.feature_vector(x,['RECENT']);self.assertEqual(v['RECENT/gap'],0);self.assertIsNone(v['RECENT/body'])
    def test_unreliable_value_excluded(self):
        cell={'family':'x','value':None,'diagnosticPastOnlyRawValue':999,'sampleConfidence':'LOW','temporalReliability':'FAIL','uncertainty':2,'nEff':10,'coverage':.2}
        row=b.feature_vector({'WHO':[cell]},['WHO']);self.assertIsNone(row['WHO/x/value']);self.assertNotIn(999,row.values());self.assertEqual(row['WHO/x/temporal_FAIL'],1)
    def test_fit_transform_does_not_see_queries(self):
        train=[{'x':float(i),'z':None} for i in range(20)];q=[{'x':3,'z':None}];a,m=b.fit_score(train,q,list(range(20)));c,n=b.fit_score(train,q+[{'x':1e10,'z':999}],list(range(20)));self.assertEqual(m,n);self.assertAlmostEqual(a[0],c[0])
    def test_all_missing_fit_column_no_future_coefficient(self):
        score,m=b.fit_score([{'x':None}]*20,[{'x':0},{'x':100}],list(range(20)));self.assertEqual(list(score),[9.5,9.5]);self.assertEqual(m['allMissingFitColumns'],['x'])
    def test_daily_future_history_rejected(self):
        h=self.history();h[-1]['session']='2024-11-18'
        with self.assertRaises(ValueError):b.recent_context('2024-11-18',101,[],h,['2024-11-16','2024-11-18'])
    def test_previous_day_missing_no_fill(self):
        x=b.recent_context('2024-11-18',101,[],self.history()[:-1],['2024-11-16','2024-11-18']);self.assertEqual(x['status'],'UNAVAILABLE')
    def test_recent_excludes_today_daily(self):
        x=b.recent_context('2024-11-18',101,[],self.history(),['2024-11-16','2024-11-18']);self.assertEqual(x['features']['previous_C'],101);self.assertLess(x['computedThrough'],'2024-11-18')
    def test_reader_future_rejected(self):
        h=self.history();bar={**h[-1]['daily'],'Date':'2024-11-18','Time':'10:00:00'}
        x=b.now_context('2024-11-18',600,[bar],h[-1]['daily'],h,['2024-11-16','2024-11-18']);self.assertEqual(x['status'],'UNAVAILABLE');self.assertIn('FUTURE',x['reason'])
    def test_lunch_rejected(self):
        h=self.history();x=b.now_context('2024-11-18',720,[],h[-1]['daily'],h,['2024-11-16','2024-11-18']);self.assertEqual(x['status'],'UNAVAILABLE')
    def test_winner_denominator_zero_not_100(self):
        rows=self.rows(2);lab=[dict(mae30=-1,mae60=None,maeEnd=-2,mfeEnd=.5,return30=0,return60=None,returnEnd=0,order='SAME_BAR_ORDER_UNKNOWN')]*2
        x=b.panel(rows,lab,{0});self.assertIsNone(x['preservation']['3']['pct']);self.assertEqual(x['retainedCommonN'],1)
    def test_common_cohort_does_not_change_with_arm(self):
        rows=self.rows(2);lab=[dict(mae30=-1,mae60=None,maeEnd=-2,mfeEnd=5,return30=1,return60=None,returnEnd=0,order='LOW_THEN_HIGH')]*2
        a=b.panel(rows,lab,{0});c=b.panel(rows,lab,{1});self.assertEqual(a['commonCohortSHA256'],c['commonCohortSHA256']);self.assertEqual(a['preservation']['5']['pct'],50)
    def test_snapshot_tensor_prefix_enforced(self):
        meta={'sessions':['2024-11-11','2024-11-12','2024-11-13'],'codes':['11110'],'targets':{'daily':[{'id':'x','transform':'identity','tier':'daily','globalStatus':'USABLE'}]}}
        z={'daily':np.ones((3,1,1)),'cov':np.ones((3,1,4)),'eligible':np.ones((3,1,2),bool)}
        def snap(data,cv,eligible,item,ix):
            self.assertEqual(len(data),1);return {'raw':[1],'sd':[1],'eff':[1],'n':[1],'coverage':[1]}
        with patch.object(b.s,'snapshot',side_effect=snap),patch.object(b.s,'sample',return_value='LOW'),patch.object(b.s,'drift',return_value=[None]):
            a=b.who_day(meta,z,'2024-11-12',['11110']);z['daily'][1:]=999;c=b.who_day(meta,z,'2024-11-12',['11110']);self.assertEqual(a,c);self.assertIsNone(a['11110'][0]['value'])
    def test_primary_budget_fixed(self):
        self.assertEqual(len(b.retain(self.rows(),[1,2,3,4,5],.8,'S2')[0]),4)
    def test_scope_lock(self):
        p=b.verify();self.assertEqual(len(p['cohortSessions']),55);self.assertFalse(set(p['fitSessions'])&set(p['evaluationSessions']));self.assertEqual(len(p['embargoSessions']),5)
if __name__=='__main__':unittest.main()
