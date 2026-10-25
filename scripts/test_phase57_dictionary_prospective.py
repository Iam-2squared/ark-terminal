import copy
import datetime as dt
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from scripts import phase57_dictionary_prospective as m

class ProspectiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = m.Store(self.tmp.name+'/store.sqlite')
        self.budget = {'purpose':'DICTIONARY_ONLY','sessions':['2026-09-24'],'exchangeSessions':['2026-09-24'],'protectedOverlap':False,'calendarSourceHash':'calendar-fixture'}
        self.clock = patch.object(m,'now',return_value='2026-09-24T09:00:00+00:00');self.clock.start()
    def tearDown(self):
        self.clock.stop();self.s.close();self.tmp.cleanup()
    def add(self, **kw):
        x=dict(kind='master',session='2026-09-24',payload={'code':'TEST'},source='fixture:official',budget=self.budget)
        x.update(kw);return self.s.append(**x)
    def test_receipt_no_retroactive_known_at(self):
        self.add(publication='2026-09-01T00:00:00+00:00')
        self.assertEqual(self.s.as_of('2026-09-23T00:00:00+00:00'),[])
        self.assertEqual(self.s.as_of(m.now())[0][1]['knownAt'],m.now())
    def test_timezone_required(self):
        with self.assertRaises(ValueError):self.s.as_of('2026-09-24')
    def test_future_publication(self):
        with self.assertRaises(ValueError):self.add(publication='2027-01-01T00:00:00+00:00')
    def test_historical_rejected(self):
        with self.assertRaises(ValueError):self.add(session='2024-09-17')
    def test_future_session(self):
        with self.assertRaises(ValueError):self.add(session='2027-01-01')
    def test_sealed_budget(self):
        for b in ({},dict(self.budget,protectedOverlap=True),dict(self.budget,purpose='ENTRY'),dict(self.budget,exchangeSessions=[])):
            with self.assertRaises(ValueError):self.add(budget=b)
    def test_outcomes_forbidden_recursive(self):
        for k in m.FORBIDDEN:
            with self.assertRaises(ValueError):self.add(payload={'x':[{k:1}]})
    def test_immutability(self):
        self.add()
        for sql in ('DELETE FROM receipts','UPDATE receipts SET previous="bad"'):
            with self.assertRaises(sqlite3.IntegrityError):self.s.db.execute(sql)
        self.assertEqual(self.s.audit()['records'],1)
    def test_corrections_preserved(self):
        self.add(payload={'code':'TEST','revision':1})
        self.add(payload={'code':'TEST','revision':2})
        self.assertEqual(self.s.audit()['records'],2)
    def test_deterministic_export(self):
        self.add();self.assertEqual(self.s.export(),self.s.export())
    def test_unknown_reason_preserved(self):
        self.add(kind='trading_state',payload={'missingReason':'UNKNOWN'})
        self.assertIn(b'UNKNOWN',self.s.export())
    def test_no_trade_needs_evidence(self):
        for r in m.REASONS-{'UNKNOWN'}:
            with self.assertRaises(ValueError):self.add(kind='trading_state',payload={'missingReason':r})
    def test_missing_identity_evidence(self):
        with self.assertRaises(ValueError):self.add(kind='identity',payload={'code':'TEST'})
    def test_code_reuse_overlap(self):
        x=dict(code='TEST',securityId='A',effectiveFrom='2026-09-24',effectiveTo='2026-10-01',evidenceHash='fixture')
        self.add(kind='identity',payload=x)
        with self.assertRaises(ValueError):self.add(kind='identity',payload=dict(x,securityId='B'))
        self.add(kind='identity',payload=dict(x,securityId='B',effectiveFrom='2026-10-01',effectiveTo='2026-11-01'))
    def test_action_contract(self):
        with self.assertRaises(ValueError):self.add(kind='corporate_action',payload={'type':'split'})
    def test_lineage(self):
        with self.assertRaises(ValueError):self.add(kind='daily_l2',parents=['bad'])
        d=self.add();self.add(kind='daily_l2',parents=[d])
    def test_unknown_source_version(self):
        self.add();self.assertEqual(self.s.as_of(m.now())[0][1]['sourceVersionStatus'],'NOT_PROVIDED')
    def test_truncation_future_poison(self):
        self.add();cut=m.now();before=self.s.as_of(cut)
        with patch.object(m,'now',return_value='2026-09-25T09:00:00+00:00'):self.add(payload={'code':'POISON'})
        self.assertEqual(before,self.s.as_of(cut))
    def test_maturity_unique_sessions(self):
        x=m.maturity(['2026-09-24']*60,12,300,{})
        self.assertEqual(x['tier1Remaining'],59);self.assertFalse(x['frozen'])
    def test_maturity_no_automatic_freeze(self):
        dates=[str(dt.date(2026,1,1)+dt.timedelta(days=i)) for i in range(60)]
        x=m.maturity(dates,12,300,{'G'+str(i):'PASS' for i in range(9)})
        self.assertTrue(x['freezeReviewEligible']);self.assertFalse(x['frozen'])
    def test_gate_missing_blocks(self):
        self.assertFalse(m.maturity(list(map(str,range(60))),12,300,{})['freezeReviewEligible'])
    def test_empty_summary(self):
        for date,n in [('2024-11-01',300),('2024-11-05',325)]:
            x=m.summarize_minute_rows(date,[]);self.assertEqual(x['expectedSlots'],n)
            self.assertFalse(x['profileEligible']);self.assertEqual(x['observedSlots'],0)
    def test_normalization_no_fill(self):
        rows=[dict(Date='2026-09-24',Time='09:0'+str(i),O=10,H=12,L=9,C=11,Vo=1,Va=10) for i in range(5)]
        x=m.summarize_minute_rows('2026-09-24',rows)
        self.assertEqual(x['bars5m'][0]['Vo'],5);self.assertIsNone(x['bars5m'][1]['O'])
        self.assertEqual(x,m.summarize_minute_rows('2026-09-24',rows))
    def test_invalid_and_duplicate_bars(self):
        r=dict(Date='2026-09-24',Time='09:00',O=10,H=12,L=9,C=11,Vo=1,Va=10)
        for rows in ([r,r],[dict(r,H=1)],[dict(r,Date='2024-01-01')]):
            with self.assertRaises(ValueError):m.summarize_minute_rows('2026-09-24',rows)
    def test_safety(self):
        self.assertEqual(len(m.contract()['safety']),9)
        self.assertTrue(all(v is False for v in m.contract()['safety'].values()))

if __name__ == '__main__': unittest.main()
