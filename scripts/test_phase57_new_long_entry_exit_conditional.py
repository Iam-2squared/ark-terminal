"""Transfer integrity tests; no Entry research, market access, or parameter search."""
import copy
import hashlib
import unittest
from pathlib import Path
from scripts import phase57_new_long_entry_exit_conditional as d

def fixture():
    future=[]
    for i,c in enumerate([-.5,-1,-2,-3,-4,1,2,1,0,1,2,3,4]):
        m=570+5*i
        future.append({'slot':i+1,'start':d.stamp('2024-09-17',m),
            'end':d.stamp('2024-09-17',m+5),'minutes':5*(i+1),'missing':False,
            'o':0 if i==0 else -1,'h':max(1,c),'l':min(-1,c),'c':c,'observedMinutes':5})
    p={'sessionDate':'2024-09-17','decisionPrice':100,'sessionEndMinute':900,'future':future}
    op={'referenceStatus':'REFERENCE_OPEN','referencePrice':99,
        'opportunityTimestamp':'2024-09-17T09:35:00+09:00','eventType':'DIP_REPRICE_OPPORTUNITY'}
    return op,p

class TransferTests(unittest.TestCase):
    def test_dip_starts_at_saved_event_and_excludes_pre_dip_extremes(self):
        op,p=fixture();p['future'][0]['h']=1000;p['future'][0]['l']=-99
        e=d.adapt(op,p)
        self.assertEqual(e['future'][0]['start'],op['opportunityTimestamp'])
        self.assertEqual(e['future'][0]['slot'],1)
        self.assertAlmostEqual(e['future'][0]['o'],0)
        self.assertLess(d.path_diagnostic(e,p['sessionDate'])['30']['mfePct'],10)
        self.assertGreater(d.path_diagnostic(e,p['sessionDate'])['30']['maePct'],-10)
        # Mapping follows the supplied causal event, not hardcoded t0+5.
        op['opportunityTimestamp']=p['future'][2]['start']
        self.assertEqual(d.adapt(op,p)['future'][0]['start'],op['opportunityTimestamp'])

    def test_close_decision_has_no_high_low_or_future_dependency(self):
        op,p=fixture();e=d.adapt(op,p);f=d.module('final_test',d.INTERFACE)
        before=d.replay_existing(e,f);self.assertEqual(before['status'],'EXIT_REFERENCE')
        changed=copy.deepcopy(e)
        for b in changed['future']:
            if not b['missing']:b['h']=999;b['l']=-99
            if b['slot']>before['exitBar']:b['missing']=True;b['c']=-99
        self.assertEqual(d.replay_existing(changed,f),before)

    def test_missing_before_exit_is_not_flat_or_imputed(self):
        op,p=fixture();e=d.adapt(op,p);e['future'][1]['missing']=True
        f=d.module('final_missing_test',d.INTERFACE)
        r=d.replay_existing(e,f)
        self.assertEqual(r['status'],'CENSORED');self.assertIsNone(r['netPct'])
        op['referenceStatus']='UNKNOWN_REFERENCE_OPEN'
        self.assertEqual(d.adapt(op,p)['status'],'INELIGIBLE_REFERENCE')

    def test_lunch_and_auction_boundaries_remain_explicit(self):
        self.assertEqual(d.grid(685,755),[685,750])
        self.assertEqual(d.grid(685,755)[1]+5-685,70)
        op,p=fixture();e=d.adapt(op,p);e['startMinute']=685
        r=d.path_diagnostic(e,'2024-09-17')
        self.assertEqual(r['10']['status'],'UNKNOWN_SEGMENT_BOUNDARY')
        self.assertEqual(d.segment_end(690,930),None)

    def test_same_bar_recovery_and_deep_winner_are_not_assumed(self):
        op,p=fixture();e=d.adapt(op,p);b=e['future'][0]
        b.update(l=-6,h=6,c=1)
        a=d.evaluate_window([b]);self.assertFalse(a['adverseRecoveredLaterClose'])
        self.assertFalse(a['downside']['5']['winner3AfterDeepAdverse'])
        second=dict(e['future'][1]);second.update(c=1,h=4)
        a=d.evaluate_window([b,second]);self.assertTrue(a['adverseRecoveredLaterClose'])
        self.assertTrue(a['downside']['5']['winner3AfterDeepAdverse'])

class SavedEvidenceTests(unittest.TestCase):
    def test_frozen_input_and_output_receipts(self):
        m=d.read(d.BASE/'manifest.json')
        for p,h in m['inputPins'].items():self.assertEqual(d.sha(d.ROOT/p),h,p)
        for p,h in m['outputPins'].items():self.assertEqual(d.sha(d.BASE/p),h,p)
        self.assertTrue(all(v is False for v in m['safety'].values()))
        self.assertTrue(all(v==0 for v in m['zeroCounters'].values()))

    def test_full_population_and_exact_106_21_identity(self):
        ledger=d.read(d.BASE/'ledger.json.gz');parity=d.read(d.BASE/'entry-parity/ledger.ndjson.gz')
        initial=[r for r in ledger if r['cohort']=='INITIAL_ENTRY_OPPORTUNITY']
        dip=[r for r in ledger if r['cohort']=='DIP_REPRICE_OPPORTUNITY']
        self.assertEqual(len(initial),2743);self.assertEqual(len(dip),541)
        ids=sorted(r['anchorId'] for r in initial)
        self.assertEqual(hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest(),d.ANCHOR_SHA)
        for k,n in [(2,106),(5,21)]:
            expected={r['anchorId'] for r in parity if r['evaluator']['primary60']
                and r['evaluator'].get('buyImprovementPct') is not None
                and r['evaluator']['buyImprovementPct']>0
                and r['evaluator']['secondaryD30']['downside']>=k}
            actual={r['anchorId'] for r in dip if f'CHEAPER_PRIMARY_D30_{k}' in r['riskTags']}
            self.assertEqual(len(actual),n);self.assertEqual(actual,expected)

    def test_paired_denominators_and_prices_are_independently_preserved(self):
        ledger=d.read(d.BASE/'ledger.json.gz');source={r['anchorId']:r for r in d.read(d.BASE/'entry-parity/ledger.ndjson.gz')}
        s=d.read(d.BASE/'summary.json')
        for cohort,n in [('INITIAL_ENTRY_OPPORTUNITY',1072),('DIP_REPRICE_OPPORTUNITY',397)]:
            rows=[r for r in ledger if r['cohort']==cohort]
            self.assertEqual(s['cohorts'][cohort]['paired']['fixed']['n'],n)
            self.assertEqual(s['cohorts'][cohort]['paired']['existing']['n'],n)
            for r in rows:
                key='initialEvent' if cohort=='INITIAL_ENTRY_OPPORTUNITY' else 'secondaryEvent'
                self.assertEqual(r['opportunity'],source[r['anchorId']]['decision'][key])
                if r['existing']['status']=='EXIT_REFERENCE':
                    self.assertLessEqual(r['existing']['exitBar'],12)
                    self.assertEqual(r['existing']['preExitPath']['status'],'COMPLETE')
                    self.assertAlmostEqual(r['existing']['grossPct']-.05,r['existing']['netPct'])

if __name__=='__main__':unittest.main()
