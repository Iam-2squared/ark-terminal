"""Synthetic reporting/accounting tests. No training or market-data requests."""
from __future__ import annotations

import copy
import datetime as dt
import json
import math
import unittest
from decimal import Decimal

from scripts import phase57_capital_endpoint_reconciliation as r

DAYS = ['2025-07-22', '2025-07-23']
EID = '2025-07-22|SYNTH|570'


def endpoints(values):
    return [{'session':(dt.date(2025,7,1)+dt.timedelta(days=i)).isoformat(),
             'equityJpy':None if v is None else str(v), 'certifiedFlatEod':v is not None}
            for i,v in enumerate(values)]


def fixture(missing_midday=False, unresolved=False):
    trade={'entryId':EID,'quantity':100,'effectiveEntryPrice':'100',
           'notionalJpy':'10000','entryTimestamp':r.timestamp(DAYS[0],570),'symbol':'SYNTH'}
    cash, realized = '990000', '0'
    position={'entryId':EID,'quantity':100,'costBasisJpy':'10000','markPrice':100,
              'markedNotionalJpy':'10000','markKnownAt':r.timestamp(DAYS[0],570),
              'missingReason':None,'unresolvedExit':False}
    size={'entryId':EID,'status':'SIZED','quantity':100,'costJpy':'10000',
          'cashBeforeSizingJpy':'1000000','cashAfterSizingJpy':cash}
    def snap(day, minute, money, eq, ps, pnl, valid=True):
        return {'session':day,'minute':minute,'timestamp':r.timestamp(day,minute),
                'cashJpy':money,'equityJpy':eq,'equityValid':valid,'positions':copy.deepcopy(ps),
                'openCount':len(ps),'unresolvedCount':sum(p['unresolvedExit'] for p in ps),
                'realizedPnlJpy':pnl,'grossExposureJpy':None if not valid else str(sum(r.dec(p['markedNotionalJpy']) for p in ps)),
                'unrealizedPnlJpy':None if not valid else str(sum(r.dec(p['markedNotionalJpy'])-r.dec(p['costBasisJpy']) for p in ps))}
    snapshots=[snap(DAYS[0],540,'1000000','1000000',[],'0'),
               snap(DAYS[0],570,cash,'1000000',[position],realized)]
    events=[{'session':DAYS[0],'minute':540,'cashJpy':'1000000','postEventEquityJpy':'1000000','exitEvents':[],'sizing':[]},
            {'session':DAYS[0],'minute':570,'cashJpy':cash,'postEventEquityJpy':'1000000','exitEvents':[],'sizing':[size]}]
    if missing_midday:
        missing=copy.deepcopy(position)
        missing.update(markPrice=None,markedNotionalJpy=None,markKnownAt=None,missingReason='NO_CROSS_LUNCH_MARK')
        snapshots.append(snap(DAYS[0],751,cash,None,[missing],realized,False))
        events.append({'session':DAYS[0],'minute':751,'cashJpy':cash,'postEventEquityJpy':None,'exitEvents':[],'sizing':[]})
    if unresolved:
        position.update(unresolvedExit=True,markPrice=None,markedNotionalJpy=None,
                        markKnownAt=None,missingReason='UNCERTIFIED_OVERNIGHT')
        snapshots.append(snap(DAYS[0],930,cash,None,[position],realized,False))
        events.append({'session':DAYS[0],'minute':930,'cashJpy':cash,'postEventEquityJpy':None,
                       'exitEvents':[{'entryId':EID,'kind':'EXIT','status':'UNRESOLVED_NO_CASH_RELEASE'}],'sizing':[]})
        snapshots.append(snap(DAYS[1],930,cash,None,[position],realized,False))
        events.append({'session':DAYS[1],'minute':930,'cashJpy':cash,'postEventEquityJpy':None,'exitEvents':[],'sizing':[]})
        closed=[]
    else:
        cash,realized='1000995','995'
        close={**trade,'exitTimestamp':r.timestamp(DAYS[0],930),'realizedPnlJpy':realized,'sellCostJpy':'5'}
        exit_event={'entryId':EID,'kind':'EXIT','status':'CLOSED','proceedsJpy':'11000','sellCostJpy':'5','realizedPnlJpy':realized}
        snapshots += [snap(DAYS[0],930,cash,cash,[],realized),snap(DAYS[1],930,cash,cash,[],realized)]
        events += [{'session':DAYS[0],'minute':930,'cashJpy':cash,'postEventEquityJpy':cash,'exitEvents':[exit_event],'sizing':[]},
                   {'session':DAYS[1],'minute':930,'cashJpy':cash,'postEventEquityJpy':cash,'exitEvents':[],'sizing':[]}]
        closed=[close]
    return {'capacity':3,'arm':'IMMEDIATE','funded':{EID:trade},'closed':closed,
            'events':events,'snapshots':snapshots,'finalCashJpy':cash,
            'endOpenEntryIds':[EID] if unresolved else [],'unresolvedEntryIds':[EID] if unresolved else [],
            'safety':dict.fromkeys(r.SAFETY_KEYS,False)}


