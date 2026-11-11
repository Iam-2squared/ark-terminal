"""One explicitly approved retry of an unregistered, source-validation failure.

Stages an isolated, exactly derived bootstrap/operator. Installed runtime files,
the original one-shot Trade/PREOPEN claims, source receipts and broker settings
are never replaced. This is not a collector resume or an order retransmission.
The native controller, model preflight, source guards and LIVE service still run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

import no11_weekly_filtered_lineage as lineage
import no11_manual_reconnect_review as review

JST = timezone(timedelta(hours=9))
PLAN = "ARK_NO11_PRESTART_SOURCE_RETRY_PLAN_V1"
STAGE = "ARK_NO11_PRESTART_SOURCE_RETRY_STAGE_V1"
CLAIM = "ARK_NO11_PRESTART_SOURCE_RETRY_CLAIM_V1"
FAILURE = "NO11_BOOTSTRAP_SOURCE_EXPORT_OR_VALIDATION_FAILED"
BOOTSTRAPS = frozenset(("19f006b08f6687db0bfea67b9bd7519d77957ce4",
                       "011171c82c960e3b2a8f520439e3e609b2578607"))
OPERATORS = frozenset(("ea8441ae08d9918317f65db13d34ddebecd6eec5",
                      "75cdb60737ba9d238fba26cf8d04c89c49981bce",
                      "7dfe6c3fd9bbcf8f342ca81faf68c10437703c22",
                      "daec623ee9b86426ca228dd412fd28d6768354a1"))
CONTROLLER = "329dbb216025b31c629f6e5fcc64d628edf29e05"
RECOVERY = "8ded9d67f0b5187eaa1fa52bdd0d03aea0512fa8"
# Exact native families before/after the official same-run cleanup installer,
# each with or without the official collector READY-to-transport relay. Their
# new-run lock/check_new/prepare/preflight/register APIs are unchanged. This
# route requires no cleanup marker and never requests same-run resume. Keep
# each installed family intact; do not mix its controller and recovery module.
KNOWN_NATIVE_PAIRS = frozenset((
    (CONTROLLER, RECOVERY),
    ("f5dd7c5d6579da498eb1ce9471bc02292a297d1a", RECOVERY),
    ("5a2fe9f6eb785f66412cc4cd09015eb37966c58c",
     "8195a1f6970ccca71f1f382403d884447a113003"),
    ("d186384ef5040e55953caacf5deb9a23b8ba134f",
     "8195a1f6970ccca71f1f382403d884447a113003"),
))
WEEKLY = "b777b944379c7c6dda15eac10ddda5959ab181c8"
FUNDING = "ca466139b984c76ba9a2f2e1bf9cdf94385627e0"
SHA = re.compile(r"[a-f0-9]{64}\Z")
WRAPPER = (
    "from pathlib import Path\n"
    "import sys\n"
    "import core\n"
    "def approved_entry(*, allow_explicit_live):\n"
    "    return core.controller_main(Path(__file__).with_name('manifest.json'),\n"
    "                                allow_explicit_live=allow_explicit_live)\n"
    "if __name__ == '__main__':\n"
    "    allow_explicit_live = '--operator-approved-broker-live' in sys.argv[1:]\n"
    "    raise SystemExit(approved_entry(allow_explicit_live=allow_explicit_live))\n"
).encode("ascii")


def need(ok, reason):
    if not ok:
        raise ValueError("NO11_PRESTART_RETRY_" + reason)


def clock(now=None):
    value = now or datetime.now(JST)
    need(isinstance(value, datetime) and value.utcoffset() == timedelta(hours=9),
         "CLOCK_JST")
    return value


def instant(value):
    need(type(value) is str, "TIMESTAMP_TYPE")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(parsed.utcoffset() is not None, "TIMESTAMP_OFFSET")
    return parsed


def session_window(now):
    need("09:00:00" <= now.strftime("%H:%M:%S") < "15:20:00",
         "CURRENT_SESSION_WINDOW")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


def normalized(raw):
    return lineage.norm(raw)[1].encode("utf-8")


def blob(raw):
    raw = normalized(raw)
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def safe(value, *, directory=False, exists=True):
    need(isinstance(value, (str, Path)) and bool(str(value)), "PATH_TYPE")
    path = Path(value)
    need(path.is_absolute(), "ABSOLUTE_PATH")
    path = Path(os.path.abspath(path))
    for p in (path, *path.parents):
        if p.exists() or p.is_symlink():
            need(not p.is_symlink() and
                 not (getattr(p.lstat(), "st_file_attributes", 0) & 1024),
                 "REPARSE_PATH")
    if exists:
        need(path.is_dir() if directory else path.is_file(), "PATH_MISSING")
    return path


def read(path):
    raw = safe(path).read_bytes()
    need(0 < len(raw) <= 25_000_000, "FILE_SIZE")
    def unique(pairs):
        out = {}
        for key, value in pairs:
            need(key not in out, "DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    obj = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)
    need(type(obj) is dict, "JSON_OBJECT")
    return obj


def pin(path, sources):
    path = safe(path)
    sources[str(path)] = digest(path.read_bytes())
    return path


def create(path, raw):
    path = safe(path, exists=False)
    safe(path.parent, directory=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _unregistered(root, day):
    need(not (root / ("received-session-" + day + ".active.json")).exists(),
         "ACTIVE_SESSION_EXISTS")
    need(not (root / "bootstrap-recovery-required.json").exists(),
         "COLLECTOR_CLEANUP_STATE_EXISTS")
    runs = sorted(root.glob("session-" + day + "-*"))
    need(bool(runs), "SOURCE_FAILURE_RUN_MISSING")
    failures = []
    for run in runs:
        safe(run, directory=True)
        need(re.fullmatch("session-" + re.escape(day) + r"-[a-f0-9]{32}",
                          run.name) is not None, "RUN_IDENTITY")
        # This specific failure occurs before prepared inputs, a registered
        # session, inference database or any collector can be created.
        children = list(run.iterdir())
        need(len(children) == 1 and children[0].name == "controller-failure.json",
             "RUN_HAS_REGISTERED_OR_UNVERIFIED_STATE")
        failed = safe(children[0])
        obj = read(failed)
        need(obj.get("reason") == FAILURE and
             obj.get("productionReady") is False and
             obj.get("orderTransmission") is False, "NOT_SOURCE_EXPORT_FAILURE")
        failures.append(failed)
    return failures


def _audit(store, *, now=None, allow_claim=False):
    now = clock(now)
    session_window(now)
    day = now.date().isoformat()
    store = safe(store, directory=True)
    sources = {}
    settings_path = pin(store / "settings.json", sources)
    binding_path = pin(store / "automatic-inputs.json", sources)
    settings, binding = read(settings_path), read(binding_path)
    need(settings.get("schemaId") == "ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1"
         and settings.get("sameDayApprovalRequired") is True
         and settings.get("automaticOrderAuthorization") is False
         and settings.get("orderTransmission") is False
         and settings.get("normalMaxPositions") == 3, "SETTINGS_CONTRACT")
    need(binding.get("schemaId") == "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1"
         and binding.get("orderTransmission") is False, "BINDING_CONTRACT")
    engine = safe(binding["engine"], directory=True)
    python = safe(binding["python"])
    need(python.name.lower() == "python.exe", "PYTHON_EXECUTABLE")
    config_file = pin(settings["bootstrapConfigFile"], sources)
    config = read(config_file)
    need(config.get("schemaId") == "ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1"
         and config.get("sessionDate") == day
         and config.get("productionReady") is False
         and config.get("orderTransmission") is False
         and "shadowAccountConfig" not in config, "CURRENT_LIVE_BOOTSTRAP")
    private = safe(config["privateRoot"], directory=True)
    need(private != engine and engine not in private.parents, "PRIVATE_ROOT_SCOPE")
    marker = pin(store / ("TRADE-" + day + ".launch.json"), sources)
    trade = read(marker)
    need(trade.get("schemaId") == "ARK_NO11_UNIFIED_START_REQUEST_V1"
         and trade.get("kind") == "TRADE" and trade.get("asOfDate") == day
         and trade.get("externalBrokerApprovalStillRequired") is True
         and trade.get("sourceSha256") == sources[str(config_file)],
         "ORIGINAL_TRADE_BOOTSTRAP_IDENTITY")
    issued = instant(trade["operatorRequestedAtJst"])
    need(issued.date().isoformat() == day and
         issued.utcoffset() == timedelta(hours=9) and issued <= now,
         "ORIGINAL_TRADE_APPROVAL_TIME")
    reserve = pin(store / ("PREOPEN-" + day + ".request.json"), sources)
    pre_claim = pin(store / ("PREOPEN-" + day + ".execution-claimed"), sources)
    pre = read(reserve)
    nonce = pre.get("nonce")
    need(pre.get("schemaId") == "ARK_NO11_PREOPEN_STANDBY_REQUEST_V1"
         and pre.get("sessionDate") == day
         and pre.get("sameDayExplicitOrderApproval") is True
         and pre.get("orderTransmissionAtArm") is False
         and pre.get("tradeLaunchedAtArm") is False
         and type(nonce) is str and re.fullmatch(r"[a-f0-9]{32}", nonce)
         and pre_claim.read_text(encoding="utf-8-sig").strip() ==
             "PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|" + day + "|" + nonce,
         "ORIGINAL_PREOPEN_APPROVAL")
    claim = store / ("PRESTART-SOURCE-RETRY-" + day + ".claim.json")
    safe(claim, exists=False)
    need(allow_claim or not claim.exists(), "RETRY_ALREADY_CLAIMED")
    failures = _unregistered(private, day)
    for failed in failures:
        pin(failed, sources)
    broker_file = pin(config["brokerExecutionConfig"], sources)
    broker = read(broker_file)
    transport = broker.get("transport")
    ledger = broker.get("ledger")
    need(broker.get("schemaId") == "ARK_NO11_BROKER_EXECUTION_CONFIG_V1"
         and broker.get("sessionDate") == day
         and broker.get("evidenceMode") == "BROKER_OBSERVATION"
         and broker.get("productionReady") is False
         and broker.get("orderTransmission") is True
         and type(transport) is dict and type(ledger) is dict
         and type(ledger.get("maxSymbols")) is int and ledger["maxSymbols"] == 3
         and type(ledger.get("lotSize")) is int and ledger["lotSize"] == 100,
         "ORIGINAL_BROKER_CONFIG")
    terms = broker.get("orderTerms")
    need(broker.get("fundingPolicy") == "RSS_BUYING_POWER"
         and broker.get("feeCourse") == "ZERO"
         and ledger.get("allocatedCashJpy") == "AUTO_RSS_BUYING_POWER"
         and ledger.get("account") == "一般" and ledger.get("sessionDate") == day
         and type(terms) is dict and terms.get("orderType") == "MARKET"
         and terms.get("timeInForce") == "DAY" and terms.get("sor") is True
         and type(terms.get("accountType")) is int and terms["accountType"] == 1
         and terms.get("accountTypeVerified") is True
         and all(broker.get(key) in (None, "") for key in
                 ("securitiesCashEvidenceFile", "buyingPowerEvidenceFile")),
         "ORIGINAL_RSS_FUNDING_CONTRACT")
    need(transport.get("mode") == "LIVE" and transport.get("sessionDate") == day
         and transport.get("orderTransmission") is True
         and transport.get("operatorEnabled") is True
         and transport.get("approvedForSession") is True
         and type(transport.get("rssSessionKey")) is str
         and SHA.fullmatch(transport["rssSessionKey"])
         and type(transport.get("expectedExcelPid")) is int
         and transport["expectedExcelPid"] > 0, "ORIGINAL_TRANSPORT")
    need(instant(transport["expiresAtJst"]) > now, "TRANSPORT_EXPIRED")
    dispatch = safe(transport["dispatchDirectory"], directory=True)
    need(not any(dispatch.iterdir()), "DISPATCH_HISTORY_PRESENT")
    account = safe(settings["accountWorkbookPath"])
    order_book = safe(settings["orderIdWorkbookPath"])
    need(account != order_book
         and safe(config["orderIdWorkbookPath"]) == order_book
         and safe(transport["workbookPath"]) == order_book, "WORKBOOK_BINDING")
    required = {
        "bootstrap": "tools/no11_received_session_bootstrap.py",
        "controller": "tools/no11_received_session_controller.py",
        "recovery": "tools/no11_received_run_recovery.py",
        "weekly": "tools/no11_verified_weekly_shadow_scope.mjs",
        "operator": "windows/Run-No11ReceivedSessionOperatorLive.ps1",
        "observer": "windows/Observe-No11AccountReadOnly.ps1",
    }
    files = {key: pin(engine / value, sources) for key, value in required.items()}
    need(blob(files["bootstrap"].read_bytes()) in BOOTSTRAPS, "UNKNOWN_BOOTSTRAP_SOURCE")
    need(blob(files["operator"].read_bytes()) in OPERATORS, "UNKNOWN_OPERATOR_SOURCE")
    controller_blob = blob(files["controller"].read_bytes())
    recovery_blob = blob(files["recovery"].read_bytes())
    need(controller_blob in {pair[0] for pair in KNOWN_NATIVE_PAIRS},
         "UNKNOWN_CONTROLLER_SOURCE")
    need(recovery_blob in {pair[1] for pair in KNOWN_NATIVE_PAIRS},
         "UNKNOWN_RECOVERY_SOURCE")
    need((controller_blob, recovery_blob) in KNOWN_NATIVE_PAIRS,
         "NATIVE_SOURCE_PAIR_MISMATCH")
    need(blob(files["weekly"].read_bytes()) == WEEKLY, "NATIVE_WEEKLY_SOURCE_CHANGED")
    need(b"import no11_rss_buying_power as rss_funding" in files["bootstrap"].read_bytes()
         and b"No11RssFundingContract.ps1" in files["operator"].read_bytes(),
         "RSS_POLICY_RUNTIME_REQUIRED")
    if b"No11RssFundingContract.ps1" in files["operator"].read_bytes():
        helper = pin(engine / "windows/No11RssFundingContract.ps1", sources)
        need(blob(helper.read_bytes()) == FUNDING, "RSS_FUNDING_HELPER_CHANGED")
    # Retain the entire currently installed source set, including approved
    # local funding/EXIT fixes; reject concurrent edits before actual launch.
    for folder, extensions in ((engine / "tools", {".py", ".mjs"}),
                               (engine / "windows", {".ps1"})):
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() in extensions:
                pin(path, sources)
    for key in ("datedMaster", "precomputedChartReceipt", "precomputedG1Mask",
                "previousContext", "pinsFile"):
        if key in config:
            pin(config[key], sources)
    for name in config.get("previousCaptureFiles", []):
        pin(name, sources)
    for key in ("dailyRun", "weeklySourceRun", "runtimeRoot", "h235ModelRoot"):
        if key in config:
            safe(config[key], directory=True)
    return {
        "schemaId": PLAN, "sessionDate": day, "store": str(store),
        "engine": str(engine), "python": str(python),
        "bootstrapFile": str(config_file), "privateRoot": str(private),
        "brokerFile": str(broker_file), "operatorFile": str(files["operator"]),
        "observerFile": str(files["observer"]), "bootstrapSource": str(files["bootstrap"]),
        "controllerSource": str(files["controller"]),
        "accountWorkbookPath": str(account), "orderIdWorkbookPath": str(order_book),
        "failureRun": str(failures[-1].parent), "failureFile": str(failures[-1]),
        "failureFiles": [str(p) for p in failures], "claimFile": str(claim),
        "sources": sources, "transport": transport, "orderTransmission": False,
    }


def audit(store, *, now=None):
    """Read only. Eligible means source repair can be staged, not Trade started."""
    return _audit(store, now=now)


def _ps_string(value):
    value = str(value)
    need("\n" not in value and "\r" not in value and "\x00" not in value, "PS_PATH")
    return "'" + value.replace("'", "''") + "'"


def derive_operator(raw, plan, package):
    need(blob(raw) in OPERATORS, "UNKNOWN_OPERATOR_SOURCE")
    bom, text, newline = lineage.norm(raw)
    replacements = (
        ("$engine=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))",
         "$engine=" + _ps_string(plan["engine"])),
        ("$controller=Join-Path $engine 'tools\\no11_received_session_controller.py'",
         "$controller=" + _ps_string(package / "controller.py")),
        ("$observer=Join-Path $PSScriptRoot 'Observe-No11AccountReadOnly.ps1'",
         "$observer=" + _ps_string(plan["observerFile"])),
    )
    for before, after in replacements:
        need(text.count(before) == 1, "OPERATOR_ANCHOR_CHANGED")
        text = text.replace(before, after, 1)
    helper = ". (Join-Path $PSScriptRoot 'No11RssFundingContract.ps1')"
    if "No11RssFundingContract.ps1" in text:
        need(text.count(helper) == 1, "OPERATOR_FUNDING_ANCHOR_CHANGED")
        text = text.replace(helper, ". " + _ps_string(
            Path(plan["engine"]) / "windows/No11RssFundingContract.ps1"), 1)
    return bom + text.replace("\n", newline).encode("utf-8")


def stage(store, package_dir, *, now=None):
    """Create only a NEW isolated package. Never install or launch anything."""
    plan = audit(store, now=now)
    package = safe(package_dir, exists=False)
    safe(package.parent, directory=True)
    need(not package.exists() and
         Path(plan["engine"]) not in package.parents and
         package != Path(plan["engine"]), "NEW_ISOLATED_PACKAGE_REQUIRED")
    payloads = {
        "bootstrap.py": lineage.transform(safe(plan["bootstrapSource"]).read_bytes()),
        "controller.py": WRAPPER,
        "OperatorLive.ps1": derive_operator(safe(plan["operatorFile"]).read_bytes(),
                                           plan, package),
        "core.py": Path(__file__).resolve().read_bytes(),
        "no11_weekly_filtered_lineage.py": Path(lineage.__file__).resolve().read_bytes(),
        "no11_manual_reconnect_review.py": Path(review.__file__).resolve().read_bytes(),
    }
    package.mkdir(mode=0o700)
    for name, raw in payloads.items():
        create(package / name, raw)
    manifest = {
        "schemaId": STAGE, "sessionDate": plan["sessionDate"], "plan": plan,
        "packageDir": str(package), "manifestFile": str(package / "manifest.json"),
        "operatorScript": str(package / "OperatorLive.ps1"),
        "controllerScript": str(package / "controller.py"),
        "bootstrapScript": str(package / "bootstrap.py"),
        "files": {name: digest(raw) for name, raw in payloads.items()},
        "packageSources": {
            str(Path(__file__).resolve()): digest(payloads["core.py"]),
            str(Path(lineage.__file__).resolve()): digest(payloads["no11_weekly_filtered_lineage.py"]),
            str(Path(review.__file__).resolve()): digest(payloads["no11_manual_reconnect_review.py"]),
        },
        "originalRuntimeModified": False, "tradeLaunched": False,
        "orderTransmission": False,
    }
    create(package / "manifest.json", encode(manifest))
    verify_manifest(package / "manifest.json", now=now)
    return manifest


def verify_manifest(manifest_file, *, now=None, allow_claim=False):
    manifest_file = safe(manifest_file)
    obj = read(manifest_file)
    need(obj.get("schemaId") == STAGE and obj.get("orderTransmission") is False
         and obj.get("originalRuntimeModified") is False, "MANIFEST_CONTRACT")
    package = safe(obj["packageDir"], directory=True)
    need(manifest_file == package / "manifest.json" and
         obj.get("manifestFile") == str(manifest_file), "MANIFEST_PATH")
    plan = obj["plan"]
    current = _audit(plan["store"], now=now, allow_claim=allow_claim)
    need(current == plan and obj.get("sessionDate") == plan["sessionDate"],
         "ORIGINAL_STATE_CHANGED")
    expected_names = {"bootstrap.py", "controller.py", "OperatorLive.ps1", "core.py",
                      "no11_weekly_filtered_lineage.py", "no11_manual_reconnect_review.py"}
    need(type(obj.get("files")) is dict and set(obj["files"]) == expected_names,
         "PACKAGE_FILE_SET")
    for name, checksum in obj["files"].items():
        need(digest(safe(package / name).read_bytes()) == checksum, "PACKAGE_CHANGED")
    copies = {
        "no11_prestart_source_retry.py": "core.py",
        "no11_weekly_filtered_lineage.py": "no11_weekly_filtered_lineage.py",
        "no11_manual_reconnect_review.py": "no11_manual_reconnect_review.py",
    }
    origins = obj.get("packageSources")
    need(type(origins) is dict and len(origins) == len(copies), "PACKAGE_SOURCE_SET")
    origin_paths = [safe(path) for path in origins]
    need({p.name for p in origin_paths} == set(copies)
         and len({p.parent for p in origin_paths}) == 1, "PACKAGE_SOURCE_SET")
    running_core = safe(Path(__file__).resolve())
    origin_core = next(p for p in origin_paths if p.name == "no11_prestart_source_retry.py")
    need(running_core in (origin_core, package / "core.py"), "CORE_ENTRY_IDENTITY")
    for original in origin_paths:
        raw = original.read_bytes()
        copy = package / copies[original.name]
        need(digest(raw) == origins[str(original)]
             and raw == copy.read_bytes(), "PACKAGE_SOURCE_CHANGED")
    need((package / "bootstrap.py").read_bytes() ==
         lineage.transform(safe(plan["bootstrapSource"]).read_bytes()),
         "BOOTSTRAP_DERIVATION_CHANGED")
    need((package / "controller.py").read_bytes() == WRAPPER, "CONTROLLER_WRAPPER_CHANGED")
    need((package / "OperatorLive.ps1").read_bytes() ==
         derive_operator(safe(plan["operatorFile"]).read_bytes(), plan, package),
         "OPERATOR_DERIVATION_CHANGED")
    need(obj["operatorScript"] == str(package / "OperatorLive.ps1") and
         obj["controllerScript"] == str(package / "controller.py") and
         obj["bootstrapScript"] == str(package / "bootstrap.py"), "STAGED_ENTRY_PATH")
    return obj


def audit_broker(plan, observation, *, now=None):
    now = clock(now)
    need(plan.get("schemaId") == PLAN and plan.get("sessionDate") == now.date().isoformat(),
         "BROKER_PLAN_SESSION")
    ext = review.observation_ok(observation, plan["sessionDate"], now)
    for key in ("orders", "executions", "positions", "idRows"):
        need(type(ext.get(key)) is list and not ext[key], "BROKER_HISTORY_NOT_EMPTY")
    session = ext.get("excelSession")
    transport = plan["transport"]
    need(type(session) is dict
         and type(session.get("processId")) is int
         and session["processId"] == transport["expectedExcelPid"]
         and session.get("sessionKey") == transport["rssSessionKey"]
         and instant(session["startedAtUtc"]) == instant(transport["expectedExcelStartedAt"]),
         "BROKER_EXCEL_SESSION_CHANGED")
    for field, key in (("accountWorkbookIdentity", "accountWorkbookPath"),
                       ("orderIdWorkbookIdentity", "orderIdWorkbookPath")):
        need(session.get(field) == digest(str(safe(plan[key])).lower().encode("utf-8")),
             "BROKER_WORKBOOK_IDENTITY")
    need(session["startedAtUtc"].endswith("Z")
         and session["sessionKey"] == digest((str(session["processId"]) + "\n" +
             session["startedAtUtc"] + "\n" + session["accountWorkbookIdentity"] + "\n" +
             session["orderIdWorkbookIdentity"]).encode("utf-8")),
         "BROKER_SESSION_KEY_DERIVATION")
    need(instant(transport["expiresAtJst"]) > now, "TRANSPORT_EXPIRED")
    return {"sessionDate": plan["sessionDate"], "brokerOrders": 0, "brokerExecutions": 0,
            "brokerPositions": 0, "rssOrderIds": 0, "brokerObservationVerified": True,
            "orderTransmission": False}


def _fresh_proof(proof, schema, day, now):
    need(proof.get("schemaId") == schema and proof.get("sessionDate") == day
         and proof.get("orderTransmission") is False, "PROOF_CONTRACT")
    at = instant(proof["observedAtJst"])
    need(at.utcoffset() == timedelta(hours=9) and at.date().isoformat() == day
         and 0 <= (now - at).total_seconds() <= 90, "PROOF_NOT_FRESH")


def audit_proofs(plan, process, transport, *, now=None):
    now = clock(now)
    day = plan["sessionDate"]
    _fresh_proof(process, "ARK_NO11_PRESTART_RETRY_PROCESS_V1", day, now)
    need(process.get("enumerationSucceeded") is True
         and type(process.get("matchingWorkers")) is int and process["matchingWorkers"] == 0
         and type(process.get("unreadableWorkers")) is int and process["unreadableWorkers"] == 0
         and type(process.get("oneClickProcesses")) is int and process["oneClickProcesses"] == 0
         and type(process.get("checkerPid")) is int and process["checkerPid"] > 0,
         "PROCESS_OVERLAP_OR_UNVERIFIED")
    _fresh_proof(transport, "ARK_NO11_PRESTART_RETRY_TRANSPORT_V1", day, now)
    original = plan["transport"]
    need(transport.get("registeredThreeBooksVerified") is True
         and transport.get("controlCellsVerified") is True
         and transport.get("triggerZero") is True
         and transport.get("excelPid") == original["expectedExcelPid"]
         and str(transport.get("excelHwnd")) == str(original["expectedExcelHwnd"])
         and transport.get("rssSessionKey") == original["rssSessionKey"]
         and instant(transport["excelStartedAtUtc"]) == instant(original["expectedExcelStartedAt"]),
         "PHYSICAL_SESSION_UNVERIFIED")


def claim(manifest_file, observation_file, process_proof_file, transport_proof_file,
          *, operator_approved=False, now=None):
    now = clock(now)
    need(operator_approved is True, "EXPLICIT_RETRY_APPROVAL_REQUIRED")
    manifest_file = safe(manifest_file)
    manifest = verify_manifest(manifest_file, now=now)
    plan = manifest["plan"]
    observation_file = safe(observation_file)
    process_proof_file = safe(process_proof_file)
    transport_proof_file = safe(transport_proof_file)
    audit_broker(plan, read(observation_file), now=now)
    audit_proofs(plan, read(process_proof_file), read(transport_proof_file), now=now)
    record = {
        "schemaId": CLAIM, "sessionDate": plan["sessionDate"],
        "operatorApproved": True, "approvedAtJst": now.isoformat(),
        "manifestFile": str(manifest_file), "manifestSha256": digest(manifest_file.read_bytes()),
        "observationFile": str(observation_file),
        "observationSha256": digest(observation_file.read_bytes()),
        "processProofFile": str(process_proof_file),
        "processProofSha256": digest(process_proof_file.read_bytes()),
        "transportProofFile": str(transport_proof_file),
        "transportProofSha256": digest(transport_proof_file.read_bytes()),
        "originalMarkersPreserved": True, "originalRuntimeModified": False,
        "priorRegisteredRunAbsent": True, "previousOrdersResent": False,
        "orderTransmission": False,
    }
    # CreateNew is a permanent attempt reservation, even if process start fails.
    create(plan["claimFile"], encode(record))
    return {"schemaId": CLAIM, "status": "CLAIMED_ONCE",
            "claimFile": plan["claimFile"], "operatorScript": manifest["operatorScript"],
            "controllerScript": manifest["controllerScript"],
            "bootstrapFile": plan["bootstrapFile"], "python": plan["python"],
            "accountWorkbookPath": plan["accountWorkbookPath"],
            "orderIdWorkbookPath": plan["orderIdWorkbookPath"],
            "orderTransmission": False}


def verify_claim(manifest_file, *, now=None):
    now = clock(now)
    manifest_file = safe(manifest_file)
    manifest = verify_manifest(manifest_file, now=now, allow_claim=True)
    plan = manifest["plan"]
    record = read(plan["claimFile"])
    need(record.get("schemaId") == CLAIM and record.get("sessionDate") == plan["sessionDate"]
         and record.get("operatorApproved") is True
         and record.get("manifestFile") == str(manifest_file)
         and record.get("manifestSha256") == digest(manifest_file.read_bytes())
         and record.get("originalMarkersPreserved") is True
         and record.get("originalRuntimeModified") is False
         and record.get("priorRegisteredRunAbsent") is True
         and record.get("previousOrdersResent") is False
         and record.get("orderTransmission") is False, "CLAIM_CONTRACT")
    approved = instant(record["approvedAtJst"])
    need(approved.utcoffset() == timedelta(hours=9)
         and 0 <= (now - approved).total_seconds() <= 90, "CLAIM_NOT_FRESH")
    documents = {}
    for name in ("observation", "processProof", "transportProof"):
        source = safe(record[name + "File"])
        need(digest(source.read_bytes()) == record[name + "Sha256"], "CLAIM_EVIDENCE_CHANGED")
        documents[name] = read(source)
    audit_broker(plan, documents["observation"], now=now)
    audit_proofs(plan, documents["processProof"], documents["transportProof"], now=now)
    return manifest


def controller_entry(manifest_file, argv=None):
    """Only the derived original operator invokes this, after a fresh claim."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--operator-approved-broker-live", action="store_true")
    args = parser.parse_args(argv)
    need(os.name == "nt", "WINDOWS_LIVE_REQUIRED")
    need(args.operator_approved_broker_live is True, "OPERATOR_LIVE_APPROVAL_REQUIRED")
    manifest = verify_claim(manifest_file)
    plan = manifest["plan"]
    need(safe(args.config) == safe(plan["bootstrapFile"]), "ORIGINAL_CONFIG_REQUIRED")
    package = safe(manifest["packageDir"], directory=True)
    create(package / "controller-entry.claimed", encode({
        "schemaId": "ARK_NO11_PRESTART_RETRY_CONTROLLER_ENTRY_V1",
        "sessionDate": plan["sessionDate"], "processId": os.getpid(),
        "originalClaimSha256": digest(safe(plan["claimFile"]).read_bytes()),
        "orderTransmission": False,
    }))
    tools = safe(Path(plan["engine"]) / "tools", directory=True)
    sys.path.insert(0, str(tools))
    spec = importlib.util.spec_from_file_location(
        "ark_verified_prestart_bootstrap", manifest["bootstrapScript"])
    need(spec is not None and spec.loader is not None, "BOOTSTRAP_LOADER")
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    bootstrap.HERE = tools
    bootstrap.WINDOWS = safe(Path(plan["engine"]) / "windows", directory=True)
    import no11_received_session_controller as controller
    need(safe(controller.__file__) == safe(plan["controllerSource"]),
         "CONTROLLER_IMPORT_IDENTITY")
    raw, _ = bootstrap.load_json(args.config, 100_000)
    config = bootstrap.validate_config(raw, allow_explicit_live=True)
    # Native controller repeats its exclusive service lock, existing-run check,
    # original model/source preflight and registration before any collector.
    controller.execute(config, bootstrap, allow_explicit_live=True)


