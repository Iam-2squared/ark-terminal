"""Synthetic provenance and feature/label boundary tests; no historical fits."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import phase57_exit_gen2_data_r41 as data
from scripts import phase57_exit_checkpoints_v1 as r20
from scripts.phase57_exit_gen2_labels_r41 import event_labels
from scripts.phase57_exit_execution_contract_v1 import continuous_minutes


DAY = "2025-05-30"


class DataBoundaryTest(unittest.TestCase):
    def protocol(self):
        return json.loads(data.PROTOCOL_PATH.read_text())

    def fixture(self, root):
        protocol = self.protocol()
        sessions = data.r25.development_sessions()
        manifest = {
            "projectionSha256": protocol["features"]["r35ProjectionSha256"],
            "fitContractSha256": protocol["features"]["coreFitContractSha256"],
            "outputHashes": {}, "sessions": 58, "populationPerArm": 2155,
            "categoricalFields": 21, "numericFields": 83,
            "checkpointCounts": {data.r36.ARMS[0]: 345893, data.r36.ARMS[1]: 310354},
            "modelFits": 0, "candidateReplays": 0, "performanceInspections": 0,
            "providerRequests": 0, "protectedPartitionsOpened": 0, "safety": data.r36.SAFETY,
        }
        for relative in [*(f"checkpoints/{s}.jsonl.gz" for s in sessions),
                         "columns.json", "entry-envelopes.json.gz"]:
            blob = (relative + " synthetic\n").encode()
            manifest["outputHashes"][relative] = hashlib.sha256(blob).hexdigest()
            for variant in ("core-a", "core-b"):
                path = root / variant / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(blob)
        for variant in ("core-a", "core-b"):
            (root / variant / "manifest.json").write_text(json.dumps(manifest))
        return manifest

    def test_all_actual_r35_file_hashes_pass_on_intact_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = self.fixture(root)
            self.assertEqual(data.verify_r35(root, self.protocol()), expected)

    def test_equal_manifests_do_not_hide_tampered_b_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "core-b/columns.json").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "R35_ACTUAL_FILE_HASH:core-b/columns.json"):
                data.verify_r35(root, self.protocol())

    def test_projection_must_match_frozen_protocol_not_just_ab(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            manifest["projectionSha256"] = "0" * 64
            for variant in ("core-a", "core-b"):
                (root / variant / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "PINNED_R35_PROJECTION"):
                data.verify_r35(root, self.protocol())

    def test_output_hash_allowlist_rejects_path_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            manifest["outputHashes"]["../secret"] = "0" * 64
            for variant in ("core-a", "core-b"):
                (root / variant / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "R35_FILE_ALLOWLIST"):
                data.verify_r35(root, self.protocol())

    def test_precommit_protocol_bytes_are_pinned(self):
        self.assertEqual(data.r36.sha(data.PROTOCOL_PATH), data.PROTOCOL_SHA256)
        self.assertEqual(self.protocol()["features"]["calendarFields"], data.CALENDAR_NAMES)

    def test_extra_checkpoint_target_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "core-a/checkpoints" / f"{DAY}.jsonl.gz"
            path.parent.mkdir(parents=True)
            row = {"session": DAY, "identity": ["IMMEDIATE", DAY + "|1111|590", 600],
                   "fresh": True, "categorical": ["UNKNOWN"] * 21, "numeric": [None] * 83,
                   "futureLabel": 1}
            with gzip.open(path, "wt") as fh:
                fh.write(json.dumps(row) + "\n")
            with self.assertRaisesRegex(ValueError, "R35_ROW_FIELDS"):
                list(data._core_rows(root, DAY))

    def test_pattern_future_mutation_changes_labels_only(self):
        schedule = continuous_minutes(DAY)
        rows = [[m, 100, 100.5, 99.5, 100, 1, 1] for m in schedule]
        path = {"previousSession": None, "previous": [], "today": rows}
        changed = copy.deepcopy(path)
        next(row for row in changed["today"] if row[0] == 605)[2] = 105
        origin = {"decisionTimestamp": "2025-05-30T09:01:00+09:00"}
        def fake_pattern(**kwargs):
            prefix = kwargs["today_prefix"]
            self.assertTrue(all(bar.start + 1 <= 600 and bar.known_at <= 600 for bar in prefix))
            return {"curated": {"test": sum(bar.h for bar in prefix)}}
        with patch.object(data.feature_contract, "pattern_now", side_effect=fake_pattern):
            self.assertEqual(data.pattern_vector(DAY, 600, path, origin, ["test"]),
                             data.pattern_vector(DAY, 600, changed, origin, ["test"]))
        self.assertEqual(event_labels(600, schedule, rows)["targets"]["CONTINUATION"], 0)
        self.assertEqual(event_labels(600, schedule, changed["today"])["targets"]["CONTINUATION"], 1)

    def test_pattern_excludes_delayed_known_at_and_unclosed_bar(self):
        path = {"previousSession": None, "previous": [], "today": [
            r20.KnownBar(598, 100, 101, 99, 100, 1, 1, 599),
            r20.KnownBar(599, 100, 101, 99, 100, 1, 1, 601),
            r20.KnownBar(600, 100, 101, 99, 100, 1, 1, 601),
        ]}
        def fake_pattern(**kwargs):
            self.assertEqual([bar.start for bar in kwargs["today_prefix"]], [598])
            return {"curated": {"test": 1}}
        with patch.object(data.feature_contract, "pattern_now", side_effect=fake_pattern):
            self.assertEqual(data.pattern_vector(DAY, 600, path,
                {"decisionTimestamp": "2025-05-30T09:01:00+09:00"}, ["test"]), [1.0])

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text("original")
            with self.assertRaisesRegex(ValueError, "APPEND_ONLY_OUTPUT_EXISTS"):
                data.r36.write_json(path, {"changed": True})
            self.assertEqual(path.read_text(), "original")


if __name__ == "__main__":
    unittest.main()
