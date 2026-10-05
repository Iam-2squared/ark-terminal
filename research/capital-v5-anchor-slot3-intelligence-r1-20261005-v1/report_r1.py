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
    lines=["# V5 Anchor Slot3 R1 — 固定結果", "",
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
              "## Quality", "", "|Profile|N|Loser ≤0|Positive >0|Weak <2|<3|Medium 3–<5|U5|U10|", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name,arm in [("V5",v5)]+[(n,arms.get(n,{})) for n in ("D","DR")]:
        q=arm.get("quality",{})
        if q.get("status")!="EVALUATED":lines.append(f"|{name}|NOT_EVALUATED|—|—|—|—|—|—|—|")
        else:
            c=q["counts"]
            vals=[q["denominator"]]+[c[k] for k in ("loser_le_zero","positive","Weak","below3","Medium","U5","U10")]
            lines.append(f"|{name}|"+"|".join(map(str,vals))+"|")
    lines += ["", "率の分母はfunded BUY unique identity N。Potential Weakと実現Loserは別指標。strict negativeとexact zero、gross loss、negative sessions、worst daily returnはQUALITY_AND_REALIZED_WINRATE.jsonに保存。", "",
              "## Slot1/2 protection", "", "元V5の41+59=100 unique identitiesは評価後のみjoin。全identity fundedと元Slot1/Slot2各group aggregate actual PnL非劣化を要求する。個別identityの数量/PnL下限は追加しない。"]
    for name in ("D","DR"):
        q=arms.get(name,{}).get("quality",{})
        p=q.get("protected_slot12")
        lines.append(f"- {name}: {p['status'] if p else 'NOT_EVALUATED'}")
    lines += ["", "## Slot3", "", "native planned/veto/veto outcome post-join/recovery/token transitions/Slot3 PnLは各decision/trade/token明細に保持。実際に成功したcausal BUYだけをrecoveredとして数える。未実行候補の回収数は未測定。", "",
              "## Winner miss", "", "U5 rank-pass113/U10 rank-pass47のfunded/Reserve/MAX3/cash等のterminal reasonsをconservationする。GAINED/LOST/COMMONの数量/PnL差は評価明細へ保存。", "",
              "## Intelligence", "", "pP/U2/U3/MRETはcompleted-past referenceのstrict-less rank。exact rank=1/2はHIGH。未来outcomeは評価専用、結果後threshold調整0。", "",
              "## Independent audit", ""]
    for name in ("D","DR"):
        q11=arms.get(name,{}).get("comparison",{}).get("gates",{}).get("Q11",{})
        lines.append(f"- {name}: {q11.get('status','NOT_EVALUATED')}")
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
    for name,data in outputs.items():
        (p/name).write_text(json.dumps(public(data),ensure_ascii=False,indent=2,allow_nan=False)+"\n")
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
