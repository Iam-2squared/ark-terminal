#!/usr/bin/env python3
"""Pinned original P1 raw/State9 -> causal feature computation, without fitting.

The historical batch entry point executes the original ``state_task`` AST,
excluding the original module's imports, run(), dataset writers and teacher
checks.  It preserves the original UNKNOWN actual-knownAt / bar-end assumption;
it does not authorize a provider substitution or select a model for 2026.
"""
import ast
from copy import deepcopy
from datetime import date
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import zipfile

import no11_frozen_p1_score_replay as core


REPO = Path(__file__).resolve().parents[3]
BASE_REL = core.BASE_REL
STATE_REL = "research/state9-safe-upside-hybrid-entry-20261003"
RC2_REL = STATE_REL + "/FROZEN_RC2_SOURCE"
MANIFEST_SHA = "bdae909069de34fe01e5548836536c02c8d41c8b3f2da93f01d0547d7a056655"
FEATURE_SHA = "ad737e63e2a3100c4413ee30b59423f54eb197da0f9f1dcce81ffa8b71022f5e"
SOURCE_KIND = "ORIGINAL_SAVED_JQUANTS_V2"
RAW_PINS = {
    "raw_paths": {
        "archive_path": "persistent_sources/raw_paths_selected.json.gz",
        "bytes": 15276285,
        "sha256": "28a7d3faadda1e677a45cf6c7290bb99e4986c3e026da6746a9f3c04883a9c86",
    },
    "source_tokens": {
        "archive_path": "private_source/PRIVATE_SELECTED_SOURCE_TOKENS.json.gz",
        "bytes": 22867396,
        "sha256": "20668479355fe37492a154ee80ea132b5af8bf2bf78269d90a2df5814d848dc7",
    },
}
_MODULE_SERIAL = 0


def check(ok, code):
    if not ok:
        raise ValueError("P1_FEATURE_" + code)


def _public_bytes(path, expected):
    core.regular_file(path)
    data = path.read_bytes().replace(b"\r\n", b"\n")
    check(core.digest(data) == expected, "PUBLIC_SOURCE_PIN_MISMATCH")
    return data


def _public_contracts(repo):
    manifest = json.loads(_public_bytes(repo / BASE_REL / "MANIFEST.json", MANIFEST_SHA))
    feature = json.loads(_public_bytes(repo / BASE_REL / "FEATURE_FREEZE.json", FEATURE_SHA))
    return manifest, feature


def materialize_saved_feature_inputs(base_zip, private_root, repo=REPO):
    """Verify the original archive before reading only three pinned raw members.

    Returned keys are raw_paths, source_tokens and watch_ranges, with Path values.
    No market numbers, source-token lexemes or models are parsed here.
    """
    repo = Path(repo)
    manifest, _ = _public_contracts(repo)
    spec = core.load_contracts(repo)
    archive_pin = spec["base_archive"]
    core.verify_file(Path(base_zip), archive_pin)
    pins = deepcopy(RAW_PINS)
    ranges = next(a for a in manifest["artifacts"]
                  if a["path"] == "PRIVATE_INPUTS/watch_row_ranges.npy")
    pins["watch_ranges"] = dict(ranges, archive_path="ark-terminal/" + BASE_REL + "/" + ranges["path"])
    cache = Path(private_root) / "verified" / archive_pin["sha256"][:16]
    result = {}
    with zipfile.ZipFile(base_zip) as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)), "DUPLICATE_ZIP_MEMBER")
        package = json.loads(archive.read("PRIVATE_PACKAGE_MANIFEST.json"))
        entries = {r["archive_path"]: r for r in package["entries"]}
        for key, pin in pins.items():
            name = pin["archive_path"]
            check(name in entries and all(entries[name][k] == pin[k] for k in ("bytes", "sha256")),
                  "RAW_MANIFEST_PIN_MISMATCH")
            info = archive.getinfo(name)
            check(not info.is_dir() and info.file_size == pin["bytes"], "RAW_MEMBER_SIZE_MISMATCH")
            out = cache / name
            core.safe_directory(out.parent)
            if out.exists():
                core.verify_file(out, pin)
            else:
                fd, temporary = tempfile.mkstemp(prefix=".p1-raw-", dir=out.parent)
                try:
                    h = hashlib.sha256()
                    size = 0
                    with os.fdopen(fd, "wb") as target, archive.open(info) as source:
                        for block in iter(lambda: source.read(1024 * 1024), b""):
                            size += len(block)
                            check(size <= pin["bytes"], "RAW_MEMBER_OVERFLOW")
                            h.update(block)
                            target.write(block)
                    check(size == pin["bytes"] and h.hexdigest() == pin["sha256"], "RAW_MEMBER_HASH_MISMATCH")
                    check(not out.exists() and not out.is_symlink(), "RAW_CACHE_COLLISION")
                    os.replace(temporary, out)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            result[key] = out
    return result


