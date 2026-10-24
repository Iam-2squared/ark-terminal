#!/usr/bin/env python3
"""2026 forward-only P1/F5/Q70 shadow bridge; no fit, broker, or order writer.

The existing frozen weights and calibration are reused unchanged. This explicit
new deployment policy is NOT the original 2025 OOF date-to-fold mapping and does
NOT certify live performance. Inputs must already contain causal P1/State9
features. SQLite records Watch refreshes and the first Entry candidate atomically.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any

REPO = Path(__file__).resolve().parents[3]
BASE = "research/persistent-watchlist-uptrend-first-entry-20261003-v2"
FEATURE_SHA = "ad737e63e2a3100c4413ee30b59423f54eb197da0f9f1dcce81ffa8b71022f5e"
POLICY_SCHEMA = "ARK_NO11_P1_F5_FORWARD_SHADOW_POLICY_V1"
FEATURE_SCHEMA = "ARK_NO11_P1_CAUSAL_FEATURE_ROW_V1"
SELECTOR_SCHEMA = "ARK_NO11_NATIVE_FROZEN_SELECTOR_OBSERVED_PREFILTER_SHADOW_V1"
DECISIONS = ("09:30", "10:00", "10:30", "11:00", "11:30", "13:00", "13:30", "14:00", "14:30", "15:00")
SYMBOL = re.compile(r"^[0-9A-Z]{4}\.T$")
JST = re.compile(r"^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?\+09:00$")
HEADS = ("UPSIDE", "QUALITY", "ADVERSE")


def require(ok: Any, code: str) -> None:
    if not ok:
        raise ValueError("P1_FORWARD_" + code)


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def day(value: Any) -> str:
    require(type(value) is str, "SESSION_INVALID")
    try:
        require(date.fromisoformat(value).isoformat() == value, "SESSION_INVALID")
    except (ValueError, TypeError):
        raise ValueError("P1_FORWARD_SESSION_INVALID") from None
    return value


def clock(value: Any, session: str) -> datetime:
    require(type(value) is str and JST.fullmatch(value) is not None, "CLOCK_INVALID")
    try:
        parsed = datetime.fromisoformat(value)
        require(parsed.utcoffset() == timedelta(hours=9) and parsed.date().isoformat() == session, "CLOCK_SESSION_MISMATCH")
        return parsed
    except (ValueError, TypeError):
        raise ValueError("P1_FORWARD_CLOCK_INVALID") from None


def symbol(value: Any) -> str:
    require(type(value) is str and SYMBOL.fullmatch(value) is not None, "SYMBOL_INVALID")
    return value


def make_policy(split: dict, spec: dict, session: str) -> dict:
    """Select F5 by saved training recency, never by profit or test-set scores."""
    day(session)
    require("2026-10-26" <= session <= "2026-12-31", "FORWARD_SESSION_OUTSIDE_2026_POLICY")
    folds = split.get("folds", [])
    require(len(folds) == 5 and {f.get("id") for f in folds} == set(range(1, 6)), "ORIGINAL_FOLDS_REQUIRED")
    for fold in folds:
        train, test = fold.get("train"), fold.get("test")
        require(isinstance(train, list) and isinstance(test, list) and train and test, "SPLIT_INVALID")
        for item in train + test:
            day(item)
        require(train == sorted(set(train)) and test == sorted(set(test)) and max(train) < min(test), "SPLIT_NOT_TEMPORAL")
    latest = max(folds, key=lambda f: max(f["train"]))
    require(latest["id"] == 5 and max(latest["train"]) == "2025-08-06", "LATEST_SAVED_FOLD_CHANGED")
    require(max(d for f in folds for d in f["test"]) < session, "OVERLAPS_ORIGINAL_OOF")
    calibration = spec["calibration"][5]
    threshold = calibration["thresholds"]["Q70"]
    require(type(threshold) in (int, float) and math.isfinite(threshold) and 0 <= threshold <= 1, "Q70_INVALID")
    feature = spec["feature"]
    require(len(feature["P1_numeric"]) == 148 and len(feature["P1_categorical"]) == 15, "FEATURE_MANIFEST_INVALID")
    pins = spec["corrected"]
    asset_names = ["PRIVATE_INPUTS/category_vocabulary.json", "PRIVATE_MODELS/P1_F5_preprocessor.pkl", "PRIVATE_MODELS/P1_F5_calibration.json"]
    for head in HEADS:
        asset_names.extend(("PRIVATE_MODELS/P1_F5_" + head + ".pkl", "PRIVATE_MODELS/P1_F5_" + head + "_train_prediction_reference.npy"))
    core = {
        "schemaId": POLICY_SCHEMA, "sessionDate": session, "selectedFold": 5,
        "selectionRule": "LATEST_SAVED_TRAINING_END_NO_PERFORMANCE_SEARCH",
        "trainingEnd": max(latest["train"]), "originalFoldTestEnd": max(latest["test"]),
        "thresholdPolicy": "Q70", "threshold": float(threshold),
        "featureManifestSha256": FEATURE_SHA,
        "assetSha256": {name: pins[name]["sha256"] for name in asset_names},
        "originalOofMappingUnchanged": True, "newForwardPolicy": True,
        "modelParametersChanged": False, "newFits": 0, "recalibrationPerformed": False,
        "shadowOnly": True, "productionReady": False, "orderTransmission": False,
    }
    return dict(core, policySha256=digest(core))


def load_policy(repo: Path, session: str) -> tuple[dict, dict]:
    import no11_frozen_p1_score_replay as original
    spec = original.load_contracts(Path(repo))
    split = json.loads((Path(repo) / BASE / "SPLIT_PRECOMMIT.json").read_text(encoding="utf-8"))
    return make_policy(split, spec, session), spec


class FrozenP1Scorer:
    """Actual hash-verified original F5 estimator, transform, references and Q70."""
    model_kind = "ORIGINAL_CORRECTED_P1_F5"

    def __init__(self, runtime_root: Path, repo: Path, session: str):
        import no11_frozen_p1_score_replay as original
        import numpy as np
        import sklearn
        require(sklearn.__version__ == "1.8.0", "REQUIRES_SCIKIT_LEARN_1_8_0")
        self.policy, spec = load_policy(repo, session)
        root = Path(runtime_root).absolute()
        if (root / "ORIGINAL_P1").is_dir():
            root = root / "ORIGINAL_P1"
        files = {}
        for name in self.policy["assetSha256"]:
            original.verify_file(root / name, spec["corrected"][name])
            files[name] = root / name
        self.np = np
        self.model = original.FrozenP1Fold(5, spec, files, original.inference_primitives(spec["source"], np), np)
        require(float(self.model.calibration["thresholds"]["Q70"]) == self.policy["threshold"], "MODEL_THRESHOLD_MISMATCH")

    def score(self, numeric: list, categorical: list) -> dict:
        from threadpoolctl import threadpool_limits
        values = self.np.asarray([[self.np.nan if v is None else v for v in numeric]], dtype=self.np.float64)
        with threadpool_limits(limits=2):
            prediction, percentiles, scores = self.model.score_named_batch(values, [categorical])
        _, unseen = self.model.encode_named_categories([categorical])
        return {"score": float(scores[0]), "headPredictions": [float(x) for x in prediction[0]],
                "headPercentiles": [float(x) for x in percentiles[0]], "unseenCategoryCounts": unseen}


class ForwardP1Session:
    """Persistent, idempotent shadow candidate state; never an order queue."""
    def __init__(self, database: Path, scorer: Any):
        self.scorer = scorer
        self.policy = deepcopy(scorer.policy)
        self.session = day(self.policy["sessionDate"])
        body = {k: v for k, v in self.policy.items() if k != "policySha256"}
        require(self.policy.get("schemaId") == POLICY_SCHEMA and digest(body) == self.policy.get("policySha256")
                and self.policy.get("shadowOnly") is True and self.policy.get("orderTransmission") is False
                and self.policy.get("productionReady") is False and self.policy.get("selectedFold") == 5,
                "POLICY_INVALID")
        path = Path(database).absolute()
        require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), "DATABASE_SYMLINK")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS watches (watch_key TEXT PRIMARY KEY, symbol TEXT NOT NULL,
            first_at TEXT NOT NULL, first_price REAL NOT NULL, last_selector_at TEXT NOT NULL,
            refresh_json TEXT NOT NULL, locked INTEGER NOT NULL DEFAULT 0);
          CREATE TABLE IF NOT EXISTS selector_events (event_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS evaluations (watch_key TEXT NOT NULL REFERENCES watches(watch_key),
            bar_end TEXT NOT NULL, fingerprint TEXT NOT NULL, result_json TEXT NOT NULL,
            PRIMARY KEY(watch_key,bar_end));
          CREATE TABLE IF NOT EXISTS candidates (watch_key TEXT PRIMARY KEY REFERENCES watches(watch_key),
            candidate_id TEXT UNIQUE NOT NULL, payload_json TEXT NOT NULL);
        """)
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO metadata VALUES ('policy',?)", (dumps(self.policy),))
            current = self.db.execute("SELECT value FROM metadata WHERE key='policy'").fetchone()[0]
        if current != dumps(self.policy):
            self.db.close()
            raise ValueError("P1_FORWARD_EXISTING_SESSION_POLICY_MISMATCH")

    def close(self) -> None:
        self.db.close()

    def register_selector(self, result: dict) -> dict:
        require(result.get("schemaId") == SELECTOR_SCHEMA and result.get("sessionDate") == self.session
                and result.get("shadowOnly") is True and result.get("productionReady") is False
                and result.get("orderTransmission") is False, "SELECTOR_SCOPE_INVALID")
        at = result.get("decisionTimestamp")
        t = clock(at, self.session)
        require(t.strftime("%H:%M") in DECISIONS and t.second == 0 and t.microsecond == 0, "SELECTOR_CLOCK_INVALID")
        events, selected = result.get("watchEvents"), result.get("selected")
        require(isinstance(events, list) and isinstance(selected, list) and len(events) <= 5 and len(selected) <= 5, "SELECTOR_TOP5_INVALID")
        selected_ids = {r.get("selectorEventId") for r in selected}
        added = refreshed = duplicates = 0
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            for event in events:
                code = symbol(event.get("symbol"))
                key = self.session + "|" + code
                event_id = self.session + "|" + at + "|" + code
                require(event.get("selectorEventId") == event_id and event_id in selected_ids
                        and event.get("firstWatchIdentity") == key and event.get("decisionTimestamp") == at
                        and event.get("sessionDate") == self.session, "SELECTOR_EVENT_IDENTITY_INVALID")
                price = event.get("decisionPrice")
                require(type(price) in (int, float) and math.isfinite(price) and price > 0, "SELECTOR_PRICE_INVALID")
                fingerprint = digest(event)
                seen = self.db.execute("SELECT fingerprint FROM selector_events WHERE event_id=?", (event_id,)).fetchone()
                if seen:
                    require(seen[0] == fingerprint, "SELECTOR_RETRY_CONFLICT")
                    duplicates += 1
                    continue
                old = self.db.execute("SELECT * FROM watches WHERE watch_key=?", (key,)).fetchone()
                if old is None:
                    require(event.get("watchEventType") == "WATCH_FIRST_SELECTION", "REFRESH_WITHOUT_PERSISTED_WATCH")
                    self.db.execute("INSERT INTO watches VALUES (?,?,?,?,?,?,0)", (key, code, at, price, at, "[]"))
                    added += 1
                else:
                    require(event.get("watchEventType") == "WATCH_REFRESH" and clock(old["last_selector_at"], self.session) < t,
                            "SELECTOR_REFRESH_OUT_OF_ORDER")
                    refreshes = json.loads(old["refresh_json"]) + [at]
                    self.db.execute("UPDATE watches SET last_selector_at=?,refresh_json=? WHERE watch_key=?", (at, dumps(refreshes), key))
                    refreshed += 1
                self.db.execute("INSERT INTO selector_events VALUES (?,?)", (event_id, fingerprint))
        return {"newWatches": added, "refreshedWatches": refreshed, "idempotentRetries": duplicates, "orderTransmission": False}

    def watch_context(self, code: str) -> dict:
        key = self.session + "|" + symbol(code)
        row = self.db.execute("SELECT * FROM watches WHERE watch_key=?", (key,)).fetchone()
        require(row is not None, "WATCH_NOT_REGISTERED")
        minute = lambda at: clock(at, self.session).hour * 60 + clock(at, self.session).minute
        return {"watch_key": key, "session": self.session, "selector_minute": minute(row["first_at"]),
                "selector_price": row["first_price"], "refresh_minutes": [minute(x) for x in json.loads(row["refresh_json"])]}

    def evaluate(self, event: dict) -> dict:
        allowed = {"schemaId", "sessionDate", "symbol", "watchKey", "barEndJst", "evaluatedAtJst",
                   "featureKnownAtJst", "stateKnownAtJst", "stateBarEndJst", "featureManifestSha256",
                   "sourceKind", "numeric", "categorical"}
        require(isinstance(event, dict) and set(event) == allowed and event["schemaId"] == FEATURE_SCHEMA
                and event["sessionDate"] == self.session and event["featureManifestSha256"] == FEATURE_SHA, "FEATURE_CONTRACT_INVALID")
        code = symbol(event["symbol"])
        key = self.session + "|" + code
        require(event["watchKey"] == key, "FEATURE_WATCH_IDENTITY_INVALID")
        bar = clock(event["barEndJst"], self.session)
        now = clock(event["evaluatedAtJst"], self.session)
        feature_seen = clock(event["featureKnownAtJst"], self.session)
        state_seen = clock(event["stateKnownAtJst"], self.session)
        state_bar = clock(event["stateBarEndJst"], self.session)
        minute = bar.hour * 60 + bar.minute
        require(bar.second == 0 and bar.microsecond == 0 and (541 <= minute <= 690 or 751 <= minute <= 930), "NOT_CLOSED_REGULAR_MINUTE")
        require(state_bar <= bar <= feature_seen <= now and state_bar <= state_seen <= feature_seen, "FEATURE_OR_STATE_FROM_FUTURE")
        require(event["sourceKind"] in ("RSS_CUMULATIVE_PROXY", "ORIGINAL_SAVED_JQUANTS_V2"), "SOURCE_KIND_NOT_DECLARED")
        numbers, categories = event["numeric"], event["categorical"]
        require(isinstance(numbers, list) and len(numbers) == 148 and any(x is not None for x in numbers)
                and all(x is None or type(x) in (int, float) and math.isfinite(x) for x in numbers), "NUMERIC_FEATURES_INVALID")
        require(isinstance(categories, list) and len(categories) == 15 and all(type(x) is str for x in categories), "CATEGORICAL_FEATURES_INVALID")
        fingerprint = digest(event)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            watch = self.db.execute("SELECT * FROM watches WHERE watch_key=?", (key,)).fetchone()
            require(watch is not None, "WATCH_NOT_REGISTERED")
            require(clock(watch["first_at"], self.session) < bar, "FEATURE_BEFORE_WATCH_ACTIVATION")
            prior = self.db.execute("SELECT fingerprint,result_json FROM evaluations WHERE watch_key=? AND bar_end=?", (key, event["barEndJst"])).fetchone()
            if prior:
                require(prior[0] == fingerprint, "FEATURE_RETRY_CONFLICT")
                return dict(json.loads(prior[1]), idempotentReplay=True)
            require(clock(watch["last_selector_at"], self.session) <= now, "WATCH_REFRESH_FROM_FUTURE")
            latest = self.db.execute("SELECT bar_end FROM evaluations WHERE watch_key=? ORDER BY bar_end DESC LIMIT 1", (key,)).fetchone()
            require(latest is None or clock(latest[0], self.session) < bar, "FEATURE_BAR_OUT_OF_ORDER")
            result = {"schemaId": "ARK_NO11_P1_FORWARD_DECISION_V1", "watchKey": key,
                      "barEndJst": event["barEndJst"], "evaluatedAtJst": event["evaluatedAtJst"],
                      "policySha256": self.policy["policySha256"], "selectedFold": 5,
                      "thresholdPolicy": "Q70", "threshold": self.policy["threshold"],
                      "sourceKind": event["sourceKind"], "modelKind": self.scorer.model_kind,
                      "shadowOnly": True, "productionReady": False, "orderTransmission": False,
                      "orderAuthorized": False, "idempotentReplay": False}
            if watch["locked"]:
                result["status"] = "FIRST_ENTRY_ALREADY_LOCKED"
            else:
                score = self.scorer.score(numbers, categories)
                value = score.get("score")
                require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1, "MODEL_SCORE_INVALID")
                # Preserve exact original >= without an epsilon or new threshold.
                crossed = value >= self.policy["threshold"]
                result.update(score=score, status="FIRST_ENTRY_CANDIDATE" if crossed else "WAIT")
                if crossed:
                    candidate_id = digest([self.policy["policySha256"], key, event["barEndJst"]])
                    result["candidateId"] = candidate_id
                    result["capitalAndExecutionChecksPending"] = True
                    self.db.execute("INSERT INTO candidates VALUES (?,?,?)", (key, candidate_id, dumps(result)))
                    self.db.execute("UPDATE watches SET locked=1 WHERE watch_key=?", (key,))
            self.db.execute("INSERT INTO evaluations VALUES (?,?,?,?)", (key, event["barEndJst"], fingerprint, dumps(result)))
        return result

    def summary(self) -> dict:
        count = lambda table: self.db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        return {"schemaId": "ARK_NO11_P1_FORWARD_SESSION_SUMMARY_V1", "sessionDate": self.session,
                "selectedFold": 5, "thresholdPolicy": "Q70", "watches": count("watches"),
                "evaluations": count("evaluations"), "firstEntryCandidates": count("candidates"),
                "modelKind": self.scorer.model_kind, "policySha256": self.policy["policySha256"],
                "newFits": 0, "orders": 0, "productionReady": False, "orderTransmission": False}


