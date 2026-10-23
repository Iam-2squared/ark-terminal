"""Generated monthly CSV.gz -> ordinary six CLI stages in separate processes."""
from __future__ import annotations
import csv
import gzip
import io
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any
from .artifact_io import exclusive_bytes, exclusive_json, sha_file
from .authority import Authority
from .contracts import ROOT, FLAGS, code_hash, configuration_hash, digest, registry
from .exact_math import V2Error
from .host_channel import JournalAuthority, channel_snapshot
from .native_fixture import fixture_authority, install_test_grant, request_for
from .source_adapter import CSV_ROUTES


def monthly_authority(root: Path) -> tuple[Authority, dict[str, Any]]:
    authority, manifest = fixture_authority(root)
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    profiles: dict[str, dict[str, Any]] = {}
    daily_fields = dict(zip(("open", "high", "low", "close", "volume", "turnover"), ("O", "H", "L", "C", "Vo", "Va")))
    for dataset in ("DAILY", "MASTER"):
        profiles[CSV_ROUTES[dataset]] = {"schema": "ARK_V2_TABULAR_SOURCE_PROFILE_V1", "dataset": dataset,
            "header": ["Date", "Code", *daily_fields.values()] if dataset == "DAILY" else ["Date", "Code"],
            "date_column": "Date", "symbol_column": "Code", "fields": daily_fields if dataset == "DAILY" else {},
            "units": ["JPY", "SHARES", "JPY"] if dataset == "DAILY" else ["IDENTITY"],
            "factors": {k: "1" for k in daily_fields} if dataset == "DAILY" else {}, "missing_tokens": [""],
            "identities": {}, "raw_suffixes": {}, "all_null_status": "NO_TRADE", "max_uncompressed_bytes": 10_000_000}
    # Factory owns these files: no caller input or existing original is read.
    for entry in manifest["entries"]:
        dataset, session = entry["dataset"], entry["session"]
        value = json.loads((authority.root / entry["path"]).read_text())
        profile = profiles[CSV_ROUTES[dataset]]
        identities = {}
        suffixes = {}
        rows = []
        for record in value["records"]:
            symbol = record["canonical_symbol"]
            source_symbol = "SOURCE_" + symbol  # Never infer security kind from a code suffix.
            identity = {"canonical_symbol": symbol, "rss_symbol": symbol + ".T", "market": "PRIME",
                        "security_kind": "COMMON_STOCK", "lot": 100, "rule_version": "ISOLATED_TEST_RULE_V1", "domestic": True, "cash": True}
            identities[source_symbol] = identity
            row = {"Date": session, "Code": source_symbol}
            if dataset == "DAILY":
                row.update({column: record[key] for key, column in daily_fields.items()})
                suffixes[source_symbol] = record["suffix"]
            rows.append(row)
        profile["identities"][session] = identities
        if dataset == "DAILY": profile["raw_suffixes"][session] = suffixes
        buckets.setdefault((dataset, session[:7]), []).extend(rows)
    pins = {}
    for (dataset, month), rows in buckets.items():
        profile = profiles[CSV_ROUTES[dataset]]
        text = io.StringIO(newline="")
        writer = csv.DictWriter(text, fieldnames=profile["header"], lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
        # A different, unapproved date has deliberately invalid prices. A
        # date-first parser never calls rational() for these poison fields.
        poison = {key: "UNAPPROVED_POISON" for key in profile["header"]}
        poison.update({"Date": "2099-12-31", "Code": "UNAPPROVED"}); writer.writerow(poison)
        path = dataset.lower() + "/monthly-" + month + ".csv.gz"
        exclusive_bytes(authority.root / path, gzip.compress(text.getvalue().encode(), mtime=0))
        pins[path] = sha_file(authority.root / path)
    entries = []
    for old in manifest["entries"]:
        entry = json.loads(json.dumps(old))
        path = entry["dataset"].lower() + "/monthly-" + entry["session"][:7] + ".csv.gz"
        sha, size = pins[path]
        entry.update({"path": path, "sha256": sha, "bytes": size, "format": CSV_ROUTES[entry["dataset"]]})
        entry["evidence"].update({"source_id": path, "source_sha256": sha,
            "source_contract_hash": digest(profiles[entry["format"]]), "transformation_version": "EXACT_APPROVED_TABULAR_SLICE_V1"})
        entry["original"].update({"source_id": path, "sha256": sha, "bytes": size})
        entries.append(entry)
    manifest = {"schema": "ARK_V2_NATIVE_MANIFEST_V1", "entries": entries}
    authority.fixture_pins = pins
    authority.manifest_pin = digest(manifest)
    authority.precommit.update({"manifest_sha256": authority.manifest_pin, "source_contracts": profiles,
        "source_routes": {"daily": CSV_ROUTES["DAILY"], "master": CSV_ROUTES["MASTER"], "optional": "SOURCE_NOT_JOINED"}})
    install_test_grant(authority, "B")
    return authority, manifest


def host_config(authority: Authority, journal: Path) -> dict[str, Any]:
    if not authority.test_only: raise V2Error("TEST_CONFIG_CANNOT_INSTALL_MARKET_CHANNEL")
    return {"schema": "ARK_V2_OS_OWNER_CHANNEL_V1", "worker_uid": os.getuid(),
            "source_root": str(authority.root), "output_root": str(authority.output), "journal_root": str(journal),
            "journal_namespace": digest(["ISOLATED_FACTORY", authority.manifest_pin, code_hash()]),
            "manifest_pin": authority.manifest_pin, "precommit": authority.precommit,
            "grants": {k: asdict(v) for k, v in authority.grants.items()}, "test_only": True,
            "fixture_pins": {k: list(v) for k, v in authority.fixture_pins.items()}}


def isolated_channel(config: dict[str, Any]) -> JournalAuthority:
    """Reconstruct the fixed factory to reject real rows relabelled synthetic."""
    with tempfile.TemporaryDirectory(prefix="v2-independent-factory-") as temporary:
        expected, manifest = monthly_authority(Path(temporary) / "fixed")
        if (config["fixture_pins"] != {k: list(v) for k, v in expected.fixture_pins.items()} or
                config["manifest_pin"] != digest(manifest)):
            raise V2Error("REAL_OR_CHANGED_ROWS_IN_ISOLATED_HOST_CHANNEL")
        pre = dict(config["precommit"])
        pre["census_receipt_sha256"] = None
        if pre != expected.precommit:
            raise V2Error("ISOLATED_FACTORY_PRECOMMIT_DRIFT")
    return channel_snapshot(config, isolated=True)


def run_monthly_fixture(output: Path) -> dict[str, Any]:
    authority, manifest = monthly_authority(output)
    journal = output / "independent-host-pins"; journal.mkdir(mode=0o700)
    process_ids = []
    def invoke(stage: str, mode: str, role: str = "FIT_CAL") -> dict[str, Any]:
        config = host_config(authority, journal)
        config_path = output / ("host-" + stage + ".json")
        request_path = output / ("request-" + stage + ".json")
        exclusive_json(config_path, config)
        exclusive_json(request_path, request_for(authority, manifest, mode, role))
        result = subprocess.run([sys.executable, str(ROOT / "tools/isolated_host_stage.py"),
            "--config", str(config_path), "--config-pin", sha_file(config_path)[0],
            "--stage", stage, "--request", str(request_path)], capture_output=True, text=True,
            timeout=240, env={**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        if result.returncode:
            raise V2Error("ISOLATED_MONTHLY_STAGE_FAILED:" + stage + ":" + result.stdout[-1000:] + result.stderr[-1000:])
        payload = json.loads(result.stdout)
        process_ids.append(payload["isolated_worker_pid"])
        return payload["result"]
    results = {"census": invoke("census", "B")}
    authority.precommit["census_receipt_sha256"] = digest(results["census"])
    install_test_grant(authority, "C")
    for stage in ("train", "calibrate"): results[stage] = invoke(stage, "C")
    for stage in ("predict", "evaluate", "restore-verify"): results[stage] = invoke(stage, "C", "VALIDATION")
    restored = channel_snapshot(host_config(authority, journal), isolated=True)
    events = list(restored.artifact_pins)
    receipt = {"schema": "ARK_V2_MONTHLY_HOST_ENGINEERING_RECEIPT_V1", "test_only": True,
        "market_approval_established": False, "code_hash": code_hash(), "config_hash": configuration_hash(),
        "schema_hash": digest(registry()), "separate_stage_processes": len(set(process_ids)),
        "entrypoint": "NORMAL_SIX_STAGE_CLI_WITH_OS_CHANNEL_TEST_DOUBLE",
        "input_route": "GENERATED_MONTHLY_CSV_GZIP_DATED_SLICE_G0_G1_G2_CORE95_TEACHERS",
        "durable_independent_pin_count": len(events), "isolated_candidate_reservations": sum("CANDIDATE_RESERVED" in k for k in events),
        "isolated_fit_starts": sum("FIT_STARTED" in k for k in events), "isolated_calibration_starts": sum("CAL_STARTED" in k for k in events),
        "restore_prediction_difference": results["restore-verify"]["prediction_max_abs_difference"],
        "validation_status": results["evaluate"]["status"], "final_status": "UNOPENED",
        "market_candidates": 0, "market_fits": 0, "market_calibrations": 0, **{f: False for f in FLAGS}}
    if receipt["separate_stage_processes"] != 6 or receipt["isolated_fit_starts"] != 2 or receipt["isolated_calibration_starts"] != 2:
        raise V2Error("ISOLATED_STAGE_PROCESS_OR_BUDGET_MISMATCH")
    exclusive_json(output / "monthly-host-receipt.json", receipt)
    return receipt
