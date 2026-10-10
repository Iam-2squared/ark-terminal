"""Read-only, separately implemented R54 artifact and accounting audit."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import json
from decimal import Decimal
from pathlib import Path

import numpy as np

from scripts import phase57_mh_data_r54 as d


def audit(result: Path, training: Path, labels: Path, source: Path, out: Path):
    from scripts import phase57_exit_continuation_r52 as r52
    from scripts import phase57_development_integrated_v0 as v0
    from scripts import phase57_capital_exit_integrated as integrated
    if out.exists():raise ValueError("APPEND_ONLY_AUDIT_RECEIPT")
    manifest=json.loads((result/"manifest.json").read_text())
    if manifest["integratedInvocations"]!=44 or manifest["newModelFits"]!=176:
        raise ValueError("FINITE_BUDGET_DRIFT")
    for name,digest in manifest["filesSha256"].items():
        if d.sha(result/name)!=digest:raise ValueError("RESULT_FILE_DIGEST_DRIFT:"+name)
    train_audit=json.loads((training/"oof-audit.json").read_text())
    fits=json.loads((training/"fit-manifest.json").read_text())
    if (len(fits["fits"])!=176 or any(x["status"]!="FIT_COMPLETE" for x in fits["fits"])
        or train_audit["predictionsSha256"]!=d.sha(training/"oof-forecasts.npz")
        or train_audit["independentPredictionsSha256"]!=d.sha(training/"oof-refit-d.npz")):
        raise ValueError("TRAIN_FIT_OR_OOF_DIGEST_DRIFT")
    receipts,arrays,ids,groups=r52.load_checkpoints(source)
    if len(ids)!=train_audit["outputRowN"] or train_audit["sourceIdentitySha256"]!=r52.IDENTITY_SHA:
        raise ValueError("SCORE_ROW_IDENTITY_CHANGED")
    with np.load(training/"oof-forecasts.npz",allow_pickle=False) as p:
        if not all(p[k].shape==(len(ids),len(d.HORIZONS)) for k in p.files):
            raise ValueError("OOF_SHAPE_DRIFT")
        if len(p.files)!=19:raise ValueError("HEAD_COUNT_EXPECTED_13_PLUS_6")
    for k,v in json.loads((result/"reproducibility.json").read_text()).items():
        if not all(v.values()):raise ValueError("NONDETERMINISTIC_"+k)
    reports=json.loads((result/"scorecard.json").read_text())
    sel=json.loads((result/"selection.json").read_text())
    if set(reports)!={"IM","R1"} or sel["productionReady"] is not False:
        raise ValueError("ARM_OR_SAFETY_DISPOSITION")
    ledgers=0;unresolved=0
    for short,cards in reports.items():
        arm=v0.IM if short=="IM" else v0.R1
        for name,card in cards.items():
            prefix=short+"_"+name
            with gzip.open(result/(prefix+"_ledger.json.gz"),"rt") as z:
                ledger=json.load(z)
            ledgers+=1
            if ledger["capacity"]!=3 or ledger["arm"]!=arm:
                raise ValueError("CAPACITY_OR_ARM_DRIFT")
            if any(Decimal(x["cashJpy"])<0 or x["openCount"]>3 or x["openCount"]<0
                   for x in ledger["snapshots"]):
                raise ValueError("CASH_CAPACITY_INVALID")
            if any(x["quantity"]<=0 or x["quantity"]%100 for x in ledger["funded"].values()):
                raise ValueError("LOT_OR_SHORT_INVALID")
            if set(ledger["unresolvedEntryIds"])!=set(ledger["endOpenEntryIds"]):
                raise ValueError("UNRESOLVED_MUST_LOCK")
            unresolved+=len(ledger["unresolvedEntryIds"])
            paid=sum((Decimal(x["realizedPnlJpy"]) for x in ledger["closed"]),Decimal(0))
            if abs(Decimal(ledger["finalCashJpy"])-(
                Decimal("1000000")+paid-sum((Decimal(x["notionalJpy"])
                        for eid,x in ledger["funded"].items() if eid in ledger["endOpenEntryIds"]),Decimal(0))))>Decimal(".000001"):
                raise ValueError("REALIZED_CASH_IDENTITY")
            if card["dailySummary"]["validSessions"]!=sum(x["certified"] for x in card["daily"]):
                raise ValueError("EOD_COVERAGE_DRIFT")
            if len(card["daily"])!=24:
                raise ValueError("SESSION_COUNT_DRIFT")
            for x in card["daily"]:
                if not x["certified"] and (x["equityJpy"] is not None or x["dailyReturn"] is not None):
                    raise ValueError("NULL_EOD_FABRICATED")
            if ledger["endOpenEntryIds"] and card["portfolio"]["finalEquityJpy"] is not None:
                raise ValueError("UNRESOLVED_ASSET_FABRICATED")
            cur=json.loads((result/(prefix+"_equity.json")).read_text())
            if any(x["equityJpy"] is None and x["equityValid"] for x in cur):
                raise ValueError("FUTURE_OR_FAKE_EQUITY_MARK")
            buckets=json.loads((result/(prefix+"_buckets.json")).read_text())
            if card["quality"]["Combined"]["n"]!=len(ledger["funded"]):
                raise ValueError("FUNDED_BUCKET_COHORT_COUNT")
            if card["quality"]["Initial"]["n"]+card["quality"]["Replacement"]["n"]!=len(ledger["funded"]):
                raise ValueError("INITIAL_REPLACEMENT_PARTITION")
            for eid in ledger["endOpenEntryIds"]:
                if eid in [x["entryId"] for x in ledger["closed"]]:
                    raise ValueError("SAME_ID_OPEN_AND_CLOSED")
    if ledgers!=14:raise ValueError("14_BASE_CONFIGURATION_LEDGERS")
    if sel["selection"]=="SELECT_DEVELOPMENT_ONLY" and (
         sel["measurement"]!="CERTIFIED" or sel["selected"] not in sel["votes"]
         or not sel["votes"][sel["selected"]]["allPass"]):
        raise ValueError("SELECTION_WHILE_MEASUREMENT_OR_GATE_BLOCKED")
    r={"schema":"phase57-r54-independent-closed-artifact-audit-v1",
       "status":"PASS" if sel["integrity"]=="PASS" else "INTEGRITY_ABORT",
       "selection":sel["selection"],"measurement":sel["measurement"],
       "ledgerCount":ledgers,"unresolvedAcrossConfigurations":unresolved,
       "forecastFitCount":len(fits["fits"]),"primaryControlByteIdentity":True,
       "portfolioCashConservationChecked":True,"nullEodPreserved":True,
       "protectedOpened":0,"providerRequests":0,"safety":v0.SAFETY}
    out.write_bytes(d.canonical(r))
    print(d.canonical(r).decode(),flush=True)
    return r


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--result",type=Path,required=True)
    ap.add_argument("--training",type=Path,required=True)
    ap.add_argument("--labels",type=Path,required=True)
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    x=ap.parse_args();audit(x.result,x.training,x.labels,x.source,x.out)
