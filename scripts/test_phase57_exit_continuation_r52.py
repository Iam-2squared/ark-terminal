"""Performance-free R52 synthetic causality, reuse, accounting and contract tests."""
import copy, unittest
import numpy as np
from decimal import Decimal
from scripts import phase57_exit_continuation_r52 as r
from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_capital_exit_integrated as integ
from scripts.test_phase57_capital_exit_integrated import fixture

class ContinuationR52Tests(unittest.TestCase):
    def test_protocol_pins_and_safety(self):
        p=r.protocol();self.assertEqual(len(p['candidateIds']),2)
        self.assertEqual(p['initialCashJpy'],1000000)
        self.assertEqual(p['capacity'],3)
        self.assertEqual(p['controlExactFinalEquityJpy'],'887131.0091250009994995')
        self.assertFalse(any(p['safety'].values()))
        self.assertEqual(p['entryDualFreeze'],'4878a1cc53430e816261dea0fb16aeb53b3c238d')
        self.assertEqual(p['pins']['scripts/phase57_exit_winner_lifecycle_r50.py'],
                         v0.digest(r.ROOT/'scripts/phase57_exit_winner_lifecycle_r50.py'))

    def test_all_profit_states_access_same_action_contract(self):
        p=r.protocol()
        for profit in (-10,-.1,0,1,2.9,3,4.9,5,13):
            self.assertEqual(r.action(-.1,True,profit,600,p)[0],'SELL_INTENT')
            self.assertEqual(r.action(+.1,True,profit,600,p)[0],'HOLD')
        self.assertEqual(r.action(-.05,True,-10,600,p)[0],'HOLD')
        self.assertEqual(r.action(-.05001,True,-10,600,p)[0],'SELL_INTENT')

    def test_missing_now_and_terminal_fallback(self):
        p=r.protocol()
        for fresh,ret,pred in [(False,-10,-100),(True,None,-100),(True,-10,None)]:
            self.assertEqual(r.action(pred,fresh,ret,600,p),('HOLD','MISSING_REQUIRED_NOW'))
        self.assertEqual(r.action(None,False,None,925,p),('FORCE_TERMINAL','SESSION_END'))

    def test_future_label_and_peak_isolation(self):
        p=r.protocol();now=(.3,True,4.2,625)
        first=r.action(*now,p)
        for future in (-100,0,5,99):
            record={'futureHigh':future,'target':future,'futureState':'DROP',
                    'postEntryUpside':future,'futureLabelAvailable':future>0}
            self.assertEqual(first,r.action(*now,p))
            self.assertFalse(set(record)&set(r.CORE_NUMERIC))

    def test_known_at_and_allowlists_are_exact(self):
        p=r.protocol()
        self.assertEqual(tuple(p['featureAllowlist']['coreNumeric']),r.CORE_NUMERIC)
        self.assertEqual(tuple(p['featureAllowlist']['additionalNumeric']),r.EXTRA_NUMERIC)
        self.assertEqual(len(p['featureAllowlist']['additionalPattern187']),187)
        self.assertEqual(len(p['folds']),4)
        for f in p['folds']:
            self.assertLess(max(f['train']),min(f['purge']))
            self.assertLess(max(f['purge']),min(f['score']))
        self.assertFalse(set(p['featureDenylist'])&set(p['featureAllowlist']['coreNumeric']))

    def test_exact_next_open_without_forward_search(self):
        ref=r.execution.ordinary_execution_reference('2025-07-22',600,
                       [[601,105,105,105,105,1,105]])
        self.assertEqual(ref['status'],'MISSING_EXECUTION_REFERENCE')
        self.assertIsNone(ref['price'])

    def test_teacher_compares_exact_open_to_frozen_r50_after_next_checkpoint(self):
        day='2025-07-22';eid=f'{day}|TEST|540';names=['facts.'+x for x in r.r50.FACTS]
        matrix=np.zeros((3,len(names)),np.float32)
        arr={'numeric':matrix,'fresh':np.ones(3,dtype=bool)}
        ids=[{'now':m} for m in (541,542,925)]
        rows={540:100,541:101,542:102,930:110}
        raw={f'{day}|TEST':{m:[m,z,z,z,z,1,z] for m,z in rows.items()}}
        entry={(v0.IM,eid):{'session':day,'opportunity':f'{day}|TEST',
                            'effectiveEntryPrice':100.,'entryMinute':540}}
        values,reasons,calendar=r.build_labels({'numericColumns':names},arr,ids,
                             {(v0.IM,eid):[0,1,2]},entry,raw)
        self.assertEqual(reasons['AVAILABLE'],2)
        self.assertAlmostEqual(values[0],(110-101)*.9995)
        self.assertEqual(calendar[v0.IM][eid],(930,110.,'FORCED_TERMINAL'))

    def test_confirmed_release_and_per_policy_funding_change(self):
        cohort,rows,raw,terminal,early=fixture()
        hold=integ.replay(v0.IM,3,cohort,rows,raw,terminal)
        exit_early=integ.replay(v0.IM,3,cohort,rows,raw,early)
        self.assertEqual(len(hold['funded']),3)
        self.assertEqual(len(exit_early['funded']),4)
        self.assertNotIn(rows[3]['entryId'],exit_early['funded'])
        self.assertIn(rows[4]['entryId'],exit_early['funded'])
        self.assertTrue(all(Decimal(x['cashJpy'])>=0 and x['openCount']<=3 for x in exit_early['snapshots']))
        self.assertTrue(all(x['quantity']%100==0 for x in exit_early['funded'].values()))
        self.assertEqual(r.classify(exit_early)[rows[4]['entryId']],'Replacement')

    def test_unresolved_exit_does_not_release_or_fabricate_equity(self):
        cohort,rows,raw,terminal,early=fixture()
        early[rows[0]['entryId']]['exitPrice']=None
        result=integ.replay(v0.IM,3,cohort,rows,raw,early)
        self.assertNotIn(rows[4]['entryId'],result['funded'])
        self.assertIn(rows[0]['entryId'],result['unresolvedEntryIds'])
        self.assertFalse(integ.daily(result,cohort['sessions'])[0][-1]['certified'])

    def test_attribution_currency_identity_and_null(self):
        cohort,rows,raw,terminal,early=fixture()
        base=integ.replay(v0.IM,3,cohort,rows,raw,terminal)
        changed=integ.replay(v0.IM,3,cohort,rows,raw,early)
        x=r.pnl_delta(base,changed)
        self.assertEqual(Decimal(x['closedPnlDeltaJpy']),Decimal(x['certifiedFinalEquityDeltaJpy']))
        incomplete=copy.deepcopy(changed);incomplete['snapshots'][-1]['equityJpy']=None
        self.assertIsNone(r.pnl_delta(base,incomplete)['certifiedFinalEquityDeltaJpy'])

    def test_future_high_cannot_alter_funding(self):
        cohort,rows,raw,terminal,early=fixture()
        one=integ.replay(v0.IM,3,cohort,rows,raw,early)
        changed=copy.deepcopy(raw)
        changed[f'{cohort["sessions"][0]}|LATE'][625]=[625,100,10000,1,100,1,100]
        two=integ.replay(v0.IM,3,cohort,rows,changed,early)
        self.assertEqual(one['funded'],two['funded'])

if __name__=='__main__':unittest.main()
