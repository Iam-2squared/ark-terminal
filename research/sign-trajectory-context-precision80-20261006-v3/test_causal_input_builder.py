"""Synthetic invariance, half-session gaps, known membership and null support."""
from copy import deepcopy
import unittest
from datetime import datetime,timedelta,timezone
import causal_input_builder as builder
from test_intent_feature_replay import fixture

class Poison(list):
    def __getitem__(self,index):
        if index!=0:raise AssertionError('future market value accessed')
        return super().__getitem__(index)

class FutureEvent(dict):
    def __getitem__(self,key):
        if key in ('symbol','decisionPrice','savedV1Score'):raise AssertionError('future selector membership accessed')
        return super().__getitem__(key)


def event(symbol,minute,available=None):
    stamp=lambda t:f'2025-08-25T{t//60:02d}:{t%60:02d}:00+09:00'
    return {'sessionDate':'2025-08-25','decisionTimestamp':stamp(minute),
            'decisionPriceAvailableAtJst':stamp(minute if available is None else available),'symbol':symbol}


class CausalInputTests(unittest.TestCase):
    def setUp(self):builder.initialize()

    def test_trajectory_future_poison_and_prices_cannot_change_output(self):
        _,e,_,raw,source=fixture()
        a=builder.trajectory(raw['today'],e['session'],580,source['previous'],True)
        b=builder.trajectory(raw['today']+[Poison([580]),Poison([750])],e['session'],580,source['previous'],True)
        self.assertEqual(a,b)
        self.assertEqual(a[0]['trajectory/lag01/close_u'],0.)
        self.assertEqual(len(a[0]),256)

    def test_missing_slot_stays_null_not_forward_filled(self):
        _,e,_,raw,source=fixture();rows=[r for r in raw['today'] if r[0]!=566]
        out,audit=builder.trajectory(rows,e['session'],580,source['previous'],True)
        self.assertEqual(out['trajectory/lag14/bar_present'],0)
        self.assertEqual(out['trajectory/lag14/half_slot_eligible'],1)
        self.assertIsNone(out['trajectory/lag14/close_u'])
        self.assertEqual(audit['observed_slots'],31)

    def test_pm_does_not_borrow_am_or_fill_lunch(self):
        _,e,_,raw,source=fixture();raw['today'].append([750,110.,110.2,109.9,110.1,100,11001])
        out,audit=builder.trajectory(raw['today'],e['session'],751,source['previous'],True)
        self.assertEqual(audit['same_half_eligible_slots'],1)
        self.assertEqual(audit['observed_slots'],1)
        self.assertEqual(out['trajectory/lag02/half_slot_eligible'],0)
        self.assertIsNone(out['trajectory/lag02/log_volume'])

    def test_unavailable_m0_does_not_invent_price_basis(self):
        _,e,_,raw,_=fixture()
        out,audit=builder.trajectory(raw['today'],e['session'],580,[],False)
        for k,v in out.items():
            if k.endswith('_u'):self.assertIsNone(v)
        self.assertIsNotNone(out['trajectory/lag01/log_volume'])
        self.assertEqual(audit['normalization_price_checks'],0)

    def test_known_selector_pool_excludes_future_event_unavailable_price_and_self(self):
        events=[event('SELF',550),event('KNOWN',550),event('KNOWN',560),event('LATEPRICE',570,581),
                FutureEvent(event('FUTURE',581))]
        self.assertEqual(builder.known_peers(events,'2025-08-25',580,'SELF'),['KNOWN'])

    def test_peer_strict_gap_null_and_past_prefix_invariance(self):
        _,_,_,raw,_=fixture()
        a=builder.peer_values(raw['today'],'2025-08-25',580)
        b=builder.peer_values(raw['today']+[Poison([580])],'2025-08-25',580)
        self.assertEqual(a,b)
        self.assertIsNotNone(a['returns'][5])
        gap=builder.peer_values([r for r in raw['today'] if r[0]!=576],'2025-08-25',580)
        self.assertTrue(gap['fresh']);self.assertIsNone(gap['returns'][5]);self.assertIsNone(gap['returns'][10])

    def test_context_support_denominators_distinguish_known_fresh_valid(self):
        _,_,_,raw,_=fixture();gap=[r for r in raw['today'] if r[0]!=576]
        out,audit=builder.context([raw['today'],gap],'2025-08-25',580)
        self.assertEqual(out['peer/known_count'],2)
        self.assertEqual(out['peer/fresh_count'],2)
        self.assertEqual(out['peer/return5/valid_count'],1)
        self.assertEqual(out['peer/return5/valid_fraction'],.5)
        self.assertEqual(len(out),16)
        empty,_=builder.context([],'2025-08-25',580)
        self.assertIsNone(empty['peer/return5/median'])
        self.assertEqual(empty['peer/return5/valid_count'],0)

    def test_auction_opening_bar_is_not_fresh_peer(self):
        row=[750,100.,100.2,99.9,100.1,100,10001]
        out=builder.peer_values([row],'2025-08-25',751)
        self.assertFalse(out['fresh'])
        self.assertIsNone(out['returns'][5])

if __name__=='__main__':unittest.main()
