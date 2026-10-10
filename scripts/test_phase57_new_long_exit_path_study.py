"""Causality, time-order and population integrity for a non-trading evaluator."""
import ast
import copy
import hashlib
import unittest
from scripts import phase57_new_long_exit_path_study as s

def bars(values):
    out=[]
    for i,(h,l,c) in enumerate(values):
        m=570+5*i
        out.append({'slot':i+1,'minute':m,'elapsed':5*(i+1),'start':s.stamp('2024-09-17',m),
            'end':s.stamp('2024-09-17',m+5),'o':0,'h':h,'l':l,'c':c,'missing':False,'observedMinutes':5})
    return out

class ObservationTests(unittest.TestCase):
    def test_prefix_does_not_change_with_future_mutation(self):
        rs=bars([(1,-1,-.5),(2,-2,1),(3,-3,2),(4,-4,3)])
        before=s.causal_prefix(rs[:2]);changed=copy.deepcopy(rs)
        for b in changed[2:]:b.update(h=999,l=-99,c=-98)
        self.assertEqual(before,s.causal_prefix(changed[:2]))
        self.assertNotEqual(s.suffix_labels(before,rs[2:]),s.suffix_labels(before,changed[2:]))
        self.assertNotIn('futureReach',before)

    def test_pre_peak_mae_is_bounded_not_order_invented(self):
        p=s.panel(bars([(1,-.5,.1),(5,-4,1),(3,-2,2)]))
        self.assertEqual(p['maeStrictlyBeforeMfeBarPct'],-.5)
        self.assertEqual(p['maeIncludingMfeBarPct'],-4)
        self.assertEqual(p['peakBarLowHighOrder'],'UNKNOWN_INTRABAR_ORDER')
        self.assertEqual(p['timeToMfe']['minutesLower'],5)
        self.assertEqual(p['timeToMfe']['minutesUpper'],10)

    def test_adverse_then_winner_requires_later_bar(self):
        p=s.panel(bars([(5,-2,1)]))
        r=p['recovery']['2'];self.assertTrue(r['sameBarWinnerOrderUnknown']['5'])
        self.assertIsNone(r['winnerAfterAdverse']['5']);self.assertIsNone(r['entryReclaim'])
        p=s.panel(bars([(1,-2,-1),(2,-1,.5),(5,0,3)]))
        r=p['recovery']['2'];self.assertEqual(r['entryReclaim']['minutesUpper'],10)
        self.assertTrue(r['winnerAfterReclaim']['5'])
        self.assertEqual((r['durationLowerMinutes'],r['durationUpperMinutes']),(5,10))

    def test_negative_snapshot_loss_counts_only_later_opportunity(self):
        rs=bars([(3,-1,-.5),(2,-1,.5),(5,0,4)]+[(4,0,1)]*9)
        out=s.panel_summary([s.panel(rs)])
        a=out['winners']['3']['negativeSnapshots']['5']
        self.assertEqual(a['laterLevelHit']['n'],1)
        self.assertEqual(a['notYetFirstHitWinner']['n'],0)
        b=out['winners']['5']['negativeSnapshots']['5']
        self.assertEqual(b['notYetFirstHitWinner']['n'],1)

    def test_giveback_rehigh_and_negative_endpoint_are_separate(self):
        rs=bars([(3,0,1),(4,0,3),(1,-2,-1)])
        e=s.giveback_events(rs,3)['events']['2pp']
        self.assertEqual(e['elapsedMinutes'],5)
        self.assertEqual(e['newHighLater']['minutesUpper'],10)
        self.assertEqual(e['outcome'],'REHIGH_NEGATIVE_ENDPOINT')
        rs=bars([(3,0,3),(1,-2,-1)])
        e=s.giveback_events(rs,3)['events']['FULL_TO_ENTRY']
        self.assertEqual(e['outcome'],'NO_POST_EVENT_WINDOW')

    def test_missing_and_end_window_are_not_zero_outcomes(self):
        rs=bars([(1,-1,0)]*12);rs[1]['missing']=True
        p={'status':'REFERENCE_OPEN','startMinute':570,'boundaryMinute':690,'rows':rs}
        coverage,observed=s.window(p,60)
        self.assertEqual(coverage['status'],'UNKNOWN_MISSING');self.assertEqual(observed,[])
        c=s.causal_prefix(rs[:1]);f=s.suffix_labels(c,[])
        self.assertEqual(f['status'],'WINDOW_ENDED');self.assertIsNone(f['remainingUpsidePct'])
        self.assertEqual(s.window({**p,'boundaryMinute':600},60)[0]['status'],'BOUNDARY_EXPIRED')

    def test_dip_rebase_uses_saved_timestamp_and_excludes_earlier_ohlc(self):
        rs=bars([(90,-80,1),(3,-2,1),(4,-1,2)])
        source={'sessionDate':'2024-09-17','decisionPrice':100,'future':[{**b,'minutes':b['elapsed']} for b in rs]}
        op={'referenceStatus':'REFERENCE_OPEN','referencePrice':100,'opportunityTimestamp':rs[1]['start']}
        p=s.prepare(op,source)
        self.assertEqual(p['startTimestamp'],rs[1]['start'])
        self.assertEqual(p['rows'][0]['slot'],1);self.assertAlmostEqual(p['rows'][0]['h'],3)
        self.assertEqual(s.window(p,5)[0]['status'],'COMPLETE')
        self.assertLess(s.causal_prefix(p['rows'][:1])['runningMfePct'],10)

    def test_evaluator_imports_only_standard_library_and_has_no_rule_api(self):
        tree=ast.parse((s.ROOT/'scripts/phase57_new_long_exit_path_study.py').read_text())
        allowed={'__future__','argparse','collections','datetime','gzip','hashlib','json','math','statistics','pathlib'}
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):self.assertTrue(all(a.name.split('.')[0] in allowed for a in n.names))
            if isinstance(n,ast.ImportFrom):self.assertIn(n.module.split('.')[0],allowed)
        self.assertFalse(any(hasattr(s,k) for k in ('on_completed_bar','new_position','fit','predict','replay_existing')))

    def test_next_interval_can_be_observed_without_complete_60m_suffix(self):
        c=s.causal_prefix(bars([(1,-1,0)]))
        obs={'status':'COMPLETE','causalPrefix':c,'evaluatorOnly':{'status':'UNKNOWN_OWN60_FUTURE',
            'nextIntervalObservation':{'status':'COMPLETE','direction':'UP','changePP':1}}}
        result=s.snapshot_summary([obs],1)
        self.assertEqual(result['suffixCoverage']['n'],0)
        self.assertEqual(result['nextIntervalCoverage']['n'],1)
        self.assertEqual(result['nextIntervalDirections'],{'UP':1})

class SavedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (s.BASE/'ledger.json.gz').exists():raise unittest.SkipTest('pre-measurement')
        cls.rows=s.read(s.BASE/'ledger.json.gz');cls.summary=s.read(s.BASE/'summary.json.gz')

    def test_exact_upstream_and_outputs(self):
        m=s.read(s.BASE/'manifest.json')
        for p,h in m['inputPins'].items():self.assertEqual(s.sha(s.ROOT/p),h,p)
        for p,h in m['outputPins'].items():self.assertEqual(s.sha(s.BASE/p),h,p)
        self.assertTrue(all(v==0 for v in m['zeroCounters'].values()))
        self.assertTrue(all(v is False for v in m['safety'].values()))

    def test_full_identity_and_frozen_events_unchanged(self):
        saved={x['anchorId']:x for x in s.read(s.PRIOR/'entry-parity/ledger.ndjson.gz')}
        initial=[r for r in self.rows if r['cohort']==s.TYPES[0]]
        dips=[r for r in self.rows if r['cohort']==s.TYPES[1]]
        self.assertEqual((len(initial),len(dips)),(2743,541))
        ids=sorted(r['anchorId'] for r in initial)
        self.assertEqual(hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest(),s.ANCHOR_SHA)
        for r in self.rows:
            key='initialEvent' if r['cohort']==s.TYPES[0] else 'secondaryEvent'
            self.assertEqual(r['opportunity'],saved[r['anchorId']]['decision'][key])
        for depth,n in ((2,106),(5,21)):
            expected={i for i,x in saved.items() if x['evaluator']['primary60']
                and x['evaluator'].get('buyImprovementPct') is not None
                and x['evaluator']['buyImprovementPct']>0 and x['evaluator']['secondaryD30']['downside']>=depth}
            actual={r['anchorId'] for r in dips if f'D30_DROP_{depth}' in r['riskTagsEvaluatorOnly']}
            self.assertEqual(expected,actual);self.assertEqual(len(actual),n)

    def test_fixed_population_for_all_winner_levels(self):
        for typ,c in self.summary['cohorts'].items():
            n=c['own60Coverage']['n']
            self.assertEqual(c['own60']['metrics']['n'],n)
            for level,w in c['own60']['winners'].items():self.assertEqual(w['count']['denominator'],n)
        self.assertEqual(self.summary['pairedPanels']['COMMON_T0_60_DIP328']['matchedAnchors'],328)
        for r in self.rows:
            p=r['panels']['own60']
            if p['status']=='COMPLETE':
                self.assertEqual(p['bars'],12)
                self.assertEqual(p['evolution']['60']['evaluatorOnly']['status'],'WINDOW_ENDED')
                for h in s.HORIZONS:
                    self.assertEqual(p['evolution'][str(h)]['causalPrefix'],r['snapshots'][str(h)]['causalPrefix'])

    def test_prior_own60_metrics_reproduce_without_replaying_exit(self):
        old=s.read(s.PRIOR/'summary.json')
        for typ in s.TYPES:
            a=self.summary['cohorts'][typ]['own60']['metrics'];b=old['cohorts'][typ]['path']['60']
            self.assertEqual(a['n'],b['n'])
            for x,y in [('mfePct','mfePct'),('maePct','maePct'),('endpointPct','closePct')]:
                self.assertAlmostEqual(a[x]['mean'],b[y]['mean'])
                self.assertAlmostEqual(a[x]['median'],b[y]['median'])

if __name__=='__main__':unittest.main()