def _compile_nodes(nodes, namespace, label):
    module = ast.fix_missing_locations(ast.Module(body=deepcopy(nodes), type_ignores=[]))
    exec(compile(module, label, "exec"), namespace)


def _functions(source, names):
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in names]
    check({n.name for n in nodes} == set(names), "CALCULATION_AST_MISMATCH")
    return nodes


def _module(name, source=None, package=False):
    module = ModuleType(name)
    module.__package__ = name if package else name.rpartition(".")[0]
    if package:
        module.__path__ = []
    sys.modules[name] = module
    if source is not None:
        exec(compile(source, "<pinned original " + name + ">", "exec"), module.__dict__)
    return module


def _history_function(state_task, namespace):
    """Retain the original history statements verbatim inside a small wrapper."""
    loops = [n for n in ast.walk(state_task) if isinstance(n, ast.While)]
    check(len(loops) == 1, "HISTORY_AST_MISMATCH")
    body = loops[0].body
    start = next((i for i, n in enumerate(body) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "formal" for t in n.targets)), None)
    check(start is not None, "HISTORY_AST_MISMATCH")
    template = ast.parse("def update_history(day, endpoint, events, end, seq, changes, segment, last_change, support_start):\n return seq, changes, segment, last_change, support_start, history\n").body[0]
    template.body = deepcopy(body[start:]) + template.body
    _compile_nodes([template], namespace, "<pinned original P1 history AST>")


