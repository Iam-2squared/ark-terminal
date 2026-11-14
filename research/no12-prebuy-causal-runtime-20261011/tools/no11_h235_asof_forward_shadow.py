#!/usr/bin/env python3
"""2026 No.1.1 H2/H3/H5 as-of R0 SHADOW, using pinned original code and 24 saved models.

Forward deployment Block08 is an explicitly NEW experimental policy; historical
OOF dispatch is unchanged. Only locally received CLOSED source is eligible.
The two post-fill accesses in original core_features.project are redirected
by a pinned AST projection to an OBSERVED bar-end and OBSERVED close. There is
no invented fill, no retraining, no Excel, broker, or order-transmission path.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = ROOT / "integration/no1-1-msii/frozen-native-code"
LINEAGE = ROOT / "research/capital-v5-sharp-drop-exit-reset20-20261007/FROZEN_NATIVE_INPUT_LINEAGE.json"
SOURCE_BLOBS = {
    "core_features.py": "685a7774ed96556b810aa23957d12fda8f9654ba",
    "preprocessing.py": "29119e9d9e5ca880159289728c9391e17f8427ca",
    "staircase.py": "6863b2dded50e4d0caa4e2d470619017fcf0b759",
}
MANIFEST_BLOB = "1cf7c59b55890ba51b570a28210fbec715d27f5e"
POLICY_SCHEMA = "ARK_NO11_H235_BLOCK08_ASOF_FORWARD_SHADOW_V1"
INPUT_SCHEMA = "ARK_NO11_H235_RECEIVED_ASOF_CANDIDATE_V1"
OUTPUT_SCHEMA = "ARK_NO11_H235_RECEIVED_ASOF_R0_V1"
HEADS = (2, 3, 5)
BLOCK = 8
FROM_SESSION = "2026-10-26"
LAST_SESSION = "2026-12-31"
TRAIN_END = "2025-08-20"
JST = re.compile(r"^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?\+09:00$")
SYMBOL = re.compile(r"^[0-9A-Z]{4}\.T$")
DISALLOWED_KEYS = frozenset((
    "fill_price", "fill_minute", "fill_timestamp", "actual_fill_price",
    "broker_fill", "future_high", "future_low", "teacher", "label",
    "realized_pnl", "actual_buy", "actual_sell", "next_open", "order",
))


def require(condition, reason):
    if not condition:
        raise ValueError("NO11_H235_" + reason)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def pin_public(path, expected):
    require(path.is_file() and not path.is_symlink(), "PINNED_SOURCE_ABSENT")
    contents = path.read_bytes().replace(b"\r\n", b"\n")
    require(git_blob(contents) == expected, "PINNED_SOURCE_CHANGED")
    return contents


def stable_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(stable_bytes(value)).hexdigest()


def timestamp(value, session):
    require(isinstance(value, str) and JST.fullmatch(value) is not None, "TIMESTAMP_INVALID")
    try:
        dt = datetime.fromisoformat(value)
        require(dt.utcoffset() == timedelta(hours=9)
                and dt.date().isoformat() == session, "TIMESTAMP_SESSION_MISMATCH")
        return dt
    except (TypeError, ValueError):
        raise ValueError("NO11_H235_TIMESTAMP_INVALID") from None


def minute(dt):
    return dt.hour * 60 + dt.minute


def positive(value, code):
    require(type(value) in (int, float) and math.isfinite(value) and value > 0, code)
    return float(value)


def eligible_closed_minute(m):
    # Original 2026 RC2 scheduled bar ends; no fabricated lunch minutes.
    return type(m) is int and (541 <= m <= 691 or 751 <= m <= 926 or m == 931)


def active_elapsed(start, end):
    require(type(start) is int and type(end) is int and 540 <= start <= end <= 931,
            "ACTIVE_CLOCK_ORDER")
    return sum(max(0, min(end, hi) - max(start, lo))
               for lo, hi in ((540, 690), (750, 925)))


def policy(session):
    require(type(session) is str, "SESSION_INVALID")
    try:
        require(date.fromisoformat(session).isoformat() == session, "SESSION_INVALID")
    except (TypeError, ValueError):
        raise ValueError("NO11_H235_SESSION_INVALID") from None
    require(FROM_SESSION <= session <= LAST_SESSION, "SHADOW_SESSION_OUTSIDE_SCOPE")
    p = {
        "schemaId": POLICY_SCHEMA,
        "sessionDate": session, "selectedBlock": BLOCK,
        "originalLatestSavedTrainThrough": TRAIN_END,
        "newForwardSelectionRule": "LATEST_SAVED_TRAIN_THROUGH_FOR_SHADOW_ONLY",
        "originalOofDateDispatchUnchanged": True,
        "originalModelWeightsUnchanged": True, "modelsExpected": 24,
        "modelHeads": ["H2", "H3", "H5"],
        "inputPolicy": "DECISION_TIME_RECEIVED_LATEST_DATA",
        "postFillColumnsReinterpreted": [
            "entry/fill_clock", "entry/intent_to_fill_active_delay",
            "selector/to_entry_active_delay", "selector/raw_entry_vs_first_price_pct",
        ],
        "originalHistoricalRankParityClaim": False,
        "nativeRealtimeCertified": False, "shadowOnly": True,
        "newFits": 0, "productionReady": False, "orderTransmission": False,
    }
    return dict(p, policySha256=digest(p))


def original_dependencies():
    source = {name: pin_public(ORIGINAL / name, pin) for name, pin in SOURCE_BLOBS.items()}
    # Load only the byte-pinned original numerical projection / preprocessing / R0.
    for name in ("core_features", "preprocessing", "staircase"):
        mod = sys.modules.get(name)
        if mod is not None:
            require(Path(mod.__file__).resolve() == (ORIGINAL / (name + ".py")).resolve(),
                    "ORIGINAL_MODULE_COLLISION")
    sys.path.insert(0, str(ORIGINAL))
    try:
        core = importlib.import_module("core_features")
        prep = importlib.import_module("preprocessing")
        stair = importlib.import_module("staircase")
    finally:
        sys.path.pop(0)
    for mod in (core, prep, stair):
        require(Path(mod.__file__).resolve().parent == ORIGINAL.resolve(),
                "ORIGINAL_MODULE_NOT_PINNED")
    require(len(core.NUMERIC) == 27 and len(core.CATEGORICAL) == 7
            and callable(prep.predict_saved) and callable(stair.materialize)
            and callable(stair.candidate_order), "ORIGINAL_FEATURE_OR_R0_CHANGED")
    return core, prep, stair, source["core_features.py"]


def asof_projector(core, core_bytes):
    """Preserve original project() AST; change exactly two fill-dependent assignments.

    t = observed closed reference bar-end, never a hypothetical next bar.
    raw = observed reference closing price, never a synthetic fill price.
    Other original projection statements remain byte-derived and unchanged.
    """
    parsed = ast.parse(core_bytes)
    funcs = [n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == "project"]
    require(len(funcs) == 1, "ORIGINAL_PROJECT_NOT_UNIQUE")
    func = deepcopy(funcs[0])
    replaced = set()
    for stmt in func.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        target = stmt.targets[0]
        if isinstance(target, ast.Name) and target.id in ("t", "raw"):
            require(target.id not in replaced, "ORIGINAL_PROJECT_REPLACEMENT_DUPLICATE")
            expected = ("entry['fill_minute']" if target.id == "t" else
                        "Decimal(str(entry['fill_price'])) / Decimal('1.0005')")
            require(ast.dump(stmt.value) == ast.dump(ast.parse(expected, mode="eval").body),
                    "ORIGINAL_PROJECT_FILL_ACCESS_CHANGED")
            stmt.value = ast.parse(
                "entry['asof_minute']" if target.id == "t"
                else "Decimal(str(entry['asof_reference_price']))",
                mode="eval").body
            replaced.add(target.id)
    require(replaced == {"t", "raw"}, "ORIGINAL_PROJECT_FILL_ACCESS_NOT_FOUND")
    func.name = "project_received_asof"
    module = ast.fix_missing_locations(ast.Module(body=[func], type_ignores=[]))
    namespace = dict(vars(core))
    exec(compile(module, "<pinned original projection with two asof substitutions>",
                 "exec"), namespace)
    return namespace["project_received_asof"]


def verify_models(private_root, manifest=None):
    """Always verify all 24 original member SHA256 and Git blob identities first."""
    if manifest is None:
        manifest = json.loads(pin_public(LINEAGE, MANIFEST_BLOB))
    require(manifest.get("status") == "EXACT_MEMBER_HASH_PASS" and
            manifest.get("original_model_member_N") == 24 and
            manifest.get("new_fit") == 0 and len(manifest.get("models", [])) == 24,
            "ORIGINAL_MANIFEST_INVALID")
    root = Path(private_root).absolute()
    require(root.is_dir() and not root.is_symlink(), "PRIVATE_ROOT_INVALID")
    base = root.resolve(strict=True)
    result = {}
    for record in manifest["models"]:
        name = record.get("local_member")
        require(type(name) is str and
                re.fullmatch(r"inputs/frozen_models/H[235]_BLOCK_0[1-8]\.json", name),
                "MODEL_MEMBER_NAME_INVALID")
        family = int(name.split("/H")[1][0])
        block = int(name.rsplit("_BLOCK_", 1)[1][:2])
        require((family, block) not in result, "MODEL_MEMBER_DUPLICATE")
        path = root / name
        require(path.is_file() and not path.is_symlink() and
                not any(parent.is_symlink() for parent in (path.parent, path.parent.parent)),
                "MODEL_MEMBER_UNSAFE")
        require(path.resolve(strict=True).is_relative_to(base), "MODEL_PATH_ESCAPE")
        data = path.read_bytes()
        require(len(data) == record.get("bytes") and
                hashlib.sha256(data).hexdigest() == record.get("sha256") and
                git_blob(data) == record.get("git_blob"), "MODEL_BYTE_HASH_MISMATCH")
        model = json.loads(data)
        require(type(model) is dict and type(model.get("base_rate")) in (int, float)
                and 0 <= model["base_rate"] <= 1 and math.isfinite(model["base_rate"]),
                "MODEL_BASE_RATE_INVALID")
        result[(family, block)] = model
    require(set(result) == {(h, b) for h in HEADS for b in range(1, 9)},
            "MODEL_24_MEMBER_SET_INCOMPLETE")
    return result


def validate_input(raw):
    require(isinstance(raw, dict) and set(raw) == {
        "schemaId", "sessionDate", "symbol", "candidateId",
        "selectorFirstAtJst", "firstIntentAtJst", "decisionAtJst",
        "p1Score", "p1Threshold", "selectorFirstPrice",
        "referencePrice", "referenceBarEndJst", "referenceKnownAtJst",
        "stateTrace", "sourceKind", "shadowOnly", "productionReady",
        "orderTransmission",
    }, "INPUT_FIELDS_INVALID")
    session = raw["sessionDate"]
    pol = policy(session)
    require(raw["schemaId"] == INPUT_SCHEMA and
            raw["shadowOnly"] is True and raw["productionReady"] is False
            and raw["orderTransmission"] is False and
            raw["sourceKind"] == "RSS_CUMULATIVE_PROXY" and
            type(raw["symbol"]) is str and SYMBOL.fullmatch(raw["symbol"]) is not None and
            type(raw["candidateId"]) is str and
            re.fullmatch(r"[0-9a-f]{64}", raw["candidateId"]) is not None,
            "INPUT_SCOPE_OR_IDENTITY_INVALID")
    first = timestamp(raw["selectorFirstAtJst"], session)
    intent = timestamp(raw["firstIntentAtJst"], session)
    decision = timestamp(raw["decisionAtJst"], session)
    ref_end = timestamp(raw["referenceBarEndJst"], session)
    ref_received = timestamp(raw["referenceKnownAtJst"], session)
    require(first <= intent <= ref_end <= ref_received <= decision,
            "INPUT_CLOCK_ORDER_INVALID")
    require(minute(first) in (570, 600, 630, 660, 690, 780, 810, 840, 870, 900)
            and minute(ref_end) < 920 and eligible_closed_minute(minute(ref_end))
            and (decision - ref_end).total_seconds() <= 90,
            "REFERENCE_BAR_STALE_OR_NOT_ORIGINAL_CLOCK")
    require(minute(intent) >= minute(first), "INTENT_PRECEDES_SELECTOR")
    score = raw["p1Score"]
    threshold = raw["p1Threshold"]
    require(type(score) in (float, int) and type(threshold) in (float, int)
            and math.isfinite(score) and math.isfinite(threshold)
            and 0 <= threshold <= score <= 1, "P1_FIRST_CROSS_NOT_CONFIRMED")
    reference_price = positive(raw["referencePrice"], "REFERENCE_PRICE_INVALID")
    selector_price = positive(raw["selectorFirstPrice"], "SELECTOR_ANCHOR_INVALID")
    trace = raw["stateTrace"]
    require(isinstance(trace, list) and 1 <= len(trace) <= 400,
            "STATE_TRACE_REQUIRED")
    seen = set()
    prev_bar = 0
    prev_received = None
    normalized = []
    for row in trace:
        require(isinstance(row, dict) and set(row) == {
            "bar_end_minute", "knownAtJst", "state", "path", "path_events"
        }, "STATE_TRACE_FIELDS_INVALID")
        t = row["bar_end_minute"]
        seen_at = timestamp(row["knownAtJst"], session)
        require(eligible_closed_minute(t) and t > prev_bar and
                t <= minute(ref_end) and
                timestamp(session + "T%02d:%02d:00+09:00" % (t // 60, t % 60),
                          session) <= seen_at <= decision and
                (prev_received is None or seen_at >= prev_received),
                "STATE_TRACE_CAUSAL_CLOCK_INVALID")
        s, p, events = row["state"], row["path"], row["path_events"]
        require(isinstance(s, dict) and isinstance(p, dict) and
                isinstance(events, list) and
                s.get("as_of") == t - 540 and
                p.get("scheduled_t") == t - 540 and
                s.get("numeric_status") in ("ACCEPTED", "REJECTED", "NOT_AVAILABLE") and
                p.get("bar_end") == session + "T%02d:%02d:00+09:00" % (t // 60, t % 60) and
                all(isinstance(e, dict) and e.get("scheduled_t") == t - 540
                    for e in events), "STATE_TRACE_ORIGINAL_SHAPE_INVALID")
        normalized.append({k: row[k] for k in ("bar_end_minute", "state",
                                              "path", "path_events")})
        prev_bar, prev_received = t, seen_at
        seen.add(t)
    require(prev_bar == minute(ref_end) and prev_received <= decision and
            ref_received <= decision, "ASOF_REFERENCE_NOT_TRACE_END")
    latest = normalized[-1]
    s, p = latest["state"], latest["path"]
    require(s.get("current_semantics_observed") is True and
            s.get("numeric_status") == "ACCEPTED" and
            s.get("observed_at") == s.get("as_of") and
            p.get("Primary_or_null") not in (None, "PULLBACK", "SHARP_DROP"),
            "FROZEN_ENTRY_STATE_EXCLUDED_OR_UNAVAILABLE")
    return pol, normalized, first, intent, decision, ref_end, reference_price, selector_price


class FrozenH235AsOf:
    def __init__(self, private_root, session, *, manifest=None):
        self.policy = policy(session)
        self.core, self.prep, self.stair, src = original_dependencies()
        self.project = asof_projector(self.core, src)
        self.models = verify_models(private_root, manifest)
        self.original_model_count = len(self.models)

    def score(self, value):
        pol, trace, first, intent, decision, ref_end, price, selector_price = validate_input(value)
        require(pol["policySha256"] == self.policy["policySha256"],
                "MODEL_SESSION_POLICY_MISMATCH")
        first_clock, intent_clock, ref_clock = minute(first), minute(intent), minute(ref_end)
        entry = {
            "first_intent": {"score": value["p1Score"], "threshold": value["p1Threshold"],
                             "intent_minute": intent_clock},
            "selector_minute": first_clock,
            "selector_price": selector_price,
            "asof_minute": ref_clock,
            "asof_reference_price": price,
            "intent_to_fill_active_delay": active_elapsed(intent_clock, ref_clock),
            "selector_to_intent_active_delay": active_elapsed(first_clock, intent_clock),
            "selector_to_entry_active_delay": active_elapsed(first_clock, ref_clock),
        }
        feature = self.project(entry, trace)
        require(set(feature["numeric"]) == set(self.core.NUMERIC) and
                set(feature["categorical"]) == set(self.core.CATEGORICAL),
                "ORIGINAL_FEATURE_LAYOUT_MISMATCH")
        ps, bases = {}, {}
        for h in HEADS:
            artifact = self.models[(h, BLOCK)]
            prep = artifact["preprocessing"]
            require(isinstance(prep, dict) and
                    set(prep["numeric_fields"]).issubset(self.core.NUMERIC) and
                    set(prep["categorical_fields"]).issubset(self.core.CATEGORICAL),
                    "MODEL_PREPROCESS_FEATURES_OUTSIDE_ORIGINAL")
            p = float(self.prep.predict_saved([feature], artifact)[0])
            require(math.isfinite(p) and 0 <= p <= 1, "MODEL_PREDICTION_NONFINITE")
            ps[h], bases[h] = p, float(artifact["base_rate"])
        materialized = self.stair.materialize({
            **{"p" + str(h): ps[h] for h in HEADS},
            **{"base" + str(h): bases[h] for h in HEADS},
        })
        output = {
            "schemaId": OUTPUT_SCHEMA, "sessionDate": value["sessionDate"],
            "candidateId": value["candidateId"], "symbol": value["symbol"],
            "entry_timestamp": value["firstIntentAtJst"],
            "decisionAtJst": value["decisionAtJst"],
            "asofReferenceBarEndJst": value["referenceBarEndJst"],
            "referenceKnownAtJst": value["referenceKnownAtJst"],
            "raw_reference": price,
            "selectedBlock": BLOCK, "policySha256": self.policy["policySha256"],
            "sourceKind": value["sourceKind"], "sourceInputSha256": digest(value),
            "changedFeatureSemantics": True,
            "modelInputOriginalHistoricalParity": False,
            "originalFrozenModelFilesVerified": self.original_model_count,
            "originalModelsExecuted": 3, "newFits": 0,
            **materialized,
            "shadowOnly": True, "productionReady": False,
            "orderTransmission": False, "orderAuthorized": False,
            "capitalExecutionAuthorized": False,
        }
        return output


def make_received_candidate(*, p1_decision, watch, reference_row, trace, session):
    """Bridge only an actually emitted P1 FIRST_ENTRY_CANDIDATE and its receipt."""
    require(p1_decision.get("status") == "FIRST_ENTRY_CANDIDATE" and
            p1_decision.get("orderTransmission") is False and
            p1_decision.get("orderAuthorized") is False and
            p1_decision.get("shadowOnly") is True,
            "P1_FIRST_INTENT_REQUIRED")
    score = p1_decision.get("score", {})
    require(type(score) is dict and "score" in score,
            "P1_MODEL_SCORE_REQUIRED")
    bar_end = p1_decision["barEndJst"]
    require(isinstance(trace, list) and trace and
            trace[-1].get("bar_end_minute") ==
            minute(timestamp(bar_end, session)), "P1_TRACE_NOT_AT_FIRST_INTENT")
    require(reference_row.get("knownAtJst") is not None,
            "RSS_REFERENCE_RECEIPT_REQUIRED")
    return {
        "schemaId": INPUT_SCHEMA, "sessionDate": session,
        "symbol": reference_row["Code"],
        "candidateId": p1_decision["candidateId"],
        "selectorFirstAtJst": session + "T%02d:%02d:00+09:00" %
                              (watch["selector_minute"] // 60,
                               watch["selector_minute"] % 60),
        "firstIntentAtJst": bar_end,
        "decisionAtJst": p1_decision["evaluatedAtJst"],
        "p1Score": score["score"],
        "p1Threshold": p1_decision["threshold"],
        "selectorFirstPrice": watch["selector_price"],
        "referencePrice": reference_row["C"],
        "referenceBarEndJst": bar_end,
        "referenceKnownAtJst": reference_row["knownAtJst"],
        "stateTrace": deepcopy(trace), "sourceKind": "RSS_CUMULATIVE_PROXY",
        "shadowOnly": True, "productionReady": False,
        "orderTransmission": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True)
    parser.add_argument("--policy-only", action="store_true")
    parser.add_argument("--model-root", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--private-output", type=Path)
    args = parser.parse_args(argv)
    pol = policy(args.session)
    if args.policy_only:
        print(json.dumps(pol, sort_keys=True))
        return
    require(args.model_root is not None and args.events is not None
            and args.private_output is not None, "PRIVATE_ARGS_REQUIRED")
    out = args.private_output.absolute()
    require(out.parent.is_dir() and not out.is_symlink() and
            ROOT not in out.parents and out != ROOT, "PRIVATE_OUTPUT_OUTSIDE_REPO_REQUIRED")
    inp = args.events.absolute()
    require(inp.is_file() and not inp.is_symlink()
            and 0 < inp.stat().st_size <= 25_000_000, "EVENT_FILE_INVALID")
    events = json.loads(inp.read_text(encoding="utf-8-sig"))
    require(isinstance(events, list) and len(events) <= 50,
            "EVENT_BATCH_LIMIT")
    scorer = FrozenH235AsOf(args.model_root, args.session)
    results = []
    seen = set()
    for item in events:
        result = scorer.score(item)
        require(result["candidateId"] not in seen, "CANDIDATE_REPLAY_DUPLICATE")
        seen.add(result["candidateId"])
        results.append(result)
    results.sort(key=scorer.stair.candidate_order)
    document = {
        "schemaId": "ARK_NO11_H235_ASOF_PRIVATE_RANK_BATCH_V1",
        "policy": pol, "results": results,
        "frozenR0Used": True, "originalHistoricalScoreParity": False,
        "capitalV5Executed": False, "brokerOrders": 0,
        "productionReady": False, "orderTransmission": False,
    }
    data = stable_bytes(document) + b"\n"
    if out.exists():
        require(out.is_file() and out.read_bytes() == data,
                "PRIVATE_OUTPUT_ALREADY_EXISTS_DIFFERENT")
    else:
        with out.open("xb") as file:
            file.write(data)
    summary = {
        "status": "FROZEN_H235_ASOF_R0_SHADOW_ONLY",
        "selectedBlock": BLOCK, "modelsVerified": 24,
        "candidates": len(results),
        "rankable": sum(bool(r["admission"]) for r in results),
        "outputSha256": hashlib.sha256(data).hexdigest(),
        "capitalV5Executed": False, "productionReady": False,
        "orderTransmission": False,
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, AssertionError,
            ImportError, RuntimeError, IndexError) as exc:
        message = str(exc)
        print(message if re.fullmatch(r"NO11_H235_[A-Z0-9_]+", message)
              else "NO11_H235_PRIVATE_SOURCE_OR_RUNTIME_BLOCKED", file=sys.stderr)
        raise SystemExit(2)
