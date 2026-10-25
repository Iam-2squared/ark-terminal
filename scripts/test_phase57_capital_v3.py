"""Focused safety and selection regressions for Capital v3."""
import copy
import unittest

from scripts import phase57_capital_v3 as v3


class CapitalV3Tests(unittest.TestCase):
    def test_contract_geometry_and_feature_identity(self):
        pre, geo, audit, gate, names = v3.contract()
        self.assertEqual(len(names), 254)
        self.assertEqual([x['id'] for x in pre['learning']['candidates']], gate['candidateIds'])
        self.assertEqual(geo['arms']['R1']['folds'][2]['fundedControl'], 0)
        self.assertFalse(any(gate['safety'].values()))

    def test_rank_applies_only_at_the_exact_entry_event(self):
        rows=[{'entryId':'a','timestamp':'2025-07-22T09:50:00+09:00','newEligibleRank':1,
               'savedV1Score':3,'symbol':'A','rankKnownAt':'2025-07-22T09:20:00+09:00'},
              {'entryId':'b','timestamp':'2025-07-22T09:50:00+09:00','newEligibleRank':2,
               'savedV1Score':2,'symbol':'B','rankKnownAt':'2025-07-22T09:20:00+09:00'},
              {'entryId':'c','timestamp':'2025-07-22T10:20:00+09:00','newEligibleRank':1,
               'savedV1Score':1,'symbol':'C','rankKnownAt':'2025-07-22T10:00:00+09:00'}]
        original=copy.deepcopy(rows)
        result=v3.ranked_intents(rows,{'a':0.1,'b':0.9,'c':0.2})
        self.assertEqual([r['newEligibleRank'] for r in result],[2,1,1])
        self.assertEqual(result[0]['rankKnownAt'],rows[0]['timestamp'])
        self.assertEqual(rows,original)
        with self.assertRaisesRegex(ValueError,'MISSING_OOF'):
            v3.ranked_intents(rows,{'a':0.1,'b':0.9})

    def test_reason_priority_for_competing_cash_and_unresolved(self):
        row={'entryId':'x','status':'REJECTED','reason':'MAX_CONCURRENT_SYMBOLS'}
        event={'sizing':[{'entryId':'w','status':'SIZED'},row]}
        self.assertEqual(v3.reason_for_miss(row,event,{'openCount':3,'unresolvedCount':0},{}),'RANK_LOSS')
        self.assertEqual(v3.reason_for_miss(row,event,{'openCount':4,'unresolvedCount':0},{}),'CAPACITY_FULL')
        self.assertEqual(v3.reason_for_miss(row,event,{'openCount':4,'unresolvedCount':1},{}),'UNRESOLVED_CASH_LOCK')
        row={'entryId':'x','status':'REJECTED','reason':'NO_100_SHARE_LOT_WITHIN_TARGET_AND_CASH','cashBeforeSizingJpy':'900'}
        event={'sizing':[row]}
        source={'x':{'effectiveEntryPrice':10}}
        self.assertEqual(v3.reason_for_miss(row,event,{'openCount':0,'unresolvedCount':0},source),'INSUFFICIENT_CASH')
        row['cashBeforeSizingJpy']='10000'
        self.assertEqual(v3.reason_for_miss(row,event,{'openCount':0,'unresolvedCount':0},source),'LOT_INFEASIBLE')

    def test_missing_eod_does_not_splice_daily_returns(self):
        sessions=['2025-07-22','2025-07-23','2025-07-24']
        snaps=[{'session':sessions[0],'minute':930,'openCount':0,'unresolvedCount':0,
                'equityValid':True,'equityJpy':'1010000','cashJpy':'1010000'},
               {'session':sessions[1],'minute':930,'openCount':1,'unresolvedCount':1,
                'equityValid':False,'equityJpy':None,'cashJpy':'700000'},
               {'session':sessions[2],'minute':930,'openCount':0,'unresolvedCount':0,
                'equityValid':True,'equityJpy':'1020000','cashJpy':'1020000'}]
        result=v3.certified_eod({'snapshots':snaps,'funded':{}},sessions)
        self.assertEqual(result['certifiedEodSessions'],2)
        self.assertEqual(result['nullSessions'],1)
        self.assertEqual(result['daily'][0]['dailyReturn'],0.01)
        self.assertIsNone(result['daily'][2]['dailyReturn'])
        self.assertIsNone(result['statistics']['geometric'])


if __name__=='__main__':unittest.main()
