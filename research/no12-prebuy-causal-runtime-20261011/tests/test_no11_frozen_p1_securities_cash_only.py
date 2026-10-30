"""Only human-confirmed securities-account cash can seed a LIVE ledger.

Synthetic local documents, no connection to Rakuten, MSII, Excel or an order.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import no11_securities_cash_only as cash
import no11_broker_execution_service as service
import no11_broker_execution_ledger as ledger

DAY = '2026-10-30'
DOCUMENT = b'X' * 1200

def evidence(**changes):
    v = {
        'schemaId': cash.SCHEMA, 'sessionDate': DAY, 'account': '特定',
        'source': cash.SOURCE, 'displayedField': cash.LABEL,
        'securitiesAvailableJpy': '1000000',
        'sourceCapturedAtJst': DAY + 'T08:45:00+09:00',
        'operatorReviewedAtJst': DAY + 'T08:47:00+09:00',
        'sourceDocumentPath': r'C:\Private\Rakuten\cash-evidence.png',
        'sourceDocumentSha256': hashlib.sha256(DOCUMENT).hexdigest(),
        'bankBridgeExcluded': True, 'autoSweepDisabledConfirmed': True,
        'marginAndCreditExcluded': True, 'operatorReviewed': True,
    }
    v.update(changes)
    return v

def verify(v, **options):
    return cash.verify_opening_evidence(
        v, session=DAY, account='特定', now_jst=DAY + 'T08:50:00+09:00',
        document_bytes=DOCUMENT, **options)

class SecuritiesOnlyFundingTests(unittest.TestCase):
    def test_securities_only_allocation_is_derived_from_reviewed_source(self):
        r = verify(evidence(securitiesAvailableJpy='26893'))
        self.assertEqual(r['allocatedCashJpy'], '26893')
        self.assertTrue(r['bankBridgeExcluded'])
        self.assertFalse(r['orderTransmission'])
        self.assertIn('NOT_MACHINE_CERTIFIED', r['basis'])

    def test_zero_cash_is_allowed_but_not_invented(self):
        self.assertEqual(verify(evidence(securitiesAvailableJpy='0'))['allocatedCashJpy'], '0')

    def test_no_bank_or_credit_funds_can_be_implicitly_admitted(self):
        for key in ('bankBridgeExcluded', 'autoSweepDisabledConfirmed',
                    'marginAndCreditExcluded', 'operatorReviewed'):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, 'SCOPE_NOT_CONFIRMED'):
                    verify(evidence(**{key: False}))
        for key in ('source', 'displayedField'):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, 'SECURITIES_ONLY_SOURCE'):
                    verify(evidence(**{key: '現物買付可能額'}))

    def test_wrong_account_session_fields_or_extra_key_fail(self):
        for edit in ({'account': '一般'}, {'sessionDate': '2026-10-29'}):
            with self.assertRaisesRegex(ValueError, 'SESSION_OR_ACCOUNT'):
                verify(evidence(**edit))
        with self.assertRaisesRegex(ValueError, 'SCHEMA_OR_FIELDS'):
            verify(evidence(rssBuyingPowerJpy='5000000'))

    def test_cash_is_exact_nonnegative_decimal_text(self):
        for amount in ('0100', '100.1', '-1', '999999999999999', '', 100, 100.0, True):
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(ValueError, 'SECURITIES_AMOUNT_FORMAT'):
                    verify(evidence(securitiesAvailableJpy=amount))

    def test_source_document_must_match_private_reviewed_bytes(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_DOCUMENT_CHANGED_OR_MISSING'):
            cash.verify_opening_evidence(
                evidence(), session=DAY, account='特定',
                now_jst=DAY + 'T08:50:00+09:00', document_bytes=b'Y' * 1200)
        with self.assertRaisesRegex(ValueError, 'SOURCE_DOCUMENT_TYPE'):
            verify(evidence(sourceDocumentPath=r'C:\Private\arbitrary.json'))

    def test_clock_and_recovery_rules(self):
        with self.assertRaisesRegex(ValueError, 'OPENING_EVIDENCE_STALE'):
            cash.verify_opening_evidence(
                evidence(), session=DAY, account='特定',
                now_jst=DAY + 'T10:30:00+09:00', document_bytes=DOCUMENT)
        self.assertEqual(cash.verify_opening_evidence(
            evidence(), session=DAY, account='特定',
            now_jst=DAY + 'T10:30:00+09:00',
            document_bytes=DOCUMENT, require_fresh=False
        )['allocatedCashJpy'], '1000000')
        with self.assertRaisesRegex(ValueError, 'FUTURE_OR_REVERSED_EVIDENCE_CLOCK'):
            verify(evidence(operatorReviewedAtJst=DAY + 'T08:40:00+09:00'))

    def test_live_config_must_use_securities_only_auto_not_a_fixed_amount(self):
        v = {'schemaId': service.CONFIG, 'sessionDate': DAY, 'evidenceMode': 'BROKER_OBSERVATION',
             'ledger': {'schemaId': ledger.CONFIG_SCHEMA, 'sessionDate': DAY,
                        'account': '特定', 'allocatedCashJpy': '1000000',
                        'evidenceMode': 'BROKER_OBSERVATION'},
             'transport': {'mode': 'LIVE', 'orderTransmission': True,
                           'operatorEnabled': True, 'approvedForSession': True,
                           'sessionDate': DAY},
             'orderTerms': {'orderType': 'MARKET', 'limitPrice': None, 'timeInForce': 'DAY',
                            'sor': False, 'accountType': 0, 'accountTypeVerified': True},
             'productionReady': False, 'orderTransmission': True}
        with self.assertRaisesRegex(ValueError, 'LIVE_SECURITIES_CASH_ONLY'):
            service.validate_config(v, DAY)
        v['ledger']['allocatedCashJpy'] = cash.AUTO
        with self.assertRaisesRegex(ValueError, 'LIVE_SECURITIES_CASH_ONLY'):
            service.validate_config(v, DAY)
        v['securitiesCashEvidenceFile'] = str(Path(tempfile.gettempdir()) / 'cash-evidence.json')
        self.assertEqual(service.validate_config(v, DAY)['ledger']['allocatedCashJpy'], cash.AUTO)
        with self.assertRaisesRegex(ValueError, 'READONLY_LAUNCHER'):
            service.validate_config(v, DAY, read_only=True)


class SecuritiesCashLedgerWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.document = self.root / 'source.png'
        self.document.write_bytes(DOCUMENT)
        self.proof = self.root / 'reviewed.json'
        self.write_proof('26893')

    def write_proof(self, amount):
        self.proof.write_text(json.dumps(evidence(
            securitiesAvailableJpy=amount, sourceDocumentPath=str(self.document)),
            ensure_ascii=False), encoding='utf-8')

    def live_config(self):
        return {'schemaId': service.CONFIG, 'sessionDate': DAY,
            'evidenceMode': 'BROKER_OBSERVATION',
            'ledger': {'schemaId': ledger.CONFIG_SCHEMA, 'sessionDate': DAY,
                       'account': '特定', 'allocatedCashJpy': cash.AUTO,
                       'evidenceMode': 'BROKER_OBSERVATION'},
            'transport': {'mode': 'LIVE', 'orderTransmission': True,
                          'operatorEnabled': True, 'approvedForSession': True,
                          'sessionDate': DAY},
            'orderTerms': {'orderType': 'MARKET', 'limitPrice': None,
                           'timeInForce': 'DAY', 'sor': False,
                           'accountType': 0, 'accountTypeVerified': True},
            'securitiesCashEvidenceFile': str(self.proof),
            'productionReady': False, 'orderTransmission': True}

    def open(self, config=None):
        return service.BrokerExecution(
            self.root, config or self.live_config(), {}, None,
            {'symbols': {}}, '2026-10-29',
            clock=lambda: DAY + 'T08:50:00+09:00')

    def test_live_ledger_seeds_verified_securities_cash_not_fixed_or_rss_cash(self):
        e = self.open()
        try:
            snapshot = e.book.snapshot(DAY + 'T08:50:00+09:00')
            self.assertEqual(snapshot['allocatedCashJpy'], '26893')
            self.assertEqual(snapshot['cashJpy'], '26893')
            self.assertFalse(snapshot['newBuysAllowed'])
            self.assertTrue(e.summary()['securitiesOnlyOpeningCashReviewed'])
            self.assertIn('NOT_MACHINE_CERTIFIED', e.summary()['openingCashScope'])
            self.assertFalse(e.summary()['brokerConnectionPhysicallyVerified'])
        finally:
            e.close()

    def test_session_recovery_rejects_changed_private_opening_cash(self):
        e = self.open()
        e.close()
        self.write_proof('26894')
        with self.assertRaisesRegex(ValueError, 'STATE_CHANGED_OR_DIFFERENT_CONFIG'):
            self.open()

    def test_same_pinned_opening_cash_evidence_reopens_without_minting_cash(self):
        e = self.open()
        e.close()
        e = self.open()
        try:
            self.assertEqual(e.book.snapshot(DAY + 'T08:50:00+09:00')['cashJpy'], '26893')
        finally:
            e.close()

if __name__ == '__main__':
    unittest.main()
