"""Evaluation-only V5 source-cell authority after R2 precommit actual GET.

No model fitting/inference or replay. This file does not feed a runtime decision.
"""
from pathlib import Path
import json
import hashlib
from metrics_exact import (json_read,jsonl_read,capital_metrics,quality_metrics,protected_audit,
                           reason_conservation,exact,public)

ROOT=Path(__file__).parents[1]
V5=ROOT/"inputs/v5/capital_v5_slot_private"
OUT=ROOT/"metrics"
TEACHERS=OUT/"evaluation_only/TEACHERS_EVALUATION.jsonl.gz"
STREAM=ROOT/"inputs/v5_source/capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz"


def build():
    result=json_read(V5/"CAPITAL_MAX3_SLOT_RESERVE_V1_RESULT.json")
    decisions=jsonl_read(V5/"CAPITAL_MAX3_SLOT_RESERVE_V1_DECISIONS.jsonl.gz")
    trades=jsonl_read(V5/"CAPITAL_MAX3_SLOT_RESERVE_V1_TRADES.jsonl.gz")
    curves=jsonl_read(V5/"CAPITAL_MAX3_SLOT_RESERVE_V1_CURVE.jsonl.gz")
    outcomes={}
    for t in jsonl_read(TEACHERS):
        if t["entry_id"] in outcomes:
            raise ValueError("Duplicate teacher identity")
        outcomes[t["entry_id"]]={"potential_pct":str(t["potential_return"]*100),
                                 "potential_return_source_cell":str(t["potential_return"]),
                                 "frozen_realized_net_return_cell":str(t["realized_net_return"]) if t.get("realized_net_return") is not None else None,
                                 "frozen_execution_status":t.get("execution_status"),
                                 "source":"FROZEN_TEACHERS_EVALUATION_POTENTIAL_RETURN_TIMES_100",
                                 "evaluation_only":True}
    stream=jsonl_read(STREAM)
    rank_pass={s["entry_id"] for s in stream if s["admission"]}
    capital=capital_metrics(result["daily_series"],curves)
    protection=protected_audit(decisions,trades,decisions,trades)
    quality=quality_metrics(decisions,trades,outcomes,capital,protection)
    expected={"U5":50,"U10":26,"Medium":27,"Weak":58,"below3":73,"loser_le_zero":82,"positive":68}
    assert quality["denominator"]==150
    assert all(quality["counts"][k]==v for k,v in expected.items()),quality["counts"]
    reasons=reason_conservation(decisions,outcomes,rank_pass)
    authority={"schema":"R1_V5_EXACT_EVALUATION_AUTHORITY_V1","purpose":"EVALUATION_ONLY",
               "primary_replay_N":0,"new_fit_N":0,"model_inference_N":0,"capital":capital,
               "quality":quality,"winner_reason_conservation":reasons,
               "frozen_source_hashes":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [V5/"CAPITAL_MAX3_SLOT_RESERVE_V1_RESULT.json",V5/"CAPITAL_MAX3_SLOT_RESERVE_V1_DECISIONS.jsonl.gz",V5/"CAPITAL_MAX3_SLOT_RESERVE_V1_TRADES.jsonl.gz",V5/"CAPITAL_MAX3_SLOT_RESERVE_V1_CURVE.jsonl.gz",TEACHERS,STREAM]}}
    for name,data in (("V5_EXACT_EVALUATION_AUTHORITY.json",authority),("evaluation_only/OUTCOMES_EXACT_EVALUATION.json",outcomes),("evaluation_only/RANK_PASS_IDS.json",sorted(rank_pass))):
        p=OUT/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(public(data),ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    protected_ids=[d["entry_id"] for d in decisions if d.get("quantity",0)>=100 and d.get("funded_slot") in (1,2)]
    (OUT/"evaluation_only/PROTECTED100_IDS.json").write_text(json.dumps({"purpose":"EVALUATION_ONLY_RUNTIME_INPUT_FORBIDDEN","identity_N":len(protected_ids),"entry_ids":protected_ids},indent=2)+"\n")
    return authority


if __name__=="__main__":
    a=build()
    print(json.dumps({"status":"PASS","session_N":len(a["capital"]["session_ids"]),"windows_N":len(a["capital"]["windows"]),"funded_N":a["quality"]["denominator"],"quality_counts":a["quality"]["counts"],"protected_N":a["quality"]["protected_slot12"]["protected_identity_N"],"model_inference_N":0,"replay_N":0},ensure_ascii=False))
