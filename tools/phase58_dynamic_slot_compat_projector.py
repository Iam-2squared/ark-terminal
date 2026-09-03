from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

FALSE_KEYS = (
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
    "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
)


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def assert_safety(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("dynamic slot safety required")
    for key in FALSE_KEYS:
        if value.get(key) is not False:
            raise ValueError(f"dynamic slot safety {key} must remain false")
    if value.get("excelMarketDataQueryWriteAllowed") is not True:
        raise ValueError("dynamic slot market-data query write scope must be explicit")


def project_dynamic_slot_row(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict) or row.get("schemaVersion") != 1 or row.get("phase") != "58.p32.dynamic-slot-capture":
        raise ValueError("Phase58 p32 dynamic-slot row required")
    assert_safety(row.get("safety"))
    methodology = row.get("methodology") or {}
    if methodology.get("futureOutcomeUsed") is not False or methodology.get("pointInTimeOnly") is not True:
        raise ValueError("dynamic slot row must be prospective and outcome-free")
    if methodology.get("excelOrderWritePerformed") is not False:
        raise ValueError("dynamic slot row cannot contain Excel order writes")
    if row.get("recordType") == "MARKET_OBSERVATION" and row.get("slotReady") is not True:
        return None
    if row.get("recordType") not in ("MARKET_OBSERVATION", "SESSION_HEARTBEAT"):
        return None
    raw_hash = canonical_sha256(row)
    projected = dict(row)
    projected["phase"] = "58.p31.multi-symbol-capture"
    projected["dynamicSlotProvenance"] = {
        "sourcePhase": "58.p32.dynamic-slot-capture",
        "sourceRowSha256": raw_hash,
        "slotId": row.get("slotId"),
        "assignmentGeneration": row.get("assignmentGeneration"),
        "watchlistAsOf": row.get("watchlistAsOf"),
        "priorMarketDataQuerySwitchObserved": row.get("recordType") == "MARKET_OBSERVATION",
    }
    projected["methodology"] = {
        **methodology,
        "preconfiguredSheetsOnly": False,
        "dynamicSlotMode": True,
        "priorMarketDataQuerySwitchObserved": row.get("recordType") == "MARKET_OBSERVATION",
        # The projected observation itself performs no Excel write. The earlier p32 assignment
        # remains auditable through dynamicSlotProvenance/sourceRowSha256.
        "symbolSwitchWritePerformed": False,
        "excelFormulaWritePerformed": False,
        "excelOrderWritePerformed": False,
        "pointInTimeOnly": True,
        "futureOutcomeUsed": False,
    }
    return projected


def project_new_lines(source: Path, destination: Path, state_file: Path) -> dict[str, int]:
    state = {"lineCount": 0}
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))
    consumed = int(state.get("lineCount", 0))
    if not source.exists():
        return {"consumed": consumed, "written": 0}
    lines = source.read_text(encoding="utf-8").splitlines()
    if consumed > len(lines):
        raise RuntimeError("dynamic slot source JSONL shrank; refusing replay")
    projected_rows = []
    for line_number, line in enumerate(lines[consumed:], consumed + 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid dynamic slot JSONL line {line_number}") from exc
        projected = project_dynamic_slot_row(row)
        if projected is not None:
            projected_rows.append(projected)
    if projected_rows:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a", encoding="utf-8", newline="\n") as handle:
            for row in projected_rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"lineCount": len(lines)}, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"consumed": len(lines), "written": len(projected_rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Project p32 dynamic-slot evidence into the existing p31 Lane M observation contract")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument("--iterations", type=int, default=30000)
    args = parser.parse_args()
    if args.poll_seconds < 0.2:
        raise SystemExit("--poll-seconds must be >= 0.2")
    if args.iterations < 1:
        raise SystemExit("--iterations must be >= 1")
    source, output, state = Path(args.source), Path(args.output), Path(args.state)
    total_written = 0
    print(json.dumps({"status": "PHASE58_DYNAMIC_SLOT_PROJECTOR_START", "source": str(source), "output": str(output)}, ensure_ascii=False))
    for index in range(args.iterations):
        result = project_new_lines(source, output, state)
        total_written += result["written"]
        if index + 1 < args.iterations:
            time.sleep(args.poll_seconds)
    print(json.dumps({"status": "PHASE58_DYNAMIC_SLOT_PROJECTOR_COMPLETE", "rowsWritten": total_written, "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
