"""Fixed V2 PRR figures after route freeze; no threshold or candidate selection."""
from __future__ import annotations

import collections
import gzip
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "docs/evidence/phase57-prr-numerical-recovery"
F = E / "figures"
COLORS = ("#2463A5", "#D97B2D")


def rows(name):
    with gzip.open(E / name, "rt") as f:
        return [json.loads(s) for s in f]


def save(name, title, xlabel, ylabel):
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(axis="y", alpha=.18)
    plt.tight_layout()
    plt.savefig(F / name, dpi=170)
    plt.close()


def main():
    F.mkdir(parents=True, exist_ok=True)
    anatomy = json.loads((E / "RANK_ANATOMY.json").read_text())
    gate = json.loads((E / "ROUTE_FEASIBILITY.json").read_text())
    decisions = rows("CANONICAL_OOF.jsonl.gz")
    deciles = anatomy["deciles"]
    for h in (5, 10):
        actual = [deciles[f"combined:head{h}:{d}"][f"actual{h}Rate"] for d in range(10)]
        n = [deciles[f"combined:head{h}:{d}"]["n"] for d in range(10)]
        plt.figure(figsize=(8.2, 4.4))
        plt.bar(range(10), actual, color=COLORS[0])
        for i, (v, k) in enumerate(zip(actual, n)):
            if v is not None:
                plt.text(i, v, f"N={k}", ha="center", va="bottom", fontsize=7)
        plt.xticks(range(10), [f"{i*10}-{(i+1)*10}" for i in range(10)],
                   rotation=40, ha="right")
        save(f"0{1 if h == 5 else 2}_head{h}_decile_actual.png",
             f"Head >= {h}%: training-reference rank decile vs actual rate",
             "Fold-local TRAIN percentile decile", "Evaluator rate")
        med = [deciles[f"combined:head{h}:{d}"]["medianUpsidePct"] for d in range(10)]
        plt.figure(figsize=(8.2, 4.4))
        plt.plot(range(10), med, marker="o", color=COLORS[0])
        plt.xticks(range(10), [f"{i*10}-{(i+1)*10}" for i in range(10)],
                   rotation=40, ha="right")
        save(f"0{3 if h == 5 else 4}_head{h}_median_upside.png",
             f"Head >= {h}%: rank decile vs median upside",
             "Fold-local TRAIN percentile decile", "Median post-Entry upside (%)")
    labels = ["LOW5/LOW10", "LOW5/HIGH10", "HIGH5/LOW10", "HIGH5/HIGH10"]
    keys = ["combined:LOW5:LOW10", "combined:LOW5:HIGH10",
            "combined:HIGH5:LOW10", "combined:HIGH5:HIGH10"]
    values = [anatomy["quadrants"][key]["n"] for key in keys]
    plt.figure(figsize=(7.5, 4.2))
    bars = plt.bar(labels, values, color=[COLORS[1], "#888", "#888", COLORS[0]])
    plt.bar_label(bars)
    plt.xticks(rotation=20, ha="right")
    save("05_median_quadrants.png", "Frozen median quadrants (N=1,614)",
         "Two-head rank state", "Entries")
    for h in (5, 10):
        pairs = [x for x in gate["perArmHead"] if x["head"] == h]
        x = np.arange(2)
        plt.figure(figsize=(6.6, 4.2))
        plt.bar(x-.18, [p["defensiveRate"] for p in pairs], width=.36,
                label="Defensive", color=COLORS[1])
        plt.bar(x+.18, [p["defaultRate"] for p in pairs], width=.36,
                label="Default", color=COLORS[0])
        plt.xticks(x, ["IM", "R1"])
        plt.legend()
        save(f"0{6 if h == 5 else 7}_route_rate_{h}.png",
             f"Actual >= {h}% rate by fixed route",
             "Frozen Entry arm", "Evaluator rate")
    sessions = sorted({r["session"] for r in decisions})
    plt.figure(figsize=(10, 4.2))
    for arm, color in zip(("IM", "R1"), COLORS):
        shares = []
        for session in sessions:
            group = [r for r in decisions if r["arm"] == arm and r["session"] == session]
            shares.append(sum(r["routeDecision"] == "DEFENSIVE_ELIGIBLE" for r in group) /
                          len(group) if group else np.nan)
        plt.plot(range(len(sessions)), shares, marker=".", label=arm, color=color)
    plt.xticks(range(0, len(sessions), 3),
               [sessions[i] for i in range(0, len(sessions), 3)],
               rotation=45, ha="right")
    plt.legend()
    save("08_defensive_share_session.png", "Defensive share by session",
         "Development session", "Share")
    routes = ("DEFENSIVE_ELIGIBLE", "CONTROL_DEFAULT")
    buckets = ("<1", "1-3", "3-5", "5-10", ">=10")
    grouped = {route: [r for r in decisions if r["routeDecision"] == route]
               for route in routes}
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bottoms = np.zeros(2)
    for i, b in enumerate(buckets):
        counts = [sum((r["teacherUpsidePctEvaluatorOnly"] < 1 if b == "<1" else
                       1 <= r["teacherUpsidePctEvaluatorOnly"] < 3 if b == "1-3" else
                       3 <= r["teacherUpsidePctEvaluatorOnly"] < 5 if b == "3-5" else
                       5 <= r["teacherUpsidePctEvaluatorOnly"] < 10 if b == "5-10" else
                       r["teacherUpsidePctEvaluatorOnly"] >= 10) for r in grouped[route])
                  for route in routes]
        ax.bar(range(2), counts, bottom=bottoms, label=b)
        bottoms += counts
    ax.set_xticks(range(2), ["Defensive", "Default"])
    ax.set_ylabel("Entries")
    ax.set_title("Evaluator upside buckets by immutable route")
    ax.legend(title="Upside %", ncol=5, fontsize=7)
    fig.tight_layout()
    fig.savefig(F / "10_upside_bucket_by_route.png", dpi=170)
    plt.close(fig)
    if (E / "LAYER_A_RESULT.json").exists():
        econ = json.loads((E / "LAYER_A_RESULT.json").read_text())
        for h in (5, 10):
            vals = [float(econ["byRankDecile"][f"IM:head{h}:{i}"]["ccmgControlDeltaJpy"]) +
                    float(econ["byRankDecile"][f"R1:head{h}:{i}"]["ccmgControlDeltaJpy"])
                    for i in range(10)]
            plt.figure(figsize=(8.2, 4.2))
            plt.bar(range(10), vals, color=[COLORS[0] if v >= 0 else COLORS[1] for v in vals])
            plt.xticks(range(10), [f"{i*10}-{(i+1)*10}" for i in range(10)],
                       rotation=40, ha="right")
            save(f"09_head{h}_routed_delta_by_decile.png",
                 f"Primary CCMG-Control PnL delta, head {h} decile",
                 "Fold-local TRAIN percentile decile", "Exact paired delta (JPY)")
        winner = econ["winner"]
        labels = [f"{a}>={h}" for a in ("IM", "R1") for h in (5, 10)]
        x = np.arange(4)
        plt.figure(figsize=(8, 4.3))
        for index, (key, color, title) in enumerate((
            ("controlPnlJpy", "#2463A5", "Control"),
            ("ccmgPnlJpy", "#aaa", "CCMG"),
            ("routedPnlJpy", "#D97B2D", "PRR"))):
            plt.bar(x+(index-1)*.24, [float(winner[k][key]) for k in labels],
                    width=.24, color=color, label=title)
        plt.xticks(x, labels)
        plt.legend()
        save("11_primary_winner_pnl.png", "Primary Winner cohort aggregate PnL",
             "Arm / evaluator cohort", "JPY on known paired")
        low = econ["lowUpsideLt5"]
        plt.figure(figsize=(5.5, 4.2))
        bars = plt.bar(("IM", "R1"), [float(low[a]["pairedDeltaJpy"]) for a in ("IM", "R1")],
                       color=COLORS[1])
        plt.bar_label(bars, fmt="%.0f")
        save("12_primary_lt5_delta.png", "Primary <5% routed-Control delta",
             "Arm", "JPY")
        defensive = econ["defensiveRoute"]
        plt.figure(figsize=(5.5, 4.2))
        bars = plt.bar(("IM", "R1"),
            [float(defensive[a]["pairedDeltaJpy"]) for a in ("IM", "R1")],
            color=COLORS[1])
        plt.bar_label(bars, fmt="%.0f")
        save("13_primary_defensive_delta.png", "Primary defensive-route paired value",
             "Arm", "CCMG-Control (JPY)")
        overall = econ["perArmOverall"]
        plt.figure(figsize=(5.5, 4.2))
        bars = plt.bar(("IM", "R1"),
            [float(overall[a]["pairedDeltaJpy"]) for a in ("IM", "R1")],
            color=COLORS[0])
        plt.bar_label(bars, fmt="%.0f")
        save("14_primary_overall_delta.png", "Primary routed-Control overall delta",
             "Arm", "Paired delta (JPY)")
    if (E / "ALL_ENTRY_RESULT.json").exists():
        broad = json.loads((E / "ALL_ENTRY_RESULT.json").read_text())
        win = broad["winner"]
        labels = [f"{a}>={h}" for a in ("IM", "R1") for h in (5, 10)]
        x = np.arange(4)
        plt.figure(figsize=(8, 4.3))
        bars = plt.bar(x, [float(win[k]["pairedDeltaJpy"]) for k in labels],
            color=[COLORS[0] if float(win[k]["pairedDeltaJpy"]) >= 0 else COLORS[1]
                   for k in labels])
        plt.bar_label(bars, fmt="%.0f")
        plt.axhline(0, color="#555", lw=.8)
        plt.xticks(x, labels)
        save("15_all_entry_winner_delta.png", "All-entry Winner: PRR-Control (100 shares)",
             "Arm / evaluator cohort", "Paired delta (JPY)")
        plt.figure(figsize=(6, 4.2))
        values = [float(broad["defensiveRoute"][a]["pairedDeltaJpy"]) for a in ("IM", "R1")]
        bars = plt.bar(("IM", "R1"), values,
                       color=[COLORS[0] if v >= 0 else COLORS[1] for v in values])
        plt.bar_label(bars, fmt="%.0f")
        plt.axhline(0, color="#555", lw=.8)
        save("16_all_entry_defensive_delta.png", "All-entry defensive subset (100 shares)",
             "Arm", "CCMG-Control paired delta (JPY)")
        for arm in ("IM", "R1"):
            names = sorted(k.split(":", 1)[1] for k in broad["bySession"] if k.startswith(arm+":"))
            vals = [float(broad["defensiveBySession"][f"{arm}:{s}"]["pairedDeltaJpy"])
                    for s in names]
            plt.figure(figsize=(10, 4.2))
            plt.bar(range(len(names)), vals,
                    color=[COLORS[0] if v >= 0 else COLORS[1] for v in vals])
            plt.axhline(0, color="#555", lw=.8)
            plt.xticks(range(0, len(names), 3), names[::3], rotation=45, ha="right")
            save(f"17_{arm.lower()}_defensive_delta_session.png",
                 f"{arm} defensive subset by Development session",
                 "Session", "CCMG-Control paired delta (JPY)")
    print(json.dumps({"figures": len(list(F.glob("*.png"))), "gate": gate["status"]}))


if __name__ == "__main__":
    main()
