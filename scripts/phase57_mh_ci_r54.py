"""Zero-real-fit identity/transport/synthetic-only CI for frozen R54."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from scripts import phase57_mh_data_r54 as data
from scripts import phase57_mh_train_r54 as trainer


def run(source, summary, labels, out, smoke_fits=True):
    from scripts import phase57_exit_continuation_r52 as r52
    from scripts import phase57_capital_exit_integrated as integrated
    from scripts import phase57_capital_v3 as v3
    from scripts import phase57_development_integrated_v0 as v0
    if out.exists():raise ValueError("ZERO_FIT_RECEIPT_APPEND_ONLY")
    s=json.loads((summary/"readiness.json").read_text());s["summaryPath"]=summary
    protocol, receipt, arrays, ids, groups=trainer.verify_protocol(s,labels,source)
    locked=json.loads((trainer.EVIDENCE/"FEATURE_SCHEMA_LOCKED.json").read_text())
    original=json.loads((summary/"feature-schema.json").read_text())
    if {k:v for k,v in locked.items() if k!="ablationSRemove"} != \
       {k:v for k,v in original.items() if k!="ablationSRemove"}:
        raise ValueError("ABLATION_S_ONLY_ZERO_FIT_CORRECTION")
    if len(locked["ablationSRemove"])!=30 or len(locked["ablationPRemove"])!=187:
        raise ValueError("FROZEN_ABLATION_LINEAGE")
    if len(ids)!=656247 or len(groups)!=3848 or len(protocol["sessions"])!=24:
        raise ValueError("CHECKPOINT_OR_SESSION_IDENTITY")
    p, original_inputs, score, calendars=integrated.load_inputs()
    _,_,cohort,intents,evaluation,_,raw,_,_,original_labels=original_inputs
    controls={}
    for arm in v0.ARMS:
        ranking=v3.ranked_intents([x for x in intents[arm]
                if x["timestamp"][:10] in protocol["sessions"]],score[arm])
        replay=integrated.replay(arm,3,{**cohort,"sessions":protocol["sessions"]},
                                 ranking,raw,calendars[arm])
        archive=r52.archive_control(arm)
        if v0.canonical(replay)!=v0.canonical(archive):
            raise ValueError("EXACT_FROZEN_R50_A_CONTROL_BYTE_IDENTITY")
        controls[arm]={"funded":len(replay["funded"]),"closed":len(replay["closed"]),
                       "ledgerSha256":v0.digest_bytes(v0.canonical(replay)) if hasattr(v0,"digest_bytes")
                       else __import__("hashlib").sha256(v0.canonical(replay)).hexdigest()}
    # Separate synthetic-framework smoke fits, never on Development labels.
    X=np.arange(480,dtype=np.float32).reshape(120,4)
    y=np.sin(X[:,0]/50).astype(np.float32)
    smoke=[]
    if smoke_fits:
        for head,quantile in (("mean",None),("q10",.1),("q90",.9)):
            m=trainer.new_model(head,quantile);m.fit(X,y)
            if not np.all(np.isfinite(m.predict(X[:5]))):raise ValueError("SYNTHETIC_SMOKE_NONFINITE")
            smoke.append(head)
    row={"schema":"phase57-r54-zero-real-fit-ci-receipt-v1",
         "status":"PASS","protocolSha256":data.sha(trainer.PROTOCOL),
         "lockedSchemaSha256":data.sha(trainer.EVIDENCE/"FEATURE_SCHEMA_LOCKED.json"),
         "teacherSha256":data.sha(labels),"sourceRows":len(ids),
         "frozenControlByteIdentical":controls,"realEstimatorFits":0,
         "syntheticEstimatorFits":len(smoke),"candidatePredictions":0,
         "newExitPolicyReplays":0,"candidatePerformanceViewed":False,
         "protectedOpened":0,"providerRequests":0,"safety":v0.SAFETY}
    out.write_bytes(data.canonical(row));print(data.canonical(row).decode(),flush=True)


if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--source",type=Path,required=True)
    a.add_argument("--summary",type=Path,required=True)
    a.add_argument("--labels",type=Path,required=True)
    a.add_argument("--skip-smoke",action="store_true")
    a.add_argument("--out",type=Path,required=True)
    x=a.parse_args();run(x.source,x.summary,x.labels,x.out,smoke_fits=not x.skip_smoke)
