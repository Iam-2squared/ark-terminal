import copy,unittest
import numpy as np
from scripts import phase57_temporal_formal as f
from scripts import phase57_sparse_trait_contract as c
from scripts import test_phase57_sparse_handoff as oldtests
s=f.s


def fixture():
    at='2025-08-22T15:30:00+09:00';available='2025-08-22T15:31:00+09:00'
    cell={'symbol':'10000','lane':'daily','trait_id':'amihud','globalStatus':'USABLE','sampleConfidence':'HIGH','temporalReliability':{'status':'PASS','computedThrough':'2025-08-21T15:30:00+09:00','availableAt':'2025-08-21T15:31:00+09:00'},'posterior':0.,'transform':'identity','uncertainty':{'posteriorSD':.1},'nEff':45.,'drift':False,'identityStatus':'DATED_MASTER_CODE_RESEARCH_ONLY','definitionHash':'fixed','evidenceClass':'RESEARCH_ONLY'}
    for key in ['computedThrough','peerArtifactThrough','normalizationThrough','referenceScaleThrough','identityComputedThrough']:cell[key]=at
    for key in ['availableAt','identityAvailableAt','definitionAvailableAt']:cell[key]=available
    return {'symbol':'10000','asOf':at,'researchOnly':True,'traits':[cell]}

