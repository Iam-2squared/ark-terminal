"""Fail-closed pre-performance provenance checks for the R41 one-shot workflow.

This module does not import decision, labels, estimator, replay or evaluator code.
Its only inputs are source bytes, the frozen protocol and GitHub run metadata.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen


REPOSITORY = "Iam-2squared/ark-terminal"
BRANCH = "research/phase57-long-only-cash-equity"
EVIDENCE = "docs/evidence/phase57-comprehensive-exit-v1"
PROTOCOL_PATH = f"{EVIDENCE}/GEN2_PRECOMMIT_R41.json"
LAUNCH_PATH = f"{EVIDENCE}/GEN2_LAUNCH_R41.json"
CONTRACT_WORKFLOW = ".github/workflows/phase57-exit-gen2-contract-r41.yml"
FINITE_WORKFLOW = ".github/workflows/phase57-exit-gen2-r41.yml"
R35_SHA256 = "a12852e36f270e247a9a0bb7f0f7f618da934297c05f7c687fccb7ceade40434"
# One explicit pre-performance technical failure, independently audited before
# this repair. This is not a general retry/allowlist mechanism.
ZERO_FIT_FAILED_RUN_ID = 36233376942
ZERO_FIT_FAILED_SHA = "8ecad9f0fd412e9ceb9ed04cc1e691979ad60d99"
ZERO_FIT_ARTIFACT_ID = 10903576190
ZERO_FIT_ARTIFACT_SHA256 = "f4830ec87fc55c00de2397056e657fbba01f49f4d09b50ca381482e6fe0456b8"
ZERO_FIT_FAILED_STEP = "Verify launch authorization, exact source and prior CI"
ZERO_FIT_SKIPPED_STEPS = (
    "Install frozen estimator dependencies",
    "Restore immutable R35 observation preparation",
    "Prepare immutable features and isolated labels without model fitting",
    "Recheck latest HEAD and duplicate jobs immediately before fitting",
    "Gen2 finite fitting and causal replay — no selection or performance report",
    "Verify completion counts and deferred audit boundary",
)
SAFETY_KEYS = frozenset((
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
))
EXPOSURE = {
    "providerRequests": 0,
    "protectedPartitionsOpened": 0,
    "gen2PerformanceInspected": False,
    "gen2ModelFits": 0,
}


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_safety(value: dict) -> None:
    require(isinstance(value, dict) and set(value) == SAFETY_KEYS,
            "exact Safety9 keys are required")
    require(all(item is False for item in value.values()), "Safety9 must all be false")


def assert_exposure(value: dict) -> None:
    require(isinstance(value, dict), "exposure must be an object")
    for key, expected in EXPOSURE.items():
        require(key in value and type(value[key]) is type(expected) and value[key] == expected,
                f"pre-performance exposure mismatch: {key}")


def _local_module(root: Path, module: str) -> Path | None:
    relative = Path(*module.split("."))
    candidates = [relative.with_suffix(".py"), relative / "__init__.py"]
    # Existing Phase57 scripts support both `scripts.foo` and `foo` imports.
    if not module.startswith("scripts."):
        candidates += [Path("scripts") / item for item in candidates]
    for candidate in candidates:
        if (root / candidate).is_file():
            return candidate
    require(not module.startswith("scripts."), f"missing local dependency: {module}")
    return None


def source_manifest(root: Path) -> dict[str, str]:
    """Hash the full static local import closure, tests, protocol and workflows."""
    seeds = list((root / "scripts").glob("phase57_exit_gen2*_r41.py"))
    seeds += list((root / "scripts").glob("test_phase57_exit_gen2*_r41.py"))
    for filename in ("phase57_exit_failure_anatomy_r40.py", "test_phase57_exit_failure_anatomy_r40.py"):
        path = root / "scripts" / filename
        require(path.is_file(), f"required failure-anatomy source is absent: {filename}")
        seeds.append(path)
    require(any(path.name == "phase57_exit_gen2_runner_r41.py" for path in seeds),
            "finite runner is absent")
    require(any(path.name.startswith("test_") for path in seeds), "focused tests are absent")
    pending = [path.relative_to(root) for path in seeds]
    included: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in included:
            continue
        included.add(relative)
        tree = ast.parse((root / relative).read_text(encoding="utf-8"), str(relative))
        module_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                module_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = list(relative.with_suffix("").parts[:-1])
                    trim = node.level - 1
                    require(trim <= len(parts), f"invalid relative import in {relative}")
                    if trim:
                        parts = parts[:-trim]
                    base = ".".join(parts + ([base] if base else []))
                if base:
                    module_names.add(base)
                    # `from scripts import foo` imports a module, whereas
                    # `from scripts.foo import function` imports an attribute.
                    for alias in node.names:
                        candidate = ".".join((base, alias.name))
                        path = Path(*candidate.split(".")).with_suffix(".py")
                        if (root / path).is_file():
                            module_names.add(candidate)
            elif isinstance(node, ast.Call) and node.args:
                function = node.func
                dynamic = (isinstance(function, ast.Name) and function.id == "__import__") or (
                    isinstance(function, ast.Attribute) and function.attr == "import_module")
                if dynamic:
                    require(isinstance(node.args[0], ast.Constant)
                            and isinstance(node.args[0].value, str),
                            f"unresolved dynamic import in source closure: {relative}")
                    module_names.add(node.args[0].value)
        for module in sorted(module_names):
            local = _local_module(root, module)
            if local is not None and local not in included:
                pending.append(local)
    included.update(map(Path, (PROTOCOL_PATH, CONTRACT_WORKFLOW, FINITE_WORKFLOW)))
    return {path.as_posix(): file_sha256(root / path) for path in sorted(included)}


def validate_protocol(protocol: dict) -> tuple[int, int]:
    assert_safety(protocol["safety"])
    assert_exposure(protocol["exposure"])
    execution = protocol["execution"]
    candidates = execution["candidateCount"]
    fits = execution["expectedModelFitCount"]
    require(type(candidates) is int and candidates > 0, "candidate count must be positive integer")
    require(type(fits) is int and fits > 0, "fit count must be positive integer")
    require(len(protocol["candidates"]) == candidates, "candidate list count differs")
    require(len(protocol["predictionSpecs"]) == execution["predictionSpecCount"],
            "prediction spec count differs")
    require(fits == execution["predictionSpecCount"] * execution["heads"]
            * execution["entryArms"] * execution["folds"], "fit budget arithmetic differs")
    require(execution["runAB"] == "REPLAY_FROM_SINGLE_IMMUTABLE_PREDICTION_SET",
            "run A/B must reuse the single immutable prediction set")
    require(execution["scorecardPhase"] == "NEXT_WORK_AFTER_ARTIFACT_AUDIT",
            "scorecard/selection is deferred to next Work")
    return candidates, fits


def contract_receipt(root: Path) -> dict:
    protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    candidates, fits = validate_protocol(protocol)
    baseline_hashes = protocol["baselineSourceHashes"]
    require(isinstance(baseline_hashes, dict) and bool(baseline_hashes),
            "baseline source pins are required")
    for relative, expected in baseline_hashes.items():
        require(isinstance(relative, str) and isinstance(expected, str)
                and re.fullmatch(r"[0-9a-f]{64}", expected) is not None,
                "invalid baseline source pin")
        path = root / relative
        require(not Path(relative).is_absolute() and path.resolve().is_relative_to(root.resolve()),
                "baseline source pin escapes repository")
        require(path.is_file() and file_sha256(path) == expected,
                f"baseline source hash mismatch: {relative}")
    return {
        "schemaVersion": "phase57-exit-gen2-contract-ci-r41-v1",
        "status": "GEN2_PREFLIGHT_CONTRACT_PASS_NOT_PERFORMANCE_PASS",
        "executionHead": os.environ.get("GITHUB_SHA", "LOCAL_SYNTHETIC_ONLY"),
        "runId": os.environ.get("GITHUB_RUN_ID"),
        "protocolSha256": file_sha256(root / PROTOCOL_PATH),
        "sourceSha256": source_manifest(root),
        "baselineSourceHashesVerified": baseline_hashes,
        "candidateCount": candidates,
        "expectedModelFitCount": fits,
        "modelFitsPerformed": 0,
        "candidateReplaysPerformed": 0,
        "candidatePerformanceInspected": False,
        "safety": protocol["safety"],
        "exposure": protocol["exposure"],
    }


def github_get(endpoint: str):
    require(isinstance(endpoint, str) and endpoint.startswith("/")
            and not any(ord(char) < 32 or char == "\\" for char in endpoint),
            "invalid GitHub endpoint")
    parts = urlsplit(endpoint)
    require(not parts.scheme and not parts.netloc and not parts.fragment,
            "invalid GitHub endpoint")
    # /compare/<sha>...<sha> is legitimate GitHub syntax; only complete dot
    # segments are traversal. Decode the path to catch encoded dot segments.
    decoded = unquote(parts.path)
    require(not any(segment in (".", "..") for segment in decoded.split("/"))
            and "\\" not in decoded, "invalid GitHub endpoint")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/repos/{REPOSITORY}{endpoint}", headers=headers)
    with urlopen(request, timeout=45) as response:
        return json.load(response)


def _all_branch_runs(workflow: str, get) -> list[dict]:
    result = []
    for page in range(1, 101):
        response = get(f"/actions/workflows/{workflow}/runs?branch={quote(BRANCH, safe='')}"
                       f"&per_page=100&page={page}")
        batch = response["workflow_runs"]
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise ValueError("workflow run pagination limit reached; cannot establish no duplicates")


def verify_single_zero_fit_failure(get) -> dict:
    """Recheck the one audited failed launch before excluding it as a fit run."""
    run = get(f"/actions/runs/{ZERO_FIT_FAILED_RUN_ID}")
    require(run["id"] == ZERO_FIT_FAILED_RUN_ID and run["head_sha"] == ZERO_FIT_FAILED_SHA
            and run["path"] == FINITE_WORKFLOW and run["run_attempt"] == 1
            and run["status"] == "completed" and run["conclusion"] == "failure",
            "audited zero-fit run identity/status drift")
    result = get(f"/actions/runs/{ZERO_FIT_FAILED_RUN_ID}/jobs?filter=all&per_page=100")
    require(result["total_count"] == len(result["jobs"]) == 1, "audited zero-fit job count drift")
    job = result["jobs"][0]
    require(job["name"] == "finite-once" and job["status"] == "completed"
            and job["conclusion"] == "failure", "audited zero-fit job identity/status drift")
    steps = {step["name"]: step for step in job["steps"]}
    require(len(steps) == len(job["steps"]), "audited zero-fit duplicate step names")
    failed = steps.get(ZERO_FIT_FAILED_STEP, {})
    require(failed.get("status") == "completed" and failed.get("conclusion") == "failure",
            "audited zero-fit preflight failure unproven")
    for name in ZERO_FIT_SKIPPED_STEPS:
        step = steps.get(name, {})
        require(step.get("conclusion") == "skipped"
                and step.get("number", -1) > failed["number"],
                f"audited zero-fit step was not skipped: {name}")
    upload = steps.get("Preserve full reproducibility evidence and any partial failure", {})
    require(upload.get("conclusion") == "success", "audited zero-fit artifact upload not successful")
    artifact = get(f"/actions/artifacts/{ZERO_FIT_ARTIFACT_ID}")
    require(artifact["id"] == ZERO_FIT_ARTIFACT_ID
            and artifact["workflow_run"]["id"] == ZERO_FIT_FAILED_RUN_ID
            and artifact["expired"] is False
            and artifact["digest"] == f"sha256:{ZERO_FIT_ARTIFACT_SHA256}",
            "audited zero-fit artifact identity/digest drift")
    return {
        "status": "VERIFIED_ZERO_FIT_PREFLIGHT_FAILURE",
        "runId": ZERO_FIT_FAILED_RUN_ID, "executionHead": ZERO_FIT_FAILED_SHA,
        "runAttempt": 1, "failedStep": ZERO_FIT_FAILED_STEP,
        "skippedSteps": list(ZERO_FIT_SKIPPED_STEPS),
        "artifactId": ZERO_FIT_ARTIFACT_ID, "artifactSha256": ZERO_FIT_ARTIFACT_SHA256,
        "dataPreparationStarted": False, "modelFitsStarted": 0, "candidateReplaysStarted": 0,
        "exceptionScope": "THIS_SINGLE_AUDITED_RUN_ONLY_NO_PERFORMANCE_RESTART",
    }


def launch_receipt(root: Path, prerequisite: dict, get=github_get) -> dict:
    current = contract_receipt(root)
    launch = json.loads((root / LAUNCH_PATH).read_text(encoding="utf-8"))
    require(launch["schemaVersion"] == "phase57-exit-gen2-launch-r41-v1", "launch schema mismatch")
    require(launch["generation"] == "R41", "generation mismatch")
    assert_safety(launch["safety"])
    assert_exposure(launch["exposure"])
    current_sha = os.environ["GITHUB_SHA"]
    run_id = int(os.environ["GITHUB_RUN_ID"])
    require(os.environ["GITHUB_REPOSITORY"] == REPOSITORY, "repository mismatch")
    require(os.environ["GITHUB_REF"] == f"refs/heads/{BRANCH}", "branch mismatch")
    require(os.environ["GITHUB_RUN_ATTEMPT"] == "1", "one-shot job cannot be rerun")
    head = get(f"/git/ref/heads/{BRANCH}")["object"]["sha"]
    require(head == current_sha, "execution SHA is no longer branch HEAD")
    require(re.fullmatch(r"[0-9a-f]{40}", launch["precommitHead"]) is not None,
            "invalid precommit SHA")
    require(current_sha != launch["precommitHead"], "launch must follow successful precommit CI")
    for key in ("protocolSha256", "sourceSha256", "candidateCount", "expectedModelFitCount"):
        require(launch[key] == current[key] == prerequisite[key], f"source/contract identity mismatch: {key}")
    require(prerequisite["status"] == "GEN2_PREFLIGHT_CONTRACT_PASS_NOT_PERFORMANCE_PASS",
            "prerequisite receipt is not contract PASS")
    require(prerequisite["executionHead"] == launch["precommitHead"], "prerequisite receipt SHA mismatch")
    required_run_id = int(launch["requiredContractRunId"])
    require(int(prerequisite["runId"]) == required_run_id, "prerequisite receipt run mismatch")
    required_run = get(f"/actions/runs/{required_run_id}")
    require(required_run["head_sha"] == launch["precommitHead"], "prerequisite run SHA mismatch")
    require(required_run["path"] == CONTRACT_WORKFLOW, "wrong prerequisite workflow")
    require(required_run["status"] == "completed" and required_run["conclusion"] == "success",
            "required pre-performance CI is not successful")
    comparison = get(f"/compare/{launch['precommitHead']}...{current_sha}")
    require(comparison["status"] == "ahead" and comparison["behind_by"] == 0,
            "launch does not descend from precommit")
    require(comparison["ahead_by"] == 1, "launch must be the direct child of precommit")
    require(len(comparison.get("files", [])) < 300, "comparison truncated")
    changed = {item["filename"] for item in comparison["files"]}
    require(changed == {LAUNCH_PATH}, "launch commit must change only the launch marker")
    current_run = get(f"/actions/runs/{run_id}")
    require(current_run["head_sha"] == current_sha and current_run["path"] == FINITE_WORKFLOW,
            "current workflow metadata mismatch")
    zero_fit_failures = []
    for other in _all_branch_runs("phase57-exit-gen2-r41.yml", get):
        if int(other["id"]) == ZERO_FIT_FAILED_RUN_ID and int(other["id"]) != run_id:
            require(not zero_fit_failures, "audited zero-fit run listed more than once")
            zero_fit_failures.append(verify_single_zero_fit_failure(get))
            continue
        require(int(other["id"]) == run_id,
                f"another generation R41 heavy run exists: {other['id']}; explicit investigation required")
    for other in _all_branch_runs("phase57-exit-finite-r36.yml", get):
        require(other["status"] not in ("requested", "pending", "queued", "in_progress", "waiting"),
                f"legacy R36 performance job is active: {other['id']}")
    r35 = launch["r35Artifact"]
    require(r35["runId"] == 36220335998 and r35["id"] == 10899151845,
            "R35 artifact identity is not the immutable preparation artifact")
    require(r35["digestSha256"] == R35_SHA256, "R35 digest differs from the independently audited archive")
    artifact = get(f"/actions/artifacts/{r35['id']}")
    require(artifact["workflow_run"]["id"] == r35["runId"], "R35 artifact run mismatch")
    require(artifact["expired"] is False, "R35 artifact expired")
    require(artifact["digest"] == f"sha256:{r35['digestSha256']}", "R35 archive digest mismatch")
    r35_run = get(f"/actions/runs/{r35['runId']}")
    require(r35_run["status"] == "completed" and r35_run["conclusion"] == "success", "R35 run not successful")
    current.update({
        "schemaVersion": "phase57-exit-gen2-launch-verification-r41-v1",
        "status": "GEN2_LAUNCH_VERIFIED_FIT_NOT_STARTED",
        "precommitHead": launch["precommitHead"],
        "requiredContractRunId": required_run_id,
        "launchSha256": file_sha256(root / LAUNCH_PATH),
        "r35Artifact": r35,
        "sourceTreeUnchangedSinceRequiredCI": True,
        "duplicateGenerationRunCount": 0,
        "auditedZeroFitPriorRuns": zero_fit_failures,
        "legacyR36ActiveRunCount": 0,
    })
    return current


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("contract", "launch"), required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--contract-receipt", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    failure_path = args.out.with_suffix(".failure.json")
    require(not args.out.exists(), f"append-only evidence already exists: {args.out}")
    require(not failure_path.exists(), f"append-only failure evidence already exists: {failure_path}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    try:
        if args.mode == "contract":
            receipt = contract_receipt(args.root.resolve())
        else:
            require(args.contract_receipt is not None, "contract CI receipt is required")
            prerequisite = json.loads(args.contract_receipt.read_text(encoding="utf-8"))
            receipt = launch_receipt(args.root.resolve(), prerequisite)
        with args.out.open("x", encoding="utf-8") as output:
            output.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print(json.dumps({key: receipt[key] for key in (
            "status", "executionHead", "runId", "protocolSha256", "candidateCount", "expectedModelFitCount")},
            sort_keys=True), flush=True)
    except Exception as error:
        failed = {
            "schemaVersion": "phase57-exit-gen2-preflight-failure-r41-v1",
            "status": "PREFLIGHT_FAILED_FIT_NOT_STARTED",
            "executionHead": os.environ.get("GITHUB_SHA"),
            "runId": os.environ.get("GITHUB_RUN_ID"),
            "exceptionType": type(error).__name__,
            "error": str(error),
            "modelFitsPerformed": 0,
            "candidateReplaysPerformed": 0,
            "safety": {key: False for key in sorted(SAFETY_KEYS)},
            "exposure": EXPOSURE,
        }
        with failure_path.open("x", encoding="utf-8") as output:
            output.write(json.dumps(failed, indent=2, sort_keys=True) + "\n")
        raise


if __name__ == "__main__":
    main()
