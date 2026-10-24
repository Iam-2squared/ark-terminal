"""MODE A: generated originals and isolated host only; no market authorization."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ark_selector_v2.artifact_io import exclusive_json
from ark_selector_v2.contracts import digest
from ark_selector_v2.exact_math import V2Error, rational
from ark_selector_v2.host_channel import channel_snapshot, check_owner_file
from ark_selector_v2.monthly_fixture import monthly_authority, host_config, isolated_channel
from ark_selector_v2.native_fixture import install_test_grant, request_for
from ark_selector_v2.native import NativeReader
from ark_selector_v2.orchestration import Store, dispatch
from ark_selector_v2.source_adapter import read_csv_session, validate_profile
from ark_selector_v2.approval_package import cash_calendar_metadata, inventory_window


class MarketConnections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="ark-v2-connections-")
        cls.a, cls.m = monthly_authority(Path(cls.temp.name) / "factory")

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def source(self, dataset="DAILY"):
        entry = copy.deepcopy(next(e for e in self.m["entries"] if e["dataset"] == dataset))
        entry["authorized_purpose"] = entry["purposes"][0]
        return entry, copy.deepcopy(self.a.precommit)

    def config(self):
        directory = Path(self.temp.name) / self.id().rsplit(".", 1)[-1]
        directory.mkdir(mode=0o700)
        return host_config(self.a, directory)

    def test_m01_monthly_slice_skips_poison_before_numeric_parse(self):
        entry, pre = self.source()
        from ark_selector_v2.source_adapter import parse_record
        with patch("ark_selector_v2.source_adapter.parse_record", wraps=parse_record) as spy:
            value, receipt = read_csv_session(self.a.root / entry["path"], entry, pre)
        self.assertEqual(len(value["records"]), 60)
        self.assertEqual(spy.call_count, 60)
        self.assertTrue(all(c.args[0]["Date"] == entry["session"] for c in spy.call_args_list))
        self.assertGreater(receipt["other_date_records_skipped"], 0)
        self.assertEqual(receipt["other_date_records_numeric_parsed"], 0)
        self.assertEqual(receipt["original_ordinals"], list(range(60)))

    def test_m02_no_allowlist_rejects_before_any_original_open(self):
        entry, pre = self.source(); pre["allowlists"][entry["authorized_purpose"]] = []
        with patch("ark_selector_v2.source_adapter.sha_file", side_effect=AssertionError("opened")) as spy:
            with self.assertRaisesRegex(V2Error, "NOT_AUTHORIZED_BEFORE_OPEN"):
                read_csv_session(self.a.root / entry["path"], entry, pre)
            spy.assert_not_called()

    def test_m03_source_contract_missing_rejects_before_raw(self):
        authority = copy.deepcopy(self.a); authority.precommit.pop("source_contracts")
        authority.output = Path(self.temp.name) / "source-contract-rejected"
        install_test_grant(authority, "B")
        with patch.object(NativeReader, "read", side_effect=AssertionError("opened")) as spy:
            with self.assertRaisesRegex(V2Error, "SOURCE_CONTRACT_REQUIRED"):
                dispatch("census", request_for(authority, self.m, "B"), authority=authority)
            spy.assert_not_called()

    def test_m04_monthly_original_hash_mismatch_rejects_before_raw(self):
        authority = copy.deepcopy(self.a); manifest = copy.deepcopy(self.m)
        authority.output = Path(self.temp.name) / "original-hash-rejected"
        manifest["entries"][0]["original"]["sha256"] = "0" * 64
        authority.manifest_pin = digest(manifest); authority.precommit["manifest_sha256"] = digest(manifest)
        install_test_grant(authority, "B")
        with patch.object(NativeReader, "read", side_effect=AssertionError("opened")):
            with self.assertRaisesRegex(V2Error, "ORIGINAL_BYTES_IDENTITY"):
                dispatch("census", request_for(authority, manifest, "B"), authority=authority)

    def test_m05_unit_factor_exact_not_float(self):
        entry, pre = self.source(); profile = pre["source_contracts"][entry["format"]]
        profile["factors"]["turnover"] = "1000"; entry["evidence"]["source_contract_hash"] = digest(profile)
        rows, _ = read_csv_session(self.a.root / entry["path"], entry, pre)
        self.assertEqual(rational(rows["records"][0]["turnover"]), 200_000_000_000)
        self.assertEqual(rational(rows["records"][0]["close"]), 200)

    def test_m06_ambiguous_raw_suffix_rejected_before_open(self):
        entry, pre = self.source(); p = pre["source_contracts"][entry["format"]]
        p["raw_suffixes"][entry["session"]] = {}; entry["evidence"]["source_contract_hash"] = digest(p)
        with self.assertRaisesRegex(V2Error, "RAW_SUFFIX_REQUIRED"): validate_profile(entry, pre)

    def test_m07_adjusted_column_is_not_raw_fallback(self):
        entry, pre = self.source(); p = pre["source_contracts"][entry["format"]]
        p["header"].append("AdjC"); p["fields"]["close"] = "AdjC"; entry["evidence"]["source_contract_hash"] = digest(p)
        with self.assertRaisesRegex(V2Error, "ADJUSTED_OR_OUTCOME"): validate_profile(entry, pre)

    def test_m08_master_explicit_alpha_identity_and_kind(self):
        entry, pre = self.source("MASTER"); p = pre["source_contracts"][entry["format"]]
        first = p["identities"][entry["session"]]["SOURCE_0001"]
        first.update({"canonical_symbol": "130A", "rss_symbol": "130A.T", "security_kind": "ETF"})
        entry["evidence"]["source_contract_hash"] = digest(p)
        result, _ = read_csv_session(self.a.root / entry["path"], entry, pre)
        self.assertEqual(result["records"][0]["canonical_symbol"], "130A")
        self.assertEqual(result["records"][0]["security_kind"], "ETF")

    def test_m09_decompression_limit_blocks(self):
        entry, pre = self.source(); p = pre["source_contracts"][entry["format"]]
        p["max_uncompressed_bytes"] = 32; entry["evidence"]["source_contract_hash"] = digest(p)
        with self.assertRaisesRegex(V2Error, "UNCOMPRESSED_SIZE_LIMIT"):
            read_csv_session(self.a.root / entry["path"], entry, pre)

    def test_m10_protected_slice_blocks_before_hash_read(self):
        entry, pre = self.source(); entry["protected"] = True
        with patch("ark_selector_v2.source_adapter.sha_file", side_effect=AssertionError("opened")):
            with self.assertRaisesRegex(V2Error, "NOT_AUTHORIZED_BEFORE_OPEN"):
                read_csv_session(self.a.root / entry["path"], entry, pre)

    def test_m11_journal_survives_new_authority_instance(self):
        config = self.config(); first = channel_snapshot(config, isolated=True)
        first.output = Path(self.temp.name) / "independent-payload-output"
        pin = Store(first).put("self-produced.json", {"origin": "THIS_GENERATED_TEST"})
        config["output_root"] = str(first.output)
        second = channel_snapshot(config, isolated=True)
        self.assertEqual(second.artifact_pins["self-produced.json"], pin)
        self.assertEqual(Store(second).get("self-produced.json"), {"origin": "THIS_GENERATED_TEST"})

    def test_m12_sidecar_never_installs_model_trust(self):
        authority = channel_snapshot(self.config(), isolated=True)
        with patch.object(Path, "read_bytes", side_effect=AssertionError("pickle opened")):
            with self.assertRaisesRegex(V2Error, "INDEPENDENT_ARTIFACT_PRODUCER_PIN"):
                Store(authority).get("forged-model.joblib", model=True)

    def test_m13_overlapping_journal_refused(self):
        config = self.config(); config["journal_root"] = config["source_root"]
        with self.assertRaisesRegex(V2Error, "JOURNAL_MUST_BE_SEPARATE"): channel_snapshot(config, isolated=True)

    def test_m14_world_writable_owner_config_refused(self):
        path = Path(self.temp.name) / "untrusted-owner.json"; exclusive_json(path, {"approved": True})
        path.chmod(0o666)
        with self.assertRaisesRegex(V2Error, "NOT_OWNER_CONTROLLED"): check_owner_file(path, os.getuid())

    def test_m15_symlink_owner_config_refused(self):
        target = Path(self.temp.name) / "owner-link.json"; target.symlink_to(ROOT / "APPROVAL_SCHEMA.json")
        with self.assertRaisesRegex(V2Error, "SYMLINK"): check_owner_file(target, os.getuid())

    def test_m16_test_channel_cannot_be_market_channel(self):
        config = self.config()
        with self.assertRaisesRegex(V2Error, "WORKER_OR_TEST_IDENTITY"): channel_snapshot(config)

    def test_m17_reconstructed_factory_rejects_changed_or_real_row_pin(self):
        config = self.config(); key = next(iter(config["fixture_pins"]))
        config["fixture_pins"][key][0] = "a" * 64
        with self.assertRaisesRegex(V2Error, "REAL_OR_CHANGED_ROWS"): isolated_channel(config)

    def test_m18_journal_event_replay_cannot_overwrite(self):
        config = self.config(); authority = channel_snapshot(config, isolated=True)
        authority.output = Path(self.temp.name) / "event-replay-payloads"
        Store(authority).event("RISK_FIT_STARTED", authority.precommit)
        with self.assertRaises(FileExistsError): Store(authority).event("RISK_FIT_STARTED", authority.precommit)

    def test_m19_calendar_cash_excludes_ose_holiday(self):
        import gzip, hashlib
        raw = gzip.compress(b"Date,HolDiv\n2040-01-01,0\n2040-01-02,1\n2040-01-03,2\n2040-01-04,3\n")
        result = cash_calendar_metadata(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["sessions"], ["2040-01-02", "2040-01-03"])

    def test_m20_calendar_prices_not_accepted_as_metadata(self):
        import gzip, hashlib
        raw = gzip.compress(b"Date,HolDiv,Close\n2040-01-01,1,100\n")
        with self.assertRaisesRegex(V2Error, "METADATA_ONLY_SCHEMA"):
            cash_calendar_metadata(raw, hashlib.sha256(raw).hexdigest())

    def test_m21_latest_inventory_keeps_protected_days_and_zero_permission(self):
        from datetime import date, timedelta
        days = [(date(2040, 1, 1) + timedelta(days=i)).isoformat() for i in range(360)]
        objects = [{"dataset": k, "period": {"from": days[0], "to": days[-1]}, "repository": "test/inventory",
            "object_key": k, "sha256": "a" * 64, "bytes": 1, "destination_commit": "b" * 40,
            "destination_git_blob": "c" * 40} for k in ("DAILY", "DATED_MASTER")]
        result = inventory_window(days, objects, [{"from": days[-100], "through": days[-1]}])
        self.assertEqual(result["split"]["FINAL"][-1], days[-1])
        self.assertEqual(len(result["protected_dates"]), 100)
        self.assertFalse(result["record_date_coverage_verified"])
        self.assertEqual(result["authorized_teacher_dates"], [])
        self.assertEqual(len(result["source_bindings"]), 700)

    def test_m22_calendar_gaps_are_not_exchange_holidays(self):
        import gzip, hashlib
        raw = gzip.compress(b"Date,HolDiv\n2040-01-01,1\n2040-01-03,1\n")
        with self.assertRaisesRegex(V2Error, "DATE_GAP_OR_DUPLICATE"):
            cash_calendar_metadata(raw, hashlib.sha256(raw).hexdigest())
