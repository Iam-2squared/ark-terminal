"""R1 Japanese final report from saved exact evaluation evidence only."""
from __future__ import annotations
import csv
import json
from fractions import Fraction
from pathlib import Path
from metrics_exact import public, rounded_yen, select_research_candidate


def restore(value):
    if isinstance(value,dict):
        if set(("numerator","denominator")).issubset(value):
            return Fraction(value["numerator"],value["denominator"])
        return {k:restore(v) for k,v in value.items()}
    if isinstance(value,list):
        return [restore(v) for v in value]
    return value


def frac_display(x,places=8):
    if x is None:return "—"
    from decimal import Decimal,localcontext
    with localcontext() as ctx:
        ctx.prec=60
        return f"{Decimal(x.numerator)/Decimal(x.denominator):.{places}f}"


def render(v5,arms,status,counts=None,notes=None):
    selected=select_research_candidate(arms)
    complete=[n for n in ("D","DR") if arms.get(n,{}).get("capital",{}).get("status")=="EVALUATED"]
    verdict=("V5の全E/Q保護条件を満たすDevelopment研究候補を確認した。" if selected else
             "未完走・未実行armがあり、D/DR全体のV5超過判定は測定不能。" if len(complete)<2 else
             "V5の全E/Q保護条件を満たす研究候補はない。V5を維持する。")
    lines=["# V5 Anchor Slot3 R1 — 固定結果", "",
           verdict, "",
           f"activeCapitalChampion=V5 / selectedResearchCandidate={selected or 'null'} / selectedCapitalCandidate=null / championUpdated=false。状態: `{status}`。", "",
           "## 100万円 → 20 sessions", "",
           "同じ連結38-session系列から切り出した19窓の正規化値。各窓を100万円・保有0へresetしたReplayではない。", "",
           "|Profile|Min ¥|Mean ¥|Median ¥|Max ¥|2x|", "|---|---:|---:|---:|---:|---:|"]
    for name,arm in [("V5",v5)]+[(name,arms.get(name,{})) for name in ("D","DR")]:
        cap=arm.get("capital",{})
        if cap.get("status")!="EVALUATED":
            lines.append(f"|{name}|NOT_EVALUATED|NOT_EVALUATED|NOT_EVALUATED|NOT_EVALUATED|NOT_EVALUATED|")
        else:
            s=cap["statistics"]
            yen=[rounded_yen(s[k]*1_000_000) for k in ("minimum","mean","median","maximum")]
            lines.append(f"|{name}|"+"|".join(yen)+f"|{s['hit_2x_N']}/19|")
    lines += ["", "## Paired19 noninferiority", "",
              "|Profile|better|equal|worse|最悪差 ¥|19/19|", "|---|---:|---:|---:|---:|---|"]
    for name in ("D","DR"):
        comp=arms.get(name,{}).get("comparison",{})
        pair=comp.get("paired19")
        if pair is None:lines.append(f"|{name}|—|—|—|—|NOT_EVALUATED|")
        else:
            fact=comp["gates"]["E1"]["facts"]
            lines.append(f"|{name}|{fact['better_N']}|{fact['equal_N']}|{fact['worse_N']}|{rounded_yen(min(p['yen_delta'] for p in pair))}|{comp['gates']['E1']['status']}|")
    lines += ["", "## Drawdown", "", "|Profile|全38 minute-MTM MaxDD|各対応20-window MaxDD|", "|---|---:|---|"]
    for name,arm in [("V5",v5)]+[(n,arms.get(n,{})) for n in ("D","DR")]:
        cap=arm.get("capital",{})
        if cap.get("status")!="EVALUATED":lines.append(f"|{name}|NOT_EVALUATED|NOT_EVALUATED|")
        else:
            check="基準" if name=="V5" else arm["comparison"]["gates"]["E7"]["status"]
            lines.append(f"|{name}|{frac_display(cap['full_maxdd']['maxdd']*100,6)}%|{check}|")
    lines += ["", "各窓の開始前EOD資産を初期peakとし、窓内の全有効minute-MTM点で再計算した。明細はPAIRED_WINDOW_MAXDD.json。", "",
              "|20-session窓|V5 MaxDD|D MaxDD|DR MaxDD|", "|---|---:|---:|---:|"]
    for i,w in enumerate(v5.get("capital",{}).get("windows") or []):
        vals=[frac_display(w["maxdd"]["maxdd"]*100,6)+"%"]
        for n in ("D","DR"):
            cap=arms.get(n,{}).get("capital",{})
            vals.append(frac_display(cap["windows"][i]["maxdd"]["maxdd"]*100,6)+"%" if cap.get("status")=="EVALUATED" else "NOT_EVALUATED")
        lines.append(f"|{w['start_session']}–{w['end_session']}|"+"|".join(vals)+"|")
    lines += ["",
              "## Quality", "", "|Profile|N|Loser ≤0|Positive >0|Weak <2|<3|Medium 3–<5|U5|U10|", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name,arm in [("V5",v5)]+[(n,arms.get(n,{})) for n in ("D","DR")]:
        q=arm.get("quality",{})
        if q.get("status")!="EVALUATED":lines.append(f"|{name}|NOT_EVALUATED|—|—|—|—|—|—|—|")
        else:
            c=q["counts"]
            vals=[q["denominator"]]+[c[k] for k in ("loser_le_zero","positive","Weak","below3","Medium","U5","U10")]
            lines.append(f"|{name}|"+"|".join(map(str,vals))+"|")
    lines += ["", "率の分母はfunded BUY unique identity N。Potential Weakと実現Loserは別指標。", "",
              "|Profile|Loser率|strict negative|exact zero|gross loss ¥|negative sessions|worst daily return|", "|---|---:|---:|---:|---:|---:|---:|"]
    for name,arm in [("V5",v5)]+[(n,arms.get(n,{})) for n in ("D","DR")]:
        q=arm.get("quality",{})
        if q.get("status")!="EVALUATED":lines.append(f"|{name}|NOT_EVALUATED|—|—|—|—|—|")
        else:lines.append(f"|{name}|{frac_display(q['rates']['loser_le_zero']*100,6)}%|{q['counts']['strict_negative']}|{q['counts']['exact_zero']}|{rounded_yen(q['gross_realized_loss_jpy'])}|{q['negative_session_N']}|{frac_display(q['worst_daily_return']*100,6)}%|")
    lines += ["",
              "## Slot1/2 protection", "", "元V5の41+59=100 unique identitiesは評価後のみjoin。全identity fundedと元Slot1/Slot2各group aggregate actual PnL非劣化を要求する。個別identityの数量/PnL下限は追加しない。"]
    for name in ("D","DR"):
        q=arms.get(name,{}).get("quality",{})
        p=q.get("protected_slot12")
        lines.append(f"- {name}: {p['status'] if p else 'NOT_EVALUATED'}")
    lines += ["", "|Profile|元Slot|funded/required|V5 PnL ¥|candidate PnL ¥|差 ¥|", "|---|---:|---:|---:|---:|---:|"]
    for n in ("D","DR"):
        p=arms.get(n,{}).get("quality",{}).get("protected_slot12")
        if p:
            for g in p["groups"]:lines.append(f"|{n}|{g['original_v5_slot']}|{g['funded_N']}/{g['expected_identity_N']}|{rounded_yen(g['v5_pnl'])}|{rounded_yen(g['candidate_pnl'])}|{rounded_yen(g['pnl_delta'])}|")
        else:lines.append(f"|{n}|—|NOT_EVALUATED|—|—|—|")
    lines += ["", "## Slot3", "", "実際に成功したcausal BUYだけをrecoveredとして数える。veto後のFrozen outcome joinは評価専用で、実際の回避損益とは呼ばない。未完走armの観測値はprefix diagnosticであり、公式全期間指標ではない。", "",
              "|Profile|scope|native planned3|veto|veto Frozen loser/positive/unknown|rescued|rescued U5/U10/Medium/Weak|closed Slot3 PnL ¥|", "|---|---|---:|---:|---|---:|---|---:|"]
    slot_notes=[]
    for n in ("D","DR"):
        slot=arms.get(n,{}).get("diagnostics",{}).get("slot3")
        if not slot:lines.append(f"|{n}|NOT_EVALUATED|—|—|—|—|—|—|");continue
        vc=slot["cohorts"]["veto"];rc=slot["cohorts"]["rescued"];v=vc["counts"];r=rc["counts"]
        lines.append(f"|{n}|{slot['scope']}|{slot['native_planned_slot3_observed_N']}|{vc['observed_identity_N']}|{v['frozen_realized_le_zero']}/{v['frozen_realized_positive']}/{v['frozen_realized_unknown']}|{rc['observed_identity_N']}|{r['U5']}/{r['U10']}/{r['Medium']}/{r['Weak']}|{rounded_yen(slot['closed_slot3_pnl_jpy'])}|")
        slot_notes += ["",f"{n} token action counts: `{json.dumps(slot['tokens']['action_counts'],ensure_ascii=False)}`。terminal reasons: `{json.dumps(slot['tokens']['terminal_reason_counts'],ensure_ascii=False)}`。", ""]
    lines += slot_notes
    lines += ["", "## Winner miss", "", "U5 rank-pass113/U10 rank-pass47のterminal reasonsをconservationする。", "",
              "|Profile|Potential|分母|funded|Reserve|MAX3|cash/lot|D veto|other|conserved|", "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for n,arm in [("V5",v5)]+[(x,arms.get(x,{})) for x in ("D","DR")]:
        cons=arm.get("winner_reason_conservation") if n=="V5" else arm.get("diagnostics",{}).get("winner_reason_conservation")
        if not cons or cons.get("status")=="NOT_EVALUATED":lines.append(f"|{n}|U5/U10|NOT_EVALUATED|—|—|—|—|—|—|—|");continue
        for label in ("U5","U10"):
            item=cons[label];rc=item["reason_counts"];groups={k:0 for k in ("funded","reserve","max3","cash","veto","other")}
            for reason,num in rc.items():
                k="funded" if reason=="FUNDED" else "veto" if reason=="V5_SLOT3_UNANIMOUS_LOW_SHIELD_REJECT" else "max3" if reason=="MAX_POSITION_CAP" or "MAX3" in reason else "reserve" if "RESERVE" in reason else "cash" if "CASH" in reason or "LOT" in reason else "other"
                groups[k]+=num
            lines.append(f"|{n}|{label}|{item['denominator']}|"+"|".join(str(groups[k]) for k in ("funded","reserve","max3","cash","veto","other"))+f"|{item['conserved']}|")
    lines += ["", "|Profile|relation|IDs|U5|U10|Medium|Weak|positive|Loser|", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    delta_notes=[]
    for n in ("D","DR"):
        delta=arms.get(n,{}).get("diagnostics",{}).get("gained_lost_common",{})
        if delta.get("gained_lost"):
            for relation,g in delta["gained_lost"].items():lines.append(f"|{n}|{relation}|"+"|".join(str(g[k]) for k in ("identity_N","U5","U10","Medium","Weak","positive","loser"))+"|")
            common=[r for r in delta["rows"] if r["relation"]=="COMMON"]
            qp=sum(r["candidate_quantity"]!=r["v5_quantity"] for r in common)
            pd=sum((r["pnl_delta"] for r in common),Fraction(0))
            delta_notes += ["",f"{n}: COMMON={len(common)}、数量差あり={qp}、COMMON PnL差=¥{rounded_yen(pd)}。全38session対称LOOは保存trade差分集中度診断で、削除後Replay/rolling20ではない。", ""]
        else:lines.append(f"|{n}|NOT_EVALUATED|—|—|—|—|—|—|—|")
        misses=arms.get(n,{}).get("diagnostics",{}).get("induced_misses")
        if misses:delta_notes += ["",f"{n} reason changes: `{json.dumps(misses['counts'],ensure_ascii=False)}`（観測ledger join）。", ""]
    lines += delta_notes
    lines += ["", "## Intelligence", "", "pP/U2/U3/MRETはcompleted-past referenceのstrict-less rank。exact rank=1/2はHIGH。未来outcomeは評価専用、結果後threshold調整0。", "",
              "|Profile|cohort|head|N|min rank|mean rank|max rank|", "|---|---|---|---:|---:|---:|---:|"]
    for n in ("D","DR"):
        slot=arms.get(n,{}).get("diagnostics",{}).get("slot3")
        if not slot:lines.append(f"|{n}|NOT_EVALUATED|—|—|—|—|—|");continue
        for cohort in ("veto","rescued"):
            rows=slot["cohorts"][cohort]["rows"]
            heads=sorted({h for row in rows for h in (row.get("four_ranks") or {})})
            if not heads:lines.append(f"|{n}|{cohort}|—|0 observed|—|—|—|")
            for h in heads:
                vals=[Fraction(r["four_ranks"][h]["numerator"],r["four_ranks"][h]["denominator"]) for r in rows if r.get("four_ranks",{}).get(h,{}).get("available")]
                if vals:lines.append(f"|{n}|{cohort}|{h}|{len(vals)}|{frac_display(min(vals),6)}|{frac_display(sum(vals,Fraction(0))/len(vals),6)}|{frac_display(max(vals),6)}|")
    lines += ["", "## Independent audit", ""]
    for name in ("D","DR"):
        q11=arms.get(name,{}).get("comparison",{}).get("gates",{}).get("Q11",{})
        lines.append(f"- {name}: {q11.get('status','NOT_EVALUATED')}")
    lines += ["", "|Gate|D|DR|", "|---|---|---|"]
    for gid in [f"E{i}" for i in range(8)]+[f"Q{i}" for i in range(1,12)]:
        vals=[arms.get(n,{}).get("comparison",{}).get("gates",{}).get(gid,{}).get("status","NOT_EVALUATED") for n in ("D","DR")]
        lines.append(f"|{gid}|"+"|".join(vals)+"|")
    lines += ["", "## Fixed STOP / next bottleneck", "",
              "このcycle終了時もV5を保持。全E0–E7/Q1–Q11 PASSでも研究候補の提示まで。追加arm/fit/threshold retune/注文/main merge/Champion切替0。", "",
              "Exposure=ITERATIVE_DEVELOPMENT_EVIDENCE。Fresh/OOS評価ではない。19窓は重複し、将来の非劣化・無損失・productionReadyを保証しない。"]
    if notes:
        lines += ["", "保存された終了理由:", ""]+[f"- {note}" for note in notes]
    if counts:
        lines += ["", "実行回数: `"+json.dumps(counts,ensure_ascii=False)+"`。"]
    cap=v5.get("capital",{})
    if cap.get("status")=="EVALUATED":
        lines += ["", "## Secondary appendix", "", f"V5全38-session末EOD資産: ¥{rounded_yen(cap['final38_equity_secondary_only'])}。20-session Primaryとは別。"]
    return "\n".join(lines)+"\n"


def write_outputs(out_dir,v5,arms,status,counts=None,notes=None):
    p=Path(out_dir);p.mkdir(parents=True,exist_ok=True)
    outputs={"QUALITY_AND_REALIZED_WINRATE.json":{"V5":v5.get("quality"),**{n:arms.get(n,{}).get("quality",{"status":"NOT_EVALUATED"}) for n in ("D","DR")}},
             "NONREGRESSION_DECISION.json":{"schema":"R1_EXACT_ALL19_AND_QUALITY_GATES_V1","status":status,"selectedResearchCandidate":select_research_candidate(arms),"activeCapitalChampion":"V5","selectedCapitalCandidate":None,"championUpdated":False,"arms":{n:arms.get(n,{}).get("comparison",{"status":"NOT_EVALUATED"}) for n in ("D","DR")}},
             "PAIRED_WINDOW_MAXDD.json":{"V5":v5.get("capital",{}).get("windows"),**{n:arms.get(n,{}).get("capital",{}).get("windows") for n in ("D","DR")}},
             "PROTECTED_SLOT12_AUDIT.json":{n:arms.get(n,{}).get("quality",{}).get("protected_slot12") for n in ("D","DR")}}
    loss_tail={}
    for name,arm in [("V5",v5)]+[(n,arms.get(n,{})) for n in ("D","DR")]:
        q=arm.get("quality",{})
        if q.get("status")!="EVALUATED":
            loss_tail[name]={"status":"NOT_EVALUATED"};continue
        c=q["counts"]
        loss_tail[name]={"status":"EVALUATED","gross_profit_jpy":q["gross_realized_profit_jpy"],
                         "gross_loss_jpy":q["gross_realized_loss_jpy"],"net_jpy":q["net_realized_pnl_jpy"],
                         "profit_factor":q["profit_factor"],"mean_positive_pnl_jpy":q["gross_realized_profit_jpy"]/c["positive"] if c["positive"] else None,
                         "mean_strict_negative_pnl_jpy":-q["gross_realized_loss_jpy"]/c["strict_negative"] if c["strict_negative"] else None,
                         "mean_nonpositive_pnl_jpy":-q["gross_realized_loss_jpy"]/c["loser_le_zero"] if c["loser_le_zero"] else None,
                         "strict_negative_N":c["strict_negative"],"exact_zero_N":c["exact_zero"],
                         "negative_session_N":q["negative_session_N"],"worst_daily_return":q["worst_daily_return"],
                         "leave_one_session_out":arm.get("diagnostics",{}).get("gained_lost_common",{}).get("leave_one_session_out")}
    outputs["LOSS_AMOUNT_AND_TAIL_DIAGNOSTICS.json"]=loss_tail
    for name,data in outputs.items():
        (p/name).write_text(json.dumps(public(data),ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    with (p/"DAILY_RETURNS.csv").open("w",newline="",encoding="utf-8") as f:
        cols=["session"]
        for n in ("V5","D","DR"):cols += [n+"_status",n+"_return_numerator",n+"_return_denominator",n+"_starting_equity_cell",n+"_ending_equity_cell"]
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader()
        indexes={n:{d["session"]:d for d in a.get("capital",{}).get("daily") or []} for n,a in [("V5",v5)]+[(n,arms.get(n,{})) for n in ("D","DR")]}
        for s in v5.get("capital",{}).get("session_ids",[]):
            row={"session":s}
            for n in ("V5","D","DR"):
                d=indexes[n].get(s);row[n+"_status"]="EVALUATED" if d else "NOT_EVALUATED"
                if d:row.update({n+"_return_numerator":d["exact_return"].numerator,n+"_return_denominator":d["exact_return"].denominator,n+"_starting_equity_cell":d["starting_equity_cell"],n+"_ending_equity_cell":d["ending_equity_cell"]})
            writer.writerow(row)
    with (p/"PAIRED_ROLLING20_JPY.csv").open("w",newline="",encoding="utf-8") as f:
        cols=["start_session","end_session","V5_growth_numerator","V5_growth_denominator","V5_yen_display"]
        for n in ("D","DR"):cols += [n+"_status",n+"_growth_numerator",n+"_growth_denominator",n+"_yen_display",n+"_delta_numerator",n+"_delta_denominator",n+"_noninferior"]
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader()
        for i,w in enumerate(v5.get("capital",{}).get("windows") or []):
            row={"start_session":w["start_session"],"end_session":w["end_session"],"V5_growth_numerator":w["growth"].numerator,"V5_growth_denominator":w["growth"].denominator,"V5_yen_display":rounded_yen(w["amount_from_1m"])}
            for n in ("D","DR"):
                cap=arms.get(n,{}).get("capital",{});row[n+"_status"]=cap.get("status","NOT_EVALUATED")
                if cap.get("status")=="EVALUATED":
                    cw=cap["windows"][i];d=cw["growth"]-w["growth"]
                    row.update({n+"_growth_numerator":cw["growth"].numerator,n+"_growth_denominator":cw["growth"].denominator,n+"_yen_display":rounded_yen(cw["amount_from_1m"]),n+"_delta_numerator":d.numerator,n+"_delta_denominator":d.denominator,n+"_noninferior":d>=0})
            writer.writerow(row)
    (p/"REPORT_FINAL-ja.md").write_text(render(v5,arms,status,counts,notes),encoding="utf-8")