def assemble_feature_event(runtime: Any, watch: dict, code: str, today: Any, previous: Any,
                           state_features: dict, *, bar_end: str, evaluated_at: str,
                           feature_known_at: str, state_known_at: str,
                           source_kind: str, source_status: str) -> dict:
    """Use original price computation plus StateFeatureStream output, no relabeling.

    The caller must supply actual closed raw prefixes and a complete frozen
    State9 stream output. No state, previous-day data or missing Va is invented.
    RSS-derived Va stays labelled as the changed input source.
    """
    session = day(watch["session"])
    end = clock(bar_end, session)
    minute = end.hour * 60 + end.minute
    require(watch["watch_key"] == session + "|" + symbol(code), "ASSEMBLER_WATCH_IDENTITY")
    require(source_kind in ("RSS_CUMULATIVE_PROXY", "ORIGINAL_SAVED_JQUANTS_V2") and type(source_status) is str, "ASSEMBLER_SOURCE_REQUIRED")
    a = runtime.np.asarray(today, dtype=runtime.np.float64)
    p = runtime.np.asarray(previous, dtype=runtime.np.float64)
    if p.size == 0:
        p = p.reshape((0, 7))
    require(a.ndim == 2 and a.shape[1] == 7 and len(a) > 0 and p.ndim == 2 and p.shape[1] == 7, "ASSEMBLER_RAW_SHAPE")
    require(runtime.np.isfinite(a).all() and runtime.np.isfinite(p).all()
            and runtime.np.all(a[:, 0] + 1 <= minute) and runtime.np.all(a[1:, 0] > a[:-1, 0]), "ASSEMBLER_UNCLOSED_OR_INVALID_PREFIX")
    price = runtime.namespace["compute"](watch, a, p, minute)
    state_numeric = state_features["numeric"].tolist()
    state_categories = list(state_features["categorical"])
    require(len(price) == 110 and len(state_numeric) == 38 and len(state_categories) == 14, "ASSEMBLER_FROZEN_WIDTH_CHANGED")
    state_minute = state_features["state_as_of_minute"]
    require(type(state_minute) is int and state_minute <= minute, "ASSEMBLER_FUTURE_STATE")
    state_end = session + f"T{state_minute // 60:02d}:{state_minute % 60:02d}:00+09:00"
    numeric = [None if math.isnan(float(v)) else float(v) for v in list(price) + state_numeric]
    return {"schemaId": FEATURE_SCHEMA, "sessionDate": session, "symbol": code,
            "watchKey": watch["watch_key"], "barEndJst": bar_end, "evaluatedAtJst": evaluated_at,
            "featureKnownAtJst": feature_known_at, "stateKnownAtJst": state_known_at,
            "stateBarEndJst": state_end, "featureManifestSha256": FEATURE_SHA,
            "sourceKind": source_kind, "numeric": numeric,
            "categorical": state_categories + [source_status]}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True)
    parser.add_argument("--policy-only", action="store_true")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--private-root", type=Path)
    parser.add_argument("--events", type=Path)
    args = parser.parse_args(argv)
    if args.policy_only:
        policy, _ = load_policy(REPO, args.session)
        print(dumps(policy))
        return
    require(args.runtime_root is not None and args.private_root is not None and args.events is not None, "RUNTIME_PRIVATE_ROOT_AND_EVENTS_REQUIRED")
    root = args.private_root.absolute()
    require(root != REPO and REPO not in root.parents and not root.is_symlink(), "PRIVATE_OUTPUT_OUTSIDE_REPO_REQUIRED")
    require(args.events.is_file() and not args.events.is_symlink() and args.events.stat().st_size <= 100_000_000, "EVENT_FILE_INVALID")
    scorer = FrozenP1Scorer(args.runtime_root, REPO, args.session)
    session = ForwardP1Session(root / ("p1-shadow-" + args.session + ".sqlite"), scorer)
    try:
        with args.events.open(encoding="utf-8-sig") as handle:
            for line in handle:
                event = json.loads(line)
                kind = event.get("kind")
                require(kind in ("selector", "p1_features"), "EVENT_KIND_INVALID")
                if kind == "selector":
                    session.register_selector(event["payload"])
                else:
                    session.evaluate(event["payload"])
        print(dumps(session.summary()))
    finally:
        session.close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        message = str(exc)
        print(message if message.startswith("P1_FORWARD_") else "P1_FORWARD_INPUT_OR_RUNTIME_ERROR", flush=True)
        raise SystemExit(2)
