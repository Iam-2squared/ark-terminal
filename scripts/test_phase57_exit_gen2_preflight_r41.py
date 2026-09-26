"""Synthetic pre-performance gates. Never reads Development artifacts."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.phase57_exit_gen2_preflight_r41 import (
    BRANCH, CONTRACT_WORKFLOW, EXPOSURE, FINITE_WORKFLOW, LAUNCH_PATH,
    PROTOCOL_PATH, R35_SHA256, REPOSITORY, SAFETY_KEYS, assert_safety,
    contract_receipt, launch_receipt, main, source_manifest, validate_protocol,
)


def synthetic_protocol():
    return {
        "execution": {"candidateCount": 16, "expectedModelFitCount": 64,
                      "predictionSpecCount": 4, "heads": 2, "entryArms": 2, "folds": 4,
                      "runAB": "REPLAY_FROM_SINGLE_IMMUTABLE_PREDICTION_SET",
                      "scorecardPhase": "NEXT_WORK_AFTER_ARTIFACT_AUDIT"},
        "candidates": [{"id": i} for i in range(16)],
        "predictionSpecs": [{"id": i} for i in range(4)],
        "baselineSourceHashes": {"scripts/frozen_baseline.py":
            hashlib.sha256(b"frozen_value = 1\n").hexdigest()},
        "safety": {key: False for key in SAFETY_KEYS},
        "exposure": dict(EXPOSURE),
    }


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.write("scripts/phase57_exit_gen2_runner_r41.py", "from scripts.dependency import value\n")
        self.write("scripts/dependency.py", "from scripts.leaf import value\n")
        self.write("scripts/leaf.py", "value = 1\n")
        self.write("scripts/frozen_baseline.py", "frozen_value = 1\n")
        self.write("scripts/test_phase57_exit_gen2_fixture_r41.py", "import scripts.dependency\n")
        self.write("scripts/phase57_exit_failure_anatomy_r40.py", "import scripts.dependency\n")
        self.write("scripts/test_phase57_exit_failure_anatomy_r40.py", "import scripts.dependency\n")
        self.write(CONTRACT_WORKFLOW, "name: synthetic contract\n")
        self.write(FINITE_WORKFLOW, "name: synthetic finite\n")
        self.write(PROTOCOL_PATH, json.dumps(synthetic_protocol()))
        self.precommit = "1" * 40
        self.execution = "2" * 40
        self.environment = {
            "GITHUB_SHA": self.precommit, "GITHUB_RUN_ID": "10", "GITHUB_REPOSITORY": REPOSITORY,
            "GITHUB_REF": f"refs/heads/{BRANCH}", "GITHUB_RUN_ATTEMPT": "1",
        }
        with patch.dict(os.environ, self.environment):
            self.prerequisite = contract_receipt(self.root)
        self.launch = {
            "schemaVersion": "phase57-exit-gen2-launch-r41-v1", "generation": "R41",
            "precommitHead": self.precommit, "requiredContractRunId": 10,
            **{key: self.prerequisite[key] for key in (
                "protocolSha256", "sourceSha256", "candidateCount", "expectedModelFitCount",
                "safety", "exposure")},
            "r35Artifact": {"runId": 36220335998, "id": 10899151845, "digestSha256": R35_SHA256},
        }
        self.write(LAUNCH_PATH, json.dumps(self.launch))
        self.environment.update(GITHUB_SHA=self.execution, GITHUB_RUN_ID="20")
        self.overrides = {}

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def get(self, endpoint):
        if endpoint in self.overrides:
            return copy.deepcopy(self.overrides[endpoint])
        if endpoint == f"/git/ref/heads/{BRANCH}":
            return {"object": {"sha": self.execution}}
        if endpoint == "/actions/runs/10":
            return {"head_sha": self.precommit, "path": CONTRACT_WORKFLOW,
                    "status": "completed", "conclusion": "success"}
        if endpoint == "/actions/runs/20":
            return {"head_sha": self.execution, "path": FINITE_WORKFLOW}
        if endpoint.startswith("/compare/"):
            return {"status": "ahead", "behind_by": 0, "ahead_by": 1,
                    "files": [{"filename": LAUNCH_PATH}]}
        if endpoint.startswith("/actions/workflows/phase57-exit-gen2-r41.yml"):
            return {"workflow_runs": [{"id": 20, "status": "in_progress"}]}
        if endpoint.startswith("/actions/workflows/phase57-exit-finite-r36.yml"):
            return {"workflow_runs": [{"id": 1, "status": "completed"}]}
        if endpoint == "/actions/artifacts/10899151845":
            return {"workflow_run": {"id": 36220335998}, "expired": False,
                    "digest": f"sha256:{R35_SHA256}"}
        if endpoint == "/actions/runs/36220335998":
            return {"status": "completed", "conclusion": "success"}
        self.fail(f"unexpected API call: {endpoint}")

    def verify(self, get=None):
        with patch.dict(os.environ, self.environment):
            return launch_receipt(self.root, self.prerequisite, get or self.get)

    def test_contract_manifest_includes_transitive_imports(self):
        manifest = source_manifest(self.root)
        self.assertIn("scripts/leaf.py", manifest)
        self.assertIn("scripts/dependency.py", manifest)
        self.assertIn("scripts/phase57_exit_failure_anatomy_r40.py", manifest)
        self.assertIn("scripts/test_phase57_exit_failure_anatomy_r40.py", manifest)
        self.assertIn(PROTOCOL_PATH, manifest)
        self.assertIn(CONTRACT_WORKFLOW, manifest)
        self.assertNotIn(LAUNCH_PATH, manifest)

    def test_synthetic_launch_passes_without_fitting(self):
        receipt = self.verify()
        self.assertEqual(receipt["status"], "GEN2_LAUNCH_VERIFIED_FIT_NOT_STARTED")
        self.assertEqual(receipt["modelFitsPerformed"], 0)
        self.assertEqual(receipt["expectedModelFitCount"], 64)

    def test_changed_transitive_dependency_fails(self):
        self.write("scripts/leaf.py", "value = 2\n")
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            self.verify()

    def test_changed_frozen_baseline_fails_before_launch(self):
        self.write("scripts/frozen_baseline.py", "frozen_value = 2\n")
        with self.assertRaisesRegex(ValueError, "baseline source hash mismatch"):
            contract_receipt(self.root)
        with self.assertRaisesRegex(ValueError, "baseline source hash mismatch"):
            self.verify()

    def test_nonliteral_dynamic_import_fails(self):
        self.write("scripts/leaf.py", "value = __import__(some_name)\n")
        with self.assertRaisesRegex(ValueError, "unresolved dynamic import"):
            source_manifest(self.root)

    def test_missing_local_dependency_fails(self):
        self.write("scripts/leaf.py", "from scripts.absent import value\n")
        with self.assertRaisesRegex(ValueError, "missing local dependency"):
            source_manifest(self.root)

    def test_latest_head_changed_fails(self):
        self.overrides[f"/git/ref/heads/{BRANCH}"] = {"object": {"sha": "3" * 40}}
        with self.assertRaisesRegex(ValueError, "no longer branch HEAD"):
            self.verify()

    def test_rerun_attempt_fails(self):
        self.environment["GITHUB_RUN_ATTEMPT"] = "2"
        with self.assertRaisesRegex(ValueError, "cannot be rerun"):
            self.verify()

    def test_unsuccessful_required_ci_fails(self):
        run = self.get("/actions/runs/10")
        run["conclusion"] = "failure"
        self.overrides["/actions/runs/10"] = run
        with self.assertRaisesRegex(ValueError, "not successful"):
            self.verify()

    def test_launch_commit_with_code_change_fails(self):
        self.overrides[f"/compare/{self.precommit}...{self.execution}"] = {
            "status": "ahead", "behind_by": 0, "ahead_by": 1,
            "files": [{"filename": LAUNCH_PATH}, {"filename": "scripts/leaf.py"}],
        }
        with self.assertRaisesRegex(ValueError, "only the launch marker"):
            self.verify()

    def test_another_gen2_run_fails_even_if_complete(self):
        def duplicate(endpoint):
            if endpoint.startswith("/actions/workflows/phase57-exit-gen2-r41.yml"):
                return {"workflow_runs": [{"id": 20}, {"id": 19, "status": "completed"}]}
            return self.get(endpoint)
        with self.assertRaisesRegex(ValueError, "another generation R41"):
            self.verify(duplicate)

    def test_active_r36_job_fails(self):
        def active(endpoint):
            if endpoint.startswith("/actions/workflows/phase57-exit-finite-r36.yml"):
                return {"workflow_runs": [{"id": 1, "status": "in_progress"}]}
            return self.get(endpoint)
        with self.assertRaisesRegex(ValueError, "legacy R36 performance job is active"):
            self.verify(active)

    def test_mutated_r35_digest_fails(self):
        artifact = self.get("/actions/artifacts/10899151845")
        artifact["digest"] = "sha256:" + "0" * 64
        self.overrides["/actions/artifacts/10899151845"] = artifact
        with self.assertRaisesRegex(ValueError, "archive digest mismatch"):
            self.verify()

    def test_exact_safety_and_exposure_types_required(self):
        for value in (True, 0, None):
            safety = synthetic_protocol()["safety"]
            safety["transmitted"] = value
            with self.assertRaises(ValueError):
                assert_safety(safety)
        protocol = synthetic_protocol()
        protocol["exposure"]["gen2ModelFits"] = False
        with self.assertRaisesRegex(ValueError, "exposure mismatch"):
            validate_protocol(protocol)

    def test_budget_and_future_scorecard_guards(self):
        for key, value in (("expectedModelFitCount", 65), ("candidateCount", 17),
                           ("scorecardPhase", "SELECT_NOW")):
            protocol = synthetic_protocol()
            protocol["execution"][key] = value
            with self.assertRaises(ValueError):
                validate_protocol(protocol)

    def test_append_only_preserves_existing_success_or_failure_evidence(self):
        for existing_kind in ("success", "failure"):
            with self.subTest(existing_kind=existing_kind):
                output = self.root / existing_kind / "receipt.json"
                failure = output.with_suffix(".failure.json")
                existing = output if existing_kind == "success" else failure
                existing.parent.mkdir(parents=True)
                previous = b'{"previous":"immutable evidence"}\n'
                existing.write_bytes(previous)
                argv = ["preflight", "--mode", "contract", "--root", str(self.root), "--out", str(output)]
                with patch("sys.argv", argv), self.assertRaisesRegex(ValueError, "evidence already exists"):
                    main()
                self.assertEqual(existing.read_bytes(), previous)
                self.assertFalse((failure if existing_kind == "success" else output).exists())


if __name__ == "__main__":
    unittest.main()
