from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
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
    parser.add_argument("--samples-per-cycle", type=int, default=110, help="110 x 2s = 220s, leaving time to refresh before snapshot staleness")
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
    capture_seconds = args.interval_seconds * max(0, args.samples_per_cycle - 1)
    if capture_seconds >= args.phase57_max_age_seconds:
        raise SystemExit("capture span must stay below Phase57 max snapshot age; lower samples-per-cycle or interval")
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
        "samplesPerCycle": args.samples_per_cycle,
        "intervalSeconds": args.interval_seconds,
        "captureSpanSeconds": capture_seconds,
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
            for command in commands:
                _run(command)
        except subprocess.CalledProcessError as exc:
            print(json.dumps({"status": "BLOCKED_PHASE58_P17_CHILD_PROCESS_FAILED", "cycle": cycle + 1, "returnCode": exc.returncode, "command": exc.cmd, "safety": SAFETY}, ensure_ascii=False))
            return 1
        if cycle + 1 < args.cycles:
            time.sleep(1.0)

    print(json.dumps({"status": "PHASE58_P17_SESSION_COMPLETE", "cycles": args.cycles, "output": args.output, "safety": SAFETY}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
