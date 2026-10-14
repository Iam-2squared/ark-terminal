"""Persistent exclusive reservation and START budgets. Failed starts remain spent."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os
from .artifact_io import exclusive_json
from .contracts import digest
from .exact_math import V2Error

EVENTS=("CANDIDATE_RESERVED","RISK_FIT_STARTED","RISK_FIT_FINISHED",
        "OPPORTUNITY_FIT_STARTED","OPPORTUNITY_FIT_FINISHED","RISK_CAL_STARTED",
        "RISK_CAL_FINISHED","OPPORTUNITY_CAL_STARTED","OPPORTUNITY_CAL_FINISHED",
        "MODEL_SEALED","WATCHLISTS_SEALED","LABEL_OPENED")


class ExperimentLedger:
    def __init__(self, path: Path, *, mode: str):
        if mode!="SYNTHETIC":
            raise V2Error("MARKET_LEDGER_REQUIRES_OWNER_APPROVAL")
        self.path=path
        self.mode=mode
        self.path.parent.mkdir(parents=True,exist_ok=True)

    @contextmanager
    def lock(self):
        p=self.path.with_suffix(self.path.suffix+".lock")
        try:
            fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError:
            raise V2Error("EXPERIMENT_LOCK_HELD_NO_AUTO_RETRY") from None
        try:
            os.write(fd,str(os.getpid()).encode())
            os.fsync(fd)
            yield
        finally:
            os.close(fd)
            p.unlink()

    def rows(self) -> list[dict[str,Any]]:
        rows=[]
        if self.path.exists():
            previous=None
            for line in self.path.read_text().splitlines():
                r=json.loads(line)
                h=r.pop("event_hash")
                if r.get("previous_hash")!=previous or digest(r)!=h:
                    raise V2Error("EXPERIMENT_LEDGER_TAMPERED")
                r["event_hash"]=h
                rows.append(r)
                previous=h
        return rows

    def append(self, event: str, candidate_id: str, binding: dict[str,Any]) -> None:
        if event not in EVENTS or not candidate_id:
            raise V2Error("INVALID_EXPERIMENT_EVENT")
        with self.lock():
            rows=self.rows()
            if event=="CANDIDATE_RESERVED":
                if any(r["event"]==event for r in rows):
                    raise V2Error("CANDIDATE_BUDGET_EXHAUSTED")
            else:
                reserved=next((r for r in rows if r["event"]=="CANDIDATE_RESERVED"),None)
                if reserved is None or reserved["candidate_id"]!=candidate_id or reserved["binding"]!=binding:
                    raise V2Error("CANDIDATE_NOT_RESERVED_OR_HASH_DRIFT")
                if any(r["event"]==event for r in rows):
                    raise V2Error("EVENT_ALREADY_SPENT_NO_RETRY")
                prev=EVENTS[EVENTS.index(event)-1]
                if not any(r["event"]==prev for r in rows):
                    raise V2Error("EXPERIMENT_EVENT_OUT_OF_ORDER")
            payload={"event":event,"candidate_id":candidate_id,"binding":binding,
                     "mode":self.mode,"timestamp":datetime.now(timezone.utc).isoformat(),
                     "previous_hash":rows[-1]["event_hash"] if rows else None}
            payload["event_hash"]=digest(payload)
            with self.path.open("a",encoding="utf8") as f:
                f.write(json.dumps(payload,sort_keys=True,allow_nan=False)+"\n")
                f.flush()
                os.fsync(f.fileno())

    def reserve(self, output: Path, candidate_id: str, binding: dict[str,Any]) -> None:
        output.mkdir(parents=True,exist_ok=False)
        self.append("CANDIDATE_RESERVED",candidate_id,binding)
        exclusive_json(output/"reservation.json",{"candidate_id":candidate_id,"binding":binding,"mode":self.mode})
