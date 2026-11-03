"""No broker I/O: actual coordinator, Node normalizer and SQLite persistence."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ENGINE=Path(os.environ['NO11_RSS_TEST_ENGINE'])
sys.path[:0]=[str(ENGINE/'tools'),str(ENGINE/'tests')]
import no11_rss_buying_power as rss
import no11_broker_execution_service as service
import no11_broker_execution_ledger as ledger
import no11_received_session_bootstrap as bootstrap
from test_no11_frozen_p1_broker_service import envelope, config as old_config, at, DAY


def live_config(source):
    c=old_config()
    c['evidenceMode']='BROKER_OBSERVATION'
    c['ledger'].update(account='一般', allocatedCashJpy=rss.AUTO, maxSymbols=3, lotSize=100,
                       evidenceMode='BROKER_OBSERVATION')
    c['transport']={'mode':'LIVE','orderTransmission':True,'operatorEnabled':True,
                    'approvedForSession':True,'sessionDate':DAY}
    c['orderTerms'].update(sor=True,accountType=1)
    c.update(fundingPolicy=rss.POLICY,feeCourse='ZERO',orderTransmission=True,
             accountObservationFile=str(source))
    return c


class FundingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.file=self.root/'observation.json'
        self.current=at()
        self.cfg=live_config(self.file)
        self.write(812345,positions=[{'symbol':'7203','account':'一般','quantity':100},
                                    {'symbol':'6501','account':'一般','quantity':200}])

    def write(self, amount, positions=(), second=10):
        self.raw=envelope(second=second,positions=positions)
        self.raw['snapshot']['buyingPower']=amount
        self.raw['brokerObservation']['buyingPower']=amount
        self.file.write_text(json.dumps(self.raw,ensure_ascii=False),encoding='utf-8')

    def open(self):
        return service.BrokerExecution(self.root,self.cfg,{},None,{'symbols':{}},'2026-10-23',
                                       clock=lambda:self.current)

    def test_actual_rss_amount_seeds_cash_not_personal_positions(self):
        e=self.open()
        try:
            state=e.book.snapshot(self.current)
            self.assertEqual(state['cashJpy'],'812345')
            self.assertEqual(state['allocatedCashJpy'],'812345')
            self.assertEqual(state['positions'],{})
            self.assertEqual(e.book.config['externalSymbols'],['6501.T','7203.T'])
            self.assertEqual(state['orders'],{})
            self.assertFalse(e.summary()['securitiesOnlyOpeningCashReviewed'])
            self.assertEqual(e.summary()['openingCashScope'],rss.BASIS)
            self.assertFalse(e.summary()['buyingPowerRefreshVerified'])
        finally:e.close()

    def test_rss_policy_needs_no_bank_or_screenshot_or_refresh_document(self):
        e=self.open()
        try:
            self.assertTrue(e.observe_file(self.current))
            self.assertTrue(e._buying_power_verified(self.current))
            self.assertTrue(e.summary()['buyingPowerUsableByPolicy'])
            self.assertFalse(e.summary()['buyingPowerRefreshVerified'])
            self.assertFalse(e.source['buyingPowerFreshnessCertified'])
        finally:e.close()

    def test_restart_reuses_cash_even_if_new_rss_amount_is_larger(self):
        e=self.open();e.close();self.write(9999999)
        e=self.open()
        try:
            self.assertEqual(e.book.snapshot(self.current)['cashJpy'],'812345')
            self.assertEqual(e.book.config['externalSymbols'],['6501.T','7203.T'])
        finally:e.close()

    def test_restart_does_not_require_opening_observer_to_be_available(self):
        e=self.open();e.close();self.file.unlink()
        e=self.open()
        try:
            self.assertFalse(e.observe_file(self.current))
            self.assertFalse(e._buying_power_verified(self.current))
        finally:e.close()

    def test_missing_receipt_cannot_reset_existing_ledger(self):
        e=self.open();e.close()
        next(self.root.glob('rss-opening-funding-*.json')).unlink()
        with self.assertRaisesRegex(ValueError,'EXISTING_LEDGER_MISSING_RECEIPT'):self.open()

    def test_changed_receipt_is_rejected(self):
        e=self.open();e.close()
        p=next(self.root.glob('rss-opening-funding-*.json'));r=json.loads(p.read_text())
        r['allocatedCashJpy']='9999999';p.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'RECOVERY_RECEIPT_CHANGED'):self.open()

    def test_resealed_larger_allocation_rejected_by_actual_ledger(self):
        e=self.open();e.close()
        p=next(self.root.glob('rss-opening-funding-*.json'));r=json.loads(p.read_text())
        r['allocatedCashJpy']='9999999';r.pop('receiptSha256');r['receiptSha256']=ledger.digest(r)
        p.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'STATE_CHANGED_OR_DIFFERENT_CONFIG'):self.open()

    def test_same_cash_modified_provenance_rejected_by_controller_identity(self):
        e=self.open();e.close()
        p=next(self.root.glob('rss-opening-funding-*.json'));r=json.loads(p.read_text())
        r['observerSha256']='f'*64;r.pop('receiptSha256');r['receiptSha256']=ledger.digest(r)
        p.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'RECOVERY_CONFIG_OR_PREVIOUS_CHANGED'):self.open()

    def test_zero_cash_is_zero_not_fallback(self):
        self.write(0);e=self.open()
        try:
            self.assertEqual(e.book.snapshot(self.current)['cashJpy'],'0')
            self.assertFalse(e.book.snapshot(self.current)['newBuysAllowed'])
        finally:e.close()

    def test_nonfinite_negative_and_bool_amount_rejected(self):
        for amount in (True,-1,float('nan'),float('inf'),'not-a-number'):
            with self.subTest(amount=amount):
                self.write(amount)
                with self.assertRaises((ValueError,TypeError)):self.open()
                self.assertEqual(list(self.root.glob('broker-execution-*.sqlite')),[])

    def test_stale_or_future_observer_rejected_without_cash(self):
        for stamp in (at(second=45),at(second=1)):
            self.current=stamp
            with self.assertRaises(ValueError):self.open()
        self.assertEqual(list(self.root.glob('broker-execution-*.sqlite')),[])

    def test_partial_or_blocked_observer_rejected(self):
        for key,value in [('status','UNAVAILABLE'),('completeTables',False),('rowsTruncated',True)]:
            self.write(812345);self.raw['brokerObservation'][key]=value
            self.file.write_text(json.dumps(self.raw))
            with self.assertRaises(ValueError):self.open()

    def test_failed_observer_after_success_blocks_buy(self):
        e=self.open()
        try:
            e.observe_file(self.current);self.file.unlink()
            self.assertFalse(e.observe_file(self.current))
            self.assertFalse(e._buying_power_verified(self.current))
        finally:e.close()

    def test_observation_age_is_checked_for_each_buy(self):
        e=self.open()
        try:
            e.observe_file(self.current)
            self.assertTrue(e._buying_power_verified(self.current))
            self.assertFalse(e._buying_power_verified(at(second=45)))
        finally:e.close()

    def test_mismatching_books_fail(self):
        self.raw['snapshot']['buyingPower']=999
        self.file.write_text(json.dumps(self.raw))
        with self.assertRaisesRegex(ValueError,'ACCOUNT_SNAPSHOT_MISMATCH'):self.open()

    def test_readonly_entry_cannot_use_live_profile(self):
        with self.assertRaisesRegex(ValueError,'READONLY_LAUNCHER'):
            service.validate_config(self.cfg,DAY,read_only=True)

    def test_day_approval_cannot_be_bypassed(self):
        for name,value in [('operatorEnabled',False),('approvedForSession',False),
                           ('orderTransmission',False),('sessionDate','2026-10-25')]:
            c=deepcopy(self.cfg);c['transport'][name]=value
            with self.assertRaises(ValueError):service.validate_config(c,DAY)

    def test_normal_max3_100_general_sor_preserved(self):
        for key,value in [('maxSymbols',1),('lotSize',1),('account','特定'),('allocatedCashJpy','123')]:
            c=deepcopy(self.cfg);c['ledger'][key]=value
            with self.assertRaises(ValueError):service.validate_config(c,DAY)
        c=deepcopy(self.cfg);c['orderTerms']['sor']=False
        with self.assertRaises(ValueError):service.validate_config(c,DAY)

    def test_unknown_or_mixed_policy_rejected(self):
        for key,value in [('fundingPolicy','UNKNOWN'),('securitiesCashEvidenceFile','x'),
                           ('buyingPowerEvidenceFile','x')]:
            c=deepcopy(self.cfg);c[key]=value
            with self.assertRaises(ValueError):service.validate_config(c,DAY)

    def test_observer_file_cannot_override_live_launcher_env(self):
        with patch.dict(os.environ,{'ARK_NO11_ACCOUNT_OBSERVATION_FILE':str(self.root/'other.json')}):
            with self.assertRaisesRegex(ValueError,'OBSERVER_PATH_CONFLICT'):self.open()

    def test_bootstrap_accepts_rss_only_on_explicit_live_route(self):
        p=self.root/'broker.json';p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'BROKER_CONFIG_NOT_READONLY'):
            bootstrap.validate_readonly_broker_config(p,DAY)
        self.assertEqual(len(bootstrap.validate_readonly_broker_config(p,DAY,allow_explicit_live=True)),64)

    def test_unchanged_legacy_funding_profile_remains_default(self):
        self.assertFalse(rss.selected(old_config()))


class DisplayAndSetupTests(unittest.TestCase):
    def test_ui_shows_rss_cash_without_fabricating_bank_review(self):
        from test_no11_live_ui2_readonly import actual,NOW,DAY as UIDAY,ui
        value=actual();value.update(fundingPolicy=rss.POLICY,openingCashScope=rss.BASIS,
            buyingPowerUsableByPolicy=True,buyingPowerRefreshVerified=False,securitiesOnlyOpeningCashReviewed=False)
        value['ledger']['newBuysAllowed']=True
        result=ui.project(value,UIDAY,NOW)
        self.assertEqual(result['cashJpy'],'650000')
        self.assertTrue(result['newBuysAllowed']);self.assertFalse(result['buyingPowerVerified'])
        self.assertFalse(result['securitiesOnlyCashReviewed'])
        self.assertFalse(result['uiCanPlaceOrders'])

    def test_setup_refuses_future_day_or_missing_inputs(self):
        import no11_make_rss_live_config as make
        with tempfile.TemporaryDirectory() as folder:
            spec={'bootstrapInputs':{'sessionDate':'2026-11-09'},'transport':{},'originalArrivalTable':'missing'}
            with self.assertRaisesRegex(ValueError,'SETUP_ACTUAL_SESSION_DAY'):
                make.build(spec,folder,'2026-11-03T09:00:00+09:00')
            with self.assertRaisesRegex(ValueError,'SETUP_SESSION_TRANSPORT_REQUIRED'):
                make.build(spec,folder,'2026-11-09T09:00:00+09:00')
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_setup_does_not_start_shadow(self):
        import no11_make_rss_live_config as make
        spec={'bootstrapInputs':{'sessionDate':DAY,'shadowAccountConfig':'old'},'transport':{},'originalArrivalTable':'missing'}
        with self.assertRaisesRegex(ValueError,'SETUP_NO_SHADOW_OR_OLD_BROKER'):make.build(spec,'unused',at())


if __name__=='__main__':unittest.main()
