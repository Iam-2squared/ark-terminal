"""Synthetic exact-gate boundaries only: no source/model/replay execution."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
from metrics_exact import exact, median_exact, mean_exact, maxdd_exact, compare_arm, select_research_candidate, public


def fixture():
    wins=[{"start_session":f"S{i:02}","end_session":f"S{i+19:02}","growth":F(6,5),"maxdd":{"maxdd":F(1,10)}} for i in range(19)]
    cap={"status":"EVALUATED","windows":wins,"statistics":{"minimum":F(6,5),"mean":F(6,5),"median":F(6,5),"maximum":F(6,5),"hit_2x_N":0,"below_1m_window_N":0},"full_maxdd":{"maxdd":F(1,10)}}
    q={"status":"EVALUATED","counts":{"U5":50,"U10":26,"Medium":27,"Weak":58,"below3":73,"loser_le_zero":82,"positive":68},"denominator":150,"gross_realized_loss_jpy":F(100),"negative_session_N":3,"worst_daily_return":F(-1,20),"protected_slot12":{"status":"PASS"}}
    return cap,q


def run():
    cases=[]
    def check(name,passed,detail=None):
        assert passed,name
        cases.append({"case":name,"status":"PASS","source":"SYNTHETIC_ONLY","detail":detail})
    check("DECIMAL_SOURCE_EXACT",exact("0.1")==F(1,10))
    try:
        exact(0.1)
    except ValueError:
        rejected=True
    else:
        rejected=False
    check("CONVENIENCE_FLOAT_SOURCE_REFUSED",rejected)
    check("MEDIAN_EXACT_EVEN",median_exact([F(1,3),F(2,3)])==F(1,2))
    check("MEAN_EXACT",mean_exact([F(1,3),F(1,7)])==F(5,21))
    dd=maxdd_exact(F(100),[{"session":"x","minute":540,"equity":"90"},{"session":"x","minute":541,"equity":"100"}])
    check("PRE_WINDOW_EQUITY_IS_INITIAL_PEAK",dd["maxdd"]==F(1,10))
    dd=maxdd_exact(F(100),[{"session":"x","minute":540,"equity":"100"},{"session":"x","minute":710,"equity":"80"},{"session":"x","minute":931,"equity":"100"}])
    check("ALL_MINUTE_VALID_POINTS_NOT_DAILY_OR_LUNCH_FILTER",dd["maxdd"]==F(1,5))
    bc,bq=fixture();cc,cq=deepcopy(bc),deepcopy(bq)
    cc["windows"][0]["growth"]-=F(1,10**30)
    cc["statistics"]["mean"]+=F(1,100)
    cc["statistics"]["median"]+=F(1,100)
    c=compare_arm(bc,cc,bq,cq,0,True)
    check("ONE_NEGATIVE_PAIRED_WINDOW_EVEN_TINY_FAILS_E1",c["gates"]["E1"]["status"]=="FAIL")
    check("AGGREGATE_GAIN_CANNOT_HIDE_PAIRED_REGRESSION",not c["eligible"])
    cc,cq=deepcopy(bc),deepcopy(bq)
    c=compare_arm(bc,cc,bq,cq,0,True)
    check("IDENTICAL_MEAN_MEDIAN_FAIL_STRICT_E2_E3",c["gates"]["E2"]["status"]==c["gates"]["E3"]["status"]=="FAIL")
    check("RATE_EQUIVALENCE_PASS_Q4_Q5",c["gates"]["Q4"]["status"]==c["gates"]["Q5"]["status"]=="PASS")
    check("LOSER_EQUIVALENCE_FAIL_STRICT_Q6",c["gates"]["Q6"]["status"]=="FAIL")
    cq["counts"]["loser_le_zero"]=81;cq["denominator"]=148
    c=compare_arm(bc,cc,bq,cq,0,True)
    check("LOSER_COUNT_AND_RATE_BOTH_STRICT_REQUIRED",c["gates"]["Q6"]["status"]=="FAIL")
    cq["counts"]["Weak"]=57;cq["denominator"]=140
    c=compare_arm(bc,cc,bq,cq,0,True)
    check("WEAK_COUNT_ALONE_NOT_ENOUGH",c["gates"]["Q4"]["status"]=="FAIL")
    cq["denominator"]=0
    c=compare_arm(bc,cc,bq,cq,0,True)
    check("ZERO_FUNDED_BUY_DENOMINATOR_NOT_PASS",c["gates"]["Q4"]["status"]=="FAIL")
    cc["windows"][0]["start_session"]="WRONG"
    c=compare_arm(bc,cc,bq,cq,0,True)
    check("EXACT19_WINDOW_ID_MISMATCH",c["gates"]["E0"]["status"]=="FAIL" and not c["eligible"])
    c=compare_arm(bc,{"status":"NOT_EVALUATED"},bq,{"status":"NOT_EVALUATED"},None,None)
    check("INCOMPLETE_ARM_ALL19_Q_UNEVALUATED_NO_ZERO_FILL",all(g["status"]=="NOT_EVALUATED" for g in c["gates"].values()) and c["paired19"] is None)
    bc,bq=fixture();cc=deepcopy(bc);cc["windows"][0]["maxdd"]["maxdd"]+=F(1,10**30)
    c=compare_arm(bc,cc,bq,bq,0,True)
    check("TINY_MTM_MAXDD_REGRESSION_FAIL",c["gates"]["E7"]["status"]=="FAIL")
    arm_d={"comparison":{"eligible":True},"capital":deepcopy(bc),"quality":deepcopy(bq)}
    arm_dr=deepcopy(arm_d)
    arm_d["quality"]["counts"]["loser_le_zero"]=70
    arm_d["quality"]["denominator"]=130
    arm_dr["quality"]["counts"]["loser_le_zero"]=71
    arm_dr["quality"]["denominator"]=150
    check("R1_WINNER_PRIORITY_LOSER_COUNT_ASC_NOT_RATE",select_research_candidate({"D":arm_d,"DR":arm_dr})=="D")
    arm_dr=deepcopy(arm_d)
    check("EXACT_WINNER_TIE_D",select_research_candidate({"D":arm_d,"DR":arm_dr})=="D")
    return {"schema":"R1_EXACT_METRICS_SYNTHETIC_CANARIES_V1","status":"PASS","case_N":len(cases),"cases":cases,"market_source_reads":0,"replays":0,"model_inferences":0,"new_fits":0}


if __name__=="__main__":
    p=Path(__file__).parents[1]/"metrics/METRICS_SYNTHETIC_CANARY.json"
    p.parent.mkdir(exist_ok=True,parents=True)
    result=run();p.write_text(json.dumps(public(result),ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="cases"}))
