from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

SAFETY = {
    "phase": "58.p17.prospective-session-runner",
    "mode": "READ_ONLY_PHASE57_PLUS_MICROSTRUCTURE_ORCHESTRATION",
    "researchOnly": True,
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "rssOrderFunctionAllowed": False,
    "liveTradingAllowed": False,
    "paperTradingAllowed": False,
    "automaticPromotionAllowed": False,
    "productionUpdateAllowed": False,
    "overnightHoldingAllowed": False,
    "transmitted": False,
    "freshHoldoutConsumed": False,
}

SNAPSHOT_FRESHNESS_MARGIN_SECONDS = 20.0
MIN_MICROSTRUCTURE_SAMPLES_PER_CYCLE = 20
SOURCE_BAR_DURATION_MINUTES = 5.0


def build_cycle_commands(
    *,
    python_exe: str,
    node_exe: str,
    symbol: str,
    sheet: str,
    history_pack: str,
    current_prefix: str,
    snapshot: str,
    output: str,
    interval_seconds: float,
    samples_per_cycle: int,
    phase57_max_age_seconds: float,
    reusable_target: bool,
    workbook: str | None = None,
) -> list[list[str]]:
    export = [
        python_exe,
        "tools/phase58_excel_5m_chart_export.py",
        "--symbol", symbol,
        "--sheet", sheet,
        "--output", current_prefix,
    ]
    if workbook:
        export.extend(["--workbook", workbook])

    snapshot_cmd = [
        node_exe,
        "tools/phase58_phase57_prospective_snapshot.mjs",
        "--history-pack", history_pack,
        "--current-prefix", current_prefix,
        "--output", snapshot,
    ]
    if reusable_target:
        snapshot_cmd.append("--reusable-target")

    capture = [
        python_exe,
        "tools/phase58_excel_synchronized_capture.py",
        "--phase57-snapshot-file", snapshot,
        "--output", output,
        "--interval-seconds", str(interval_seconds),
        "--samples", str(samples_per_cycle),
        "--phase57-max-age-seconds", str(phase57_max_age_seconds),
    ]
    if workbook:
        capture.extend(["--workbook", workbook])
    return [export, snapshot_cmd, capture]


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _snapshot_freshness_boundary(snapshot_path: Path) -> datetime:
    parsed = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot = parsed.get("snapshot") if isinstance(parsed, dict) and isinstance(parsed.get("snapshot"), dict) else parsed
    if not isinstance(snapshot, dict):
        raise RuntimeError("Phase57 snapshot file must contain a JSON object or {snapshot:{...}}")

    as_of = _parse_iso(snapshot.get("asOf"))
    if as_of is None:
        raise RuntimeError("Phase57 snapshot asOf must be a valid ISO timestamp")
    context = snapshot.get("context") if isinstance(snapshot.get("context"), dict) else {}
    close_raw = context.get("sourceBarCloseAt")
    if close_raw in (None, ""):
        return as_of

    close_at = _parse_iso(close_raw)
    if close_at is None:
        raise RuntimeError("Phase57 snapshot sourceBarCloseAt must be a valid ISO timestamp")
    try:
        duration = float(context.get("sourceBarDurationMinutes"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Phase57 snapshot sourceBarDurationMinutes must be numeric") from exc
    if duration != SOURCE_BAR_DURATION_MINUTES:
        raise RuntimeError("Phase57 prospective sourceBarDurationMinutes must remain exactly 5")
    if abs((close_at - as_of).total_seconds() - duration * 60.0) > 1e-6:
        raise RuntimeError("Phase57 snapshot sourceBarCloseAt does not match asOf + sourceBarDurationMinutes")
    return close_at


def freshness_adjusted_samples(
    *,
    snapshot_path: Path,
    requested_samples: int,
    interval_seconds: float,
    max_age_seconds: float,
    now: datetime | None = None,
    safety_margin_seconds: float = SNAPSHOT_FRESHNESS_MARGIN_SECONDS,
) -> dict[str, float | int | str | bool]:
    freshness_at = _snapshot_freshness_boundary(snapshot_path)
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_seconds = (now_utc - freshness_at).total_seconds()
    if age_seconds < 0:
        raise RuntimeError("Phase57 snapshot freshness boundary is in the future")

    remaining_seconds = max_age_seconds - age_seconds
    usable_seconds = remaining_seconds - safety_margin_seconds
    max_samples = 0 if usable_seconds < 0 else math.floor(usable_seconds / interval_seconds) + 1
    actual_samples = max(0, min(requested_samples, max_samples))
    capture_span_seconds = interval_seconds * max(0, actual_samples - 1)
    return {
        "freshnessAsOf": freshness_at.isoformat().replace("+00:00", "Z"),
        "ageSeconds": age_seconds,
        "remainingSeconds": remaining_seconds,
        "safetyMarginSeconds": safety_margin_seconds,
        "requestedSamples": requested_samples,
        "maxSamplesWithinBudget": max_samples,
        "actualSamples": actual_samples,
        "adjusted": actual_samples != requested_samples,
        "captureSpanSeconds": capture_span_seconds,
    }


def _set_option(command: list[str], name: str, value: object) -> list[str]:
    out = list(command)
    try:
        index = out.index(name)
    except ValueError as exc:
        raise RuntimeError(f"capture command missing required option {name}") from exc
    if index + 1 >= len(out):
        raise RuntimeError(f"capture command missing value for {name}")
    out[index + 1] = str(value)
    return out


def _run(command: Sequence[str]) -> None:
    print(json.dumps({"status": "PHASE58_P17_COMMAND_START", "command": list(command), "safety": SAFETY}, ensure_ascii=False))
    subprocess.run(list(command), check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="READ ONLY prospective Phase57 + Phase58 session orchestrator")
    parser.add_argument("--symbol", required=True, help="Target symbol, e.g. 7203.T")
    parser.add_argument("--sheet", required=True, help="Reusable/current RssChart 5M sheet")
    parser.add_argument("--history-pack", default="data/phase58/phase57-p21-history-sessions.json")
    parser.add_argument("--current-prefix", default="data/phase58/phase57-live-5m-prefix.json")
    parser.add_argument("--snapshot", default="data/phase58/live-phase57-snapshot.json")
    parser.add_argument("--output", default="data/phase58/phase57-microstructure-sync-live.jsonl")
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--samples-per-cycle", type=int, default=110, help="Requested maximum; runner shrinks it to the remaining snapshot-freshness budget when needed")
    parser.add_argument("--phase57-max-age-seconds", type=float, default=300.0)
    parser.add_argument("--cycles", type=int, default=1, help="Finite number of refresh/capture cycles")
    parser.add_argument("--reusable-target", action="store_true", help="Research-only target outside frozen five-symbol training universe")
    parser.add_argument("--workbook", default=None)
    args = parser.parse_args()

    if args.interval_seconds < 0.2:
        raise SystemExit("--interval-seconds must be >= 0.2")
    if args.samples_per_cycle < 1:
        raise SystemExit("--samples-per-cycle must be >= 1")
    if args.cycles < 1:
        raise SystemExit("--cycles must be >= 1")
    if args.phase57_max_age_seconds <= 0:
        raise SystemExit("--phase57-max-age-seconds must be > 0")
    requested_capture_seconds = args.interval_seconds * max(0, args.samples_per_cycle - 1)
    if requested_capture_seconds >= args.phase57_max_age_seconds:
        raise SystemExit("requested capture span must stay below Phase57 max snapshot age; lower samples-per-cycle or interval")
    if not Path(args.history_pack).exists():
        raise SystemExit(f"history pack not found: {args.history_pack}")

    node = shutil.which("node")
    if not node:
        raise SystemExit("node executable not found on PATH")
    python_exe = sys.executable

    print(json.dumps({
        "status": "PHASE58_P17_SESSION_START",
        "symbol": args.symbol,
        "sheet": args.sheet,
        "cycles": args.cycles,
        "requestedSamplesPerCycle": args.samples_per_cycle,
        "intervalSeconds": args.interval_seconds,
        "requestedCaptureSpanSeconds": requested_capture_seconds,
        "freshnessSafetyMarginSeconds": SNAPSHOT_FRESHNESS_MARGIN_SECONDS,
        "minimumMicrostructureSamplesPerCycle": MIN_MICROSTRUCTURE_SAMPLES_PER_CYCLE,
        "reusableTarget": args.reusable_target,
        "safety": SAFETY,
    }, ensure_ascii=False))

    for cycle in range(args.cycles):
        commands = build_cycle_commands(
            python_exe=python_exe,
            node_exe=node,
            symbol=args.symbol,
            sheet=args.sheet,
            history_pack=args.history_pack,
            current_prefix=args.current_prefix,
            snapshot=args.snapshot,
            output=args.output,
            interval_seconds=args.interval_seconds,
            samples_per_cycle=args.samples_per_cycle,
            phase57_max_age_seconds=args.phase57_max_age_seconds,
            reusable_target=args.reusable_target,
            workbook=args.workbook,
        )
        print(json.dumps({"status": "PHASE58_P17_CYCLE_START", "cycle": cycle + 1, "cycles": args.cycles, "safety": SAFETY}, ensure_ascii=False))
        try:
            _run(commands[0])
            _run(commands[1])
            budget = freshness_adjusted_samples(
                snapshot_path=Path(args.snapshot),
                requested_samples=args.samples_per_cycle,
                interval_seconds=args.interval_seconds,
                max_age_seconds=args.phase57_max_age_seconds,
            )
            print(json.dumps({"status": "PHASE58_P17_FRESHNESS_BUDGET", "cycle": cycle + 1, **budget, "safety": SAFETY}, ensure_ascii=False))
            actual_samples = int(budget["actualSamples"])
            if actual_samples < MIN_MICROSTRUCTURE_SAMPLES_PER_CYCLE:
                print(json.dumps({
                    "status": "BLOCKED_PHASE58_P17_INSUFFICIENT_FRESHNESS_BUDGET",
                    "cycle": cycle + 1,
                    "minimumSamplesRequired": MIN_MICROSTRUCTURE_SAMPLES_PER_CYCLE,
                    **budget,
                    "retryGuidance": "rerun after the next completed 5-minute source bar becomes available",
                    "safety": SAFETY,
                }, ensure_ascii=False))
                return 1
            capture_command = _set_option(commands[2], "--samples", actual_samples)
            _run(capture_command)
        except (subprocess.CalledProcessError, RuntimeError, OSError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, subprocess.CalledProcessError):
                print(json.dumps({"status": "BLOCKED_PHASE58_P17_CHILD_PROCESS_FAILED", "cycle": cycle + 1, "returnCode": exc.returncode, "command": exc.cmd, "safety": SAFETY}, ensure_ascii=False))
            else:
                print(json.dumps({"status": "BLOCKED_PHASE58_P17_FRESHNESS_BUDGET_ERROR", "cycle": cycle + 1, "error": str(exc), "safety": SAFETY}, ensure_ascii=False))
            return 1
        if cycle + 1 < args.cycles:
            time.sleep(1.0)

    print(json.dumps({"status": "PHASE58_P17_SESSION_COMPLETE", "cycles": args.cycles, "output": args.output, "safety": SAFETY}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
