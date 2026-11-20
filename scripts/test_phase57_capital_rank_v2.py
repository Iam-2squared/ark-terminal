"""Small synthetic causality and accounting checks; no candidate performance."""
import copy
import math
import unittest

from scripts import phase57_capital_rank_v2 as rank
from scripts import phase57_development_integrated_v0 as v0


class CapitalRankV2Tests(unittest.TestCase):
    def setUp(self):
        self.p,self.audit=rank.contract()
        self.day='2025-07-03'
        self.intent={'entryId':self.day+'|23340|570','symbol':'23340',
                     'timestamp':self.day+'T09:30:00+09:00',
                     'entryKnownAt':self.day+'T09:30:00+09:00',
                     'effectiveEntryPrice':100,'newEligibleRank':1,
                     'savedV1Score':10,'rankKnownAt':self.day+'T09:30:00+09:00',
                     'side':'LONG','account':'CASH'}
        self.origin={'decisionTimestamp':self.intent['rankKnownAt'],
                     'decisionPrice':100,'newEligibleRank':1,'savedV1Score':10}
        self.path={'previousSession':'2025-07-02','previous':[],
                   'today':[[minute,100,100,100,100,1000,100000]
                            for minute in range(540,570)]}

    def values(self,set_name='C',path=None,intent=None,origin=None):
        names=self.p['features']['sets'][set_name]
        return rank.make_features(intent or self.intent,path or self.path,
                                  origin or self.origin,names,
                                  self.audit['pattern187'] if set_name=='C' else [])

    def test_frozen_protocol_exact_space_and_safety(self):
        self.assertEqual(rank.PROTOCOL_SHA256,v0.digest(rank.PROTOCOL))
        self.assertEqual(len(self.p['selection']['candidateIds']),3)
        self.assertEqual(self.p['selection']['expectedFits'],24)
        self.assertEqual(len(rank.registry_names()),476)
        self.assertEqual(len(self.audit['pattern187']),187)
        self.assertEqual(len(rank.json.loads(rank.WINDOW.read_text())['portfolioSessions']),24)
        self.assertEqual(self.p['safety'],dict.fromkeys(self.p['safety'],False))

    def test_frozen_temporal_folds_and_purge(self):
        test=[]
        for fold in self.p['split']['folds']:
            self.assertEqual(len(fold['purgeSessions']),2)
            self.assertLess(fold['trainSessions'][-1],fold['purgeSessions'][0])
            self.assertLess(fold['purgeSessions'][-1],fold['testSessions'][0])
            test.extend(fold['testSessions'])
        self.assertEqual(len(set(test)),24)

    def test_future_suffix_isolation_all_candidates(self):
        changed=copy.deepcopy(self.path)
        changed['today'].extend([[minute,999,999,999,999,1000,999000]
                                 for minute in (570,571,930)])
        for key in 'ABC':self.assertEqual(self.values(key),self.values(key,path=changed))

    def test_unknown_signal_distinct_from_false(self):
        names=self.p['features']['sets']['B']
        vals=self.values('B')
        for family in rank.registry.SIGNAL_FAMILIES:
            self.assertEqual(sum(vals[names.index(f'signal.{family}.{x}')]
                                 for x in ('TRUE','FALSE','UNKNOWN')),1)

    def test_decision_now_and_future_feature_denylist(self):
        late=copy.deepcopy(self.intent)
        late['rankKnownAt']=self.day+'T09:31:00+09:00'
        with self.assertRaisesRegex(ValueError,'RANK_KNOWN_AFTER_ENTRY'):self.values('A',intent=late)
        infected=copy.deepcopy(self.intent)
        infected['futureHigh']=130
        with self.assertRaisesRegex(ValueError,'OUTCOME_IN_RANK_INTENT'):self.values('A',intent=infected)
        infected.pop('futureHigh')
        infected['target']=1
        with self.assertRaisesRegex(ValueError,'OUTCOME_IN_RANK_INTENT'):self.values('A',intent=infected)

    def test_r1_score_entry_timestamp_validation(self):
        r1=copy.deepcopy(self.intent)
        r1['timestamp']=self.day+'T09:35:00+09:00'
        r1['entryKnownAt']=r1['timestamp']
        r1['entryId']=self.day+'|23340|575'
        self.assertEqual(len(self.values('B',intent=r1)),67)

    def test_state_today_unclosed_bar_rejected_by_suffix(self):
        a=self.values('B')
        bad=copy.deepcopy(self.path)
        bad['today'].append([570,100,200,100,200,1000,200000])
        self.assertEqual(self.values('B',path=bad),a)

    def test_no_imputed_future_when_auction_missing(self):
        self.assertFalse(any(row[0]==930 for row in self.path['today']))
        self.assertEqual(self.values('A'),self.values('A',path=self.path))

    def test_feature_table_never_reads_evaluator_mapping(self):
        class ForbiddenEvaluator:
            def __getitem__(self,key):raise AssertionError('EVALUATOR_ENTERED_FEATURE_PIPELINE')
        identifier=self.intent['entryId'].rsplit('|',1)[0]
        data=(self.p,self.audit,{},
              {arm:[self.intent] for arm in v0.ARMS},ForbiddenEvaluator(),
              {},{}, {identifier:self.path},{identifier:self.origin}, {})
        result=rank.feature_table(data,self.p['features']['sets']['A'])
        for arm in v0.ARMS:self.assertEqual(len(result[arm][self.intent['entryId']]),8)

    def test_old_rank_control_and_score_order(self):
        intents=[]
        labels={}
        evaluation={}
        for idx in range(4):
            x=copy.deepcopy(self.intent);x['entryId']=f'{self.day}|{idx}|570'
            x['symbol']=str(idx);x['newEligibleRank']=idx+1
            intents.append(x);labels[x['entryId']]=int(idx==3)
            evaluation[x['entryId']]={'postUpsidePct':6 if idx==3 else 0,
                                     'canonicalBucket':'<5%'}
        score={x['entryId']:int(x['symbol'])/4 for x in intents}
        old=rank.ranked_enrichment(v0.IM,intents,evaluation,labels,{self.day})
        new=rank.ranked_enrichment(v0.IM,intents,evaluation,labels,{self.day},score)
        self.assertEqual(old['top']['1']['hit'],0)
        self.assertEqual(new['top']['1']['hit'],1)
        self.assertEqual(new['top']['3']['selected'],3)

    def test_select_zero_and_exact_tie(self):
        cards={key:{arm:{'top':{'3':{'enrichment':1.2}}} for arm in v0.ARMS}
               for key in ('A','B')}
        self.assertIsNone(rank.select_from_gate({'A':{'pass':False}},cards))
        self.assertIsNone(rank.select_from_gate({'A':{'pass':True},'B':{'pass':True}},cards))

    def test_daily_formula_and_prev_end_composition(self):
        ledger={'snapshots':[{'timestamp':self.day+'T09:00:00+09:00','equityJpy':'1000000',
                              'cashJpy':'1000000','grossExposureJpy':'0','utilization':0,'equityValid':True},
                             {'timestamp':self.day+'T15:30:00+09:00','equityJpy':'1100000',
                              'cashJpy':'1100000','grossExposureJpy':'0','utilization':0,'equityValid':True},
                             {'timestamp':'2025-07-04T09:00:00+09:00','equityJpy':'1100000',
                              'cashJpy':'1100000','grossExposureJpy':'0','utilization':0,'equityValid':True},
                             {'timestamp':'2025-07-04T15:30:00+09:00','equityJpy':'1210000',
                              'cashJpy':'1210000','grossExposureJpy':'0','utilization':0,'equityValid':True}],
                'endOpenEntryIds':[]}
        card=rank.daily_reporting(ledger)
        self.assertAlmostEqual(card['meanPct'],10)
        self.assertAlmostEqual(card['geometricPct'],10)
        self.assertAlmostEqual(card['portfolioReturnPct'],21)
        self.assertEqual(card['daily'][1]['startEquityJpy'],'1100000')
        self.assertAlmostEqual(card['mechanicalCompoundingPct']['20'],100*(1.1**20-1))

    def test_null_session_never_fabricates_daily_or_compound(self):
        ledger={'snapshots':[{'timestamp':self.day+'T09:00:00+09:00','equityJpy':None,
                              'cashJpy':'1','grossExposureJpy':None,'utilization':None,'equityValid':False}],
                'endOpenEntryIds':['censored']}
        card=rank.daily_reporting(ledger)
        self.assertIsNone(card['daily'][0]['dailyReturnPct'])
        self.assertIsNone(card['geometricPct'])
        self.assertIsNone(card['mechanicalCompoundingPct'])


if __name__=='__main__':unittest.main()
