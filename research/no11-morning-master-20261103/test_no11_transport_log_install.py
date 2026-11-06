"""Synthetic fail-closed installer regression: no Excel or orders."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_no11_transport_error_forwarding as mod


def h(raw):
    return hashlib.sha256(raw).hexdigest()


class TransportLogInstallerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = self.root / "unified-launcher"
        self.store.mkdir()
        self.bridge = self.root / "launcher_automatic_bridge_v4.py"
        self.original = (
            b"def forward(lines):\n"
            b"    for line in lines:\n"
            b"        " + mod.OLD + b"\n"
            b"            print(line)\n"
        )
        self.bridge.write_bytes(self.original)
        self.probe = self.root / "Prepare-No11AutomaticLiveTransportV3.ps1"
        self.probe.write_text("# no Excel access", encoding="utf-8")
        self.settings = self.store / "settings.json"
        self.settings.write_text(json.dumps({
            "schemaId": "ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1",
            "sameDayApprovalRequired": True,
            "automaticOrderAuthorization": False,
            "orderTransmission": False
        }), encoding="utf-8")
        self.binding_path = self.store / "automatic-inputs.json"
        self.binding = {
            "schemaId": mod.SCHEMA,
            "orderTransmission": False,
            "bridge": str(self.bridge),
            "bridgeSha256": h(self.original),
            "transportProbe": str(self.probe),
            "transportProbeSha256": h(self.probe.read_bytes()),
            "settings": str(self.settings),
            "unrelatedSourceHash": "never-touch",
        }
        self.write_binding()

    def write_binding(self):
        self.binding_path.write_text(json.dumps(self.binding, separators=(",", ":")) + "\n",
                                     encoding="utf-8")

    def test_audit_does_not_modify_or_create_files(self):
        before = self.binding_path.read_bytes()
        self.assertEqual(mod.apply(self.binding_path, live=False), "READY")
        self.assertEqual(self.bridge.read_bytes(), self.original)
        self.assertEqual(self.binding_path.read_bytes(), before)
        self.assertEqual(len(list(self.store.glob("transport-log-fix-backup-*"))), 0)

    def test_apply_exact_line_and_pinned_hash_with_backup_and_idempotence(self):
        prior = self.binding_path.read_bytes()
        self.assertEqual(mod.apply(self.binding_path, _test_mode=True), "PASS")
        patched = self.original.replace(mod.OLD, mod.NEW)
        self.assertEqual(self.bridge.read_bytes(), patched)
        newbinding = json.loads(self.binding_path.read_text(encoding="utf-8"))
        self.assertEqual(newbinding["bridgeSha256"], h(patched))
        self.assertEqual(newbinding["unrelatedSourceHash"], "never-touch")
        self.assertEqual(newbinding["transportProbeSha256"], self.binding["transportProbeSha256"])
        self.assertEqual(self.settings.read_text(encoding="utf-8"),
                         self.settings.read_text(encoding="utf-8"))
        backups = list(self.store.glob("transport-log-fix-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "bridge.before.py").read_bytes(), self.original)
        self.assertEqual((backups[0] / "automatic-inputs.before.json").read_bytes(), prior)
        self.assertEqual(mod.apply(self.binding_path, _test_mode=True), "ALREADY_APPLIED")
        self.assertEqual(len(list(self.store.glob("transport-log-fix-backup-*"))), 1)

    def test_local_bridge_changed_fails_closed(self):
        before = self.binding_path.read_bytes()
        self.bridge.write_bytes(self.original + b"# local change\n")
        with self.assertRaisesRegex(ValueError, "BOUND_BRIDGE_SHA_CHANGED"):
            mod.apply(self.binding_path, _test_mode=True)
        self.assertEqual(self.binding_path.read_bytes(), before)
        self.assertEqual(len(list(self.store.glob("transport-log-fix-backup-*"))), 0)

    def test_physical_probe_changed_fails_closed(self):
        self.probe.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "PHYSICAL_TRANSPORT_PROBE_CHANGED"):
            mod.apply(self.binding_path, _test_mode=True)
        self.assertEqual(self.bridge.read_bytes(), self.original)

    def test_modified_log_filter_fails_closed(self):
        changed = self.original.replace(mod.OLD, b"if line.startswith(('SILENT',)):")
        self.bridge.write_bytes(changed)
        self.binding["bridgeSha256"] = h(changed)
        self.write_binding()
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_BRIDGE_CONTENT"):
            mod.apply(self.binding_path, _test_mode=True)

    def test_unsafe_order_setting_fails_closed(self):
        settings = json.loads(self.settings.read_text(encoding="utf-8"))
        settings["automaticOrderAuthorization"] = True
        self.settings.write_text(json.dumps(settings), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SAFETY_SETTINGS"):
            mod.apply(self.binding_path, _test_mode=True)
        self.assertEqual(self.bridge.read_bytes(), self.original)

    def test_rollback_after_binding_write_failure(self):
        before_binding = self.binding_path.read_bytes()
        original_atomic = mod.write_atomic
        failed = [False]

        def fail_binding(path, content, previous):
            if path == self.binding_path and not failed[0]:
                failed[0] = True
                raise OSError("mock IO error")
            return original_atomic(path, content, previous)

        with patch.object(mod, "write_atomic", side_effect=fail_binding):
            with self.assertRaises(OSError):
                mod.apply(self.binding_path, _test_mode=True)
        self.assertEqual(self.bridge.read_bytes(), self.original)
        self.assertEqual(self.binding_path.read_bytes(), before_binding)


if __name__ == "__main__":
    unittest.main(verbosity=2)