def load_feature_runtime(repo=REPO, np=None):
    """Load verified calculations; no original run(), fit(), teacher or I/O AST."""
    global _MODULE_SERIAL
    repo = Path(repo)
    manifest, feature = _public_contracts(repo)
    artifacts = {r["path"]: r for r in manifest["artifacts"]}
    sources = {}
    for name in ("common.py", "price_primitives.py", "price_features.py", "causal_features.py"):
        sources[name] = _public_bytes(repo / BASE_REL / name, artifacts[name]["sha256"])
    identity = feature["state_identity"]
    check(len(identity["source_files"]) == 16, "RC2_SOURCE_SET_MISMATCH")
    for pin in identity["source_files"]:
        sources[pin["path"]] = _public_bytes(repo / RC2_REL / pin["path"], pin["sha256"])
    profile = json.loads(_public_bytes(repo / STATE_REL / "FROZEN_PUBLIC_INPUTS/profile.json",
                                      identity["profile_sha256"]))
    schema = json.loads(sources["FEATURE_SCHEMA_V2.json"])
    if np is None:
        import numpy as np
    # Isolated packages avoid collisions with the separate Stage3 candidate.*.
    _MODULE_SERIAL += 1
    prefix = "_no11_p1_feature_rc2_" + str(_MODULE_SERIAL)
    _module(prefix, package=True)
    _module(prefix + ".candidate", package=True)
    for name in ("exact", "kernel", "api"):
        _module(prefix + ".candidate." + name, sources["candidate/" + name + ".py"])
    normalize80 = _module(prefix + ".normalize80", sources["normalize80.py"])
    normalize120 = _module(prefix + ".normalize120", sources["normalize120.py"])
    path = _module(prefix + ".path", sources["PATH_FROZEN.py"])
    builder = _module(prefix + ".builder", sources["CAUSAL_FEATURE_BUILDER.py"])
    namespace = {
        "__name__": prefix + ".calculation", "np": np, "math": math,
        "json": json, "hashlib": hashlib, "Decimal": Decimal, "localcontext": localcontext,
        "SimpleNamespace": SimpleNamespace,
        "Engine": sys.modules[prefix + ".candidate.api"].Engine,
        "normalize80": normalize80, "normalize120": normalize120,
        "PathBuilder": path.PathBuilder, "validate": path.validate,
        "FeatureBuilder": builder.FeatureBuilder, "SCHEMA": schema, "PROFILE": profile,
    }
    _compile_nodes(_functions(sources["common.py"], {
        "stamp", "regular_starts", "close_minute", "active_elapsed", "valid_bar", "clean_array",
    }), namespace, "<pinned original P1 common calculations>")
    _compile_nodes(_functions(sources["input_gate.py"], {"scheduled_minutes"}), namespace,
                   "<pinned original schedule only>")
    nodes = [n for n in ast.parse(sources["price_primitives.py"]).body
             if isinstance(n, (ast.FunctionDef, ast.Assign))]
    _compile_nodes(nodes, namespace, "<pinned original price primitives>")
    nodes = [n for n in ast.parse(sources["price_features.py"]).body
             if isinstance(n, ast.Assign) or isinstance(n, ast.FunctionDef) and n.name == "compute"]
    _compile_nodes(nodes, namespace, "<pinned original P1 price feature calculation>")
    check(namespace["P0_NAMES"] + namespace["P1_NUM"] == feature["P1_numeric"]
          and namespace["P1_CAT"] == feature["P1_categorical"], "FROZEN_FEATURE_ORDER_MISMATCH")
    state_task = _functions(sources["causal_features.py"], {"state_task"})[0]
    _compile_nodes([state_task], namespace, "<pinned original P1 state_task only>")
    _history_function(state_task, namespace)
    check(not any(k in namespace for k in ("run", "fit", "teacher", "write", "write_lines")),
          "NONCALCULATION_CODE_PRESENT")
    return SimpleNamespace(np=np, namespace=namespace, feature=feature, schema=schema,
                           state_task=namespace["state_task"], Engine=namespace["Engine"],
                           profile=profile, source_snapshot_sha256=identity["source_snapshot_sha256"],
                           numeric_names=tuple(feature["P1_numeric"]),
                           categorical_names=tuple(feature["P1_categorical"]))


def _day(value):
    check(type(value) is str, "SESSION_REQUIRED")
    try:
        check(date.fromisoformat(value).isoformat() == value, "SESSION_FORMAT")
    except (ValueError, TypeError):
        raise ValueError("P1_FEATURE_SESSION_FORMAT") from None
    return value


def _watch(watch):
    check(isinstance(watch, dict), "CANONICAL_WATCH_REQUIRED")
    keys = ("watch_key", "session", "selector_minute", "selector_price", "refresh_minutes")
    check(all(k in watch for k in keys), "CANONICAL_WATCH_REQUIRED")
    w = {k: deepcopy(watch[k]) for k in keys}
    _day(w["session"])
    check(isinstance(w["watch_key"], str) and bool(w["watch_key"]), "WATCH_ID_REQUIRED")
    check(type(w["selector_minute"]) is int, "SELECTOR_CLOCK_REQUIRED")
    check(type(w["selector_price"]) in (int, float) and math.isfinite(w["selector_price"])
          and w["selector_price"] > 0, "SELECTOR_ANCHOR_REQUIRED")
    check(isinstance(w["refresh_minutes"], list)
          and all(type(x) is int and x >= w["selector_minute"] for x in w["refresh_minutes"])
          and w["refresh_minutes"] == sorted(w["refresh_minutes"]), "REFRESH_CLOCKS_INVALID")
    return w