class ArithmeticTests(unittest.TestCase):
    def test_mean_differs_from_geometric(self):
        m=r.endpoint_metrics(endpoints([1100000,990000]))
        self.assertAlmostEqual(m['arithmeticDailyPct'],0)
        self.assertAlmostEqual(m['endpointReturnPct'],-1)
        self.assertAlmostEqual(m['geometricPerScheduledSessionPct'],100*(.99**.5-1))

    def test_daily_series_telescope(self):
        m=r.endpoint_metrics(endpoints([1010000,990000,1020000]))
        self.assertAlmostEqual(math.prod(1+x['dailyReturnPct']/100 for x in m['daily']),1.02)

    def test_missing_day_not_zero(self):
        m=r.endpoint_metrics(endpoints([1100000,None,1210000,1331000]))
        self.assertEqual([x['dailyReturnPct'] for x in m['daily']],[10.0,None,None,10.0])
        self.assertIsNone(m['arithmeticDailyPct'])
        self.assertIsNone(m['medianDailyPct'])

    def test_scheduled_denominator_not_survivor_count(self):
        m=r.endpoint_metrics(endpoints([1100000,None,1210000,1331000]))
        self.assertEqual(m['scheduledSessions'],4)
        self.assertEqual(m['validDailyReturns'],2)
        self.assertAlmostEqual(m['geometricPerScheduledSessionPct'],100*(1.331**.25-1))

    def test_final_unknown_all_full_metrics_null(self):
        m=r.endpoint_metrics(endpoints([1100000,None]))
        for key in ('certifiedFinalEquityJpy','endpointReturnPct','geometricPerScheduledSessionPct',
                    'arithmeticDailyPct','medianDailyPct','mechanicalNotForecastPct','maxDrawdownEodPct'):
            self.assertIsNone(m[key],key)

    def test_no_splicing_known_days(self):
        m=r.endpoint_metrics(endpoints([1000000,None,1100000]))
        self.assertFalse(m['completeEodSeries'])
        self.assertIsNone(m['daily'][2]['dailyReturnPct'])

    def test_later_valid_adjacent_days_recover(self):
        m=r.endpoint_metrics(endpoints([None,1000000,1100000]))
        self.assertEqual(m['daily'][2]['dailyReturnPct'],10)

    def test_eod_drawdown_not_intraday(self):
        m=r.endpoint_metrics(endpoints([1100000,880000,1000000]))
        self.assertAlmostEqual(m['maxDrawdownEodPct'],-20)
        self.assertIsNone(m['strictIntradayMaxDrawdownPct'])

    def test_initial_equity_in_drawdown(self):
        m=r.endpoint_metrics(endpoints([900000,950000]))
        self.assertAlmostEqual(m['maxDrawdownEodPct'],-10)

    def test_no_drawdown_over_missing_eod(self):
        m=r.endpoint_metrics(endpoints([1100000,None,900000]))
        self.assertIsNone(m['maxDrawdownEodPct'])
        self.assertTrue(all(x['drawdownEodPct'] is None for x in m['daily']))

    def test_flat_no_trade_day_zero_valid(self):
        m=r.endpoint_metrics(endpoints([1000000,1000000]))
        self.assertEqual(m['arithmeticDailyPct'],0)
        self.assertEqual(m['positiveDayRate'],0)
        self.assertEqual(m['negativeDayRate'],0)

    def test_input_not_mutated(self):
        ep=endpoints([1100000,1000000]); before=copy.deepcopy(ep)
        r.endpoint_metrics(ep)
        self.assertEqual(ep,before)

    def test_duplicate_day_rejected(self):
        e=endpoints([1000000,1000000]);e[1]['session']=e[0]['session']
        with self.assertRaisesRegex(ValueError,'ENDPOINT_ORDER'):r.endpoint_metrics(e)

    def test_nonfinite_money_rejected(self):
        for v in ('NaN','Infinity',True,None):
            with self.assertRaises(ValueError):r.dec(v)

    def test_percentile_linear(self):
        self.assertEqual(r.percentile([0,10],.25),2.5)