def blocked_reason(exc):
    message = str(exc)
    return message if re.fullmatch(r"(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]+", message) else \
        "NO11_PRESTART_RETRY_SOURCE_OR_IO_UNVERIFIED"


def controller_main(manifest_file, *, allow_explicit_live=False):
    """Keep native exit codes and redact private runtime exception details."""
    try:
        need(allow_explicit_live is True, "OPERATOR_LIVE_APPROVAL_REQUIRED")
        controller_entry(manifest_file)
        print("NO11_LIVE_OPERATOR_MODE=EXPLICIT_SESSION_ONLY", flush=True)
        return 0
    except KeyboardInterrupt:
        print("NO11_BOOTSTRAP_STOP=USER_INTERRUPT_READONLY", flush=True)
        return 130
    except Exception as exc:
        print(blocked_reason(exc), file=sys.stderr, flush=True)
        return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    audit_args = commands.add_parser("audit")
    audit_args.add_argument("--store", type=Path, required=True)
    stage_args = commands.add_parser("stage")
    stage_args.add_argument("--store", type=Path, required=True)
    stage_args.add_argument("--package-dir", type=Path, required=True)
    claim_args = commands.add_parser("claim")
    for key in ("manifest", "observation", "process-proof", "transport-proof"):
        claim_args.add_argument("--" + key, type=Path, required=True)
    claim_args.add_argument("--operator-approved", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.mode == "audit":
            value = audit(args.store)
        elif args.mode == "stage":
            value = stage(args.store, args.package_dir)
        else:
            value = claim(args.manifest, args.observation, args.process_proof,
                          args.transport_proof, operator_approved=args.operator_approved)
        print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "reason": blocked_reason(exc),
                          "orderTransmission": False}, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