def _raw_rows(rows):
    check(isinstance(rows, (list, tuple)), "RAW_ROWS_REQUIRED")
    for row in rows:
        check(isinstance(row, (list, tuple)) and len(row) == 7, "OHLCV_AND_REAL_VA_REQUIRED")
        check(type(row[0]) in (int, float) and math.isfinite(row[0]) and int(row[0]) == row[0],
              "RAW_CLOCK_INVALID")
        check(type(row[6]) in (int, float) and math.isfinite(row[6]) and row[6] >= 0,
              "REAL_VA_REQUIRED")


def compute_watch_features(runtime, watch, raw, source, *, watch_index=0,
                           as_of_minute=None, source_kind=SOURCE_KIND):
    """Original historical feature batch, with today's input clipped BEFORE AST.

    ``source_kind`` describes the pinned archived provider, never RSS.  Historical
    bar-end availability is preserved as an assumption, not receipt-time proof.
    Invalid previous basis follows the original SOURCE_UNAVAILABLE/missing path.
    Missing Va and absent canonical Watch fields are not estimated.
    """
    check(source_kind == SOURCE_KIND, "PROVIDER_SUBSTITUTION_NOT_ALLOWED")
    w = _watch(watch)
    check(isinstance(raw, dict) and all(k in raw for k in ("today", "previous")), "RAW_INPUT_REQUIRED")
    check(isinstance(source, dict) and all(k in source for k in ("previous", "previous_daily", "previous_session")),
          "PREVIOUS_SOURCE_FIELDS_REQUIRED")
    check(isinstance(raw["today"], (list, tuple)), "RAW_ROWS_REQUIRED")
    for row in raw["today"]:
        check(isinstance(row, (list, tuple)) and len(row) >= 1
              and type(row[0]) in (int, float) and math.isfinite(row[0]) and int(row[0]) == row[0],
              "RAW_CLOCK_INVALID")
    if as_of_minute is None:
        as_of_minute = max((int(r[0]) + 1 for r in raw["today"]), default=w["selector_minute"])
    check(type(as_of_minute) is int, "ASOF_CLOCK_INVALID")
    previous_day = _day(source["previous_session"])
    check(previous_day < w["session"], "PREVIOUS_SOURCE_NOT_PAST")
    # Neither future rows nor their first-AM/PM auction minima reach state_task.
    clipped = {"today": [list(r) for r in raw["today"] if int(r[0]) + 1 <= as_of_minute],
               "previous": deepcopy(raw["previous"])}
    _raw_rows(clipped["today"])
    _raw_rows(clipped["previous"])
    previous_source = {k: deepcopy(source[k]) for k in ("previous", "previous_daily", "previous_session")}
    for row in previous_source["previous"]:
        check(isinstance(row, dict) and row.get("Date") == previous_day, "PREVIOUS_LEXEME_DATE_MISMATCH")
    result = runtime.state_task((int(watch_index), w, clipped, previous_source))
    wi, numeric, categories, meta, receipt = result
    check(numeric.shape == (len(meta), 148) and len(categories) == len(meta)
          and all(len(row) == 15 for row in categories), "OUTPUT_SHAPE_MISMATCH")
    check(all(m["intent_minute"] <= as_of_minute
              and (m["state_as_of_minute"] is None or m["state_as_of_minute"] <= m["intent_minute"])
              for m in meta), "OUTPUT_CAUSAL_CLOCK_MISMATCH")
    receipt = dict(receipt, featureScope="ORIGINAL_SAVED_RAW_CAUSAL_FEATURE_REPLAY",
                   actualKnownAt="UNKNOWN", assumedAvailableAt="bar_end", sourceKind=source_kind,
                   asOfMinute=as_of_minute, fullOofReplay=False, modelDispatch2026="UNDEFINED_IN_ORIGINAL_FROZEN_SPLIT",
                   orderTransmission=False, modelFits=0)
    return wi, numeric, categories, meta, receipt


