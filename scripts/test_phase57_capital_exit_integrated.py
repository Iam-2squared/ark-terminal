"""Synthetic ordering, 100-share cash recycling and evaluator isolation."""
import copy
import unittest
from decimal import Decimal

from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_development_integrated_v1 as v1
from scripts import phase57_capital_exit_integrated as integrated

DAY='2025-07-22'


def stamp(m): return v0.minute_stamp(DAY,m)


def intent(sym,minute,rank):
    return {'entryId':f'{DAY}|{sym}|{minute}', 'symbol':sym,
            'timestamp':stamp(minute),'entryKnownAt':stamp(minute),
            'effectiveEntryPrice':100.05,'newEligibleRank':rank,
            'savedV1Score':float(10-rank),'rankKnownAt':stamp(minute),
            'side':'LONG','account':'CASH'}


def bar(minute,price):
    return [minute,price,price,price,price,1000,1000*price]


def fixture():
    rows=[intent(f'A{i}',578,i) for i in (1,2,3)]
    rows.extend([intent('TOO_EARLY',590,1),intent('LATE',600,1)])
    raw={f'{DAY}|{r["symbol"]}':{578:bar(578,100),600:bar(600,105),930:bar(930,110)}
         for r in rows}
    raw[f'{DAY}|TOO_EARLY'][590]=bar(590,100)
    terminal={r['entryId']:{'session':DAY,'exitMinute':930,
                            'exitPrice':110,'exitKind':'FORCED_TERMINAL'} for r in rows}
    model=copy.deepcopy(terminal)
    model[rows[0]['entryId']]={'session':DAY,'exitMinute':600,
                                'exitPrice':105,'exitKind':'MODEL_EXIT'}
    return {'sessions':[DAY]},rows,raw,terminal,model


class IntegratedSynthetic(unittest.TestCase):
    def test_frozen_contract_and_sources(self):
        p=integrated.contract()
        self.assertEqual(p['capacity'],3)
        self.assertEqual(len(p['sessions']),24)
        self.assertFalse(any(p['safety'].values()))

    def test_same_time_exit_precedes_entry_and_recycling_is_exclusive(self):
        cohort,rows,raw,terminal,model=fixture()
        base=integrated.replay(v0.IM,3,cohort,rows,raw,terminal)
        early=integrated.replay(v0.IM,3,cohort,rows,raw,model)
        self.assertEqual(len(base['funded']),3)
        self.assertEqual(len(early['funded']),4)
        self.assertNotIn(rows[3]['entryId'],early['funded'])
        self.assertIn(rows[4]['entryId'],early['funded'])
        event=next(x for x in early['events'] if x['minute']==600)
        self.assertEqual(event['exitEvents'][0]['status'],'CLOSED')
        self.assertEqual(event['sizing'][0]['status'],'SIZED')
        self.assertLess(Decimal(base['finalCashJpy']),Decimal(early['finalCashJpy']))
        self.assertEqual(len(early['closed']),4)
        self.assertTrue(all(x['quantity']%100==0 for x in early['funded'].values()))
        self.assertTrue(all(Decimal(x['cashJpy'])>=0 and x['openCount']<=3
                            for x in early['snapshots']))

    def test_no_unconfirmed_cash_and_null_cross_session(self):
        cohort,rows,raw,_,model=fixture()
        model[rows[0]['entryId']]['exitPrice']=None
        early=integrated.replay(v0.IM,3,cohort,rows,raw,model)
        self.assertEqual(len(early['funded']),3)
        self.assertNotIn(rows[4]['entryId'],early['funded'])
        event=next(x for x in early['events'] if x['minute']==600)
        self.assertEqual(event['exitEvents'][0]['status'],'UNRESOLVED_NO_CASH_RELEASE')
        self.assertIn(rows[0]['entryId'],early['endOpenEntryIds'])
        next_day='2025-07-23'
        cohort['sessions'].append(next_day)
        late=integrated.replay(v0.IM,3,cohort,rows,raw,model)
        self.assertIsNone(late['snapshots'][-1]['equityJpy'])

    def test_future_fields_cannot_enter_rank_or_sizing(self):
        cohort,rows,raw,_,model=fixture()
        first=integrated.replay(v0.IM,3,cohort,rows,raw,model)
        second=integrated.replay(v0.IM,3,cohort,copy.deepcopy(rows),copy.deepcopy(raw),model)
        self.assertEqual(v0.canonical(first),v0.canonical(second))
        rows[0]['futureHigh']=1000000
        with self.assertRaisesRegex(ValueError,'SIZING_INTENT_ALLOWLIST'):
            integrated.replay(v0.IM,3,cohort,rows,raw,model)

    def test_bucket_boundaries_and_censored(self):
        f=integrated.upside_bucket
        self.assertEqual([f(x) for x in (-.1,0,.99,1,2,3,4,5,7.5,10,None)],
                         ['<0%','0–1%','0–1%','1–2%','2–3%','3–4%',
                          '4–5%','5–7.5%','7.5–10%','>=10%',
                          'UNKNOWN/CENSORED'])

    def test_daily_gap_preserved(self):
        sessions=['2025-07-22','2025-07-23','2025-07-24','2025-07-25']
        amounts=['1010000',None,'1020000','1030000']
        snapshots=[{'session':s,'minute':930,'openCount':0 if x else 1,
                    'unresolvedCount':0 if x else 1,'equityValid':x is not None,
                    'equityJpy':x,'cashJpy':x or '700000'}
                   for s,x in zip(sessions,amounts)]
        rows,stats=integrated.daily({'snapshots':snapshots},sessions)
        self.assertEqual(rows[0]['dailyReturn'],.01)
        self.assertEqual([r['dailyReturn'] for r in rows[1:3]],[None,None])
        self.assertAlmostEqual(rows[3]['dailyReturn'],103/102-1)
        self.assertIsNone(stats['geometric'])
        self.assertEqual(stats['validContiguousReturnDays'],2)

    def test_terminal_replay_matches_original_accounting(self):
        cohort,rows,raw,terminal,_=fixture()
        old=v1.replay(v0.IM,3,cohort,rows,terminal,raw)
        new=integrated.replay(v0.IM,3,cohort,rows,raw,terminal)
        self.assertEqual(v0.canonical(new),v0.canonical(old))


if __name__=='__main__':unittest.main()
