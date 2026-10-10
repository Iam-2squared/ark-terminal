import unittest

from scripts.phase57_cash_portfolio_r37 import (
    SizedCashPortfolio, assert_reproducible, evaluator_bucket_attribution,
    portfolio_scorecard,
)

T0='2025-07-03T09:01:00+09:00'
T1='2025-07-03T09:02:00+09:00'


def intent(i, now=T0, price='1000', rank=1, **changes):
    row=dict(entryId=f'e{i}',symbol=f'S{i}',timestamp=now,entryKnownAt=now,
             effectiveEntryPrice=price,newEligibleRank=rank,savedV1Score='10',
             rankKnownAt=now,side='LONG',account='CASH')
    row.update(changes);return row


def exit_event(i, confirmed=True, price='1100', now=T1):
    return dict(entryId=f'e{i}',timestamp=now,knownAt=now,
                price=price if confirmed else None,confirmed=confirmed)


def mark(i, now=T1, price='1000'):
    return {f'e{i}':dict(timestamp=now,knownAt=now,price=price)}


FREEZE={'outcome':'SELECT','selectedCandidateId':'NEW_EXIT_PRECOMMITTED_01',
        'freezeCommit':'a'*40}


class SizedPortfolioTests(unittest.TestCase):
    def test_exact_equity_over_max_n_sizing(self):
        for cap, expected in ((3,300),(4,200),(5,200)):
            p=SizedCashPortfolio(cap)
            out=p.step(T0,[intent(1)])
            self.assertEqual(out['sizing'][0]['quantity'],expected)
            self.assertGreaterEqual(float(out['ledger']['cashJpy']),0)

    def test_confirmed_exit_cash_precedes_new_sizing(self):
        p=SizedCashPortfolio(3)
        p.step(T0,[intent(1,price='3333')])
        out=p.step(T1,[intent(2,now=T1,price='1000')],[exit_event(1)],{})
        self.assertEqual(out['postExitPreview']['events'][0]['status'],'CLOSED')
        self.assertEqual(out['sizing'][0]['status'],'SIZED')
        # The confirmed loss is reflected in post-EXIT equity before sizing.
        self.assertEqual(out['sizing'][0]['quantity'],200)

    def test_missing_fresh_mark_blocks_all_new_sizing_without_stale_substitute(self):
        p=SizedCashPortfolio(3)
        p.step(T0,[intent(1)])
        out=p.step(T1,[intent(2,now=T1)],marks={})
        self.assertFalse(out['sizingResolved'])
        self.assertEqual(out['sizing'][0]['reason'],'MISSING_FRESH_MARK_UNRESOLVED_SIZING')
        self.assertEqual(out['ledger']['openSymbols'],1)

    def test_unresolved_exit_releases_neither_cash_nor_slot(self):
        p=SizedCashPortfolio(3)
        p.step(T0,[intent(i,rank=i) for i in (1,2,3)])
        out=p.step(T1,[intent(4,now=T1)],
                   [exit_event(1,confirmed=False)],
                   {**mark(1),**mark(2),**mark(3)})
        self.assertEqual(out['postExitPreview']['events'][0]['status'],'UNRESOLVED_NO_CASH_RELEASE')
        self.assertEqual(out['sizing'][0]['reason'],'MAX_CONCURRENT_SYMBOLS')

    def test_outcome_fields_cannot_enter_sizing_intent(self):
        p=SizedCashPortfolio(3)
        for field in ('bucket','futureHigh','finalPnl','capture','exitPrice'):
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'ALLOWLIST'):
                p.step(T0,[intent(1,**{field:99})])

    def test_rejected_intent_cannot_reappear_later(self):
        p=SizedCashPortfolio(3)
        p.step(T0,[intent(1,price='999999')])
        with self.assertRaisesRegex(ValueError,'ENTRY_ALREADY_PROCESSED'):
            p.step(T1,[intent(1,now=T1,price='1')])

    def test_score_and_bucket_helpers_require_select_freeze(self):
        with self.assertRaisesRegex(ValueError,'NO_SELECTION'):
            portfolio_scorecard(freeze={'outcome':'NO_SELECTION_STOP'},snapshots=[],
                                closed_trades=[],ledger_events=[])
        with self.assertRaisesRegex(ValueError,'NO_SELECTION'):
            evaluator_bucket_attribution(freeze={'outcome':'NO_SELECTION_STOP'},opportunities=[])

    def test_evaluator_attribution_is_posthoc_and_separate(self):
        rows=[dict(opportunity='a',bucket='>=5%',entered=True,entryNotionalJpy='300000',
                   realizedCapturePct='60'),
              dict(opportunity='b',bucket='>=5%',entered=False,entryNotionalJpy='0',
                   realizedCapturePct=None),
              dict(opportunity='c',bucket='2-3%',entered=True,entryNotionalJpy='200000',
                   realizedCapturePct='50')]
        out=evaluator_bucket_attribution(freeze=FREEZE,opportunities=rows)
        self.assertEqual(out['winnerN'],2);self.assertEqual(out['reachedN'],1)
        self.assertFalse(out['fedBackToRankingOrSizing'])

    def test_portfolio_scorecard_uses_matched_complete_equity_exposure(self):
        snaps=[{'equityJpy':'1000000','cashJpy':'500000','grossExposureJpy':'500000',
                'positions':{'e1':{'cost':'500000'}}},
               {'equityJpy':'1100000','cashJpy':'1100000','grossExposureJpy':'0',
                'positions':{}}]
        trades=[{'realizedPnlJpy':'100000','entryNotionalJpy':'500000',
                 'exitNotionalJpy':'600000'}]
        out=portfolio_scorecard(freeze=FREEZE,snapshots=snaps,closed_trades=trades,
                                ledger_events=[])
        self.assertEqual(out['portfolioReturnPct'],'10.0')
        self.assertEqual(out['capitalUtilizationMean'],'0.25')
        self.assertEqual(out['maximumSinglePositionEquityShare'],'0.5')

    def test_reproducibility_hash(self):
        self.assertEqual(assert_reproducible({'b':2,'a':1},{'a':1,'b':2}),
                         assert_reproducible({'a':1,'b':2},{'b':2,'a':1}))
        with self.assertRaisesRegex(ValueError,'RUN_AB'):
            assert_reproducible({'a':1},{'a':2})


if __name__=='__main__':unittest.main()
