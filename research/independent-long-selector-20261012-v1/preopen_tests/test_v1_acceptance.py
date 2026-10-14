"""Tamper and negative-regression tests for the read-only measured V1 gate."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "v1_acceptance" / "verify.py"
spec = importlib.util.spec_from_file_location("preopen_v1_read_only_acceptance", MODULE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class ReadOnlyV1AcceptanceTests(unittest.TestCase):
    def test_existing_measured_v1_is_complete_only_as_research(self):
        receipt = gate.verify(ROOT)
        self.assertEqual(receipt["verdict"], "RESEARCH_ENGINEERING_ARTIFACT_COMPLETE")
        self.assertEqual(receipt["quality"], "NOT_APPROVED")
        self.assertEqual(receipt["liveReadiness"], "NOT_CERTIFIED")
        self.assertEqual((receipt["up1SelectedN"], receipt["up1TurnoverBaselineN"]), (34, 56))
        self.assertFalse(receipt["newCandidateAuthorized"])
        self.assertEqual(receipt["freshOosCredit"], 0)
        self.assertEqual(receipt["realOrders"], 0)
        self.assertEqual(len(receipt["tickShiftedColumns"]), 5)
        for flag in gate.SAFE_FLAGS:
            self.assertIs(receipt[flag], False)

    def _copy_public_artifacts(self, dest):
        for name in gate.PINNED_PUBLIC_BLOBS:
            shutil.copyfile(ROOT / name, dest / name)
        for path in ROOT.glob("*.py"):
            shutil.copyfile(path, dest / path.name)

    def test_research_score_false_promotion_is_rejected_even_if_hash_resigned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._copy_public_artifacts(root)
            p = root / "REPORT_AGGREGATE.json"
            report = json.loads(p.read_text(encoding="utf-8"))
            report["researchQuality"]["predictionQualityPass"] = True
            p.write_text(json.dumps(report), encoding="utf-8")
            modified = gate.blob_sha(p.read_bytes())
            with patch.dict(gate.PINNED_PUBLIC_BLOBS, {"REPORT_AGGREGATE.json": modified}):
                with self.assertRaisesRegex(gate.GateError, "RESEARCH_QUALITY_FALSE_PROMOTION"):
                    gate.verify(root)

    def test_live_execution_true_is_rejected_even_if_hash_resigned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._copy_public_artifacts(root)
            p = root / "CURRENT_STATUS.json"
            status = json.loads(p.read_text(encoding="utf-8"))
            status["executionAllowed"] = True
            p.write_text(json.dumps(status), encoding="utf-8")
            modified = gate.blob_sha(p.read_bytes())
            with patch.dict(gate.PINNED_PUBLIC_BLOBS, {"CURRENT_STATUS.json": modified}):
                with self.assertRaisesRegex(gate.GateError, "status:UNSAFE_OR_MISSING_FLAG"):
                    gate.verify(root)

    def test_unreviewed_public_report_edit_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._copy_public_artifacts(root)
            p = root / "REPORT_AGGREGATE.json"
            p.write_bytes(p.read_bytes() + b" ")
            with self.assertRaisesRegex(gate.GateError, "PUBLIC_ARTIFACT_CHANGED:REPORT"):
                gate.verify(root)

    def test_root_computation_code_is_bound_even_if_gate_not_in_hash(self):
        self.assertEqual(gate.check_source_code_binding(ROOT), gate.CODE_SHA)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._copy_public_artifacts(root)
            p = root / "preopen_selector.py"
            p.write_bytes(p.read_bytes() + b"\n# changed\n")
            with self.assertRaisesRegex(gate.GateError, "COMPUTATION_CODE_HASH_DRIFT"):
                gate.verify(root)


if __name__ == "__main__":
    unittest.main()
