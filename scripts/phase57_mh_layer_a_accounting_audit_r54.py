"""Append-only R54 Layer A reconciliation against the frozen R34 cost basis.

This consumes completed, saved research outputs. It does not fit an estimator,
change an EXIT calendar, or invoke the integrated replay engine.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import json
from decimal import Decimal
from pathlib import Path

from scripts import phase57_mh_data_r54 as data
from scripts import phase57_mh_replay_r54 as replay
from scripts import phase57_mh_train_r54 as trainer

RUN_ID = 36382668368
RUN_HEAD = "2166772f719bcd947382fa242ec63231c3f91fbe"
SELL_FEE_PP = Decimal("0.05")


def corrected_pair(row, funded, exit_price):
    """Preserve the precommitted quantity and price; correct only sell fee."""
    quantity = int(funded["quantity"])
    notional = Decimal(funded["notionalJpy"])
    if (quantity <= 0 or quantity % 100 or
        row["quantity"] != quantity or row["entryId"] != funded["entryId"]):
        raise ValueError("LAYER_A_CONTROL_QUANTITY_DRIFT")
    out = dict(row)
    if exit_price is None:
        if row["candidatePnlJpy"] is not None:
            raise ValueError("MISSING_FILL_FABRICATED")
        return out, Decimal(0)
    proceeds = Decimal(str(exit_price)) * quantity
    old = proceeds * Decimal("0.9995") - notional
    if Decimal(row["candidatePnlJpy"]) != old:
        raise ValueError("OLD_LAYER_A_OR_PRICE_IDENTITY_DRIFT")
    true_pnl = proceeds - notional * SELL_FEE_PP / 100 - notional
    out["candidatePnlJpy"] = str(true_pnl)
    former = row["controlPnlJpy"]
    out["sameQuantityPnlDeltaJpy"] = (None if former is None else
                                        str(true_pnl - Decimal(former)))
    return out, true_pnl - old


def audit(result: Path, out: Path):
    if out.exists():
        raise ValueError("APPEND_ONLY_ACCOUNTING_AUDIT")
    protocol = json.loads(trainer.PROTOCOL.read_text())
    if (data.sha(trainer.PROTOCOL) != trainer.PROTOCOL_SHA.read_text().strip() or
        protocol["cycleId"] != "CYCLE2_CORRECTED_D_TEACHER" or
        any(protocol["safety"].values())):
        raise ValueError("PRECOMMITTED_CYCLE_IDENTITY")
    manifest = json.loads((result / "manifest.json").read_text())
    if (manifest["newModelFits"] != 176 or
        manifest["integratedInvocations"] != 44 or
        any(manifest["safety"].values())):
        raise ValueError("FINITE_BUDGET_OR_SAFETY")
    for name, digest in manifest["filesSha256"].items():
        if data.sha(result / name) != digest:
            raise ValueError("SAVED_RESULT_DIGEST:" + name)

    original = json.loads((result / "paired-layer-a.json").read_text())
    reports = json.loads((result / "scorecard.json").read_text())
    metrics = json.loads((result / "forecast-metrics.json").read_text())
    stress = json.loads((result / "cost-stress.json").read_text())
    reproduce = json.loads((result / "reproducibility.json").read_text())
    old_verdict = json.loads((result / "selection.json").read_text())
    with gzip.open(result / "standalone-all-entries.json.gz", "rt") as stream:
        standalone = json.load(stream)
    paired = copy.deepcopy(original)
    receipts = {}
    controls = {}
    for arm in ("IM", "R1"):
        with gzip.open(result / (arm + "_R50_A_CONTROL_ledger.json.gz"), "rt") as stream:
            controls[arm] = json.load(stream)
        for name, rows in original[arm].items():
            price_rows = standalone[arm + "_" + name]
            by_id = {x["entryId"]: x for x in price_rows}
            if len(by_id) != len(price_rows):
                raise ValueError("DUPLICATE_STANDALONE_ENTRY_ID")
            amended = []
            delta = Decimal(0)
            corrected_count = 0
            for row in rows:
                eid = row["entryId"]
                if eid not in controls[arm]["funded"] or eid not in by_id:
                    raise ValueError("CONTROL_OR_PRICE_ID_MISSING")
                new, change = corrected_pair(row, controls[arm]["funded"][eid],
                                             by_id[eid]["exitPrice"])
                amended.append(new)
                delta += change
                corrected_count += new["candidatePnlJpy"] is not None
            paired[arm][name] = amended
            receipts[arm + "_" + name] = {
                "pairedN": len(amended), "pricedN": corrected_count,
                "exactR34SellFeeCorrectionJpy": str(delta)}

    if not all(reproduce["sameSavedForecast"].values()):
        raise ValueError("SAVED_REPLAY_NOT_REPRODUCIBLE")
    if not all(reproduce["independentDRefits"].values()):
        raise ValueError("D_REFIT_NOT_REPRODUCIBLE")
    from scripts import phase57_development_integrated_v0 as v0
    corrected = replay.frozen_gate(protocol, reports, paired, metrics["IM"],
                                   v0.IM, controls["IM"], stress, True, True)
    out.mkdir(parents=True)
    (out / "paired-layer-a-r34.json").write_bytes(data.canonical(paired))
    (out / "selection-r34.json").write_bytes(data.canonical(corrected))
    (out / "accounting-audit.json").write_bytes(data.canonical({
        "schema": "phase57-r54-cycle2-layer-a-accounting-audit-v1",
        "status": "PASS", "sourceRunId": RUN_ID, "sourceHead": RUN_HEAD,
        "sourceResultManifestSha256": data.sha(result / "manifest.json"),
        "sourcePairedSha256": data.sha(result / "paired-layer-a.json"),
        "sourceSelectionSha256": data.sha(result / "selection.json"),
        "oldDiagnosticSelection": old_verdict["selection"],
        "correctedSelection": corrected["selection"],
        "corrections": receipts, "realFitsAdded": 0,
        "integratedReplaysAdded": 0, "candidateOrThresholdChanges": 0,
        "correctedPairedSha256": data.sha(out / "paired-layer-a-r34.json"),
        "correctedSelectionSha256": data.sha(out / "selection-r34.json"),
        "safety": protocol["safety"]}))
    return corrected


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(data.canonical(audit(args.result, args.out)).decode(), flush=True)
