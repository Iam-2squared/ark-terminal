"""Guard tests use invented metadata only; no market prices or network calls."""
from datetime import datetime, timezone, timedelta
import json
import tempfile
from pathlib import Path
import unittest
from preflight import atomic_report, inspect_inputs, license_reasons, rate_reasons, snapshot_reasons, storage_reasons


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 6, 4, tzinfo=timezone.utc)
        self.license = {
            "dataset": "SYNTHETIC", "active_now": True,
            "evidence": [{"kind": "LIVE_ACCOUNT", "observed_at": "2026-10-06T03:59:00Z"}],
            "acquisition_allowed_until": "2026-10-06T10:02:00Z",
            "use_allowed_until": "2026-10-06T10:02:00Z",
            "retention_requires_active_license": True,
        }

    def test_screenshot_never_proves_live_entitlement(self):
        self.license["evidence"][0]["kind"] = "USER_SCREENSHOT"
        self.assertIn("LIVE_ENTITLEMENT_EVIDENCE_MISSING", license_reasons(self.license, self.now))

    def test_exact_deadline_rejects_fetch_and_read(self):
        end = datetime(2026, 10, 6, 10, 2, tzinfo=timezone.utc)
        for operation in ("acquire", "read"):
            self.assertIn("LICENSE_ENDED_USE_STOPPED", license_reasons(self.license, end, operation))

    def test_base_and_addon_deadlines_stay_distinct(self):
        now = datetime(2026, 10, 6, 10, 3, tzinfo=timezone.utc)
        base = license_reasons(self.license, now)
        addon = dict(self.license, acquisition_allowed_until="2026-10-06T10:07:00Z", use_allowed_until="2026-10-06T10:07:00Z")
        self.assertIn("LICENSE_ENDED_USE_STOPPED", base)
        self.assertNotIn("LICENSE_ENDED_USE_STOPPED", license_reasons(addon, now))

    def test_unconfirmed_extension_rejected(self):
        self.license["previous_confirmed_until"] = "2026-10-06T09:00:00Z"
        self.license["renewal_confirmed"] = True
        self.assertIn("UNSUPPORTED_LICENSE_EXTENSION", license_reasons(self.license, self.now))

    def test_future_or_naive_clock_is_not_evidence(self):
        for value in ("2026-10-07T04:00:00Z", "2026-10-06T03:59:00"):
            self.license["evidence"][0]["observed_at"] = value
            self.assertIn("LIVE_ENTITLEMENT_EVIDENCE_MISSING", license_reasons(self.license, self.now))
        with self.assertRaises(ValueError):
            license_reasons(self.license, self.now.replace(tzinfo=None))

    def test_missing_durable_root_never_becomes_success(self):
        self.assertIn("BLOCKED_DURABLE_DESTINATION", storage_reasons({"private_cache_root": None}))

    def test_private_name_and_scratch_marker_do_not_prove_durability(self):
        with tempfile.TemporaryDirectory(prefix="private-cache-") as name:
            root = Path(name)
            (root / ".ark-cache-binding.json").write_text('{"binding_id":"fixture"}')
            binding = dict.fromkeys(("owner_controlled", "owner_only_access_verified", "durability_verified", "deletion_supported"), True)
            binding.update(private_cache_root=name, binding_id="fixture")
            self.assertIn("EPHEMERAL_STORAGE_NOT_DURABLE", storage_reasons(binding))

    def test_worker_local_rate_limit_never_counts_as_shared(self):
        contract = {"shared_rate_limit": {"bound": True, "aggregate_rpm": 54}}
        self.assertIn("SHARED_ACCOUNT_LIMITER_UNBOUND", rate_reasons(contract))

    def test_pinned_head_without_allowlist_is_insufficient(self):
        contract = {"main_snapshot": {"basis_head": "fixture", "automatic_adoption": False}, "cancel_in_progress": False}
        self.assertIn("MAIN_SNAPSHOT_READER_BINDING_UNVERIFIED", snapshot_reasons(contract))

    def test_missing_inputs_cannot_report_zero_target_complete(self):
        report = inspect_inputs({}, {}, {}, True, self.now)
        self.assertEqual(report["status"], "CACHE_BLOCKED_AUTH_OR_STORAGE")
        for name in ("provider_requests", "raw_bytes_transferred", "model_fits", "capital_replays", "main_jobs_cancelled"):
            self.assertEqual(report[name], 0)
        self.assertIn("DATASET_ENTITLEMENT_REGISTRY_UNBOUND", report["blockers"])

    def test_reports_publish_complete_json_atomically(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "report.json"
            atomic_report(path, {"status": "OLD"})
            atomic_report(path, {"status": "BLOCKED", "objects_total": None})
            self.assertEqual(json.loads(path.read_text()), {"status": "BLOCKED", "objects_total": None})
            self.assertEqual(len(list(Path(name).iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
