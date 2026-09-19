import copy
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts import phase57_raw_selector_direct_entry_window as study


class FrozenWindowEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol, cls.episodes, cls.paths, cls.legacy = study.load_sources()
        cls.train = [episode for episode in cls.episodes if episode["session"] in cls.protocol["split"]["TRAIN"]]

    def test_source_identity_and_partition_counts(self):
        self.assertEqual(len(self.episodes), 2841)
        self.assertEqual(len(self.train), 1422)
        self.assertEqual(sum(e["session"] in self.protocol["split"]["VALIDATION"] for e in self.episodes), 710)
        self.assertEqual(sum(e["session"] in self.protocol["split"]["DEVELOPMENT_TEST"] for e in self.episodes), 709)

    def test_every_snapshot_is_exact_top5(self):
        rows = study.preflight.project(study.read(study.RAW_PATH)["new"])
        counts = {}
        for row in rows:
            counts[row["decisionTimestamp"]] = counts.get(row["decisionTimestamp"], 0) + 1
        self.assertEqual(len(counts), 760)
        self.assertEqual(set(counts.values()), {5})

    def test_episode_is_one_symbol_session(self):
        self.assertEqual(len({episode["id"] for episode in self.episodes}), 2841)
        self.assertTrue(all(episode["id"] == episode["session"] + "|" + episode["symbol"] for episode in self.episodes))

    def test_score_rank_decision_price_fixed_inside_window(self):
        episode = next(e for e in self.train if e["firstSelector"]["decisionTimeJst"] == "09:30")
        first = episode["firstSelector"]
        path = self.paths[first["selectorEventId"]]
        rows = study.states(episode, path, self.legacy.get(first["selectorEventId"], {}))
        available = [row for row in rows if row["status"] == "AVAILABLE"]
        self.assertEqual({row["selectorScore"] for row in available}, {first["savedV1Score"]})
        self.assertEqual({row["selectorRank"] for row in available}, {first["newEligibleRank"]})
        self.assertEqual({row["decisionPrice"] for row in available}, {first["decisionPrice"]})
        self.assertEqual([row["features"]["snapshotAge"] for row in available], [0, 5, 10])

    def test_no_future_bar_changes_past_state(self):
        episode = next(e for e in self.train if e["firstSelector"]["decisionTimeJst"] == "09:30")
        first = episode["firstSelector"]
        path = self.paths[first["selectorEventId"]]
        baseline = study.state(episode, path, self.legacy.get(first["selectorEventId"], {}), 5)
        changed = copy.deepcopy(path)
        for bar in changed["future"]:
            if study.minute(bar["start"]) >= study.minute(first["decisionTimestamp"]) + 5 and not bar.get("missing"):
                bar.update(o=999, h=999, l=-999, c=999)
        self.assertEqual(baseline, study.state(episode, changed, self.legacy.get(first["selectorEventId"], {}), 5))

    def test_execution_uses_scheduled_open_after_fixed_decision(self):
        episode = next(e for e in self.train if e["firstSelector"]["decisionTimeJst"] == "09:30")
        first = episode["firstSelector"]
        path = self.paths[first["selectorEventId"]]
        expected = study.v2.open_reference(path, study.minute(first["decisionTimestamp"]) + 5)
        actual = study.evaluate(episode, path, 5)
        self.assertAlmostEqual(actual["price"], expected)

    def test_boundary_snapshots_do_not_carry_lunch_or_close(self):
        for time in ("11:30", "15:00"):
            episode = next(e for e in self.train if e["firstSelector"]["decisionTimeJst"] == time)
            first = episode["firstSelector"]
            path = self.paths[first["selectorEventId"]]
            self.assertEqual(study.state(episode, path, self.legacy.get(first["selectorEventId"], {}), 0)["status"], "EXPIRE_BOUNDARY")

    def test_train_labels_only_use_now_and_exact_next(self):
        pit, rows = study.training_dataset(self.train[:80], self.paths, self.legacy)
        self.assertTrue(rows)
        self.assertTrue(all(row["delay"] in (0, 5) for row in rows))
        self.assertTrue(all(len(row["targets"]) == 3 for row in rows))
        self.assertTrue(all(row["targets"][1] in (0.0, 5.0) for row in rows))
        weights = {}
        for row in rows:
            weights[row["id"]] = weights.get(row["id"], 0) + row["weight"]
        self.assertTrue(all(abs(value - 1) < 1e-12 for value in weights.values()))

    def test_serialized_tree_replay_is_deterministic(self):
        rows = []
        for index in range(240):
            features = {name: float((index + offset) % 11) for offset, name in enumerate(study.FEATURES)}
            if index % 7 == 0:
                features[study.FEATURES[-1]] = None
            rows.append({"features": features, "targets": [float(index % 3), float(index % 2) * 5, float(index % 5) / 10], "weight": 1.0})
        model1 = study.Model.fit_once(rows, self.protocol)
        model2 = study.Model.fit_once(rows, self.protocol)
        self.assertEqual(model1.artifact["tree"], model2.artifact["tree"])
        self.assertTrue(np.array_equal(model1.predict_many([r["features"] for r in rows]), model2.predict_many([r["features"] for r in rows])))

    def test_watch_cap_forces_buy(self):
        episode = next(e for e in self.train if e["firstSelector"]["decisionTimeJst"] == "09:30")
        first = episode["firstSelector"]
        path = self.paths[first["selectorEventId"]]
        projected = study.states(episode, path, self.legacy.get(first["selectorEventId"], {}))

        class AlwaysWatch:
            @staticmethod
            def predict(_features):
                return [1.0, 0.0, 1.0]

        decision = study.decide(episode, path, projected, AlwaysWatch(), self.protocol)
        self.assertEqual(decision["status"], "COUNTERFACTUAL_ENTER")
        self.assertEqual(decision["delay"], 10)
        self.assertEqual([row["action"] for row in decision["transitions"]], ["WATCH", "WATCH", "BUY_NOW"])

    def test_no_drop_or_model_skip_action(self):
        source = Path(study.__file__).read_text()
        self.assertNotIn('"MODEL_SKIP"', source)
        self.assertNotIn('"DROP"', source)

    def test_feature_manifest_exact_and_future_free(self):
        self.assertEqual(study.FEATURES, study.read(study.FEATURE_PATH)["features"])
        forbidden = ("future", "mfe", "mae", "terminal")
        self.assertTrue(all(not any(token in name.lower() for token in forbidden) for name in study.FEATURES))

    def test_safety_and_no_overwrite(self):
        self.assertEqual(len(study.SAFETY), 9)
        self.assertTrue(all(value is False for value in study.SAFETY.values()))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                study.run(directory)


if __name__ == "__main__":
    unittest.main()