class FormalTests(unittest.TestCase):
    now='2025-08-25T12:35:00+09:00'
    def test_exact_proposal_adopted(self):f.verify()
    def test_temporal_perfect_pass(self):
        spec=f.verify()[1];rows=[{'eligible':True,'x':x,'y':x,'posteriorChange':0} for x in [-1,0,1]]
        self.assertEqual(f.temporal_result(rows,spec)['status'],'PASS')
    def test_temporal_fail_never_promoted(self):
        spec=f.verify()[1];rows=[{'eligible':True,'x':x,'y':-x,'posteriorChange':0} for x in [-1,.1,1]]
        self.assertEqual(f.temporal_result(rows,spec)['status'],'FAIL')
    def test_temporal_missing_not_fail_or_zero(self):
        spec=f.verify()[1];self.assertEqual(f.temporal_result([{'eligible':False}],spec)['status'],'INSUFFICIENT')
    def test_zero_value_is_available(self):
        x=c.payload(fixture(),self.now)[0];self.assertEqual(x['availability'],'AVAILABLE');self.assertEqual(x['value'],0.)
    def test_medium_retains_medium(self):
        p=fixture();p['traits'][0]['sampleConfidence']='MEDIUM';self.assertEqual(c.payload(p,self.now)[0]['sampleConfidence'],'MEDIUM');self.assertEqual(c.payload(p,self.now)[0]['availability'],'AVAILABLE')
    def test_bad_sibling_does_not_veto_symbol(self):
        p=fixture();q=copy.deepcopy(p['traits'][0]);q.update(trait_id='pdh_break',sampleConfidence='INSUFFICIENT',posterior=None);q['temporalReliability']['status']='INSUFFICIENT';p['traits'].append(q)
        x=c.payload(p,self.now);self.assertEqual([a['availability'] for a in x],['AVAILABLE','UNAVAILABLE']);self.assertIsNone(x[1]['value'])
    def test_all_unavailable_states_are_null(self):
        for conf,tem in [('LOW','PASS'),('INSUFFICIENT','PASS'),('HIGH','FAIL'),('MEDIUM','INSUFFICIENT')]:
            p=fixture();p['traits'][0]['sampleConfidence']=conf;p['traits'][0]['temporalReliability']['status']=tem
            x=c.payload(p,self.now)[0];self.assertIsNone(x['value']);self.assertEqual(x['availability'],'UNAVAILABLE')
    def test_future_temporal_pass_cannot_backfill(self):
        p=fixture();p['traits'][0]['temporalReliability']['computedThrough']='2025-08-25T15:30:00+09:00';p['traits'][0]['temporalReliability']['availableAt']='2025-08-25T15:31:00+09:00'
        self.assertIn('TEMPORAL_NOT_AVAILABLE_ASOF',c.payload(p,self.now)[0]['reasons'])
    def test_artifact_available_after_decision(self):
        for key in ['availableAt','definitionAvailableAt','identityAvailableAt']:
            p=fixture();p['traits'][0][key]='2025-08-25T12:36:00+09:00';self.assertEqual(c.payload(p,self.now)[0]['availability'],'UNAVAILABLE')
    def test_computed_through_strictly_before(self):
        with self.assertRaises(ValueError):c.payload(fixture(),'2025-08-22T15:30:00+09:00')
    def test_mixed_asof_rejected(self):
        p=fixture();p['traits'][0]['normalizationThrough']='2025-08-21T15:30:00+09:00'
        with self.assertRaises(ValueError):c.payload(p,self.now)
    def test_nonfinite_value_or_uncertainty_rejected(self):
        p=fixture();p['traits'][0]['posterior']=float('nan');self.assertEqual(c.payload(p,self.now)[0]['availability'],'UNAVAILABLE')
        p=fixture();p['traits'][0]['uncertainty']['posteriorSD']=None;self.assertEqual(c.payload(p,self.now)[0]['availability'],'UNAVAILABLE')
    def test_watch_never_dispatch(self):
        p=fixture();p['traits'][0]['globalStatus']='WATCH';self.assertEqual(c.payload(p,self.now)[0]['availability'],'UNAVAILABLE')
    def test_drift_unknown_kept_with_warning_for_medium(self):
        p=fixture();p['traits'][0].update(sampleConfidence='MEDIUM',drift=None);x=c.payload(p,self.now)[0];self.assertEqual(x['availability'],'AVAILABLE');self.assertEqual(x['warning'],'DRIFT_UNTESTED')
    def test_histogram_deduplicates_amihud_lanes(self):
        p=fixture();q=copy.deepcopy(p['traits'][0]);q['lane']='intraday';p['traits'].append(q)
        x=c.coverage([p],self.now);self.assertEqual(x['symbolBins']['1'],1);self.assertEqual(x['laneQualifiedSymbolBins']['2'],1);self.assertEqual(x['oldUsableTotals']['available'],2)
    def test_counts_partition_all_cells(self):
        p=fixture();q=copy.deepcopy(p);q['symbol']='20000'
        for row in q['traits']:row['symbol']='20000';row['temporalReliability']['status']='FAIL'
        x=c.coverage([p,q],self.now);tot=x['oldUsableTotals'];self.assertEqual(tot['evaluated'],sum(tot[k] for k in ['PASS','FAIL','INSUFFICIENT']));self.assertEqual(x['symbolBins']['0'],1);self.assertEqual(x['atLeast']['1'],1)
    def test_watch_mapping_frozen_before_independent_periods(self):
        spec=f.verify()[1];x=np.linspace(-1,1,110);out=f.watch_mapping([(x,2*x),(x,2*x),(x,2*x)],spec)
        self.assertTrue(out['newVersionCandidate']);self.assertFalse(out['promotion'])
    def test_missing_watch_mapping_not_fabricated(self):
        x=np.linspace(-1,1,99);out=f.watch_mapping([(x,x),(x,x),(x,x)],f.verify()[1]);self.assertIsNone(out['mapping']);self.assertFalse(out['newVersionCandidate'])
    def test_reader_receives_only_causally_admitted_cells(self):
        q=oldtests.ReaderTests();q.setUp();p=fixture();p['asOf']='2025-08-24T15:30:00+09:00'
        for row in p['traits']:
            for key in ['computedThrough','peerArtifactThrough','normalizationThrough','referenceScaleThrough','identityComputedThrough']:row[key]=p['asOf']
        bad=copy.deepcopy(p['traits'][0]);bad['trait_id']='bad';bad['temporalReliability']['availableAt']='2025-08-26T15:31:00+09:00';p['traits'].append(bad)
        out=c.reader_context(q.day,570,q.rows(),q.previous,q.hist,q.cal,p)
        self.assertEqual(out['status'],'RESEARCH_CONTEXT_AVAILABLE');self.assertEqual(len(out['personality']),1);self.assertEqual(out['dictionaryFeaturePayload'][1]['availability'],'UNAVAILABLE')

if __name__=='__main__':unittest.main()
