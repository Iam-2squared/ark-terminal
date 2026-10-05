"""Post-run evaluator consumes ledgers only; never starts/restarts a replay.

Run manifest schema:
{"D":{"result":path,"decisions":path,"trades":path,"curves":path,"token_events":path},"DR":{...}}
Optional audit is {"D":{"independent_mismatch_N":0,"all_causal_canaries_pass":true},...}.
Missing arm is NOT_EVALUATED. Paths are explicit, with no source searching.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from metrics_exact import (json_read,jsonl_read,capital_metrics,quality_metrics,protected_audit,
                           reason_conservation,compare_arm,select_research_candidate,delta_ledger,
                           slot3_and_token_diagnostics,induced_miss_diagnostics,public)
from report_r1 import write_outputs,restore

ROOT=Path(__file__).parents[1]
V5=ROOT/"inputs/v5/capital_v5_slot_private"
EVAL=ROOT/"metrics/evaluation_only"


def evaluate_arm(name,paths,v5,v5_decisions,v5_trades,outcomes,rankpass,audit):
    missing=[key for key in ("result","decisions","trades","curves") if key not in paths or not Path(paths[key]).exists()]
    if missing:
        capital={"status":"NOT_EVALUATED","reasons":["ARM_OUTPUT_NOT_COMPLETE"],"missing":missing}
        quality={"status":"NOT_EVALUATED"}
        return {"capital":capital,"quality":quality,"comparison":compare_arm(v5["capital"],capital,v5["quality"],quality,None,None)}
    result=json_read(paths["result"])
    daily=result.get("daily_series",result.get("daily"))
    if daily is None:
        raise ValueError("Explicit arm result missing daily series")
    decisions,trades,curves=[jsonl_read(paths[k]) for k in ("decisions","trades","curves")]
    tokens=jsonl_read(paths["token_events"]) if paths.get("token_events") else []
    cap=capital_metrics(daily,curves,v5["capital"]["session_ids"])
    complete=cap["status"]=="EVALUATED"
    protection=protected_audit(v5_decisions,v5_trades,decisions,trades) if complete else None
    quality=quality_metrics(decisions,trades,outcomes,cap,protection)
    comparison=compare_arm(v5["capital"],cap,v5["quality"],quality,audit.get("independent_mismatch_N"),audit.get("all_causal_canaries_pass"))
    diagnostic={"slot3":slot3_and_token_diagnostics(decisions,trades,tokens,outcomes,complete),
                "induced_misses":induced_miss_diagnostics(v5_decisions,decisions,outcomes)}
    if complete:
        diagnostic["winner_reason_conservation"]=reason_conservation(decisions,outcomes,rankpass)
        diagnostic["gained_lost_common"]=delta_ledger(v5_trades,trades,outcomes,v5["capital"]["session_ids"])
    else:
        diagnostic["winner_reason_conservation"]={"status":"NOT_EVALUATED","reason":"PARTIAL_FULL_DENOMINATOR_NOT_CONSERVED"}
        diagnostic["gained_lost_common"]={"status":"NOT_EVALUATED","reason":"PARTIAL_COUNTS_NOT_OFFICIAL"}
    return {"name":name,"capital":cap,"quality":quality,"comparison":comparison,"diagnostics":diagnostic,
            "source_hashes":{str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths.values() if isinstance(p,str) and Path(p).is_file()}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--run-manifest",required=True);parser.add_argument("--audit");parser.add_argument("--out",default=str(ROOT/"metrics/final"));parser.add_argument("--status");parser.add_argument("--notes");parser.add_argument("--counts")
    args=parser.parse_args()
    manifest=json_read(args.run_manifest);audit=json_read(args.audit) if args.audit else {}
    v5=restore(json_read(ROOT/"metrics/V5_EXACT_EVALUATION_AUTHORITY.json"))
    vd=jsonl_read(V5/"CAPITAL_MAX3_SLOT_RESERVE_V1_DECISIONS.jsonl.gz");vt=jsonl_read(V5/"CAPITAL_MAX3_SLOT_RESERVE_V1_TRADES.jsonl.gz")
    outcomes=json_read(EVAL/"OUTCOMES_EXACT_EVALUATION.json");rankpass=set(json_read(EVAL/"RANK_PASS_IDS.json"))
    arms={name:evaluate_arm(name,manifest.get(name,{}),v5,vd,vt,outcomes,rankpass,audit.get(name,{})) for name in ("D","DR")}
    selected=select_research_candidate(arms)
    status=args.status or ("V5_ANCHOR_DEV_NONREGRESSION_CANDIDATE" if selected else "V5_ANCHOR_EXECUTION_INCOMPLETE" if any(a["capital"]["status"]!="EVALUATED" for a in arms.values()) else "V5_SLOT3_INCREMENT_NO_GO")
    notes=json_read(args.notes) if args.notes else None;counts=json_read(args.counts) if args.counts else None
    p=Path(args.out);p.mkdir(exist_ok=True,parents=True)
    for name,a in arms.items():(p/(name+"_EXACT_EVALUATION.json")).write_text(json.dumps(public(a),ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    write_outputs(p,v5,arms,status,counts,notes)
    (p/"GAINED_LOST_AND_TOKEN_RECOVERY.json").write_text(json.dumps(public({n:a["diagnostics"] for n,a in arms.items() if a.get("diagnostics")}),ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":status,"selectedResearchCandidate":selected,"activeCapitalChampion":"V5","selectedCapitalCandidate":None,"candidate_statuses":{n:a["comparison"]["status"] for n,a in arms.items()}},ensure_ascii=False))


if __name__=="__main__":
    main()
