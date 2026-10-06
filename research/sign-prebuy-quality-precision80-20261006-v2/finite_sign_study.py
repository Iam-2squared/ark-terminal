"""Finite Sign-only study. Market fitting requires a verified frozen precommit.

No import-time execution. Only allowlisted numeric/categories and unit sign
labels enter training. Public outputs are aggregate; models/predictions remain
private. The 20 candidate/q pairs share at most 20 Discovery model fits.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import pickle
import re

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

VERSION = "FINITE_INTENT_SIGN_ONLY_V2"
QS = (.5, .6, .7, .8, .85)
CANDIDATES = (("BASE_LOGISTIC", "BASE", "LOGISTIC"),
              ("BASE_HGB", "BASE", "HGB"),
              ("BASE_STRUCTURE_LOGISTIC", "BASE_STRUCTURE", "LOGISTIC"),
              ("BASE_STRUCTURE_HGB", "BASE_STRUCTURE", "HGB"))
FORBIDDEN = ("future_", "realized", "pnl", "wealth", "capital_state", "exit_reason",
             "mfe", "mae", "quantity", "fill_clock", "fill_price", "fill_delay",
             "to_fill", "to_entry", "raw_entry", "buy_debit", "sell_credit")
JST = timezone(timedelta(hours=9))
ENTRY_ID = re.compile(r'"entry_id"\s*:\s*("(?:[^"\\]|\\.)*")')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def signature(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def stamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("NAIVE_TIMESTAMP")
    return result


def midnight(day):
    return datetime.fromisoformat(day).replace(tzinfo=JST)


def missing(value):
    return type(value) not in (int, float) or not math.isfinite(value)


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        f.write(canonical(value) + "\n")


class StageLabels:
    """Decode sign values only for requested sessions. Raw bytes coexist in
    the supplied input file; hashing it is not performance grading. The reader
    extracts entry_id alone before JSON decoding, never retains out-of-stage
    records, and logs exactly which sessions' signs were decoded.
    """
    def __init__(self, path):
        self.path = Path(path)
        self.access = []

    def read(self, sessions, purpose, before=None):
        dates = set(sessions)
        out = {}
        opener = gzip.open if self.path.suffix == ".gz" else open
        with opener(self.path, "rt", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                token = ENTRY_ID.search(line)
                if token is None:
                    raise ValueError("LABEL_ENTRY_ID_REQUIRED")
                key = json.loads(token.group(1))
                day = key.split("|", 1)[0]
                if day not in dates:
                    continue
                raw = json.loads(line)
                if "sign_status" in raw:
                    if set(raw) != {"entry_id", "session", "sign_status", "y_plus", "label_maturity", "source_hash"}:
                        raise ValueError("LABEL_MAGNITUDE_OR_UNDECLARED_FIELD")
                    sign = {"PLUS": "PLUS", "MINUS": "MINUS", "EXACT_ZERO": "ZERO", "UNKNOWN": "UNKNOWN"}.get(raw["sign_status"])
                    expected_y = {"PLUS": 1, "MINUS": 0, "ZERO": None, "UNKNOWN": None}.get(sign)
                    if (sign is None or raw["y_plus"] != expected_y
                            or (expected_y is not None and type(raw["y_plus"]) is not int)
                            or not isinstance(raw["source_hash"], str)):
                        raise ValueError("ORIGINAL_SIGN_DIRECTION_OR_SCHEMA")
                    mature = raw["label_maturity"]
                else:
                    if set(raw) - {"entry_id", "session", "sign", "matured_at"}:
                        raise ValueError("LABEL_MAGNITUDE_OR_UNDECLARED_FIELD")
                    sign, mature = raw.get("sign"), raw.get("matured_at")
                if raw.get("session", day) != day or sign not in ("PLUS", "MINUS", "ZERO", "UNKNOWN"):
                    raise ValueError("LABEL_SCHEMA")
                if key in out:
                    raise ValueError("DUPLICATE_LABEL")
                if sign in ("PLUS", "MINUS", "ZERO") and mature is None:
                    raise ValueError("KNOWN_LABEL_MATURITY_REQUIRED")
                if before is not None and (mature is None or stamp(mature) >= before):
                    continue
                out[key] = {"entry_id": key, "session": day, "sign": sign,
                            "matured_at": mature}
        self.access.append({"purpose": purpose, "sessions": sorted(dates),
                            "retained_N": len(out), "before": before.isoformat() if before else None})
        return out


def check_features(rows, representations):
    numeric = set().union(*(set(s["numeric"]) for s in representations.values()))
    cats = set().union(*(set(s["categorical"]) for s in representations.values()))
    if any(any(term in column.lower() for term in FORBIDDEN) for column in numeric | cats):
        raise ValueError("FORBIDDEN_FEATURE")
    if numeric & cats:
        raise ValueError("FEATURE_TYPE_COLLISION")
    ids = set()
    for row in rows:
        key = row["entry_id"]
        if key in ids or key.split("|", 1)[0] != row["session"]:
            raise ValueError("FEATURE_IDENTITY")
        ids.add(key)
        if set(row["numeric"]) != numeric or set(row["categorical"]) != cats:
            raise ValueError("FEATURE_SCHEMA_KEYS")
        if type(row["supported"]) is not bool or type(row["intent_minute"]) is not int:
            raise ValueError("FEATURE_SUPPORT_OR_CLOCK")
        decision = midnight(row["session"]) + timedelta(minutes=row["intent_minute"])
        if not 0 <= row["intent_minute"] < 1440 or (row["supported"] and
                (row.get("input_asof") is None or stamp(row["input_asof"]) > decision)):
            raise ValueError("INPUT_AFTER_INTENT")
    return rows


def verify_precommit(config, receipt, config_hash, code_hash, features_hash, labels_hash):
    if config.get("frozen") is not True or receipt.get("actual_get_verified") is not True:
        raise ValueError("FROZEN_PRECOMMIT_ACTUAL_GET_REQUIRED")
    expected = {"config_sha256": config_hash, "code_sha256": code_hash,
                "features_sha256": features_hash, "labels_sha256": labels_hash,
                "schema_sha256": signature(config["representations"]),
                "split_sha256": signature(config["blocks"])}
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError("PRECOMMIT_HASH_MISMATCH")
    if not all(receipt.get(k) is True for k in ("provenance_verified", "producer_lineage_verified",
                                               "intent_identity_verified", "source_originals_verified")):
        raise ValueError("INPUT_PROVENANCE_NOT_VERIFIED")
    if config.get("version") != VERSION or config.get("score_quantiles") != list(QS):
        raise ValueError("RECIPE_OR_QUANTILES_CHANGED")
    if config.get("candidate_order") != [c[0] for c in CANDIDATES] or config.get("fit_ceiling") != 33:
        raise ValueError("CANDIDATE_OR_BUDGET_CHANGED")
    if config.get("versions") != {"numpy": np.__version__, "sklearn": sklearn.__version__}:
        raise ValueError("SOFTWARE_VERSION_CHANGED")
    if len(config["blocks"]) != 8 or [b["block"] for b in config["blocks"]] != list(range(1, 9)):
        raise ValueError("EXACT_EIGHT_TIME_BLOCKS_REQUIRED")
    for block in config["blocks"]:
        fit, cal, test = (block[p] for p in ("FIT", "CAL", "TEST"))
        if (not fit or len(cal) != 5 or not test or max(fit) >= min(cal) or max(cal) >= min(test)
                or any(v != sorted(set(v)) for v in (fit, cal, test))):
            raise ValueError("TIME_SPLIT_ORDER")


def preprocess_fit(rows, spec, scale):
    columns, categories = spec["numeric"], spec["categorical"]
    values = np.array([[float(r["numeric"][k]) if not missing(r["numeric"][k]) else np.nan
                        for k in columns] for r in rows], dtype=float)
    medians = np.array([np.median(v[np.isfinite(v)]) if np.isfinite(v).any() else 0.
                        for v in values.T])
    masks = ~np.isfinite(values)
    x = np.hstack([np.where(masks, medians, values), masks.astype(float)])
    mean = x.mean(axis=0) if scale else np.zeros(x.shape[1])
    std = x.std(axis=0) if scale else np.ones(x.shape[1])
    std[std == 0] = 1
    vocab = {k: sorted({category(r["categorical"][k]) for r in rows} | {"MISSING", "UNKNOWN"})
             for k in categories}
    return {"spec": spec, "median": medians.tolist(), "mean": mean.tolist(),
            "scale": std.tolist(), "vocabulary": vocab, "fit_ids": [r["entry_id"] for r in rows]}


def category(value):
    return "MISSING" if value is None else "VALUE:" + str(value)


def transform(rows, prep):
    spec = prep["spec"]
    if not rows:
        return np.zeros((0, len(prep["mean"]) + sum(map(len, prep["vocabulary"].values()))))
    values = np.array([[float(r["numeric"][k]) if not missing(r["numeric"][k]) else np.nan
                        for k in spec["numeric"]] for r in rows])
    masks = ~np.isfinite(values)
    x = np.hstack([np.where(masks, np.array(prep["median"]), values), masks.astype(float)])
    parts = [(x - np.array(prep["mean"])) / np.array(prep["scale"])]
    for k in spec["categorical"]:
        vocab = prep["vocabulary"][k]
        lookup = {v: i for i, v in enumerate(vocab)}
        onehot = np.zeros((len(rows), len(vocab)))
        for i, row in enumerate(rows):
            onehot[i, lookup.get(category(row["categorical"][k]), lookup["UNKNOWN"])] = 1
        parts.append(onehot)
    return np.hstack(parts)


def estimator(family):
    if family == "LOGISTIC":
        return LogisticRegression(C=.1, solver="lbfgs", penalty="l2", max_iter=2000,
                                  tol=.0001, class_weight=None, random_state=57)
    return HistGradientBoostingClassifier(loss="log_loss", max_depth=3, max_leaf_nodes=7,
        max_iter=100, learning_rate=.05, min_samples_leaf=20, l2_regularization=1.,
        early_stopping=False, categorical_features=None, max_bins=255,
        warm_start=False, class_weight=None, random_state=57)


def threshold_info(cal, q):
    rows = [r for r in cal if r["sign"] in ("PLUS", "MINUS") and r["score"] is not None]
    tau = float(np.quantile([r["score"] for r in rows], q, method="linear")) if rows else None
    counts = Counter(r["sign"] for r in rows)
    passed = [r for r in rows if tau is not None and r["score"] >= tau]
    positives = sum(r["sign"] == "PLUS" for r in passed)
    precision = Fraction(positives, len(passed)) if passed else None
    retention = Fraction(positives, counts["PLUS"]) if counts["PLUS"] else None
    qualified = (precision is not None and precision >= Fraction(4, 5)
                 and retention is not None and retention >= Fraction(1, 4)
                 and len(passed) >= 20 and len({r["session"] for r in passed}) >= 3)
    return {"q": q, "tau": tau, "qualified": qualified, "known_CAL_N": len(rows),
            "pass_N": len(passed), "PLUS": positives, "MINUS": len(passed) - positives,
            "precision": float(precision) if precision is not None else None,
            "retention": float(retention) if retention is not None else None}


def metrics(rows, labels, mode="filter"):
    table = Counter()
    status = Counter()
    dates = set()
    pass_dates = set()
    for row in rows:
        if row["entry_id"] not in labels:
            raise ValueError("EVALUATION_LABEL_JOIN_MISSING_NOT_UNKNOWN")
        sign = labels[row["entry_id"]]["sign"]
        if sign not in ("PLUS", "MINUS", "ZERO", "UNKNOWN"):
            raise ValueError("EVALUATION_SIGN_SCHEMA")
        score = row["score"]
        status["ABSTAIN_N"] += score is None
        action = row["pass"] if mode == "filter" else score is not None and score >= .5
        status[sign] += 1
        status["PASS_" + sign] += bool(action)
        dates.add(row["session"])
        if sign not in ("PLUS", "MINUS"):
            continue
        if score is None:
            status["known_ABSTAIN"] += 1
            if mode == "binary":
                continue
        table[(sign, bool(action))] += 1
        if action:
            pass_dates.add(row["session"])
    tp, fp = table["PLUS", True], table["MINUS", True]
    fn, tn = table["PLUS", False], table["MINUS", False]
    ratio = lambda a, b: a / b if b else None
    recall, removal = ratio(tp, tp + fn), ratio(tn, tn + fp)
    divisor = (tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
    known_pass, known_total = tp+fp, tp+fp+fn+tn
    return {"mode": mode, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "PLUS_precision": ratio(tp, tp+fp), "PLUS_retention": recall,
            "MINUS_removal": removal, "pass_MINUS_rate": ratio(fp, tp+fp),
            "MINUS_precision": ratio(tn, tn+fn), "accuracy": ratio(tp+tn, known_total),
            "BA": (recall+removal)/2 if recall is not None and removal is not None else None,
            "MCC": (tp*tn-fp*fn)/math.sqrt(divisor) if divisor else None,
            "known_N": known_total, "known_pass_N": known_pass,
            "known_pass_fraction": ratio(known_pass, known_total),
            "all_N": len(rows), "status_counts": dict(status),
            "known_prediction_coverage": ratio(known_total-status["known_ABSTAIN"], known_total)
                if mode == "filter" else ratio(known_total, status["PLUS"]+status["MINUS"]),
            "sessions": sorted(dates), "pass_sessions_N": len(pass_dates),
            "all_pass_unknown_fraction": ratio(status["PASS_UNKNOWN"], sum(status["PASS_"+s]
                for s in ("PLUS", "MINUS", "ZERO", "UNKNOWN"))),
            "uncalibrated_score": True}


def gate(m):
    return (m["PLUS_precision"] is not None and m["PLUS_precision"] >= .8
            and m["PLUS_retention"] is not None and m["PLUS_retention"] >= .25
            and m["known_pass_N"] >= 50 and m["pass_sessions_N"] >= 8
            and .1 <= m["known_pass_fraction"] <= .8)


def select_pair(aggregates):
    qualified = [r for r in aggregates if r["qualified_CAL_blocks"] >= 3 and gate(r["filter"])]
    if not qualified:
        return None
    order = {c[0]: i for i, c in enumerate(CANDIDATES)}
    def key(r):
        m = r["filter"]
        return (Fraction(m["TP"], m["TP"]+m["FN"]), Fraction(m["TP"], m["TP"]+m["FP"]),
                -order[r["candidate"]], -QS.index(r["q"]))
    return max(qualified, key=key)


def session_ci(rows, labels):
    sessions = sorted({r["session"] for r in rows})
    values = {k: [] for k in ("PLUS_precision", "PLUS_retention", "MINUS_removal")}
    rng = np.random.default_rng(57)
    for _ in range(1000):
        selected = rng.choice(sessions, len(sessions), replace=True) if sessions else []
        repeated = [r for session in selected for r in rows if r["session"] == session]
        m = metrics(repeated, labels)
        for k in values:
            if m[k] is not None:
                values[k].append(m[k])
    return {k: {"valid_replicates": len(v), "interval95": np.quantile(v, [.025, .975]).tolist()
                if v else None} for k, v in values.items()}


class FiniteStudy:
    def __init__(self, config, receipt, config_hash, rows, label_reader, private, public,
                 code_hash, features_hash, labels_hash, resume_confirmation=False):
        verify_precommit(config, receipt, config_hash, code_hash, features_hash, labels_hash)
        self.config, self.rows = config, check_features(rows, config["representations"])
        if (config.get("population") != "FROZEN_FILLED_ENTRY1600"
                or len(rows) != 1600 or config.get("entry_N") != 1600
                or config.get("entry_id_sha256") != signature(sorted(r["entry_id"] for r in rows))):
            raise ValueError("PRECOMMITTED_ENTRY1600_POPULATION_REQUIRED")
        self.labels, self.private, self.public = label_reader, Path(private), Path(public)
        if any((p / ".git").exists() for p in [self.private, *self.private.resolve().parents]):
            raise ValueError("PRIVATE_OUTPUT_MUST_BE_OUTSIDE_GIT_REPOSITORY")
        self.private.mkdir(parents=True, exist_ok=True)
        self.public.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.private / "FIT_LEDGER.json"
        if self.ledger_path.exists() and not resume_confirmation:
            raise ValueError("STUDY_ALREADY_STARTED_NO_AUTOMATIC_RERUN")
        self.ledger = {"actual_model_fit_calls": 0, "preprocessing_fits": 0, "equivalent_reuses": 0,
                       "technical_retries": 0, "diagnostic_fits": 0, "attempts": []}
        self.precommit = config_hash
        if resume_confirmation:
            started = json.loads((self.private / "STARTED.json").read_text())
            if started["config_sha256"] != config_hash or (self.private / "CONFIRMATION_PREDICTIONS_SEALED.json").exists():
                raise ValueError("CONFIRMATION_RESUME_SOURCE_OR_COMPLETION")
            self.ledger = json.loads(self.ledger_path.read_text())
            if self.ledger["actual_model_fit_calls"] > 33 or any(a["phase"] != "DISCOVERY" for a in self.ledger["attempts"]):
                raise ValueError("CONFIRMATION_ALREADY_ATTEMPTED_NO_RETRY")

    def save_ledger(self):
        temp = self.ledger_path.with_suffix(".pending")
        temp.write_text(canonical(self.ledger) + "\n")
        temp.replace(self.ledger_path)

    def trial(self, candidate, block, phase):
        name, representation, family = candidate
        spec = self.config["representations"][representation]
        fit_labels = self.labels.read(block["FIT"], phase+"_FIT", midnight(min(block["CAL"])))
        cal_labels = self.labels.read(block["CAL"], phase+"_CAL", midnight(min(block["TEST"])))
        fit = [r for r in self.rows if r["session"] in block["FIT"] and r["supported"]
               and fit_labels.get(r["entry_id"], {}).get("sign") in ("PLUS", "MINUS")]
        cal = [r for r in self.rows if r["session"] in block["CAL"] and r["supported"]
               and cal_labels.get(r["entry_id"], {}).get("sign") in ("PLUS", "MINUS")]
        test = [r for r in self.rows if r["session"] in block["TEST"]]
        support = Counter(fit_labels[r["entry_id"]]["sign"] for r in fit)
        params = estimator(family).get_params()
        if params != self.config["resolved_parameters"][family]:
            raise ValueError("ESTIMATOR_DEFAULTS_CHANGED")
        payload = {"recipe": VERSION, "spec": spec, "parameters": params, "versions": self.config["versions"],
                   "FIT_cutoff": min(block["CAL"]), "sample_weight": None, "class_weight": None,
                   "rows": [{"id": r["entry_id"], "numeric": [None if missing(r["numeric"][k]) else r["numeric"][k] for k in spec["numeric"]],
                             "categorical": [r["categorical"][k] for k in spec["categorical"]],
                             "y": int(fit_labels[r["entry_id"]]["sign"] == "PLUS"),
                             "matured_at": fit_labels[r["entry_id"]]["matured_at"]} for r in fit]}
        key = signature(payload)
        record = {"candidate": name, "block": block["block"], "phase": phase, "signature": key,
                  "FIT_N": len(fit), "CAL_N": len(cal), "TEST_N": len(test), "status": "UNSUPPORTED"}
        model, prep = None, None
        if len(fit) >= 100 and len({r["session"] for r in fit}) >= 10 and min(support["PLUS"], support["MINUS"]) >= 20:
            previous = next((a for a in self.ledger["attempts"] if a["signature"] == key
                             and a["status"] == "FITTED"), None)
            path = self.private / "models" / (key + ".pkl")
            if previous:
                if sha(path) != previous["model_sha256"]:
                    raise ValueError("SAVED_MODEL_HASH_CHANGED")
                with path.open("rb") as f:
                    model, prep = pickle.load(f)
                self.ledger["equivalent_reuses"] += 1
                record.update(status="REUSED", model_sha256=previous["model_sha256"])
            else:
                if self.ledger["actual_model_fit_calls"] >= 33:
                    raise ValueError("FIT_BUDGET_EXHAUSTED")
                prep = preprocess_fit(fit, spec, family == "LOGISTIC")
                self.ledger["preprocessing_fits"] += 1
                model = estimator(family)
                fit_x = transform(fit, prep)
                fit_y = np.array([int(fit_labels[r["entry_id"]]["sign"] == "PLUS") for r in fit])
                self.ledger["actual_model_fit_calls"] += 1
                record["status"] = "FIT_STARTED"
                self.ledger["attempts"].append(record)
                self.save_ledger()  # counted before .fit, including failed calls
                try:
                    model.fit(fit_x, fit_y)
                except Exception:
                    record["status"] = "FIT_FAILED_NO_RETRY"
                    self.save_ledger()
                    raise
                path.parent.mkdir(exist_ok=True)
                with path.open("xb") as f:
                    pickle.dump((model, prep), f, protocol=5)
                record.update(status="FITTED", model_sha256=sha(path))
        if record not in self.ledger["attempts"]:
            self.ledger["attempts"].append(record)
        self.save_ledger()
        if model is None:
            cal_scores, test_scores = [None]*len(cal), [None]*len(test)
        else:
            if list(model.classes_) != [0, 1]:
                raise ValueError("CLASS_ORDER_CHANGED")
            cal_scores = model.predict_proba(transform(cal, prep))[:, 1].tolist() if cal else []
            eligible = [r for r in test if r["supported"]]
            scored = model.predict_proba(transform(eligible, prep))[:, 1].tolist() if eligible else []
            mapping = dict(zip([r["entry_id"] for r in eligible], scored))
            test_scores = [mapping.get(r["entry_id"]) for r in test]
        cal_rows = [{"entry_id": r["entry_id"], "session": r["session"],
                     "sign": cal_labels[r["entry_id"]]["sign"], "score": score} for r, score in zip(cal, cal_scores)]
        quantiles = QS if phase == "DISCOVERY" else (self.locked_q,)
        choices = [threshold_info(cal_rows, q) for q in quantiles]
        predictions = [{"entry_id": r["entry_id"], "session": r["session"], "score": score,
                        "predicted_sign": "ABSTAIN" if score is None else "PLUS" if score >= .5 else "MINUS",
                        "actions": {str(t["q"]): bool(score is not None and t["tau"] is not None and score >= t["tau"])
                                    for t in choices}} for r, score in zip(test, test_scores)]
        write_new(self.private / "predictions" / f'{phase}_{name}_{block["block"]}.json',
                  {"candidate": name, "block": block["block"], "thresholds": choices,
                   "predictions": predictions, "TEST_grading_before_save": False})
        return {"candidate": name, "block": block["block"], "thresholds": choices, "predictions": predictions}

    def run(self):
        write_new(self.private / "STARTED.json", {"config_sha256": self.precommit,
                   "version": VERSION, "actual_start_utc": datetime.now(timezone.utc).isoformat()})
        discovery = [self.trial(candidate, b, "DISCOVERY") for b in self.config["blocks"][:5] for candidate in CANDIDATES]
        write_new(self.private / "DISCOVERY_PREDICTIONS_SEALED.json", {"trial_N": len(discovery)})
        signs = self.labels.read(sorted({d for b in self.config["blocks"][:5] for d in b["TEST"]}), "DISCOVERY_GRADING_AFTER_SEAL")
        aggregates = []
        for candidate in CANDIDATES:
            trials = [t for t in discovery if t["candidate"] == candidate[0]]
            for q in QS:
                rows = [{**r, "pass": r["actions"][str(q)]} for t in trials for r in t["predictions"]]
                aggregates.append({"candidate": candidate[0], "q": q,
                    "qualified_CAL_blocks": sum(t["thresholds"][QS.index(q)]["qualified"] for t in trials),
                    "filter": metrics(rows, signs), "binary": metrics(rows, signs, "binary")})
        chosen = select_pair(aggregates)
        write_new(self.public / "DISCOVERY_AGGREGATES.json", {"pairs": aggregates, "models_max": 20,
                    "exposure": "HISTORICALLY_EXPOSED_DEVELOPMENT_NOT_FRESH"})
        lock = {"candidate": chosen["candidate"] if chosen else None, "q": chosen["q"] if chosen else None,
                "selected_before_confirmation": True, "config_sha256": self.precommit}
        write_new(self.private / "PAIR_LOCK.json", lock)
        write_new(self.public / "PAIR_LOCK.json", lock)
        write_new(self.private / "DISCOVERY_LABEL_ACCESS.json", self.labels.access)
        # No candidate => no confirmation FIT/CAL reads, model fits or grading.
        if chosen is None:
            write_new(self.public / "RESULT.json", {"status": "NO_QUALIFIED_DISCOVERY_PAIR_FINITE_WORK_CLOSED",
                "confirmation_trials": 0, "confirmation_signs_graded": 0, "ledger": self.ledger,
                "labels_access": self.labels.access, "minimum_80_confirmed": False})
            return
        write_new(self.public / "DISCOVERY_STATUS.json", {
            "status": "PAIR_LOCK_PENDING_GITHUB_ACTUAL_GET", "pair": lock,
            "pair_lock_sha256": sha(self.private / "PAIR_LOCK.json"),
            "confirmation_trials": 0, "confirmation_signs_graded": 0,
            "ledger": self.ledger, "labels_access": self.labels.access})

    def run_confirmation(self, receipt):
        lock_path = self.private / "PAIR_LOCK.json"
        lock = json.loads(lock_path.read_text())
        if (receipt.get("actual_get_verified") is not True
                or receipt.get("pair_lock_sha256") != sha(lock_path)
                or receipt.get("config_sha256") != self.precommit
                or lock.get("candidate") is None or lock.get("config_sha256") != self.precommit):
            raise ValueError("CONFIRMATION_PAIR_LOCK_ACTUAL_GET_REQUIRED")
        candidate = next(c for c in CANDIDATES if c[0] == lock["candidate"])
        self.locked_q = lock["q"]
        confirmation = [self.trial(candidate, b, "CONFIRMATION") for b in self.config["blocks"][5:]]
        write_new(self.private / "CONFIRMATION_PREDICTIONS_SEALED.json", {"trial_N": len(confirmation), **lock})
        labels = self.labels.read(sorted({d for b in self.config["blocks"][5:] for d in b["TEST"]}), "CONFIRMATION_GRADING_AFTER_SEAL")
        rows = [{**r, "pass": r["actions"][str(lock["q"])]} for t in confirmation for r in t["predictions"]]
        summary = metrics(rows, labels)
        write_new(self.public / "RESULT.json", {"status": "LOCKED_DEV_80_MET_NOT_FRESH" if gate(summary) else "LOCKED_DEV_80_NOT_MET_FINITE_WORK_CLOSED",
            "pair": lock, "filter": summary, "binary": metrics(rows, labels, "binary"),
            "session_CI": session_ci(rows, labels), "bootstrap_repeats": 1000, "bootstrap_seed": 57,
            "sessions": [{"session": d, "filter": metrics([r for r in rows if r["session"] == d], labels)}
                         for d in sorted({r["session"] for r in rows})],
            "CAL_qualification_diagnostic": [{"block": t["block"], "threshold": t["thresholds"][0]} for t in confirmation],
            "ledger": self.ledger, "labels_access": {
                "discovery": json.loads((self.private / "DISCOVERY_LABEL_ACCESS.json").read_text()),
                "confirmation": self.labels.access},
            "exposure": "HISTORICALLY_EXPOSED_DEVELOPMENT_NOT_FRESH", "productionReady": False})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "receipt", "features", "labels", "private-output", "public-output"):
        p.add_argument("--"+name, type=Path, required=True)
    p.add_argument("--config-sha256", required=True)
    p.add_argument("--receipt-sha256", required=True)
    p.add_argument("--phase", choices=("discovery", "confirmation"), default="discovery")
    p.add_argument("--lock-receipt", type=Path)
    p.add_argument("--lock-receipt-sha256")
    args = p.parse_args()
    if sha(args.config) != args.config_sha256 or sha(args.receipt) != args.receipt_sha256:
        raise ValueError("EXTERNAL_PRECOMMIT_PIN_MISMATCH")
    config, receipt = json.loads(args.config.read_text()), json.loads(args.receipt.read_text())
    feature_hash, label_hash = sha(args.features), sha(args.labels)
    verify_precommit(config, receipt, args.config_sha256, sha(__file__), feature_hash, label_hash)
    opener = gzip.open if args.features.suffix == ".gz" else open
    with opener(args.features, "rt", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    study = FiniteStudy(config, receipt, args.config_sha256, rows, StageLabels(args.labels),
                        args.private_output, args.public_output, sha(__file__), feature_hash, label_hash,
                        resume_confirmation=args.phase == "confirmation")
    if args.phase == "discovery":
        study.run()
    else:
        if args.lock_receipt is None or sha(args.lock_receipt) != args.lock_receipt_sha256:
            raise ValueError("EXTERNAL_PAIR_LOCK_PIN_REQUIRED")
        study.run_confirmation(json.loads(args.lock_receipt.read_text()))


if __name__ == "__main__":
    main()
