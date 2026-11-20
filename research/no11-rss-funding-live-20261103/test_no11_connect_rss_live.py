#!/usr/bin/env python3
"""Pure stdlib tests. No Excel, accounts, network, ledger or trading."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_connect_rss_live as c


DAY = "2026-11-09"


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return path


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.account = self.dir / "Ark_No11_MSII_RSS.xlsx"
        self.market = self.dir / "Ark_No11_MARKET_RSS.xlsx"
        self.order = self.dir / "Ark_No11_BROKER_READONLY.xlsx"
        self.arrival = self.dir / "original-arrival-table.json"
        for f in (self.account, self.market, self.order, self.arrival):
            f.write_bytes(b"LOCAL_PLACEHOLDER")
        self.settings = {k: "" for k in c.KEYS}
        self.settings.update(schemaId=c.SETTINGS_SCHEMA,
            accountWorkbookPath=str(self.account),
            marketWorkbookPath=str(self.market),
            orderIdWorkbookPath=str(self.order),
            normalMaxPositions=3, sameDayApprovalRequired=True,
            automaticOrderAuthorization=False, orderTransmission=False)
        self.prepared = dict(schemaId=c.BOOT_SCHEMA, sessionDate=DAY,
            dailyRun=str(self.dir), datedMaster=str(self.arrival),
            runtimeRoot=str(self.dir), h235ModelRoot=str(self.dir),
            privateRoot=str(self.dir), previousContext=str(self.arrival),
            orderIdWorkbookPath=str(self.order), productionReady=False,
            orderTransmission=False)
        self.physical = dict(schemaId="ARK_NO11_MSII_TRANSPORT_CONFIG_V1",
            sessionDate=DAY, mode="LIVE", orderTransmission=True,
            operatorEnabled=True, approvedForSession=True,
            workbookPath=str(self.order), rssSessionKey="test-key",
            expiresAtJst=DAY+"T15:20:00+09:00",
            dispatchDirectory=str(self.dir), worksheetName="ARK_ORDER_IDS_READONLY",
            formulaCell="BD4", triggerCell="BD2", guardCell="BD1",
            sessionCell="BD3", guardValue="ARK_NO11_SEND_ONCE",
            expectedExcelPid=1, expectedExcelHwnd=1,
            expectedExcelStartedAt=DAY+"T08:30:00+09:00",
            expectedAddInPaths=[], expectedOpenWorkbooks=[],
            permitMaximumAgeMs=10000, responseTimeoutMs=3000)
        self.broker_file = self.dir / "broker.json"
        self.boot_file = self.dir / "boot.json"
        self.settings_file = self.dir / "settings.json"
        write(self.settings_file, self.settings)
        self.broker = dict(schemaId=c.BROKER_SCHEMA, sessionDate=DAY,
            fundingPolicy="RSS_BUYING_POWER", feeCourse="ZERO",
            evidenceMode="BROKER_OBSERVATION", orderTransmission=True,
            productionReady=False, transport=dict(self.physical),
            ledger=dict(account="一般", maxSymbols=3, lotSize=100,
                allocatedCashJpy="AUTO_RSS_BUYING_POWER"),
            orderTerms=dict(sor=True, accountType=1,
                accountTypeVerified=True, orderType="MARKET",
                timeInForce="DAY"))
        self.boot = dict(self.prepared,
            brokerExecutionConfig=str(self.broker_file))
        write(self.boot_file, self.boot)
        write(self.broker_file, self.broker)

    def check_input(self):
        return c.validate_inputs(self.settings, self.prepared,
                                 self.physical, self.arrival, DAY)

    def test_input_good_and_no_mutation(self):
        before = self.settings_file.read_bytes()
        self.check_input()
        self.assertEqual(self.settings_file.read_bytes(), before)

    def test_both_previous_sources_block(self):
        self.prepared["previousCaptureFiles"] = [str(self.arrival)]
        with self.assertRaisesRegex(ValueError, "EXACTLY_ONE_PREVIOUS_SOURCE"):
            self.check_input()

    def test_neither_previous_source_block(self):
        self.prepared.pop("previousContext")
        with self.assertRaisesRegex(ValueError, "EXACTLY_ONE_PREVIOUS_SOURCE"):
            self.check_input()

    def test_previous_day_rejected(self):
        self.prepared["sessionDate"] = "2026-11-02"
        with self.assertRaisesRegex(ValueError, "CURRENT_DAY_PREPARED_INPUT_REQUIRED"):
            self.check_input()

    def test_shadow_rejected(self):
        self.prepared["shadowAccountConfig"] = str(self.arrival)
        with self.assertRaisesRegex(ValueError, "OLD_BROKER_OR_SHADOW"):
            self.check_input()

    def test_account_workbook_identity_rejected(self):
        self.prepared["orderIdWorkbookPath"] = str(self.account)
        with self.assertRaisesRegex(ValueError, "ORDER_ID_WORKBOOK_MISMATCH"):
            self.check_input()

    def test_disabled_auto_order_required(self):
        self.settings["automaticOrderAuthorization"] = True
        with self.assertRaisesRegex(ValueError, "SETTINGS_UNSAFE"):
            self.check_input()

    def test_physical_approval_not_created_by_connector(self):
        self.physical["approvedForSession"] = False
        with self.assertRaisesRegex(ValueError, "ACTUAL_APPROVED_PHYSICAL"):
            self.check_input()

    def test_physical_guard_not_forged(self):
        self.physical["guardValue"] = "DISABLED"
        with self.assertRaisesRegex(ValueError, "GUARD_VALUE_MISMATCH"):
            self.check_input()

    def test_duplicate_json_property_rejected(self):
        p = self.dir / "duplicate.json"
        p.write_text('{"x":1,"x":2}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            c.read_json(p)

    def test_register_creates_backup_and_changes_only_bootstrap(self):
        old = self.settings_file.read_bytes()
        backup = c.register(self.settings_file, self.boot_file,
                            self.broker_file, self.dir,
                            DAY+"T09:01:00+09:00")
        changed, _ = c.read_json(self.settings_file)
        self.assertEqual(backup.read_bytes(), old)
        self.assertEqual(changed["bootstrapConfigFile"], str(self.boot_file))
        self.assertFalse(changed["automaticOrderAuthorization"])
        self.assertFalse(changed["orderTransmission"])
        for key in c.KEYS:
            if key != "bootstrapConfigFile":
                self.assertEqual(changed[key], self.settings[key])

    def test_second_registration_rejected_no_overwrite(self):
        c.register(self.settings_file, self.boot_file, self.broker_file,
                   self.dir, DAY+"T09:01:00+09:00")
        updated = self.settings_file.read_bytes()
        with self.assertRaisesRegex(ValueError, "ALREADY_SET"):
            c.register(self.settings_file, self.boot_file, self.broker_file,
                       self.dir, DAY+"T09:01:00+09:00")
        self.assertEqual(self.settings_file.read_bytes(), updated)

    def test_wrong_broker_day_blocks_without_setting_change(self):
        old = self.settings_file.read_bytes()
        self.broker["sessionDate"] = "2026-11-02"
        write(self.broker_file, self.broker)
        with self.assertRaisesRegex(ValueError, "GENERATED_BROKER_CONFIG_UNSAFE"):
            c.register(self.settings_file, self.boot_file, self.broker_file,
                       self.dir, DAY+"T09:01:00+09:00")
        self.assertEqual(self.settings_file.read_bytes(), old)

    def test_fee_sor_max3_general_cannot_be_changed(self):
        for field, value in [("feeCourse","OTHER"),("fundingPolicy","UNKNOWN")]:
            value0 = self.broker[field]
            self.broker[field] = value
            write(self.broker_file, self.broker)
            with self.assertRaises(ValueError):
                c.register(self.settings_file, self.boot_file,
                           self.broker_file, self.dir,
                           DAY+"T09:01:00+09:00")
            self.broker[field] = value0
        write(self.broker_file, self.broker)

    def test_no_actual_order_io_functions_in_registration(self):
        source = Path(c.__file__).read_text(encoding="utf-8")
        self.assertNotIn("RssStockOrder(", source)
        self.assertNotIn("RssCancelOrder(", source)
        self.assertNotIn("Start-Process", source)
        self.assertNotIn("Workbooks.Open", source)


if __name__ == "__main__":
    unittest.main()