class AccountingTests(unittest.TestCase):
    def test_valid_cash_book(self):
        a=r.audit_ledger(fixture(),DAYS)
        self.assertEqual(a['status'],'PASS')
        self.assertEqual(r.dec(a['finalCashJpy']),Decimal('1000995'))

    def test_midday_null_not_eod_null(self):
        a=r.audit_ledger(fixture(missing_midday=True),DAYS)
        self.assertEqual(a['intradayNullEvents'],1)
        m=r.endpoint_metrics(a['endpoints'])
        self.assertTrue(m['completeEodSeries'])
        self.assertAlmostEqual(m['endpointReturnPct'],.0995)

    def test_unresolved_not_cash_endpoint(self):
        a=r.audit_ledger(fixture(unresolved=True),DAYS)
        self.assertEqual(a['remainingOpen'],[EID])
        self.assertTrue(all(not x['certifiedFlatEod'] for x in a['endpoints']))

    def test_cash_is_not_equity_with_open_position(self):
        a=r.audit_ledger(fixture(unresolved=True),DAYS)
        m=r.endpoint_metrics(a['endpoints'])
        self.assertEqual(a['finalCashJpy'],'990000')
        self.assertIsNone(m['certifiedFinalEquityJpy'])

    def test_unresolved_cannot_create_proceeds(self):
        l=fixture(unresolved=True);l['events'][-2]['exitEvents'][0]['proceedsJpy']='10000'
        with self.assertRaisesRegex(ValueError,'UNRESOLVED_CREATED_PROCEEDS'):r.audit_ledger(l,DAYS)

    def test_final_cash_mismatch_rejected(self):
        l=fixture();l['finalCashJpy']='2000000'
        with self.assertRaisesRegex(ValueError,'FINAL_CASH'):r.audit_ledger(l,DAYS)

    def test_external_deposit_cannot_hide(self):
        l=fixture();l['events'][-1]['cashJpy']='2000000';l['snapshots'][-1]['cashJpy']='2000000'
        with self.assertRaisesRegex(ValueError,'EVENT_CASH'):r.audit_ledger(l,DAYS)

    def test_future_mark_rejected(self):
        l=fixture();l['snapshots'][1]['positions'][0]['markKnownAt']=r.timestamp(DAYS[1],570)
        with self.assertRaisesRegex(ValueError,'FUTURE_MARK'):r.audit_ledger(l,DAYS)

    def test_missing_mark_cannot_be_equity(self):
        l=fixture(missing_midday=True);l['snapshots'][2]['equityValid']=True
        with self.assertRaisesRegex(ValueError,'VALID_WITH_MISSING_POSITION'):r.audit_ledger(l,DAYS)

    def test_non_lot_quantity_rejected(self):
        l=fixture();l['events'][1]['sizing'][0]['quantity']=101
        with self.assertRaisesRegex(ValueError,'INVALID_LONG_LOT'):r.audit_ledger(l,DAYS)

    def test_negative_quantity_rejected(self):
        l=fixture();l['events'][1]['sizing'][0]['quantity']=-100
        with self.assertRaisesRegex(ValueError,'INVALID_LONG_LOT'):r.audit_ledger(l,DAYS)

    def test_capacity_not_supported(self):
        l=fixture();l['capacity']=10
        with self.assertRaisesRegex(ValueError,'CAPACITY'):r.audit_ledger(l,DAYS)

    def test_safety_nonboolean_rejected(self):
        l=fixture();l['safety']['executionAllowed']=0
        with self.assertRaisesRegex(ValueError,'SAFETY9'):r.audit_ledger(l,DAYS)

    def test_fee_counted_once(self):
        a=r.audit_ledger(fixture(),DAYS)
        self.assertEqual(Decimal(a['confirmedRealizedPnlJpy']),Decimal('995'))

    def test_nonmonotone_events_rejected(self):
        l=fixture();l['events'][-1]['session']=DAYS[0];l['snapshots'][-1]['session']=DAYS[0]
        l['snapshots'][-1]['timestamp']=r.timestamp(DAYS[0],930)
        with self.assertRaises(ValueError):r.audit_ledger(l,DAYS)

    def test_missing_eod_not_last_intraday_price(self):
        l=fixture();l['events'][-1]['minute']=929;l['snapshots'][-1]['minute']=929
        l['snapshots'][-1]['timestamp']=r.timestamp(DAYS[1],929)
        a=r.audit_ledger(l,DAYS)
        self.assertFalse(a['endpoints'][-1]['certifiedFlatEod'])
        self.assertIsNone(a['endpoints'][-1]['equityJpy'])

    def test_audit_does_not_modify_source(self):
        l=fixture(missing_midday=True); before=copy.deepcopy(l)
        r.audit_ledger(l,DAYS)
        self.assertEqual(l,before)


class GeometryTests(unittest.TestCase):
    def test_im_loose_bound(self):
        self.assertAlmostEqual(r.loose_enrichment_ceiling(819,808,731),1.1222222222222222)

    def test_r1_loose_bound(self):
        self.assertAlmostEqual(r.loose_enrichment_ceiling(795,786,776),1.0247718383311604)

    def test_top_all_bound_is_one(self):
        self.assertEqual(r.loose_enrichment_ceiling(100,90,100),1)

    def test_no_known_selected_no_finite_bound(self):
        self.assertIsNone(r.loose_enrichment_ceiling(100,80,10))

    def test_invalid_geometry_rejected(self):
        with self.assertRaises(ValueError):r.loose_enrichment_ceiling(10,11,3)

    def test_gate_impossibility_without_price_input(self):
        for total,known,selected in ((819,808,731),(795,786,776)):
            self.assertLess(r.loose_enrichment_ceiling(total,known,selected),1.15)


if __name__=='__main__':unittest.main()
