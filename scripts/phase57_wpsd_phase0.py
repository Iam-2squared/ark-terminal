"""Precommitted WPSD zero-fit separability audit on frozen Control lifecycles.

This module never fits an estimator, replays a portfolio, or reads a future
label while selecting FIRST_DAMAGE_EVENT. It accepts only saved artifacts.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import random
import statistics
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path

import numpy as np

from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_exit_continuation_r52 as r52
from scripts import phase57_exit_execution_contract_v1 as clock


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/phase57-wpsd-exit"
PRE = EVIDENCE / "PHASE0_PRECOMMIT.json"
PRE_SHA = "792c05ab2bd4e8e6222baecfdaa5b7a7990cc97108a9137d03bd3ae0bc703332"
R54_CLOSURE = ROOT / "docs/evidence/phase57-exit-mh-r54/CYCLE2_FINAL_CLOSURE.json"
R54_PROTOCOL = ROOT / "docs/evidence/phase57-exit-mh-r54/CYCLE2_PRECOMMIT.json"
SCHEMA = ROOT / "docs/evidence/phase57-exit-mh-r54/FEATURE_SCHEMA_LOCKED.json"
R50_CALENDAR = ROOT / "docs/evidence/phase57-capital-exit-integrated/INPUTS/R50_A_LIFECYCLE-run-a.jsonl.gz"
R50_ARCHIVE = ROOT / "docs/evidence/phase57-capital-exit-integrated/RESULT/phase57-integrated-result.zip"
PRIMARY_R54 = ROOT / "docs/evidence/phase57-post-r54-winner-anatomy/PRIMARY_ENTRY_EVALUATOR_ONLY.json"
R45_FEATURE = "gen3/data/decision-features.npz"
R45_IDS = "gen3/data/row-identities.jsonl.gz"
CRITICAL = ("HIGHER_LOW", "CONTINUATION", "RECLAIM", "COMPRESSION_EXPANSION")
REASONS = ("no_lookback", "source_missing", "session_proximity",
           "signal_not_computable", "other")
ARMS = {v0.IM: "IM", v0.R1: "R1"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def bytes_digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode()


def member(z, name, expected):
    raw = z.read(name)
    require(bytes_digest(raw) == expected, "PIN:" + name)
    return raw


def finite(value):
    value = float(value)
    return value if math.isfinite(value) else None


def close(path, minute):
    row = path.get(minute)
    if row is None or len(row) != 7:
        return None
    x = row[4]
    return float(x) if isinstance(x, (int, float)) and math.isfinite(x) and x > 0 else None


def load_fixed(r45_zip, replay_zip, audit_zip):
    require(digest(PRE) == PRE_SHA, "PHASE0_PRECOMMIT_CHANGED")
    pre = json.loads(PRE.read_text())
    pins = pre["sourcePins"]
    require(pre["status"] == "FROZEN_BEFORE_WPSD_FIRST_DAMAGE_EVENT_OR_CANDIDATE_PERFORMANCE"
            and pre["budget"] == {"newEstimatorFitsAllowed": 0,
                "integratedReplaysAllowed": 0, "providerRequestsAllowed": 0,
                "protectedOpenedAllowed": 0, "thresholdSearchAllowed": False,
                "additionalFamiliesAllowed": False}, "PHASE0_AUTHORITY_OR_BUDGET")
    require(pre["safety"] == clock.SAFETY and not any(pre["safety"].values()),
            "PHASE0_SAFETY")
    paths = ((r45_zip, "r45ArtifactZipSha256"),
             (replay_zip, "r54ReplayZipSha256"),
             (audit_zip, "r34AuditZipSha256"),
             (SCHEMA, "r45SchemaSha256"), (r52.RAW, "rawPathSha256"),
             (R50_CALENDAR, "r50AllEntryCalendarSha256"),
             (R54_CLOSURE, "r54FinalClosureSha256"),
             (PRIMARY_R54, "postR54PrimarySha256"))
    for path, key in paths:
        require(digest(path) == pins[key], "PIN:" + key)
    require(r52.FEATURE_SHA == pins["r45FeatureMemberSha256"] and
            r52.IDENTITY_SHA == pins["r45RowIdentityMemberSha256"],
            "R45_SOURCE_CONSTANT_DRIFT")
    closure = json.loads(R54_CLOSURE.read_text())
    protocol = json.loads(R54_PROTOCOL.read_text())
    require(digest(R54_PROTOCOL) == closure["lineage"]["protocolSha256"] and
            closure["lineage"]["correctedTeacherSha256"] ==
            protocol["inputHashes"]["labels"] == pins["r54TeacherSha256"] and
            closure["finalStatus"]["integrity_status"] == "PASS" and
            closure["finalStatus"]["measurement_status"] == "MEASUREMENT_BLOCKED" and
            closure["selected"] is None and
            closure["fixed"]["entryDualFreeze"] == pre["frozen"]["entryDualFreeze"] and
            closure["fixed"]["capital"] == pre["frozen"]["capital"] and
            not any(closure["safety"].values()), "R54_CONTROLLING_LINEAGE")
    with zipfile.ZipFile(R50_ARCHIVE) as z:
        ledgers = {}
        for short, key in (("IM", "imControlLedgerSha256"),
                           ("R1", "r1ControlLedgerSha256")):
            raw = member(z, short + "_V3_B_R50_A_ledger.json.gz", pins[key])
            ledgers[short] = json.loads(gzip.decompress(raw))
    with zipfile.ZipFile(replay_zip) as z:
        manifest_raw = member(z, "r54-result/manifest.json",
                              closure["lineage"]["resultManifestSha256"])
        manifest = json.loads(manifest_raw)
        require(manifest["newModelFits"] == 176 and
                manifest["integratedInvocations"] == 44 and
                not any(manifest["safety"].values()) and
                manifest["filesSha256"]["standalone-all-entries.json.gz"] ==
                bytes_digest(z.read("r54-result/standalone-all-entries.json.gz")),
                "R54_REPLAY_MANIFEST")
    with zipfile.ZipFile(audit_zip) as z:
        paired = json.loads(member(z, "paired-layer-a-r34.json",
                                   pins["r34PairedSha256"]))
        receipt = json.loads(z.read("accounting-audit.json"))
        require(receipt["status"] == "PASS" and
                receipt["correctedPairedSha256"] == pins["r34PairedSha256"] and
                receipt["sourceResultManifestSha256"] ==
                closure["lineage"]["resultManifestSha256"] and
                not any(receipt["safety"].values()), "R34_CORRECTED_LINEAGE")
    with zipfile.ZipFile(r45_zip) as z:
        require(R45_FEATURE in z.namelist() and R45_IDS in z.namelist(),
                "R45_MEMBERS_MISSING")
        r45_receipt = json.loads(z.read("gen3/data/data-receipt.json"))
        require(r45_receipt["rows"] == 656247 and
                r45_receipt["outputHashes"]["decision-features.npz"] ==
                pins["r45FeatureMemberSha256"] and
                r45_receipt["outputHashes"]["row-identities.jsonl.gz"] ==
                pins["r45RowIdentityMemberSha256"] and
                r45_receipt["providerRequests"] == 0 and
                r45_receipt["protectedPartitionsOpened"] == 0,
                "R45_RECEIPT_LINEAGE")
    return pre, r45_receipt, ledgers, paired


def control_universe(pre, ledgers):
    entries = r52.all_frozen_entries()
    sessions = tuple(json.loads(R54_PROTOCOL.read_text())["sessions"])
    require(len(sessions) == 24 and len(set(sessions)) == 24,
            "FROZEN_24_SESSION_SCOPE")
    chosen = {(arm, eid): entry for (arm, eid), entry in entries.items()
              if entry["session"] in sessions}
    require(collections.Counter(arm for arm, _ in chosen) ==
            {v0.IM: 819, v0.R1: 795}, "FROZEN_ENTRY_COUNTS")
    calendar = {}
    with gzip.open(R50_CALENDAR, "rt") as stream:
        for line in stream:
            row = json.loads(line)
            key = (row["entryArm"], row["entryId"])
            if key not in chosen:
                continue
            entry = chosen[key]
            now = row["decisionNow"]
            require(key not in calendar and row["candidateId"] == "R50_A_LIFECYCLE"
                    and row["session"] == entry["session"]
                    and row["entryMinute"] == entry["entryMinute"]
                    and math.isclose(float(row["entryPrice"]),
                                     float(entry["effectiveEntryPrice"]), rel_tol=0,
                                     abs_tol=1e-7) and
                    now in clock.decision_endpoints(entry["session"], entry["entryMinute"])
                    and row["decisionFacts"]["now"] == now and
                    row["decisionFacts"]["maxKnownAt"] <= now and
                    row["decisionFacts"]["maxBarEnd"] <= now,
                    "CONTROL_ID_OR_ASOF_DRIFT")
            if row["exitKind"] == "MODEL_EXIT":
                require(row["exitMinute"] ==
                        clock.next_execution_start(entry["session"], now),
                        "CONTROL_MODEL_FILL_GEOMETRY")
            else:
                require(row["exitKind"] == "FORCED_TERMINAL" and now == 925,
                        "CONTROL_TERMINAL_GEOMETRY")
            calendar[key] = now
    require(set(calendar) == set(chosen), "CONTROL_ALL_ENTRY_CENSUS")
    funded = {}
    context = {}
    for arm, short, count in ((v0.IM, "IM", 79), (v0.R1, "R1", 32)):
        ledger = ledgers[short]
        require(len(ledger["funded"]) == count and
                all((arm, eid) in chosen for eid in ledger["funded"]),
                "CONTROL_FUNDED_CENSUS:" + short)
        funded.update({(arm, eid): item for eid, item in ledger["funded"].items()})
        context.update({(arm, eid): x for eid, x in r52.classify(ledger).items()})
    require(len(funded) == 111 and len(context) == 111,
            "PRIMARY_CONTROL_CENSUS")
    # Decode only the pinned 24-session Entry opportunities, not unrelated paths.
    raw, skipped = v0.allowlisted_raw_paths(
        r52.RAW, {e["opportunity"] for e in chosen.values()})
    require(skipped == 5375 - len(raw) and
            set(raw) == {e["opportunity"] for e in chosen.values()},
            "FROZEN_RAW_PROJECTION")
    return chosen, calendar, funded, context, raw, sessions


def source_score(index, entry, path, now, arrays, columns, decoders, schedule):
    """Runtime-only score; no evaluator, R54 SELL, or future field in scope."""
    numeric, cats, fresh = arrays
    def num(name):
        return finite(numeric[index, columns["numeric"][name]])
    def cat(name):
        code = int(cats[index, columns["categorical"][name]])
        require(code in decoders[name], "UNDECLARED_CATEGORY_CODE:" + name)
        return decoders[name][code]

    state = cat("currentState.state")
    known_state = state != "UNKNOWN"
    f1 = int(known_state and state == "DROP")
    f1_reason = None if known_state else "signal_not_computable"
    tri = [cat("signal." + name + ".currentTriState") for name in CRITICAL]
    require(all(x in ("TRUE", "FALSE", "UNKNOWN") for x in tri),
            "SIGNAL_TRISTATE_DRIFT")
    true_n, false_n = tri.count("TRUE"), tri.count("FALSE")
    known_signal = true_n + false_n >= 2
    f2 = int(known_signal and false_n > true_n)
    f2_reason = None if known_signal else "signal_not_computable"

    k = schedule["index"].get(now - 1)
    now_close = close(path, now - 1) if k is not None and bool(fresh[index]) else None
    entry_price = float(entry["effectiveEntryPrice"])
    require(math.isfinite(entry_price) and entry_price > 0, "ENTRY_EFFECTIVE_PRICE")
    net = None if now_close is None else 100 * (now_close / entry_price - 1.0005)
    up_run = None
    run_reason = None
    if k is None:
        run_reason = "session_proximity"
    elif k == 0:
        run_reason = "no_lookback"
    elif now_close is None:
        run_reason = "source_missing"
    else:
        predecessor = close(path, schedule["minutes"][k-1])
        if predecessor is None:
            run_reason = "source_missing"
        else:
            up_run = 0
            cursor = k
            while cursor > 0:
                b = close(path, schedule["minutes"][cursor])
                a = close(path, schedule["minutes"][cursor-1])
                if b is None or a is None or b <= a:
                    break
                up_run += 1
                cursor -= 1
    f3_known = net is not None and up_run is not None
    f3 = int(f3_known and net <= 0 and up_run == 0)
    f3_reason = None if f3_known else (run_reason or "source_missing")

    loss = num("facts.signalLossN")
    failed = num("facts.failedRecovery")
    require(loss is None or loss >= 0, "SIGNAL_LOSS_RANGE")
    require(failed is None or failed in (0, 1), "FAILED_RECOVERY_RANGE")
    f4 = int((loss is not None and loss > 0) or failed == 1)
    f4_known = bool(f4) or (loss is not None and failed is not None)
    f4_reason = (None if f4_known else
                 "source_missing" if not bool(fresh[index]) else
                 "no_lookback" if now == entry["entryMinute"] + 1 else
                 "signal_not_computable")
    full = num("position.fullOwnedPrefix")
    require(full is None or full in (0, 1), "FULL_PREFIX_FLAG")
    votes = (f1, f2, f3, f4)
    known = (known_state, known_signal, f3_known, f4_known)
    reasons = (f1_reason, f2_reason, f3_reason, f4_reason)
    preservation = (int(net is not None and net > 0),
                    int(known_state and state in ("REBOUND", "RISE")),
                    int(true_n >= 1 and false_n <= true_n),
                    int(up_run is not None and up_run > 0))
    require(sum(votes) <= 4 and all(not vote or available for vote, available in
                                    zip(votes, known)), "DAMAGE_VOTE_WITHOUT_EVIDENCE")
    return {"damageScore": sum(votes), "familyVotes": dict(zip(("F1", "F2", "F3", "F4"), votes)),
            "familyEvaluable": dict(zip(("F1", "F2", "F3", "F4"), known)),
            "familyUnknownCause": dict(zip(("F1", "F2", "F3", "F4"), reasons)),
            "evaluableFamilies": sum(known),
            "preservationVotes": dict(zip(("P1", "P2", "P3", "P4"), preservation)),
            "preservationScore": sum(preservation), "veto": sum(preservation) >= 2,
            "currentState": state, "criticalSignals": dict(zip(CRITICAL, tri)),
            "currentNetPct": net, "upRun": up_run, "sourceFresh": bool(fresh[index]),
            "sourceFullOwnedPrefix": None if full is None else bool(full)}


def scan_anchors(r45_zip, pre, receipt, entries, calendar, raw, funded, context):
    pins = pre["sourcePins"]
    runtime = {}
    seen_rows = collections.Counter()
    last = {}
    nonzero_eval = collections.Counter()
    unknown_all = collections.Counter()
    with tempfile.TemporaryDirectory(prefix="wpsd-r45-") as tmp:
        feature_file = Path(tmp) / "decision-features.npz"
        with zipfile.ZipFile(r45_zip) as z:
            h = hashlib.sha256()
            with z.open(R45_FEATURE) as source, feature_file.open("wb") as target:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    h.update(block)
                    target.write(block)
            require(h.hexdigest() == pins["r45FeatureMemberSha256"],
                    "R45_FEATURE_MEMBER_PIN")
            schema = json.loads(SCHEMA.read_text())
            columns = {kind: {name: j for j, name in
                     enumerate(receipt[kind + "Columns"])} for kind in
                     ("numeric", "categorical")}
            required_nums = ("facts.signalLossN", "facts.failedRecovery",
                             "position.fullOwnedPrefix")
            required_cats = ("currentState.state",) + tuple(
                "signal." + name + ".currentTriState" for name in CRITICAL)
            require(all(x in columns["numeric"] for x in required_nums) and
                    all(x in columns["categorical"] and x in schema["categorical"]
                        for x in required_cats), "R45_REQUIRED_FEATURES")
            decoders = {name: {int(code): word for word, code in
                        schema["categorical"][name]["sourceCodes"].items()}
                        for name in required_cats}
            with np.load(feature_file, allow_pickle=False) as npz:
                # Do not allocate the large, irrelevant Pattern187 matrix.
                arrays = (npz["numeric"], npz["categorical"], npz["fresh"])
            require(len(arrays[0]) == len(arrays[1]) == len(arrays[2]) == 656247,
                    "R45_ARRAY_CENSUS")
            schedules = {}
            for session in {e["session"] for e in entries.values()}:
                minutes = clock.continuous_minutes(session)
                schedules[session] = {"minutes": minutes,
                    "index": {minute: j for j, minute in enumerate(minutes)},
                    "endpoints": {minute + 1 for minute in minutes}}
            id_file = Path(tmp) / "row-identities.jsonl.gz"
            id_hash = hashlib.sha256()
            with z.open(R45_IDS) as raw_ids, id_file.open("wb") as target:
                for block in iter(lambda: raw_ids.read(1024 * 1024), b""):
                    id_hash.update(block)
                    target.write(block)
            require(id_hash.hexdigest() == pins["r45RowIdentityMemberSha256"],
                    "R45_ROW_IDENTITY_MEMBER_PIN")
            with gzip.open(id_file, "rb") as ids:
                    for index, line in enumerate(ids):
                        row = json.loads(line)
                        require(row["index"] == index, "R45_ROW_ID_ORDER")
                        key = (row["arm"], row["entryId"])
                        if key not in entries:
                            continue
                        entry = entries[key]
                        now = row["now"]
                        schedule = schedules[entry["session"]]
                        require(row["session"] == entry["session"] and
                                now in schedule["endpoints"] and
                                now > entry["entryMinute"] and
                                now > last.get(key, -1), "R45_ENTRY_OR_CLOSED_NOW_DRIFT")
                        last[key] = now
                        if now > calendar[key]:
                            continue
                        seen_rows[key] += 1
                        if key in runtime:
                            continue
                        fact = source_score(index, entry, raw[entry["opportunity"]],
                                            now, arrays, columns, decoders, schedule)
                        nonzero_eval[key] += fact["evaluableFamilies"] > 0
                        for family, cause in fact["familyUnknownCause"].items():
                            if cause is not None:
                                unknown_all[(key, family, cause)] += 1
                        if fact["damageScore"] == 0:
                            continue
                        require(fact["damageScore"] >= 1, "ANCHOR_SCORE")
                        runtime[key] = {"arm": ARMS[key[0]], "entryId": key[1],
                            "session": entry["session"], "symbol": entry["symbol"],
                            "entryMinute": entry["entryMinute"], "now": now,
                            "anchor": "FIRST_DAMAGE_EVENT", "sourceIndex": index,
                            "controlDecisionNow": calendar[key],
                            "controlContext": context.get(key),
                            "archivedControlFunded": key in funded, **fact}
            require(index + 1 == 656247 and set(seen_rows) == set(entries),
                    "R45_CONTROL_LIFECYCLE_CENSUS")
    no_anchor = {}
    for key in entries:
        if key not in runtime:
            no_anchor[key] = {
                "arm": ARMS[key[0]], "entryId": key[1],
                "session": entries[key]["session"],
                "controlContext": context.get(key),
                "archivedControlFunded": key in funded,
                "reason": ("NO_DAMAGE_WITH_EVALUABLE_EVIDENCE" if nonzero_eval[key]
                           else "NO_EVALUABLE_DAMAGE_EVIDENCE"),
                "closedCheckpoints": seen_rows[key]}
    return runtime, no_anchor, unknown_all, seen_rows


def auc(rows):
    """Mann-Whitney AUC with half credit for tied integer scores."""
    counts = collections.Counter((r["damageScore"], r["defenseLt5"])
                                 for r in rows if r["defenseLt5"] is not None)
    positives = sum(n for (_, positive), n in counts.items() if positive)
    negatives = sum(n for (_, positive), n in counts.items() if not positive)
    if not positives or not negatives:
        return None
    lower_negatives = 0
    wins = 0
    for score in range(5):
        pos = counts[score, True]
        neg = counts[score, False]
        wins += pos * (2 * lower_negatives + neg)
        lower_negatives += neg
    return wins / (2 * positives * negatives)


def percentile_linear(sorted_values, p):
    at = p * (len(sorted_values) - 1)
    lo, hi = math.floor(at), math.ceil(at)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (at - lo)


def bootstrap(primary, sessions):
    by_session = collections.defaultdict(list)
    for row in primary:
        if row["defenseLt5"] is not None:
            by_session[row["session"]].append(row)
    ordered = sorted(sessions)
    require(len(ordered) == 24 and len(set(ordered)) == 24,
            "BOOTSTRAP_FROZEN_SESSION_COUNT")
    rng = random.Random(52)
    valid = []
    invalid = 0
    for _ in range(10000):
        sample = [row for session in rng.choices(ordered, k=24)
                  for row in by_session[session]]
        value = auc(sample)
        if value is None:
            invalid += 1
        else:
            valid.append(value)
    valid.sort()
    return {"point": auc(primary), "validReplicates": len(valid),
            "invalidSingleClass": invalid, "seed": 52, "replicates": 10000,
            "clusterUnit": "session", "ci95": (None if not valid else [
                percentile_linear(valid, .025), percentile_linear(valid, .975)])}


def counts(rows):
    score = collections.Counter(str(r["damageScore"]) for r in rows)
    return {"n": len(rows), "score": dict(sorted(score.items())),
            "familyVote": {k: sum(r["familyVotes"][k] for r in rows)
                           for k in ("F1", "F2", "F3", "F4")},
            "familyUnknown": {k: sum(not r["familyEvaluable"][k] for r in rows)
                              for k in ("F1", "F2", "F3", "F4")},
            "preservationVote": {k: sum(r["preservationVotes"][k] for r in rows)
                                 for k in ("P1", "P2", "P3", "P4")},
            "vetoN": sum(r["veto"] for r in rows),
            "evaluableFamilyDistribution": dict(sorted(collections.Counter(
                str(r["evaluableFamilies"]) for r in rows).items())),
            "medianDamage": statistics.median(r["damageScore"] for r in rows)
                            if rows else None}


def loss_tail(saved_primary, arm, cutoff):
    rows = [row for row in saved_primary if (arm == "COMBINED" or row["arm"] == arm)
            and row["upsidePct"] is not None and row["upsidePct"] >= cutoff]
    losses = sorted((-Decimal(row["candidatePnlJpy"])
                     + Decimal(row["controlPnlJpy"]) for row in rows
                     if row["candidatePnlJpy"] is not None and
                     row["controlPnlJpy"] is not None and
                     Decimal(row["candidatePnlJpy"]) < Decimal(row["controlPnlJpy"])),
                    reverse=True)
    total = sum(losses, Decimal(0))
    cumulative = Decimal(0)
    half_n = None
    for j, value in enumerate(losses, 1):
        cumulative += value
        if cumulative * 2 >= total:
            half_n = j
            break
    return {"cohortN": len(rows), "negativeDeltaTradeN": len(losses),
            "negativeDeltaTotalJpy": str(total),
            "worst1Share": float(sum(losses[:1], Decimal(0)) / total) if total else None,
            "worst3Share": float(sum(losses[:3], Decimal(0)) / total) if total else None,
            "worst5Share": float(sum(losses[:5], Decimal(0)) / total) if total else None,
            "tradesForHalfLoss": half_n}


def prefix_at_anchor(row, entry, path):
    minutes = [m for m in clock.continuous_minutes(row["session"])
               if entry["entryMinute"] <= m < row["now"]]
    if not minutes or not all(m in path and len(path[m]) == 7 and
                              all(isinstance(path[m][j], (int, float)) and
                                  math.isfinite(path[m][j]) and path[m][j] > 0
                                  for j in (1, 2, 3, 4)) for m in minutes):
        return {"fullPrefix": False, "mfePct": None,
                "drawdownFromHighPct": None, "recoveryFromLowPct": None}
    high = max(path[m][2] for m in minutes)
    low = min(path[m][3] for m in minutes)
    last = close(path, row["now"] - 1)
    price = float(entry["effectiveEntryPrice"])
    return {"fullPrefix": last is not None,
            "mfePct": 100 * (high / price - 1) if last is not None else None,
            "drawdownFromHighPct": 100 * (high-last) / high if last is not None else None,
            "recoveryFromLowPct": 100 * (last / low - 1) if last is not None else None}


def summarize(pre, runtime, no_anchor, entries, funded, context, raw, sessions,
              paired, replay_zip, unknown_all):
    # Evaluation starts here, after all FIRST_DAMAGE_EVENT identities are fixed.
    with zipfile.ZipFile(replay_zip) as z:
        standalone = json.loads(gzip.decompress(z.read(
            "r54-result/standalone-all-entries.json.gz")))
    evaluator = {}
    for arm, short in ARMS.items():
        source = standalone[short + "_R50_A_CONTROL"]
        require(len(source) == (819 if short == "IM" else 795),
                "ALL_ENTRY_EVALUATOR_CENSUS")
        for item in source:
            key = (arm, item["entryId"])
            require(key not in evaluator and key in entries and
                    item["session"] == entries[key]["session"],
                    "EVALUATOR_IDENTITY")
            evaluator[key] = item["evaluatorOnlyPostEntryUpsidePct"]
    require(set(evaluator) == set(entries), "EVALUATOR_ALL_ENTRY_IDENTITY")
    saved_primary = json.loads(PRIMARY_R54.read_text())
    require(len(saved_primary) == len(funded) == 111,
            "POST_R54_PRIMARY_COUNT")
    saved_index = {}
    for item in saved_primary:
        arm = v0.IM if item["arm"] == "IM" else v0.R1
        key = (arm, item["entryId"])
        require(key not in saved_index and key in funded and
                evaluator[key] == item["upsidePct"], "POST_R54_PRIMARY_IDENTITY")
        saved_index[key] = item
    require(set(saved_index) == set(funded), "POST_R54_PRIMARY_SET")
    for arm, short in ARMS.items():
        pairs = paired[short]["FULL_MH_WAIT15"]
        require({x["entryId"] for x in pairs} ==
                {eid for a, eid in funded if a == arm}, "R34_PAIRED_IDENTITY")
        for pair in pairs:
            key = (arm, pair["entryId"])
            item = saved_index[key]
            require(pair["quantity"] == funded[key]["quantity"] and
                    pair["candidatePnlJpy"] == item["candidatePnlJpy"] and
                    pair["controlPnlJpy"] == item["controlPnlJpy"] and
                    pair["evaluatorOnlyUpsidePct"] == evaluator[key],
                    "POST_R54_R34_PAIRED_DRIFT")
    labels = {}
    for key, value in evaluator.items():
        require(value is None or isinstance(value, (float, int)) and
                math.isfinite(value), "EVALUATOR_UPSIDE_VALUE")
        labels[key] = {"upsidePct": value,
                       "defenseLt5": None if value is None else value < 5,
                       "winnerGe5": None if value is None else value >= 5,
                       "winnerGe10": None if value is None else value >= 10}
    joined = []
    for key, r in sorted(runtime.items()):
        extra = labels[key]
        diagnostic = prefix_at_anchor(r, entries[key], raw[entries[key]["opportunity"]])
        require(r["sourceFullOwnedPrefix"] is not None and
                diagnostic["fullPrefix"] == r["sourceFullOwnedPrefix"],
                "R45_RAW_PREFIX_COMPLETENESS_DRIFT")
        joined.append({**r, **extra, "prefix": diagnostic,
                       "usefulDefensiveR54": (saved_index[key]["defensive"]
                                                if key in saved_index else None)})
    primary = [r for r in joined if r["archivedControlFunded"]]
    secondary = joined
    arm_auc = {short: auc([r for r in primary if r["arm"] == short])
               for short in ("IM", "R1")}
    combined = bootstrap(primary, sessions)
    secondary_medians = {}
    for short in ("IM", "R1"):
        arm_rows = [r for r in secondary if r["arm"] == short]
        secondary_medians[short] = {
            "defense": counts([r for r in arm_rows if r["defenseLt5"] is True])["medianDamage"],
            "winner": counts([r for r in arm_rows if r["winnerGe5"] is True])["medianDamage"]}
    gates = {"primaryCombinedAucCiLowerStrictlyAbove0.5":
             combined["point"] is not None and combined["validReplicates"] >= 9500
             and combined["ci95"] is not None and combined["ci95"][0] > .5,
             "bothArmAucAtLeast0.5": all(x is not None and x >= .5 for x in arm_auc.values()),
             "secondaryBothArmDefenseMedianAtLeastWinnerMedian":
             all(d["defense"] is not None and d["winner"] is not None and
                 d["defense"] >= d["winner"] for d in secondary_medians.values()),
             "allPinnedSourceDigestsAndEntryIdentityPass": True,
             "historicalAsOfNoFutureLeakage": True,
             "allSafetyFlagsFalse": not any(pre["safety"].values())}
    # Denominators include no-anchor and missing labels: never impute either.
    populations = {}
    for universe, keyset in (("primary", funded), ("secondary", entries)):
        populations[universe] = {}
        for short in ("IM", "R1", "COMBINED"):
            keys = {key for key in keyset if short == "COMBINED" or ARMS[key[0]] == short}
            anchored = [r for r in joined if (r["arm"] == short or short == "COMBINED")
                        and (v0.IM if r["arm"] == "IM" else v0.R1, r["entryId"]) in keys]
            missing = [key for key in keys if key in no_anchor]
            require(len(anchored) + len(missing) == len(keys),
                    "PHASE0_ANCHOR_PARTITION:" + universe + ":" + short)
            populations[universe][short] = {
                "entryN": len(keys), "anchorN": len(anchored),
                "noAnchorN": len(missing),
                "noAnchorReasons": dict(collections.Counter(no_anchor[key]["reason"]
                                                               for key in missing)),
                "anchorKnownLabelN": sum(r["defenseLt5"] is not None for r in anchored),
                "anchorMissingLabelN": sum(r["defenseLt5"] is None for r in anchored),
                "noAnchorByClass": dict(collections.Counter(
                    "UNKNOWN" if labels[key]["defenseLt5"] is None else
                    "DEFENSE_LT5" if labels[key]["defenseLt5"] else "WINNER_GE5"
                    for key in missing)),
                "winnerGe10AnchorN": sum(r["winnerGe10"] is True for r in anchored)}
    groups = {}
    for universe, rows in (("primary", primary), ("secondary", secondary)):
        groups[universe] = {}
        for short in ("IM", "R1", "COMBINED"):
            arm_rows = [r for r in rows if short == "COMBINED" or r["arm"] == short]
            groups[universe][short] = {
                "all": counts(arm_rows),
                "defenseLt5": counts([r for r in arm_rows if r["defenseLt5"] is True]),
                "winnerGe5": counts([r for r in arm_rows if r["winnerGe5"] is True]),
                "winnerGe10Subset": counts([r for r in arm_rows if r["winnerGe10"] is True])}
    cause_counts = collections.Counter()
    for r in joined:
        cls = "UNKNOWN" if r["defenseLt5"] is None else (
              "DEFENSE_LT5" if r["defenseLt5"] else "WINNER_GE5")
        for family, cause in r["familyUnknownCause"].items():
            if cause is not None:
                cause_counts[(r["arm"], cls, family, cause)] += 1
    unknown = {"anchorByArmClassFamilyCause": [
        {"arm": arm, "class": cls, "family": family, "cause": cause, "n": n}
        for (arm, cls, family, cause), n in sorted(cause_counts.items())],
        "allScannedBeforeAnchorByClassFamilyCause": [
            {"arm": ARMS[key[0]], "entryId": key[1], "family": family,
             "class": ("UNKNOWN" if labels[key]["defenseLt5"] is None else
                       "DEFENSE_LT5" if labels[key]["defenseLt5"] else "WINNER_GE5"),
             "cause": cause, "checkpoints": n}
            for (key, family, cause), n in sorted(unknown_all.items())],
        "causeVocabulary": REASONS,
        "sessionProximityN": sum(r["familyUnknownCause"]["F3"] ==
                                 "session_proximity" for r in joined)}
    strata = {}
    for name, get in (("timeOfDay", lambda x: "EARLY" if x["now"] < 630 else
                       "MID" if x["now"] < 810 else "LATE"),
                      ("controlContext", lambda x: x["controlContext"] or "UNFUNDED_UNKNOWN")):
        strata[name] = [{"universe": scope, "arm": short, "stratum": value,
                         "class": cls, **counts(part)}
            for scope, data in (("primary", primary), ("secondary", secondary))
            for short in ("IM", "R1")
            for value in sorted({get(r) for r in data if r["arm"] == short})
            for cls, criterion in (("DEFENSE_LT5", lambda r: r["defenseLt5"] is True),
                                   ("WINNER_GE5", lambda r: r["winnerGe5"] is True),
                                   ("UNKNOWN", lambda r: r["defenseLt5"] is None))
            if (part := [r for r in data if r["arm"] == short and get(r) == value
                         and criterion(r)])]
    prefix = {}
    for cls, subset in (("DEFENSE_LT5", [r for r in primary if r["defenseLt5"] is True]),
                        ("WINNER_GE5", [r for r in primary if r["winnerGe5"] is True])):
        known = [r["prefix"] for r in subset if r["prefix"]["fullPrefix"]]
        prefix[cls] = {"anchorN": len(subset), "completePrefixN": len(known),
                       **{name: (statistics.median(x[name] for x in known) if known else None)
                          for name in ("mfePct", "drawdownFromHighPct",
                                       "recoveryFromLowPct")}}
    tails = {arm: {str(cutoff): loss_tail(saved_primary, arm, cutoff)
                   for cutoff in (5, 10)} for arm in ("IM", "R1", "COMBINED")}
    result = {"schema": "phase57-wpsd-phase0-result-v1", "status":
              "PHASE0_GO" if all(gates.values()) else "PHASE0_NO_GO",
              "precommitSha256": PRE_SHA, "sourcePins": pre["sourcePins"],
              "sourceLineageStatus": "PASS", "asOfStatus": "PASS",
              "auc": {"combinedSessionClusterBootstrap": combined,
                      "arm": arm_auc},
              "secondaryMedian": secondary_medians, "gates": gates,
              "population": populations, "cohorts": groups,
              "unknown": unknown, "strata": strata,
              "r54NegativeWinnerDeltaTail": tails,
              "fullPrefixDescriptive": prefix,
              "budget": {"newEstimatorFits": 0, "integratedReplays": 0,
                         "providerRequests": 0, "protectedOpened": 0,
                         "thresholdSearches": 0},
              "safety": pre["safety"],
              "limitations": ["Development-only outcome-exposed separability, not predictive validation",
                  "Alternate IM/R1 Entry worlds are not additive portfolio PnL",
                  "Unknown and missing future labels are excluded from AUC, never zero",
                  "Historical closed-bar end is a knownAt proxy, not provider publication certification",
                  "Full-prefix metrics require every owned OHLC; incomplete prefixes remain null"]}
    return result, joined, no_anchor


def save(out, result, runtime, joined, no_anchor):
    require(not out.exists(), "PHASE0_APPEND_ONLY_OUTPUT_EXISTS")
    out.mkdir(parents=True, exist_ok=False)
    (out / "RESULT.json").write_bytes(canonical(result))
    outputs = (("ANCHORS_RUNTIME.jsonl.gz", list(runtime.values())),
               ("ANCHORS_EVALUATOR_ONLY.jsonl.gz", joined),
               ("NO_ANCHOR.jsonl.gz", list(no_anchor.values())))
    for name, rows in outputs:
        payload = b"".join(canonical(r) for r in sorted(
            rows, key=lambda r: (r["arm"], r["entryId"])))
        (out / name).write_bytes(gzip.compress(payload, mtime=0))
    manifest = {"schema": "phase57-wpsd-phase0-manifest-v1",
                "precommitSha256": PRE_SHA, "status": result["status"],
                "filesSha256": {p.name: digest(p) for p in sorted(out.iterdir())},
                "sourcePins": result["sourcePins"], "safety": result["safety"]}
    (out / "MANIFEST.json").write_bytes(canonical(manifest))


def run(r45_zip, replay_zip, audit_zip, out):
    require(not out.exists(), "PHASE0_APPEND_ONLY_OUTPUT_EXISTS")
    pre, receipt, ledgers, paired = load_fixed(r45_zip, replay_zip, audit_zip)
    entries, calendar, funded, context, raw, sessions = control_universe(pre, ledgers)
    runtime, no_anchor, unknown_all, _ = scan_anchors(
        r45_zip, pre, receipt, entries, calendar, raw, funded, context)
    result, joined, no_anchor = summarize(
        pre, runtime, no_anchor, entries, funded, context, raw,
        sessions, paired, replay_zip, unknown_all)
    save(out, result, runtime, joined, no_anchor)
    print(canonical({"status": result["status"], "auc": result["auc"],
                     "gates": result["gates"], "output": str(out)}).decode(), end="")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r45-zip", required=True, type=Path)
    parser.add_argument("--r54-replay-zip", required=True, type=Path)
    parser.add_argument("--r34-audit-zip", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    run(args.r45_zip, args.r54_replay_zip, args.r34_audit_zip, args.out)
