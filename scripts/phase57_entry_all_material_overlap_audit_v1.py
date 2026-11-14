#!/usr/bin/env python3
"""Audit whether an existing causal feature export can join to the 2,155 Entry ledger.

Inventory/lineage tooling only. It never fits a model, selects a threshold, or changes an
Entry decision. Output is restricted to identifier schema, join cardinalities, feature
coverage, and safety/lineage assertions.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import re
from pathlib import Path

SAFETY_KEYS = (
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
)
FORBIDDEN_OUTPUT_TOKENS = (
    "outcome", "oracle", "mfe", "mae", "return", "pnl", "profit", "high", "low",
)


def read_json(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_symbol(value):
    if value is None:
        return None
    s = str(value).strip().upper()
    s = re.sub(r"\.(T|JP)$", "", s)
    return s or None


def norm_date(value):
    if value is None:
        return None
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", str(value).strip())
    return m.group(1) if m else None


def norm_timestamp(value):
    if value is None:
        return None
    s = str(value).strip()
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat()
    except ValueError:
        pass
    m = re.search(r"(20\d{2}-\d{2}-\d{2})[ T](\d{2}):(\d{2})", s)
    return f"{m.group(1)}T{m.group(2)}:{m.group(3)}" if m else None


def public_keys(row):
    return sorted(k for k in row if not any(t in k.lower() for t in FORBIDDEN_OUTPUT_TOKENS))


def first_value(row, keys):
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def identifiers(row):
    raw_id = first_value(row, ("opportunity", "opportunityId", "eventId", "selectorEventId", "id"))
    session = first_value(row, ("sessionDate", "session", "date", "tradingDate"))
    symbol = first_value(row, ("symbol", "code", "ticker"))
    timestamp = first_value(row, (
        "decisionTimestamp", "selectorTimestamp", "selectionTimestamp", "selectedAt",
        "opportunityTimestamp", "timestamp", "minute",
    ))
    text = str(raw_id or "")
    if session is None:
        session = norm_date(text)
    if timestamp is None:
        timestamp = norm_timestamp(text)
    if symbol is None and "|" in text:
        symbol = text.rsplit("|", 1)[-1]
    return {
        "rawId": str(raw_id) if raw_id is not None else None,
        "session": norm_date(session),
        "symbol": norm_symbol(symbol),
        "timestamp": norm_timestamp(timestamp),
    }


def feature_coverage(feature_rows):
    names = sorted({k for row in feature_rows for k in row.get("values", {})})
    out = {}
    n = len(feature_rows)
    for name in names:
        available = sum(row.get("values", {}).get(name) is not None for row in feature_rows)
        reasons = collections.Counter(
            row.get("reasons", {}).get(name, "UNSPECIFIED")
            for row in feature_rows if row.get("values", {}).get(name) is None
        )
        out[name] = {
            "available": available,
            "missing": n - available,
            "coveragePct": 100 * available / n if n else None,
            "missingReasons": dict(sorted(reasons.items())),
        }
    return out


def audit(opportunities, feature_rows, export_audit, opportunity_sha, feature_sha, artifact_digest):
    if len(opportunities) != 2155:
        raise ValueError(f"OPPORTUNITY_POPULATION:{len(opportunities)}")
    if export_audit.get("rows") != len(feature_rows):
        raise ValueError("FEATURE_ROW_COUNT_MISMATCH")
    if any(export_audit.get(k) != 0 for k in ("providerRequests", "freshAccess", "oosAccess")):
        raise ValueError("SOURCE_BOUNDARY_VIOLATION")
    safety = export_audit.get("safety", {})
    if any(safety.get(key) is not False for key in SAFETY_KEYS):
        raise ValueError("SAFETY_NOT_FALSE")

    opp_ids = [identifiers(row) for row in opportunities]
    feat_ids = [identifiers(row) for row in feature_rows]

    def keys_for(rows, fields):
        values = []
        for row in rows:
            key = tuple(row.get(f) for f in fields)
            if all(v is not None for v in key):
                values.append(key)
        return values

    joins = {}
    for name, fields in (
        ("rawId", ("rawId",)),
        ("sessionSymbol", ("session", "symbol")),
        ("sessionSymbolTimestamp", ("session", "symbol", "timestamp")),
    ):
        a, b = keys_for(opp_ids, fields), keys_for(feat_ids, fields)
        ca, cb = collections.Counter(a), collections.Counter(b)
        shared = set(ca) & set(cb)
        joins[name] = {
            "fields": list(fields),
            "opportunityRowsWithCompleteKey": len(a),
            "featureRowsWithCompleteKey": len(b),
            "sharedKeys": len(shared),
            "matchedOpportunityRows": sum(ca[k] for k in shared),
            "matchedFeatureRows": sum(cb[k] for k in shared),
            "oneToOneSharedKeys": sum(ca[k] == 1 and cb[k] == 1 for k in shared),
            "opportunityDuplicateRowsOnKey": sum(v - 1 for v in ca.values() if v > 1),
            "featureDuplicateRowsOnKey": sum(v - 1 for v in cb.values() if v > 1),
        }

    sample = opportunities[0] if opportunities else {}
    return {
        "id": "PHASE57_ENTRY_ALL_MATERIAL_CAUSAL_FEATURE_OVERLAP_AUDIT_V1",
        "scope": "identifier/coverage audit only; no model fit, prediction, threshold selection or Entry decision",
        "opportunityPopulation": len(opportunities),
        "featureExportRows": len(feature_rows),
        "featureExportSessions": len({row.get("sessionDate") for row in feature_rows}),
        "opportunityInputSHA256": opportunity_sha,
        "featureMatrixSHA256": feature_sha,
        "featureArtifactDigest": artifact_digest,
        "featureSourceHead": export_audit.get("sourceHead"),
        "opportunityTopLevelKeysRedacted": public_keys(sample),
        "identifierCompleteness": {
            side: {field: sum(row.get(field) is not None for row in rows) for field in ("rawId", "session", "symbol", "timestamp")}
            for side, rows in (("opportunity", opp_ids), ("feature", feat_ids))
        },
        "joinDiagnostics": joins,
        "featureCoverage": feature_coverage(feature_rows),
        "lineage": {
            "providerRequests": export_audit.get("providerRequests"),
            "freshAccess": export_audit.get("freshAccess"),
            "oosAccess": export_audit.get("oosAccess"),
            "modelFit": export_audit.get("modelFit"),
            "modelPrediction": export_audit.get("modelPrediction"),
        },
        "safety": {key: False for key in SAFETY_KEYS},
        "decisionOutputsCreated": 0,
        "performanceMetricsRead": 0,
        "featureAdmissionAutomatic": False,
    }


def self_test():
    opportunities = [
        {"opportunity": "2024-09-17|2024-09-17T09:30:00+09:00|1111", "session": "2024-09-17", "symbol": "1111.T"},
        {"opportunity": "x2", "session": "2024-09-17", "symbol": "2222.T", "decisionTimestamp": "2024-09-17T10:00:00+09:00"},
    ] * 1077
    opportunities.append({"opportunity": "last", "session": "2024-09-18", "symbol": "4444.T"})
    feature_rows = [
        {"eventId": "2024-09-17|2024-09-17T09:30:00+09:00|1111", "sessionDate": "2024-09-17", "symbol": "1111", "decisionTimestamp": "2024-09-17T09:30:00+09:00", "values": {"x": 1}},
        {"eventId": "z", "sessionDate": "2024-09-17", "symbol": "3333", "decisionTimestamp": "2024-09-17T10:00:00+09:00", "values": {"x": None}, "reasons": {"x": "MISSING"}},
    ]
    export = {"rows": 2, "providerRequests": 0, "freshAccess": 0, "oosAccess": 0, "modelFit": 0, "modelPrediction": 0,
              "safety": {key: False for key in SAFETY_KEYS}, "sourceHead": "test"}
    out = audit(opportunities, feature_rows, export, "opp", "feat", "artifact")
    assert out["opportunityPopulation"] == 2155
    assert out["featureCoverage"]["x"]["available"] == 1
    assert out["decisionOutputsCreated"] == 0
    assert out["performanceMetricsRead"] == 0
    print(json.dumps({"syntheticTests": 4, "passed": 4, "modelFits": 0, "modelPredictions": 0}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--opportunities")
    p.add_argument("--feature-matrix")
    p.add_argument("--export-audit")
    p.add_argument("--artifact-digest", default="")
    p.add_argument("--output")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test(); return
    opp_path, feature_path, audit_path = map(Path, (args.opportunities, args.feature_matrix, args.export_audit))
    result = audit(read_json(opp_path), read_json(feature_path), read_json(audit_path),
                   sha256(opp_path), sha256(feature_path), args.artifact_digest)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "opportunities": result["opportunityPopulation"],
                      "featureRows": result["featureExportRows"], "performanceMetricsRead": 0,
                      "decisionOutputsCreated": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
