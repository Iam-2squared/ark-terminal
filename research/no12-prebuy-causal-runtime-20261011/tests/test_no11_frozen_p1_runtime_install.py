"""Stdlib tests of portable bundle integrity and sampled-runtime scope."""

import builtins
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location(
    "no11_frozen_p1_runtime_install", TOOLS / "no11_frozen_p1_runtime_install.py")
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


class RuntimeInstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_spec = RUNTIME.core.load_contracts()
        cls.original_package = RUNTIME.load_package(cls.original_spec)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.private = self.root / "private"
        self.bundle = self.root / "tiny-private-fixture.zip"
        self.spec = deepcopy(self.original_spec)
        self.package = deepcopy(self.original_package)
        self.payloads = {name: (name + "\n").encode()
                         for name in self.package["members"]}
        for name, data in self.payloads.items():
            pin = {"bytes": len(data), "sha256": RUNTIME.core.digest(data)}
            self.package["members"][name].update(pin)
            if name.startswith("ORIGINAL_P1/"):
                self.spec["corrected"][name[len("ORIGINAL_P1/"):]].update(pin)
        self.write_bundle()

    def write_bundle(self, omit=None):
        with zipfile.ZipFile(self.bundle, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in self.payloads.items():
                if name != omit:
                    archive.writestr(name, data)
        data = self.bundle.read_bytes()
        self.package["bundle"] = {"filename": self.bundle.name, "bytes": len(data),
                                   "sha256": RUNTIME.core.digest(data)}

    def materialize(self):
        return RUNTIME.materialize_bundle(
            self.bundle, self.package, self.spec, self.private)

    def test_all_43_members_verified_and_restored(self):
        files = self.materialize()
        self.assertEqual(len(files), 43)
        self.assertEqual(len(RUNTIME.inference_names(self.spec)), 41)
        for name, path in files.items():
            self.assertEqual(path.read_bytes(), self.payloads[name])

    def test_whole_bundle_modification_fails_before_extraction(self):
        data = bytearray(self.bundle.read_bytes())
        data[100] ^= 1
        self.bundle.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "P1_ARTIFACT_HASH_MISMATCH"):
            self.materialize()
        self.assertFalse((self.private / "verified").exists())

    def test_member_modification_fails_even_with_updated_container_hash(self):
        name = next(iter(self.payloads))
        self.payloads[name] = bytes([self.payloads[name][0] ^ 1]) + self.payloads[name][1:]
        self.write_bundle()
        with self.assertRaisesRegex(ValueError, "P1_RUNTIME_ZIP_MEMBER_HASH_MISMATCH"):
            self.materialize()
        self.assertFalse((self.private / "verified").exists())

    def test_missing_model_member_is_rejected(self):
        self.write_bundle(omit="ORIGINAL_P1/PRIVATE_MODELS/P1_F5_ADVERSE.pkl")
        with self.assertRaisesRegex(ValueError, "P1_RUNTIME_ZIP_MEMBERS_MISMATCH"):
            self.materialize()
        self.assertFalse((self.private / "verified").exists())

    def test_package_cannot_reduce_the_fifteen_model_allowlist(self):
        del self.package["members"]["ORIGINAL_P1/PRIVATE_MODELS/P1_F5_ADVERSE.pkl"]
        self.package["memberCount"] -= 1
        self.package["originalModelCount"] -= 1
        with self.assertRaisesRegex(ValueError, "P1_RUNTIME_MEMBER_SET_INCOMPLETE"):
            RUNTIME.validate_package(self.package, self.spec)

    def test_an_extra_path_is_not_extracted(self):
        self.payloads["../escaped.txt"] = b"must not be extracted"
        self.write_bundle()
        with self.assertRaisesRegex(ValueError, "P1_RUNTIME_ZIP_MEMBERS_MISMATCH"):
            self.materialize()
        self.assertFalse((self.private / "verified").exists())

    def test_verify_only_never_imports_science_or_executes_models(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.split(".", 1)[0] in {"numpy", "scipy", "sklearn", "threadpoolctl"}:
                raise AssertionError("scientific import during verify-only")
            return original_import(name, *args, **kwargs)

        output = io.StringIO()
        with mock.patch.object(RUNTIME.core, "load_contracts", return_value=self.spec), \
                mock.patch.object(RUNTIME, "load_package", return_value=self.package), \
                mock.patch.object(RUNTIME, "run_runtime_smoke") as smoke, \
                mock.patch("builtins.__import__", guarded_import), redirect_stdout(output):
            code = RUNTIME.main(["--private-root", str(self.private),
                                 "--bundle", str(self.bundle), "--verify-only"])
        self.assertEqual(code, 0)
        smoke.assert_not_called()
        self.assertIn("PRECHECK=PASS", output.getvalue())
        self.assertNotIn("REPORT_JSON=", output.getvalue())
        self.assertEqual(list(self.private.glob("*.json")), [])

    def test_missing_bundle_writes_a_blocked_aggregate_report(self):
        with mock.patch.object(RUNTIME.core, "load_contracts", return_value=self.spec), \
                mock.patch.object(RUNTIME, "load_package", return_value=self.package), \
                redirect_stdout(io.StringIO()):
            code = RUNTIME.main(["--private-root", str(self.private)])
        self.assertEqual(code, 2)
        reports = list(self.private.glob("no11-frozen-p1-score-replay-*.json"))
        self.assertEqual(len(reports), 1)
        report = json.loads(reports[0].read_bytes())
        self.assertEqual(report["status"], "BLOCKED_PRIVATE_P1_INFERENCE_BUNDLE_MISSING")
        self.assertEqual(report["reason"], "P1_RUNTIME_BUNDLE_REQUIRED")
        self.assertFalse(report["fullOofReplay"])
        self.assertFalse(report["firstIntentParityPassed"])
        self.assertFalse(report["orderTransmission"])
        self.assertEqual(report["originalP1ModelsExecuted"], 0)

    def test_sample_and_prior_full_replay_scopes_cannot_be_confused(self):
        report = RUNTIME.new_runtime_report()
        self.assertEqual(report["samplePerFold"], 32)
        self.assertTrue(report["sampledRuntimeOnly"])
        self.assertFalse(report["fullOofReplay"])
        self.assertFalse(report["firstIntentParityPassed"])
        self.assertEqual(report["priorFullReplayEvidenceSha256"], RUNTIME.FULL_REPLAY_SHA256)
        self.assertEqual(report["modelDispatch2026"], "UNDEFINED_IN_ORIGINAL_FROZEN_SPLIT")
        self.package["fullOofReplay"] = True
        with self.assertRaisesRegex(ValueError, "P1_RUNTIME_PACKAGE_SCOPE_CHANGED"):
            RUNTIME.validate_package(self.package, self.spec)

    def test_runtime_failure_leaves_a_sanitized_blocked_report(self):
        with mock.patch.object(RUNTIME.core, "load_contracts", return_value=self.spec), \
                mock.patch.object(RUNTIME, "load_package", return_value=self.package), \
                mock.patch.object(RUNTIME, "run_runtime_smoke", side_effect=RuntimeError("PRIVATE_DATA")), \
                redirect_stdout(io.StringIO()):
            code = RUNTIME.main(["--private-root", str(self.private), "--bundle", str(self.bundle)])
        self.assertEqual(code, 2)
        reports = list(self.private.glob("no11-frozen-p1-score-replay-*.json"))
        self.assertEqual(len(reports), 1)
        text = reports[0].read_text()
        self.assertNotIn("PRIVATE_DATA", text)
        report = json.loads(text)
        self.assertEqual(report["status"], "BLOCKED_ORIGINAL_P1_RUNTIME_SMOKE")
        self.assertEqual(report["reason"], "RuntimeError")

    def test_public_receipt_pin_accepts_windows_crlf(self):
        public = self.root / "package.json"
        original = RUNTIME.PACKAGE_PATH.read_bytes().replace(b"\r\n", b"\n")
        public.write_bytes(original.replace(b"\n", b"\r\n"))
        self.assertEqual(RUNTIME.load_package(self.original_spec, public), self.original_package)

    def test_public_receipt_modification_is_rejected(self):
        public = self.root / "package.json"
        public.write_bytes(RUNTIME.PACKAGE_PATH.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "P1_RUNTIME_PUBLIC_PACKAGE_PIN_MISMATCH"):
            RUNTIME.load_package(self.original_spec, public)


if __name__ == "__main__":
    unittest.main()
