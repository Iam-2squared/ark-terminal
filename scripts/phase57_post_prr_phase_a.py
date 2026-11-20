"""Read-only, append-only Post-PRR Phase A accounting and census.

The three subcommands deliberately enforce the exposure order. No model or
EXIT policy is executed. JSON money is serialized as exact decimal strings.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/phase57-post-prr-phase-a"
PRR = ROOT / "docs/evidence/phase57-prr-numerical-recovery"
CCMG = ROOT / "docs/evidence/phase57-checkpoint-certified-guard-exit"
LEDGERS = ROOT / "docs/evidence/phase57-exit-persistent-value-r53/RESULT"
FEE = Decimal("0.0005")
ZERO = Decimal(0)


def read(name):
    return json.loads((OUT / name).read_text())


def write(name, value):
    path = OUT / name
    if path.exists():
        raise ValueError("APPEND_ONLY:" + name)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                               allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def write_rows(name, entries):
    path = OUT / name
    if path.exists():
        raise ValueError("APPEND_ONLY:" + name)
    data = b"".join((json.dumps(x, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False) + "\n").encode()
                    for x in entries)
    path.write_bytes(gzip.compress(data, mtime=0))


def D(value):
    return None if value is None else Decimal(str(value))


def money(price, cost, quantity):
    return None if price is None else D(price) * quantity - cost * (1 + FEE)


def checked_map(entries):
    result = {(x["arm"], x["entryId"]): x for x in entries}
    if len(result) != len(entries):
        raise AssertionError("DUPLICATE_ARM_ENTRY")
    return result


def sources():
    pre = read("PHASE_A_PRECOMMIT.json")
    if sha(OUT / "PHASE_A_PRECOMMIT.json") != (OUT / "PHASE_A_PRECOMMIT.sha256").read_text().split()[0]:
        raise AssertionError("PHASE_A_PRECOMMIT_DRIFT")
    for pin in pre["sourcePins"].values():
        if sha(ROOT / pin["path"]) != pin["sha256"]:
            raise AssertionError("SOURCE_PIN_DRIFT:" + pin["path"])
    for directory, manifest, member_key in ((PRR, "MANIFEST.json", "fileSha256"),
                                             (CCMG, "MANIFEST.json", "filesSha256")):
        for name, expected in json.loads((directory / manifest).read_text())[member_key].items():
            if sha(directory / name) != expected:
                raise AssertionError("MANIFEST_MEMBER_DRIFT:" + name)
    frozen = json.loads((PRR / "CANONICAL_OOF_FREEZE.json").read_text())
    if sha(PRR / "CANONICAL_OOF.jsonl.gz") != frozen["canonicalOofSha256"] or \
       sha(PRR / "ROUTE_DECISIONS.jsonl.gz") != frozen["routeDecisionsSha256"]:
        raise AssertionError("CANONICAL_OOF_OR_ROUTE_DRIFT")
    return {
        "base": checked_map(rows(CCMG / "LAYER_A_ENTRY_ROWS.jsonl.gz")),
        "summary": checked_map(rows(CCMG / "CHECKPOINT_ENTRY_SUMMARY.jsonl.gz")),
        "routes": checked_map(rows(PRR / "ROUTE_DECISIONS.jsonl.gz")),
        "oof": checked_map(rows(PRR / "CANONICAL_OOF.jsonl.gz")),
        "prrAll": checked_map(rows(PRR / "ALL_ENTRY_ENTRY_ROWS.jsonl.gz")),
        "prrPrimary": checked_map(rows(PRR / "LAYER_A_ENTRY_ROWS.jsonl.gz")),
        "funded": {arm: json.loads(gzip.decompress(
            (LEDGERS / f"{arm}_R50_A_CONTROL_ledger.json.gz").read_bytes()))["funded"]
            for arm in ("IM", "R1")},
    }


def accounting():
    s = sources()
    keys = set(s["base"])
    if len(keys) != 1614 or any(set(s[name]) != keys for name in
                                ("summary", "routes", "oof", "prrAll", "prrPrimary")):
        raise AssertionError("SOURCE_ENTRY_POPULATION_MISMATCH")
    receipts = []
    for arm, eid in sorted(keys):
        key = arm, eid
        b, a, o, summary, route = (s[name][key] for name in
                                   ("base", "prrAll", "oof", "summary", "routes"))
        p = s["prrPrimary"].get(key)
        parts = eid.split("|")
        if (len(parts) != 3 or parts[0] != b["session"] or parts[2] != str(b["entryMinute"]) or
            any(x["session"] != b["session"] for x in (a, o, summary, route) if x) or
            any(x["entryId"] != eid for x in (a, o, summary, route) if x) or
            any(x["arm"] != arm for x in (a, o, summary, route) if x) or
            any(x["entryPrice"] != b["entryPrice"] for x in (a, p) if x) or
            any(x["primary"] != b["primary"] for x in (a, p, summary) if x) or
            route["routeDecision"] != a["routeDecision"] or
            route["routeDecision"] != o["routeDecision"] or
            abs(D(b["postEntryUpsidePct"]) - D(o["teacherUpsidePctEvaluatorOnly"])) > D("1e-12") or
            a["controlExitPrice"] != b["controlExitPrice"] or
            a["ccmgExitPrice"] != b["candidateExitPrice"] or
            a["controlExitMinute"] != b["controlExitMinute"] or
            a["ccmgExitMinute"] != b["candidateExitMinute"]):
            raise AssertionError("ENTRY_IDENTITY_OR_PRICE_DRIFT:" + str(key))
        q = D(b["quantity"])
        cost = D(b["entryPrice"]) * q
        funded = s["funded"][arm].get(eid)
        if b["primary"]:
            if not funded or D(funded["notionalJpy"]) != cost or funded["quantity"] != int(q) or \
               funded["symbol"] != parts[1] or funded["entryMinute"] != b["entryMinute"]:
                raise AssertionError("FUNDED_R34_COST_OR_SYMBOL_DRIFT:" + str(key))
        elif funded:
            raise AssertionError("PRIMARY_FLAG_DRIFT:" + str(key))
        for world, quantity in (("ALL_100", D(100)), ("PRIMARY_FUNDED", q)):
            if world == "PRIMARY_FUNDED" and not b["primary"]:
                continue
            world_cost = D(b["entryPrice"]) * quantity
            c = money(b["controlExitPrice"], world_cost, quantity)
            m = money(b["candidateExitPrice"], world_cost, quantity)
            old = a if world == "ALL_100" else p
            if world == "ALL_100" and a["quantity"] != 100 or \
               world == "PRIMARY_FUNDED" and p["quantity"] != int(q):
                raise AssertionError("WORLD_QUANTITY_DRIFT")
            oldc, oldm = D(old["controlPnlJpy"]), D(old["ccmgPnlJpy"])
            if (c is None) != (oldc is None) or (m is None) != (oldm is None):
                raise AssertionError("OLD_PRICE_NULL_IDENTITY")
            # All-100 PRR used sell proceeds basis on both sides. Primary
            # inherited R34 Control, while its CCMG may delegate Control.
            if world == "ALL_100":
                for price, saved in ((b["controlExitPrice"], oldc),
                                     (b["candidateExitPrice"], oldm)):
                    if price is not None and saved != D(price) * quantity * (1 - FEE) - world_cost:
                        raise AssertionError("OLD_ALL_PRICE_IDENTITY")
            if world == "PRIMARY_FUNDED" and c is not None and oldc != c:
                raise AssertionError("PRIMARY_R34_CONTROL_IDENTITY")
            receipts.append({"world": world, "arm": arm, "entryId": eid,
                "session": b["session"], "symbol": parts[1],
                "opportunityId": "|".join(parts[:2]), "entryMinute": b["entryMinute"],
                "entryPrice": b["entryPrice"], "quantity": int(quantity),
                "entryCostJpy": str(world_cost), "primary": b["primary"],
                "routeDecision": route["routeDecision"],
                "controlExitPrice": b["controlExitPrice"],
                "ccmgExitPrice": b["candidateExitPrice"],
                "controlExitMinute": b["controlExitMinute"],
                "ccmgExitMinute": b["candidateExitMinute"],
                "oldControlPnlJpy": None if oldc is None else str(oldc),
                "oldCcmgPnlJpy": None if oldm is None else str(oldm),
                "normalizedControlPnlJpy": None if c is None else str(c),
                "normalizedCcmgPnlJpy": None if m is None else str(m),
                "oldControlDifferenceJpy": None if c is None else str(c-oldc),
                "oldCcmgDifferenceJpy": None if m is None else str(m-oldm),
                "deltaPnlJpy": None if c is None or m is None else str(m-c),
                "oldDeltaPnlJpy": None if oldc is None or oldm is None else str(oldm-oldc),
                "futureUpsidePctEvaluatorOnly": b["postEntryUpsidePct"],
                "score5": route["score5"], "score10": route["score10"],
                "fold": route["fold"], "rank5Decile": a["rank5Decile"],
                "rank10Decile": a["rank10Decile"],
                "terminalReason": b["terminalReason"], "fillStatus": b["fillStatus"],
                "ccmgFirstIntentMinute": summary["firstSellIntent"],
                "controlDecisionMinute": summary["controlNow"],
                "controlExitKind": summary["controlExitKind"]})
    write_rows("ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz", receipts)
    by = {}
    for world in ("ALL_100", "PRIMARY_FUNDED"):
        subset = [r for r in receipts if r["world"] == world]
        for policy in ("Control", "Ccmg"):
            key = "old" + policy + "DifferenceJpy"
            available = [D(r[key]) for r in subset if r[key] is not None]
            changed = [r for r in subset if r[key] is not None and D(r[key]) != 0]
            by[f"{world}:{policy}"] = {"knownN":len(available), "changedN":len(changed),
                "totalCorrectionJpy":str(sum(available, ZERO)),
                "exampleIds": [r["arm"] + ":" + r["entryId"] for r in changed[:3]]}
    sign_changes = []
    for r in receipts:
        if r["deltaPnlJpy"] is not None:
            old, new = D(r["oldDeltaPnlJpy"]), D(r["deltaPnlJpy"])
            if (old > 0) - (old < 0) != (new > 0) - (new < 0):
                sign_changes.append(r["world"] + ":" + r["arm"] + ":" + r["entryId"])
            if r["world"] == "ALL_100" and old != new * (1 - FEE):
                raise AssertionError("ALL_100_COMMON_COST_CANCELLATION")
    write("ACCOUNTING_RECONCILIATION_RECEIPT.json", {
        "schema":"phase57-post-prr-accounting-reconciliation-v1",
        "status":"PASS_WITH_APPEND_ONLY_NORMALIZATION", "precommitSha256":sha(OUT / "PHASE_A_PRECOMMIT.json"),
        "rowsSha256":sha(OUT / "ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz"),
        "sourceContract": ["scripts/phase57_cash_capital_r34.py::CashBook.step",
                           "scripts/phase57_mh_layer_a_accounting_audit_r54.py::corrected_pair",
                           "docs/evidence/phase57-exit-persistent-value-r53/RESULT/{IM,R1}_R50_A_CONTROL_ledger.json.gz"],
        "frozenFormula":"proceeds=exitPrice*quantity; paidCost=effectiveEntryPrice*quantity (buy cost embedded); sellFee=paidCost*0.0005; pnl=proceeds-sellFee-paidCost; netPct=100*pnl/paidCost",
        "oldCode":{"CCMG_candidate":"scripts/phase57_ccmg_guard.py::corrected_pnl_jpy charges 0.0005*sale proceeds; delegated Primary Control is copied",
                   "PRR_all100":"scripts/phase57_prr_v2_economics.py::pnl100 charges 0.0005*sale proceeds on both policies",
                   "PRR_primary":"scripts/phase57_prr_v2_economics.py::join inherits CCMG funded rows",
                   "PRR_winner":"scripts/phase57_prr_v2_economics.py::winner_gate compares mean JPY rather than mean per-entry Net%"},
        "ledgerHashes":{arm:sha(LEDGERS / f"{arm}_R50_A_CONTROL_ledger.json.gz") for arm in ("IM","R1")},
        "byWorldPolicy":by, "signChangedRows":sign_changes,
        "commonCostCancellation":"normalized paired price-known same Entry and quantity: delta=quantity*(CCMG exit price-R50 exit price); all-100 old delta=0.9995*normalized delta",
        "oldClosureAndReportsUnmodified":True})
    return receipts, s


def census():
    if not (OUT / "ACCOUNTING_RECONCILIATION_RECEIPT.json").exists():
        raise AssertionError("CONTRACT_AUDIT_FIRST")
    s = sources()
    rec = rows(OUT / "ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz")
    trace_at_intent = defaultdict(list)
    for t in rows(CCMG / "CHECKPOINT_DRY_TRACE.jsonl.gz"):
        if t["state"] == "SELL_INTENT":
            trace_at_intent[(t["arm"], t["entryId"], t["now"])].append(t)
    masks = []
    for r in rec:
        summary = s["summary"][(r["arm"],r["entryId"])]
        intent = r["ccmgFirstIntentMinute"]
        ts = trace_at_intent.get((r["arm"],r["entryId"],intent), []) if intent is not None else []
        asof = (len(ts)==1 and ts[0]["freshClosedPrice"] is True and
                ts[0]["inputMaxKnownAt"] is not None and
                ts[0]["inputMaxBarEnd"] is not None and
                ts[0]["inputMaxKnownAt"]<=intent and ts[0]["inputMaxBarEnd"]<=intent)
        control_intent = (r["controlDecisionMinute"] if r["controlExitKind"]=="MODEL_EXIT" else None)
        order = ("UNKNOWN" if intent is None or control_intent is None else
                 "CCMG_FIRST" if intent<control_intent else
                 "R50_FIRST" if control_intent<intent else "SAME_MINUTE")
        flags = {"control_outcome_known":r["normalizedControlPnlJpy"] is not None,
                 "ccmg_outcome_known":r["normalizedCcmgPnlJpy"] is not None,
                 "paired_outcome_known":r["deltaPnlJpy"] is not None,
                 "entry_cost_basis_known":D(r["entryCostJpy"])>0,
                 "quantity_known":r["quantity"]>0,
                 "control_intent_time_known":control_intent is not None,
                 "ccmg_first_intent_time_known":intent is not None,
                 "fill_time_known":r["controlExitMinute"] is not None and r["ccmgExitMinute"] is not None,
                 "future_label_known":r["futureUpsidePctEvaluatorOnly"] is not None,
                 "runtime_feature_asof_valid":bool(asof)}
        masks.append({"world":r["world"],"arm":r["arm"],"entryId":r["entryId"],
            "session":r["session"],"symbol":r["symbol"],"opportunityId":r["opportunityId"],
            "entryMinute":r["entryMinute"],"entryPrice":r["entryPrice"],
            "quantity":r["quantity"],"primary":r["primary"],"routeDecision":r["routeDecision"],
            **flags,"has_ccmg_first_intent":intent is not None,
            "controlExitKind":r["controlExitKind"],"controlIntentMinute":control_intent,
            "controlTerminalDecisionMinute":r["controlDecisionMinute"],
            "ccmgFirstIntentMinute":intent,"intentOrder":order,
            "causalGuardTraceAtIntent":len(ts)==1,
            "fullStage2RuntimeFeatureSnapshot":False,
            "deltaEquality":"UNAVAILABLE" if r["deltaPnlJpy"] is None else
                "ZERO" if D(r["deltaPnlJpy"])==0 else "NONZERO"})
        if intent is not None and len(ts)!=1:
            raise AssertionError("CCMG_INTENT_TRACE_IDENTITY")
    write_rows("COMPARISON_MASK_ROWS.jsonl.gz", masks)
    table = {}
    for arm in ("IM","R1"):
        for population in ("ALL_100","PRIMARY_FUNDED","PRIMARY_OUTSIDE_100"):
            for route in ("ALL_ROUTES","DEFENSIVE_ELIGIBLE","CONTROL_DEFAULT"):
                xs=[x for x in masks if x["arm"]==arm and
                    (x["world"]=="PRIMARY_FUNDED" if population=="PRIMARY_FUNDED" else
                     x["world"]=="ALL_100" and
                     (population!="PRIMARY_OUTSIDE_100" or not x["primary"])) and
                    (route=="ALL_ROUTES" or x["routeDecision"]==route)]
                both=sum(x["paired_outcome_known"] for x in xs)
                table[f"{arm}:{population}:{route}"]={
                    "entryN":len(xs),"distinctSessionN":len({x["session"] for x in xs}),
                    "distinctOpportunityN":len({x["opportunityId"] for x in xs}),
                    "controlKnownN":sum(x["control_outcome_known"] for x in xs),
                    "ccmgKnownN":sum(x["ccmg_outcome_known"] for x in xs),
                    "pairedKnownN":both,
                    "controlOnlyN":sum(x["control_outcome_known"] and not x["ccmg_outcome_known"] for x in xs),
                    "ccmgOnlyN":sum(x["ccmg_outcome_known"] and not x["control_outcome_known"] for x in xs),
                    "bothUnknownN":sum(not x["control_outcome_known"] and not x["ccmg_outcome_known"] for x in xs),
                    "deltaEqualityN":dict(Counter(x["deltaEquality"] for x in xs)),
                    "ccmgIntentN":sum(x["has_ccmg_first_intent"] for x in xs),
                    "controlModelIntentN":sum(x["control_intent_time_known"] for x in xs),
                    "intentOrderN":dict(Counter(x["intentOrder"] for x in xs)),
                    "causalGuardTraceN":sum(x["causalGuardTraceAtIntent"] for x in xs),
                    "runtimeFeatureAsOfValidN":sum(x["runtime_feature_asof_valid"] for x in xs),
                    "fullStage2RuntimeFeatureSnapshotN":sum(x["fullStage2RuntimeFeatureSnapshot"] for x in xs),
                    "pairedFillTimeN":sum(x["fill_time_known"] for x in xs),
                    "futureLabelKnownN":sum(x["future_label_known"] for x in xs)}
                if both + table[f"{arm}:{population}:{route}"]["controlOnlyN"] + \
                   table[f"{arm}:{population}:{route}"]["ccmgOnlyN"] + \
                   table[f"{arm}:{population}:{route}"]["bothUnknownN"] != len(xs):
                    raise AssertionError("PARTITION_COUNT")
    if (table["IM:ALL_100:ALL_ROUTES"]["entryN"],
        table["R1:ALL_100:ALL_ROUTES"]["entryN"],
        table["IM:PRIMARY_FUNDED:ALL_ROUTES"]["entryN"],
        table["R1:PRIMARY_FUNDED:ALL_ROUTES"]["entryN"]) != (819,795,79,32):
        raise AssertionError("FROZEN_POPULATION_COUNT")
    freeze = json.loads((PRR / "CANONICAL_OOF_FREEZE.json").read_text())
    write("A0_CENSUS.json",{"schema":"phase57-post-prr-a0-census-v1",
        "precommitSha256":sha(OUT / "PHASE_A_PRECOMMIT.json"),
        "accountingReceiptSha256":sha(OUT / "ACCOUNTING_RECONCILIATION_RECEIPT.json"),
        "maskRowsSha256":sha(OUT / "COMPARISON_MASK_ROWS.jsonl.gz"),
        "table":table,
        "sessionRange":sorted({x["session"] for x in masks if x["world"]=="ALL_100"}),
        "oldReleasedDevelopment":{"bothR50AndCCMGOutcomeOutsideCurrent1614":"NOT_ESTABLISHED",
                                  "note":"No separately pinned old-period paired CCMG teacher in current source manifests. No replay or fit used to fill."},
        "potentialLineage":{"canonicalOofPresent":True,"canonicalOofSha256":freeze["canonicalOofSha256"],
             "foldAndScorePresent":True,"frozenFeaturesArrayLocalPresent":False,
             "featureArrayRecordedSha256":"54bf771f6a090eb3e8035f7ee433ca1fbd617c165d77955ab71054b4e259a3fe",
             "fitProtocolAndSourceLineageReceiptsPresent":True,
             "stage2Use":"lineage review required; no new fit"},
        "meaning":"Delta ZERO/NONZERO counts viewed, so A0 is not outcome-blind; no feature-to-delta association examined."})
    write("A0_FREEZE.json",{"schema":"phase57-post-prr-a0-freeze-v1",
        "a0Sha256":sha(OUT / "A0_CENSUS.json"),
        "maskSha256":sha(OUT / "COMPARISON_MASK_ROWS.jsonl.gz"),
        "accountingRowsSha256":sha(OUT / "ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz"),
        "columns":list(masks[0].keys()),"period":sorted({x["session"] for x in masks}),
        "population":"Primary funded subset of all-entry 100-share; IM/R1 alternative Entry worlds",
        "exposure":"A0 viewed route, outcome-known and delta equality counts; no score/delta relationship"})
    print(json.dumps({"status":"A0_FROZEN","a0Sha256":sha(OUT / "A0_CENSUS.json"),
        "counts":{k:v["entryN"] for k,v in table.items() if k.endswith("ALL_ROUTES")}}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("contract","a0"))
    args = parser.parse_args()
    if args.stage == "contract":
        receipts, _ = accounting()
        print(json.dumps({"status":"CONTRACT_AUDITED","rowN":len(receipts),
                          "receiptSha256":sha(OUT / "ACCOUNTING_RECONCILIATION_RECEIPT.json")}))
    else:
        census()
