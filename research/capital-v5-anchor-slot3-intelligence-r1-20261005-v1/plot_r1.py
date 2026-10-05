"""Measured-only R1 plots. Float conversion is display-only, never gate input.

An incomplete candidate contributes no series/bars. Partial prefix economics
are never shown as rolling20/all38 results. All plot source values are saved.
"""
from pathlib import Path
from fractions import Fraction
import argparse
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter,MaxNLocator
from report_r1 import restore
from metrics_exact import json_read,public,exact

COLORS={"V5":"#273B65","D":"#16A58E","DR":"#EE9F34"}
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.titlesize":16,
                    "axes.labelsize":11,"axes.spines.top":False,"axes.spines.right":False,
                    "figure.facecolor":"#FAFCFF","axes.facecolor":"#FAFCFF","savefig.facecolor":"#FAFCFF"})


def style(ax):
    ax.grid(axis="y",color="#DDE4EE",linewidth=.7)
    ax.set_axisbelow(True)


def save(fig,out,name):
    fig.tight_layout()
    fig.savefig(out/(name+".png"),dpi=190,bbox_inches="tight")
    fig.savefig(out/(name+".svg"),bbox_inches="tight")
    plt.close(fig)


def measured_plot(v5,arms,out):
    out=Path(out);out.mkdir(exist_ok=True,parents=True)
    measured={"V5":v5,**{n:a for n,a in arms.items() if a.get("capital",{}).get("status")=="EVALUATED"}}
    missing=[n for n in ("D","DR") if n not in measured]
    missing_note="; ".join(n+": NOT_EVALUATED" for n in missing)
    source={"schema":"R1_MEASURED_ONLY_PLOT_VALUES_V1","gate_domain":"EXACT_RATIONAL",
            "float_conversion":"PLOT_COORDINATES_ONLY","window_reset_replay_N":0,
            "missing_arm_series":missing,"partial_prefix_plot_N":0,"panels":{}}
    basewins=v5["capital"]["windows"]
    x=list(range(1,20))
    labels=[w["start_session"][5:] for w in basewins]
    fig,ax=plt.subplots(figsize=(11,5.4))
    for n,a in measured.items():
        vals=[w["amount_from_1m"] for w in a["capital"]["windows"]]
        ax.plot(x,[float(v) for v in vals],color=COLORS[n],lw=2.3,label=n,marker="o",markersize=3)
        source["panels"].setdefault("rolling20_amount",{})[n]=vals
    ax.axhline(2_000_000,color="#AD6571",ls="--",lw=1.3,label="JPY 2,000,000 target")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,pos:f"{v/1_000_000:.2f}m"))
    ax.set(title="JPY 1,000,000 → 20 sessions",xlabel="Rolling20 start session (19 overlapping windows)",ylabel="Normalized ending amount (JPY)")
    ax.set_xticks(x[::3],labels[::3]);ax.legend(frameon=False,ncol=4,loc="upper left")
    style(ax)
    if missing_note:fig.text(.01,.005,missing_note+". No candidate series or fabricated values.",color="#657182",fontsize=10)
    save(fig,out,"01_ROLLING20_AMOUNT")
    fig,ax=plt.subplots(figsize=(11,4.8))
    for n in ("D","DR"):
        if n not in measured:continue
        vals=[1_000_000*(cw["growth"]-bw["growth"]) for bw,cw in zip(basewins,arms[n]["capital"]["windows"])]
        ax.plot(x,[float(v) for v in vals],color=COLORS[n],lw=2.2,marker="o",markersize=3,label=n)
        source["panels"].setdefault("paired20_delta",{})[n]=vals
    ax.axhline(0,color="#273B65",lw=1.2)
    ax.set(title="Paired 20-session change versus V5",xlabel="Same rolling20 start session",ylabel="Candidate minus V5 (JPY)")
    ax.set_xticks(x[::3],labels[::3]);ax.yaxis.set_major_formatter(FuncFormatter(lambda v,pos:f"{v:,.0f}"));style(ax)
    if len(measured)>1:ax.legend(frameon=False)
    else:ax.text(.5,.55,"D / DR NOT_EVALUATED\nNo complete candidate rolling20 series",ha="center",va="center",transform=ax.transAxes,color="#657182",fontsize=14)
    save(fig,out,"02_PAIRED20_DELTA")
    fig,ax=plt.subplots(figsize=(11,5.1))
    groups=["Positive","Loser","U5","U10","Medium"]
    nonbase=[n for n in ("D","DR") if n in measured]
    if not nonbase:
        q=v5["quality"]["counts"];vals=[q[k] for k in ("positive","loser_le_zero","U5","U10","Medium")]
        ax.bar(groups,vals,color=COLORS["V5"],width=.55,label="V5 measured baseline")
        for i,v in enumerate(vals):ax.text(i,v+1,str(v),ha="center",fontsize=10)
        source["panels"]["winner_loser_identity"]={"V5_only_measured_baseline":dict(zip(groups,vals)),"D":"NOT_EVALUATED","DR":"NOT_EVALUATED"}
        ax.text(.98,.96,"D / DR NOT_EVALUATED\nMaintained / gained / lost are unmeasured",ha="right",va="top",transform=ax.transAxes,color="#657182")
        ax.legend(frameon=False)
    else:
        data={}
        for n in nonbase:
            rows=arms[n]["diagnostics"]["gained_lost_common"]["rows"]
            entries={}
            for label in groups:
                def in_group(r,side):
                    present=r["relation"]!="CANDIDATE_ONLY" if side=="v5" else r["relation"]!="V5_ONLY"
                    if not present:return False
                    pot=exact(r["potential_pct_cell"]);pnl=r[side+"_pnl"]
                    return pnl>0 if label=="Positive" else pnl<=0 if label=="Loser" else pot>=5 if label=="U5" else pot>=10 if label=="U10" else 3<=pot<5
                b={r["entry_id"] for r in rows if in_group(r,"v5")};c={r["entry_id"] for r in rows if in_group(r,"candidate")}
                entries[label]={"maintained":len(b&c),"gained":len(c-b),"lost":len(b-c)}
            data[n]=entries
        positions=list(range(len(groups)*len(nonbase)));width=.24
        ticklabels=[f"{group}\n{n}" for group in groups for n in nonbase]
        for j,(kind,color) in enumerate((("maintained","#5B749E"),("gained","#16A58E"),("lost","#C85765"))):
            vals=[data[n][group][kind] for group in groups for n in nonbase]
            ax.bar([i+(j-1)*width for i in positions],vals,width=width,color=color,label=kind)
        ax.set_xticks(positions,ticklabels);ax.legend(frameon=False,ncol=3)
        source["panels"]["winner_loser_identity"]=data
    ax.set(title="Winner / loser identity preservation",ylabel="Unique funded BUY identities")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True));style(ax)
    save(fig,out,"03_WINNER_LOSER_IDENTITIES")
    fig,(a1,a2)=plt.subplots(1,2,figsize=(11,4.9),gridspec_kw={"width_ratios":[1.2,1]})
    vprotect=v5["quality"]["protected_slot12"]["groups"]
    slotnames=["Original Slot1","Original Slot2"]
    offsets={"V5":-.22,"D":0,"DR":.22}
    for n,a in measured.items():
        protection=a["quality"].get("protected_slot12")
        if not protection:continue
        vals=[g["v5_pnl"] if n=="V5" else g["candidate_pnl"] for g in protection["groups"]]
        a1.bar([i+offsets[n] for i in range(2)],[float(v) for v in vals],width=.2,color=COLORS[n],label=n)
        source["panels"].setdefault("protected_group_pnl",{})[n]=vals
    a1.set_xticks([0,1],slotnames);a1.set(title="Protected Slot1 / Slot2 groups",ylabel="Aggregate actual PnL (JPY)")
    a1.yaxis.set_major_formatter(FuncFormatter(lambda v,pos:f"{v/1000:.0f}k"));a1.legend(frameon=False);style(a1)
    if nonbase:
        for idx,n in enumerate(nonbase):
            slot=arms[n]["diagnostics"]["slot3"]
            vals=[slot["cohorts"][k]["observed_identity_N"] for k in ("veto","rescued")]
            a2.bar([i+(idx-(len(nonbase)-1)/2)*.28 for i in range(2)],vals,width=.27,color=COLORS[n],label=n)
            source["panels"].setdefault("slot3_interventions",{})[n]={"veto":vals[0],"rescued":vals[1]}
        a2.set_xticks([0,1],["Direct veto","Causal rescued BUY"]);a2.legend(frameon=False)
    else:
        a2.text(.5,.5,"D / DR NOT_EVALUATED\nSlot3 intervention economics\nnot measured over all38",ha="center",va="center",transform=a2.transAxes,color="#657182",fontsize=12)
        a2.set_xticks([])
    a2.set(title="Slot3 intervention",ylabel="Unique identities (complete arm only)")
    a2.yaxis.set_major_locator(MaxNLocator(integer=True));style(a2)
    save(fig,out,"04_SLOT_PROTECTION_AND_INTERVENTION")
    (out/"PLOT_SOURCE_VALUES.json").write_text(json.dumps(public(source),ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    return source


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--evaluation-dir",required=True);parser.add_argument("--out");parser.add_argument("--v5-authority",default=str(Path(__file__).parents[1]/"metrics/V5_EXACT_EVALUATION_AUTHORITY.json"));args=parser.parse_args()
    p=Path(args.evaluation_dir)
    arms={n:restore(json_read(p/(n+"_EXACT_EVALUATION.json"))) for n in ("D","DR") if (p/(n+"_EXACT_EVALUATION.json")).exists()}
    source=measured_plot(restore(json_read(args.v5_authority)),arms,args.out or p/"plots")
    print(json.dumps({"status":"PASS","plot_N":4,"partial_prefix_plot_N":0,"missing_arm_series":source["missing_arm_series"]}))
