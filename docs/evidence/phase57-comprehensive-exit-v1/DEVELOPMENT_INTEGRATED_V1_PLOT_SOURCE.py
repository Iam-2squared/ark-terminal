"""Render audited v1 CSV marks. NaN gaps retain every invalid valuation span."""
import argparse
import csv
import datetime as dt
import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def load(path):
    rows=list(csv.DictReader(path.open()))
    xs=[dt.datetime.fromisoformat(r["timestamp"]) for r in rows]
    equities=[float(r["equityJpy"]) if r["equityJpy"] else math.nan for r in rows]
    valid=[r["equityValid"]=="True" for r in rows]
    assert len(xs)==len(equities)==len(valid) and all((not math.isnan(v))==ok for v,ok in zip(equities,valid))
    return xs,equities,valid


def render(title, data, output):
    fig,ax=plt.subplots(figsize=(13,4.5),layout="constrained")
    first=None
    observed=[]
    last_valid=None
    for label,path in data:
        xs,ys,valid=load(path)
        line_x,line_y=[],[]
        for i,(x,y) in enumerate(zip(xs,ys)):
            if i and x.date()!=xs[i-1].date():
                line_x.append(x);line_y.append(math.nan)
            line_x.append(x);line_y.append(y)
        ax.plot(line_x,line_y,label=f"{label} ({sum(valid)}/{len(valid)} valid points)",
                linewidth=1.7,marker=".",markersize=2)
        if first is None:first=xs
        observed.extend(y for y in ys if not math.isnan(y))
        valid_stamps=[x for x,y in zip(xs,ys) if not math.isnan(y)]
        if valid_stamps:last_valid=max(last_valid or valid_stamps[-1],valid_stamps[-1])
    if last_valid is not None and last_valid<max(first):
        ax.axvspan(last_valid,max(first),color="#aaaaaa",alpha=.13,
                   label="No valid equity marks after last observed point")
    ax.axhline(1000000,linewidth=.8,linestyle="--",color="#888",label="Initial cash")
    ax.set_xlim(min(first),max(first))
    if observed:
        low,high=min(observed+[1000000]),max(observed+[1000000])
        pad=max((high-low)*.08,10000)
        ax.set_ylim(low-pad,high+pad)
    ax.set_title(title+" | Development, terminal-hold benchmark, NOT final EXIT")
    ax.set_ylabel("Causal marked equity (JPY); invalid = gap")
    ax.set_xlabel("2025 JST; no forward fill, no missing-auction sale")
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO,interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.grid(alpha=.2)
    ax.legend(loc="upper right",fontsize=8)
    fig.savefig(output,dpi=170)
    plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("csv_dir",type=Path)
    parser.add_argument("output_dir",type=Path)
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    im="IMMEDIATE";r1="ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF"
    for arm,label in ((im,"IM"),(r1,"R1")):
        render(label+" MAX3/4/5",[(f"MAX{n}",args.csv_dir/(arm+f"_MAX{n}.csv"))
                                 for n in (3,4,5)],
               args.output_dir/(label.lower()+"-max345.png"))
    render("MAX3 IM vs R1",[(label,args.csv_dir/(arm+"_MAX3.csv"))
                            for arm,label in ((im,"IM"),(r1,"R1"))],
           args.output_dir/"max3-im-vs-r1.png")
