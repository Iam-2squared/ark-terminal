"""Synthetic contract and causal checks; never opens Development performance."""
import copy
import datetime as dt
import json
import tempfile
import unittest
from unittest.mock import patch

from scripts import phase57_replacement_capital as rc
from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_capital_rank_v2 as old


DAY='2025-07-22'


def intent(symbol, minute, price='1000'):
    eid=f'{DAY}|{symbol}|{minute}'
    now=v0.minute_stamp(DAY,minute)
    return {'entryId':eid,'symbol':symbol,'timestamp':now,'entryKnownAt':now,
            'effectiveEntryPrice':price,'newEligibleRank':1,'savedV1Score':1.0,
            'rankKnownAt':now,'side':'LONG','account':'CASH'}


class ReplacementCapitalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=rc.contract()

    def fixture(self, prob=.8, confirm=True):
        a,b=intent('AAA',570),intent('BBB',620)
        raw={f'{DAY}|AAA':{570:[570,1000,1000,1000,1000,1],
             620:[620,1050,1050,1050,1050,1],930:[930,1050,1050,1050,1050,1]},
             f'{DAY}|BBB':{620:[620,1000,1000,1000,1000,1],
             930:[930,1005,1005,1005,1005,1]}}
        exits={a['entryId']:{'session':DAY,'exitMinute':620,'exitPrice':1050 if confirm else None,
                            'exitKind':'MODEL_EXIT'},
               b['entryId']:{'session':DAY,'exitMinute':930,'exitPrice':1005,'exitKind':'FORCED_TERMINAL'}}
        scores={a['entryId']:9.0,b['entryId']:4.0}
        pred={'magnitude':{a['entryId']:6.0,b['entryId']:4.0},
              'prob3':{a['entryId']:.8,b['entryId']:prob}}
        return [a,b],raw,exits,scores,pred

    def run_fixture(self, prob=.8, confirm=True):
        rows,raw,exits,scores,pred=self.fixture(prob,confirm)
        return rc.replay(v0.IM,3,{'sessions':[DAY]},rows,raw,exits,
                         'RC_MAG_FLOOR',scores,pred)

    def test_frozen_pins_and_safety(self):
        p=self.protocol
        self.assertEqual(p['entryFreezeCommit'],'4878a1cc53430e816261dea0fb16aeb53b3c238d')
        self.assertEqual(p['exit']['protocolSha256'],
                         '011b4959bf7cd343694f44e2986d13d87c07b6fa238dc326f5273e86885afe18')
        self.assertEqual(p['allocation']['cashJpy'],1000000)
        self.assertEqual(p['allocation']['capacity'],3)
        self.assertEqual(p['allocation']['sharesPerLot'],100)
        self.assertEqual(p['learning']['fitCount'],16)
        self.assertEqual(len(p['learning']['featureNames']),255)
        self.assertEqual(len(p['safety']),9)
        self.assertFalse(any(p['safety'].values()))

    def test_exit_before_same_timestamp_entry_and_replacement(self):
        ledger=self.run_fixture()
        a,b=intent('AAA',570),intent('BBB',620)
        event=next(x for x in ledger['events'] if x['minute']==620)
        self.assertEqual(event['exitEvents'][0]['status'],'CLOSED')
        self.assertTrue(event['context']['isReplacement'])
        self.assertEqual(event['context']['confirmedSameDayModelExits'],1)
        self.assertEqual(ledger['funded'][b['entryId']]['capitalContext'],'replacement')
        self.assertIn(a['entryId'],ledger['funded'])
        self.assertEqual(len(ledger['closed']),2)
        self.assertTrue(all(int(x['quantity'])%100==0 for x in ledger['funded'].values()))
        self.assertTrue(all(float(x['cashJpy'])>=0 and x['openCount']<=3
                            for x in ledger['snapshots']))

    def test_floor_rejects_without_retroactive_entry(self):
        ledger=self.run_fixture(prob=.49)
        event=next(x for x in ledger['events'] if x['minute']==620)
        self.assertEqual(event['sizing'][0]['reason'],'QUALITY_FLOOR')
        self.assertNotIn(intent('BBB',620)['entryId'],ledger['funded'])
        self.assertEqual(len(ledger['funded']),1)

    def test_unconfirmed_exit_never_releases_cash_or_replacement(self):
        ledger=self.run_fixture(confirm=False)
        event=next(x for x in ledger['events'] if x['minute']==620)
        self.assertEqual(event['exitEvents'][0]['status'],'UNRESOLVED_NO_CASH_RELEASE')
        self.assertFalse(event['context']['isReplacement'])
        self.assertEqual(event['context']['cashAvailableJpy'],'700000')
        self.assertEqual(ledger['unresolvedEntryIds'],[intent('AAA',570)['entryId']])

    def test_future_outcome_and_label_cannot_affect_funding(self):
        rows,raw,exits,scores,pred=self.fixture()
        one=rc.replay(v0.IM,3,{'sessions':[DAY]},rows,raw,exits,
                      'RC_PROB3_FLOOR',scores,pred)
        raw2=copy.deepcopy(raw)
        raw2[f'{DAY}|BBB'][625]=[625,1000,5000,990,1000,1]
        two=rc.replay(v0.IM,3,{'sessions':[DAY]},rows,raw2,exits,
                      'RC_PROB3_FLOOR',scores,pred)
        self.assertEqual(one['funded'],two['funded'])
        with self.assertRaises(ValueError):
            rc.ranked_quality(rows,'RC_MAG_FLOOR',{'isReplacement':True},
                              scores,{'magnitude':{},'prob3':{}})

    def test_rank_and_quality_context_are_deterministic(self):
        rows,_,_,scores,pred=self.fixture()
        initial=rc.ranked_quality(rows,'RC_MAG_FLOOR',{'isReplacement':False},scores,pred)
        replacement=rc.ranked_quality(rows,'RC_MAG_FLOOR',{'isReplacement':True},scores,pred)
        self.assertEqual(initial[0][0]['entryId'],rows[0]['entryId'])
        self.assertEqual(replacement[0][0]['entryId'],rows[0]['entryId'])
        self.assertEqual(replacement,rc.ranked_quality(rows,'RC_MAG_FLOOR',
                         {'isReplacement':True},scores,pred))

    def test_no_future_entry_or_retroactive_eligibility(self):
        rows,raw,exits,scores,pred=self.fixture()
        rows[1]['entryKnownAt']=v0.minute_stamp(DAY,621)
        with self.assertRaisesRegex(ValueError,'FUTURE_ENTRY_INFORMATION'):
            rc.replay(v0.IM,3,{'sessions':[DAY]},rows,raw,exits,
                      'RC_MAG_FLOOR',scores,pred)
        rows[1]['entryKnownAt']=rows[1]['timestamp']
        rows[1]['timestamp']=v0.minute_stamp(DAY,621)
        with self.assertRaisesRegex(ValueError,'ENTRY_ID_TIME_OR_SYMBOL_DRIFT'):
            rc.replay(v0.IM,3,{'sessions':[DAY]},rows,raw,exits,
                      'RC_MAG_FLOOR',scores,pred)

    def test_lot_infeasibility_preserves_cash(self):
        rows,raw,exits,scores,pred=self.fixture()
        rows[0]['effectiveEntryPrice']='4000'  # one lot exceeds frozen equity/3 target
        result=rc.replay(v0.IM,3,{'sessions':[DAY]},rows,raw,exits,
                         'RC_MAG_FLOOR',scores,pred)
        first=next(x for x in result['events'] if x['minute']==570)
        self.assertEqual(first['sizing'][0]['reason'],'NO_100_SHARE_LOT_WITHIN_TARGET_AND_CASH')
        self.assertEqual(first['cashJpy'],'1000000')
        self.assertFalse(next(x for x in result['events'] if x['minute']==620)['context']['isReplacement'])

    def test_missing_eod_mark_is_null_and_unresolved_never_cash(self):
        rows,raw,exits,scores,pred=self.fixture()
        exits[rows[1]['entryId']]['exitPrice']=None
        raw[f'{DAY}|BBB'].pop(930)
        result=rc.replay(v0.IM,3,{'sessions':[DAY]},rows,raw,exits,
                         'RC_MAG_FLOOR',scores,pred)
        last=result['snapshots'][-1]
        self.assertIsNone(last['equityJpy'])
        self.assertIsNone(last['unrealizedPnlJpy'])
        self.assertEqual(result['unresolvedEntryIds'],[rows[1]['entryId']])
        daily,summary=rc.integ.daily(result,[DAY])
        self.assertIsNone(daily[0]['dailyReturn'])
        self.assertIsNone(summary['geometric'])

    def test_bucket_and_context_reconcile(self):
        result=self.run_fixture()
        entries=list(result['funded'])
        evaluator={entries[0]:{'postUpsidePct':6.0},entries[1]:{'postUpsidePct':.5}}
        groups={kind:rc.group_quality(result,evaluator,kind) for kind in
                ('initial','replacement','combined')}
        self.assertEqual((groups['initial']['N'],groups['replacement']['N'],
                          groups['combined']['N']),(1,1,2))
        self.assertEqual(groups['combined']['ge5Count'],1)
        self.assertEqual(sum(x['count'] for x in groups['combined']['buckets']),2)
        self.assertEqual(sum(float(groups[k]['allocatedCapitalJpy'])
                             for k in ('initial','replacement')),
                         float(groups['combined']['allocatedCapitalJpy']))

    def test_temporal_oof_purge_and_scored_label_isolation(self):
        p=self.protocol
        sessions=sorted(set(s for fold in p['learning']['split'] for s in
                            fold['trainSessions']+fold['testSessions']))
        intents={arm:[] for arm in v0.ARMS};evals={arm:{} for arm in v0.ARMS}
        tables={arm:{} for arm in v0.ARMS}
        for arm in v0.ARMS:
            for index,day in enumerate(sessions):
                x=intent('S'+str(index),570);x['timestamp']=v0.minute_stamp(day,570)
                x['entryKnownAt']=x['rankKnownAt']=x['timestamp']
                x['entryId']=day+'|S'+str(index)+'|570'
                intents[arm].append(x)
                tables[arm][x['entryId']]=[float(index%3)]*254
                evals[arm][x['entryId']]={'postUpsidePct':6.0 if index%2 else 1.0}
        data=(None,None,None,intents,evals,None,None,None,None,None)
        with patch.object(old,'feature_table',return_value=tables):
            first,folds,_=rc.temporal_oof(data,p)
            changed=copy.deepcopy(evals)
            first_test=p['learning']['split'][0]['testSessions'][0]
            for arm in v0.ARMS:changed[arm][first_test+'|S'+str(sessions.index(first_test))+'|570']['postUpsidePct']=19.0
            second,_,_=rc.temporal_oof((None,None,None,intents,changed,None,None,None,None,None),p)
        self.assertEqual(len(folds),16)
        for arm in v0.ARMS:
            test_ids={x['entryId'] for x in intents[arm] if x['timestamp'][:10] in
                      p['learning']['split'][0]['testSessions']}
            for target in ('magnitude','prob3'):
                self.assertEqual({i:first[arm][target][i] for i in test_ids},
                                 {i:second[arm][target][i] for i in test_ids})

if __name__=='__main__':unittest.main()
