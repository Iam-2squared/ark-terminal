"""Synthetic causality/missing tests and independent saved-path arithmetic checks."""
import copy
import hashlib
import math
import unittest
from scripts import phase57_entry_location_study as s


def event():
    return {'selectorEventId':'synthetic','symbol':'TEST','sessionDate':'2024-10-01','decisionTimestamp':'2024-10-01T09:30:00+09:00',
            'decisionPrice':100.,'entryMinute':570,'sessionEndMinute':900,'direction':'LONG','future':[
                {'start':f'2024-10-01T{m//60:02}:{m%60:02}:00+09:00','end':f'2024-10-01T{(m+5)//60:02}:{(m+5)%60:02}:00+09:00',
                 'missing':False,'o':0.,'h':4.,'l':-3.,'c':-1.,'observedMinutes':5} for m in range(570,650,5)]}


class SyntheticTests(unittest.TestCase):
    def test_conditional_causality(self):
        self.assertEqual(s.choose_delay('DIP_CLOSE_FALLBACK10',100,[99]),5)
        self.assertEqual(s.choose_delay('DIP_CLOSE_FALLBACK10',100,[100]),10)
        self.assertEqual(s.choose_delay('OBSERVE5_DELAY_DIP10',100,[99]),10)
        self.assertEqual(s.choose_delay('OBSERVE5_DELAY_DIP10',100,[100]),5)
        self.assertIsNone(s.choose_delay('OBSERVE5_DELAY_DIP10',100,[None]))
        self.assertEqual(s.choose_delay('IMMEDIATE',100,[]),0)

    def test_future_extremes_cannot_change_timing(self):
        e=event();a=s.entry_reference('DIP_CLOSE_FALLBACK10',e,s.absolute_path(e))
        for b in e['future'][2:]:b.update(h=999.,l=-99.,c=50.)
        self.assertEqual(a,s.entry_reference('DIP_CLOSE_FALLBACK10',e,s.absolute_path(e)))

    def test_reference_open_not_low_or_signal_close(self):
        e=event();e['future'][1].update(o=2.,h=4.,l=-10.,c=-1.)
        x=s.evaluate_anchor(e,'UNKNOWN')['policies']['WAIT5']
        self.assertEqual(x['price'],102.)
        self.assertAlmostEqual(x['buyImprovementPct'],-2.)
        self.assertAlmostEqual(x['windows']['5']['downside'],100*(1-90/102))

    def test_postentry_excludes_preentry_low(self):
        e=event();e['future'][0]['l']=-50
        r=s.evaluate_anchor(e,'UNKNOWN')
        self.assertAlmostEqual(r['policies']['IMMEDIATE']['windows']['5']['downside'],50.)
        self.assertAlmostEqual(r['policies']['WAIT5']['windows']['5']['downside'],3.)

    def test_missing_open_not_next_observation(self):
        e=event();e['future'][1]={'start':e['future'][1]['start'],'end':e['future'][1]['end'],'missing':True}
        r=s.evaluate_anchor(e,'UNKNOWN')
        self.assertIsNone(r['policies']['WAIT5']['price'])
        self.assertEqual(r['policies']['WAIT5']['status'],'UNKNOWN_REFERENCE_OPEN')
        self.assertIsNone(r['policies']['IMMEDIATE']['windows']['10']['downside'])
        self.assertFalse(r['primary60'])

    def test_missing_close_no_false_nodip(self):
        e=event();e['future'][0]={'start':e['future'][0]['start'],'end':e['future'][0]['end'],'missing':True}
        r=s.evaluate_anchor(e,'UNKNOWN')
        self.assertIsNone(r['firstClosedDip'])
        self.assertIsNone(r['policies']['DIP_CLOSE_FALLBACK10']['delay'])

    def test_lunch_no_crossing_or_interpolation(self):
        self.assertIsNone(s.segment_end(690,900));self.assertIsNone(s.segment_end(720,900))
        self.assertEqual(s.segment_end(685,900),690)
        e=event();e['entryMinute']=685
        self.assertEqual(s.entry_reference('WAIT5',e,{})['status'],'EXPIRED_BOUNDARY')

    def test_quantiles_and_es95(self):
        d=s.distribution(list(range(1,21)))
        self.assertEqual(d['median'],10.5);self.assertEqual(d['ES95'],20)
        self.assertAlmostEqual(d['p95'],19.05)
        self.assertIsNone(s.distribution([None])['mean'])

    def test_unknown_is_not_failure(self):
        e=event();e['future'][1]['missing']=True
        x=s.evaluate_anchor(e,'UNKNOWN')['censusSavedSession']
        self.assertIsNone(x['upside']);self.assertIsNotNone(x['observedUpsideLowerBound'])
        self.assertEqual(x['status'],'UNKNOWN_INCOMPLETE')


class SavedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=s.read(s.BASE/'protocol.json');cls.r=s.read(s.BASE/'result.json.gz');cls.l=s.read(s.BASE/'ledger.json.gz')
        cls.paths={e['selectorEventId']:e for e in s.read(s.PATHS)['events']}

    def test_source_and_selector_identity(self):
        for p,sha in self.c['sourcePins'].items():self.assertEqual(s.sha(p),sha)
        f=s.read(s.SELECTOR)
        raw=s.json.dumps(f['freezePayload'],sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),self.c['selector']['payload'])
        self.assertEqual(f['hashes']['savedModelArtifactSha256'],self.c['selector']['ridge'])
        self.assertEqual(f['freezePayload']['selectorSpecification']['trainingTarget']['name'],'Y30')

    def test_anchor_and_panel_counts(self):
        self.assertEqual(len(self.l),2743)
        self.assertEqual(hashlib.sha256(('\n'.join(sorted(r['eventId'] for r in self.l))+'\n').encode()).hexdigest(),s.ANCHOR_SHA)
        self.assertEqual(sum(r['primary60'] for r in self.l),878)
        self.assertEqual(sum(r['primary60'] and r['firstClosedDip'] for r in self.l),328)
        self.assertEqual(len({(r['symbol'],r['sessionDate']) for r in self.l}),2743)

    def test_independent_absolute_vs_normalized_arithmetic(self):
        comparisons=0
        for r in self.l:
            e=self.paths[r['eventId']];by={s.minute(b['start']):b for b in e['future']};m=e['entryMinute']
            for policy,v in r['policies'].items():
                if v['price'] is None:continue
                start=m+v['delay'];entry=by[start];factor=1+entry['o']/100
                self.assertAlmostEqual(v['price'],e['decisionPrice']*factor,places=9)
                for n in [5,10,15,30,60]:
                    a=v['windows'][str(n)]
                    if a['status']!='COMPLETE':continue
                    bars=[by[t] for t in range(start,start+n,5)]
                    self.assertTrue(all(not b['missing'] for b in bars))
                    up=max(0.,(max(b['h'] for b in bars)-entry['o'])/factor)
                    down=max(0.,(entry['o']-min(b['l'] for b in bars))/factor)
                    self.assertAlmostEqual(a['upside'],up,places=9)
                    self.assertAlmostEqual(a['downside'],down,places=9);comparisons+=2
        self.assertGreater(comparisons,40000)

    def test_prior_location_parity(self):
        all=self.r['cohorts']['ALL']['policies']
        self.assertEqual(all['WAIT5']['capture']['3']['hits'],192)
        self.assertEqual(all['WAIT5']['capture']['5']['hits'],86)
        d=self.r['cohorts']['FIRST_CLOSED_DIP']['policies']['WAIT5']
        self.assertEqual(d['capture']['3']['hits'],56);self.assertEqual(d['capture']['5']['hits'],21)
        self.assertAlmostEqual(d['buyImprovementPct']['mean'],1.11841,places=5)

    def test_full_ledger_coverage_and_safe_counters(self):
        for p in s.POLICIES:self.assertEqual(sum(self.r['coverage']['fullLedgerEntryStates'][p].values()),2743)
        self.assertTrue(all(v==0 for v in self.r['counters'].values()))
        self.assertFalse(any(self.r['safety'].values()))
        self.assertNotIn('profitFactor',self.r)
        self.assertEqual(self.r['status'],'ENTRY_LOCATION_STUDY_COMPLETE')

    def test_saved_primary_aggregates_recomputed(self):
        actual=s.summarize([r for r in self.l if r['primary60']])
        expected=self.r['cohorts']['ALL']
        def check(a,b):
            if isinstance(b,dict):
                self.assertEqual(set(a),set(b))
                for k in b:check(a[k],b[k])
            elif isinstance(b,float):self.assertTrue(math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12))
            else:self.assertEqual(a,b)
        check(actual,expected)

    def test_manifest(self):
        raw=(s.BASE/'manifest.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),(s.BASE/'manifest.json.sha256').read_text().strip())
        for p,expected in s.json.loads(raw)['files'].items():self.assertEqual(s.sha(p),expected,p)


if __name__=='__main__':unittest.main()