def encode_categories(runtime, categories, vocabulary):
    """Lossless encoding into the existing frozen global dictionary; no refit."""
    check(isinstance(vocabulary, list) and len(vocabulary) == 15, "CATEGORY_VOCABULARY_INVALID")
    maps = []
    for values in vocabulary:
        check(isinstance(values, list) and all(type(v) is str for v in values)
              and len(values) == len(set(values)), "CATEGORY_VOCABULARY_INVALID")
        maps.append({value: i for i, value in enumerate(values)})
    result = runtime.np.empty((len(categories), 15), dtype=runtime.np.int32)
    for i, row in enumerate(categories):
        check(len(row) == 15, "CATEGORY_ROW_SHAPE")
        for j, value in enumerate(row):
            check(value in maps[j], "CATEGORY_OUTSIDE_ORIGINAL_GLOBAL_VOCABULARY")
            result[i, j] = maps[j][value]
    return result


def verify_saved_compact_overlap(raw, source):
    """Audit exact saved lexeme/compact overlap without exposing any values.

    This is provenance validation only; its token rows never become predictors.
    Empty historical previous source remains explicit unavailable provenance.
    """
    counts = {"currentPrefixDecimalChecks": 0, "previousDecimalChecks": 0}
    for compact_key, tokens_key, count_key in (
        ("today", "current_prefix", "currentPrefixDecimalChecks"),
        ("previous", "previous", "previousDecimalChecks"),
    ):
        rows = {int(r[0]): r for r in raw[compact_key]}
        for token in source.get(tokens_key, []):
            minute = int(token["Time"][:2]) * 60 + int(token["Time"][3:5])
            check(minute in rows, "SAVED_LEXEME_MINUTE_MISSING")
            for index, field in enumerate(("O", "H", "L", "C", "Vo", "Va"), 1):
                check(Decimal(str(rows[minute][index])) == Decimal(token[field]), "SAVED_LEXEME_VALUE_MISMATCH")
                counts[count_key] += 1
    return dict(counts, mismatches=0)


class StateFeatureStream:
    """Incremental full State9 -> original Path -> 38 numeric / 14 string fields.

    Call from the start of the scheduled session, including missing slots.  The
    caller retains the real provider and known_at fields in the full state.  No
    price, Watch, Va or source-status field is synthesized by this boundary.
    """
    def __init__(self, runtime, session, watch_key):
        self.runtime = runtime
        self.day = _day(session)
        check(isinstance(watch_key, str) and bool(watch_key), "WATCH_ID_REQUIRED")
        self.path = runtime.namespace["PathBuilder"](watch_key)
        self.builder = runtime.namespace["FeatureBuilder"](runtime.schema)
        self.history_state = ([], [], None, None, None)

    def push(self, state, slot):
        ns = self.runtime.namespace
        check(isinstance(state, dict) and isinstance(slot, dict)
              and type(slot.get("scheduled_t")) is int, "FULL_STATE_AND_SLOT_REQUIRED")
        end = slot["scheduled_t"] + 540
        check(slot.get("bar_end") == ns["stamp"](self.day, end), "STATE_BAR_END_MISMATCH")
        ns["validate"](state, slot, self.path.endpoints[-1] if self.path.endpoints else None)
        old = len(self.path.events)
        endpoint = self.path._push(state, slot)
        events = self.path.events[old:]
        values = self.builder.push(state, endpoint, events, self.path.runs)
        updated = ns["update_history"](self.day, endpoint, events, end, *self.history_state)
        self.history_state = updated[:5]
        history = updated[5]
        numeric = [values[k.split("/", 1)[1]] if k.startswith("state/")
                   else history[k.split("/", 1)[1]] for k in ns["P1_NUM"]]
        numeric = self.runtime.np.asarray([self.runtime.np.nan if v is None else float(v) for v in numeric])
        categorical = [str(values[k.split("/", 1)[1]]) if k.startswith("state/")
                       else str(history[k.split("/", 1)[1]]) for k in ns["P1_CAT"][:-1]]
        return {"numeric": numeric, "categorical": categorical, "state_as_of_minute": end,
                "endpoint": deepcopy(endpoint), "source_status_assigned": False}
