"""Additional operational regressions, all with synthetic temporary stores."""
from __future__ import annotations

import base64
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import unittest
from unittest.mock import patch

import install_no11_oneclick_display_v2 as old
import install_no11_oneclick_display_overlay_compat as overlay
import no11_display_install_chain as chain
import no11_nightly_resume as n
import no11_decision_audit_readonly as inspect_only
import test_no11_oneclick_display_v2 as fixture
import test_no11_oneclick_display_overlay_compat as overlay_fixture
import test_no11_operational_hardening as operational


class HistoricalPayloadTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.InstallTests('test_audit_is_readonly_and_does_not_run_processes')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.launcher.write_bytes(overlay_fixture.make_source())
        with patch.object(old, 'gate'), patch.object(old, 'parse_launcher'):
            old.install(self.case.store, apply=True)
        path = 'research/no11-morning-master-20261103/no11_oneclick_display_v2.py'
        # HEAD retains the historical source; staging only derives new bytes in
        # the checkout. This simulates a PC with the already-shipped release.
        raw = subprocess.check_output(['git', 'show', 'HEAD:' + path])
        self.assertEqual(n.digest(raw), chain.HISTORICAL_DISPLAY)
        self.set_base_payload(raw)
        with patch.object(old, 'gate'), patch.object(old, 'parse_launcher'):
            overlay.install(self.case.store, apply=True)

    def set_base_payload(self, raw):
        contract = {'schemaId': 'ARK_NO11_ONECLICK_DISPLAY_INSTALL_V2',
                    'displaySha256': n.digest(raw),
                    'legacyStatusSha256': n.digest(self.case.legacy.read_bytes()),
                    'orderTransmission': False, 'authorizationSourceChanged': False}
        payload = {old.DISPLAY: raw, old.CONTRACT: n.encode(contract)}
        for name, data in payload.items():
            (self.case.home / name).write_bytes(data)
        receipt_path = self.case.store / old.JOURNAL
        record = n.checkpoint(receipt_path)
        record['sidecars'] = {name: base64.b64encode(data).decode('ascii') for name, data in payload.items()}
        n.atomic(receipt_path, record)

    def test_historical_v2_and_overlay_both_pass_without_reinstalling(self):
        before = self.case.snapshot()
        self.assertEqual(old.install(self.case.store), 'ALREADY_APPLIED')
        self.assertEqual(overlay.install(self.case.store), 'ALREADY_APPLIED')
        self.assertEqual(self.case.snapshot(), before)

    def test_rehashed_receipt_cannot_authorize_an_unknown_display_program(self):
        self.set_base_payload(b'raise RuntimeError("unreviewed")\n')
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_DISPLAY_RELEASE'):
            chain.validate_v2_dependencies(self.case.store)


class ReadOnlyAuditTests(unittest.TestCase):
    def setUp(self):
        self.case = operational.DecisionAuditTests('test_event_chain_survives_reopen_without_reissuing_candidate')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_utf8_and_raw_json_errors_do_not_print_account_contents(self):
        self.assertEqual(inspect_only.parse('{"label":"一般"}'.encode('utf-8'))['label'], '一般')
        with self.assertRaises(inspect_only.AuditError) as raised:
            inspect_only.parse(b'{"private-account":"secret", broken')
        self.assertNotIn('secret', str(raised.exception))

    def test_active_wal_is_read_consistently_without_changing_ledger_state(self):
        self.case.fund([operational.row()])
        before = self.case.book.snapshot(operational.AT)
        out = inspect_only.database_summary(self.case.database, operational.DAY)
        after = self.case.book.snapshot(operational.AT)
        self.assertEqual(before, after)
        self.assertEqual(out['consumedCount'], 1)
        self.assertEqual(out['decisionCounts'], {'BUY_INTENT_CREATED': 1})
        self.assertEqual(out['legacyConsumedWithoutReason'], 0)
        self.assertFalse(out['databaseWriteRequested'])
        self.assertFalse(out['orderTransmissionByThisAudit'])
        text = json.dumps(out, ensure_ascii=False)
        for field in ('allocatedCashJpy', 'buyingPowerJpy', 'accountObservation', 'positions'):
            self.assertNotIn(field, text)

    def test_legacy_records_remain_unknown_not_no_signal_or_no_funds(self):
        r = operational.row()
        self.case.book.checkpoint_source('capital.consumed', {r['candidateId']: operational.digest(r)}, operational.AT)
        out = inspect_only.database_summary(self.case.database, operational.DAY)
        self.assertEqual(out['legacyConsumedWithoutReason'], 1)
        self.assertEqual(out['decisionCounts'], {})
        self.assertFalse(out['historicalReasonsReconstructed'])

    def test_wrong_session_and_modified_state_hash_are_rejected(self):
        with self.assertRaisesRegex(inspect_only.AuditError, 'STATE_IDENTITY_OR_HASH'):
            inspect_only.database_summary(self.case.database, '2026-11-13')
        self.case.book.db.execute("UPDATE broker_state SET sha='unverified' WHERE singleton=1")
        with self.assertRaisesRegex(inspect_only.AuditError, 'STATE_IDENTITY_OR_HASH'):
            inspect_only.database_summary(self.case.database, operational.DAY)


if __name__ == '__main__':
    unittest.main(verbosity=2)
