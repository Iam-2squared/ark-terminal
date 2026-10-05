"""Schema normalization only; imports neither primary nor independent evaluator.

The independent evaluator's own saved values must already exist. All compared
numeric domains are numerator/denominator pairs; display decimals are ignored.
"""
from fractions import Fraction
from pathlib import Path
import argparse
import hashlib
import json


def rational(x):
    return Fraction(x["numerator"],x["denominator"])


def compare(primary,independent):
    checks=[]
    def add(key,a,b):checks.append({"field":key,"match":a==b})
    p,i=primary["capital"],independent["capital"]
    add("capital.status",p["status"],i["status"])
    if p["status"]!="EVALUATED" or i["status"]!="EVALUATED":
        return {"status":"NOT_EVALUATED","checks":checks,"mismatch_N":sum(not c["match"] for c in checks)}
    add("capital.session_ids",p["session_ids"],i["session_ids"])
    add("capital.window_N",len(p["windows"]),len(i["windows"]))
    for n,(pw,iw) in enumerate(zip(p["windows"],i["windows"])):
        for key in ("start_session","end_session","hit_2x","below_1m"):add(f"window{n}.{key}",pw[key],iw[key])
        for key in ("growth","amount_from_1m"):add(f"window{n}.{key}",rational(pw[key]),rational(iw[key]))
        add(f"window{n}.maxdd",rational(pw["maxdd"]["maxdd"]),rational(iw["maxdd"]))
        add(f"window{n}.point_N",pw["maxdd"]["valid_minute_point_N"],iw["point_N"])
    for key in ("minimum","mean","median","maximum"):
        add("statistics."+key,rational(p["statistics"][key]),rational(i["statistics"][key]))
    for key in ("hit_2x_N","below_1m_window_N"):
        add("statistics."+key,p["statistics"][key],i["statistics"][key])
    add("capital.full_maxdd",rational(p["full_maxdd"]["maxdd"]),rational(i["full_maxdd"]))
    for key in ("negative_session_N",):add("capital."+key,p[key],i[key])
    for key in ("worst_daily_return","final38_equity_secondary_only"):
        add("capital."+key,rational(p[key]),rational(i[key]))
    pq,iq=primary["quality"],independent["quality"]
    add("quality.denominator",pq["denominator"],iq["denominator"])
    for key in pq["counts"]:
        add("quality.count."+key,pq["counts"][key],iq["count"][key])
        add("quality.rate."+key,rational(pq["rates"][key]),rational(iq["rate"][key]))
    add("quality.gross_loss",rational(pq["gross_realized_loss_jpy"]),rational(iq["gross_loss"]))
    for pg in pq["protected_slot12"]["groups"]:
        slot=str(pg["original_v5_slot"]);ig=iq["protectedSlot12"][slot]
        add("protection."+slot+".groupN",pg["identity_N"],ig["group_N"])
        add("protection."+slot+".fundedN",pg["funded_N"],ig["funded_N"])
        add("protection."+slot+".candidatePnl",rational(pg["candidate_pnl"]),rational(ig["candidate_group_pnl"]))
        add("protection."+slot+".V5Pnl",rational(pg["v5_pnl"]),rational(ig["V5_group_pnl"]))
        add("protection."+slot+".PASS",pg["all_identities_funded"] and pg["aggregate_pnl_noninferior"],ig["PASS"])
    pending=[]
    for gid,pg in primary["comparison"]["gates"].items():
        if pg["status"]=="NOT_EVALUATED" and gid=="Q11":pending.append("Q11");continue
        add("gate."+gid,pg["status"]=="PASS",independent["gates"][gid])
    facts=primary["comparison"]["gates"]["E1"]["facts"]
    for pk,ik in (("better_N","better"),("equal_N","equal"),("worse_N","worse")):
        add("paired19."+ik,facts[pk],independent["paired19"][ik])
    add("paired19.worst_delta",rational(facts["worst_growth_delta"]),rational(independent["paired19"]["worst_paired_delta"]))
    add("eligible",primary["comparison"]["eligible"],independent["eligible"])
    mismatches=[c for c in checks if not c["match"]]
    return {"status":"PASS" if not mismatches else "FAIL","comparison_N":len(checks),"mismatch_N":len(mismatches),
            "primary_audit_pending_gates":pending,"checks":checks,"mismatches":mismatches,
            "schema_normalization_only":True,"evaluator_import_N":0,"replay_N":0,"numeric_tolerance":0}


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--primary",required=True);parser.add_argument("--independent",required=True);parser.add_argument("--out",required=True);args=parser.parse_args()
    pp,ip=Path(args.primary),Path(args.independent)
    p=json.loads(pp.read_text());i=json.loads(ip.read_text())
    result=compare(p,i)
    result["source_sha256"]={"primary":hashlib.sha256(pp.read_bytes()).hexdigest(),"independent":hashlib.sha256(ip.read_bytes()).hexdigest()}
    Path(args.out).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("checks","mismatches","source_sha256")}))
