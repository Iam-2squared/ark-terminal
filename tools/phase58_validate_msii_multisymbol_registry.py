from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from phase58_excel_multisymbol_microstructure_capture import SAFETY, validate_registry


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_registry_preflight(payload: Any, *, source_path: str | None = None) -> dict[str, Any]:
    registry = validate_registry(payload)
    return {
        "schemaVersion": 1,
        "phase": "58.p31.registry-preflight",
        "status": "PHASE58_MSII_REGISTRY_PREFLIGHT_READY",
        "sourcePath": source_path,
        "workbook": registry.get("workbook"),
        "symbolCount": len(registry["symbols"]),
        "symbols": [row["symbol"] for row in registry["symbols"]],
        "registrySha256": canonical_sha256(registry),
        "methodology": {
            "offlineValidationOnly": True,
            "excelOpenedByPreflight": False,
            "excelFormulaWritePerformed": False,
            "symbolSwitchWritePerformed": False,
            "futureDynamicSelectionCoverageGuaranteed": False,
            "coverageMustBeMeasuredProspectively": True,
        },
        "safety": SAFETY,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline validation/freeze manifest for a preconfigured MarketSpeed II multi-symbol registry")
    parser.add_argument("--registry", required=True)
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()

    source = Path(args.registry)
    payload = json.loads(source.read_text(encoding="utf-8"))
    report = build_registry_preflight(payload, source_path=str(source))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.manifest:
        output = Path(args.manifest)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
