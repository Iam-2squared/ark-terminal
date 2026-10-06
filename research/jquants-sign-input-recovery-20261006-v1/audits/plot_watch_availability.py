"""Render only saved public aggregate counts, never private rows or outcomes."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

HERE = Path(__file__).resolve().parent
REPORT = HERE / "RESTORED_RAW_COVERAGE_AUDIT.json"
EXPECTED_SHA = "29f07a6939a906dfddcb24e7d2e81965d29a87cbc8df52575e6d8a3b2110fae4"


def main():
    body = REPORT.read_bytes()
    assert hashlib.sha256(body).hexdigest() == EXPECTED_SHA
    audit = json.loads(body)
    denominator = audit["bar_and_grid_counts"]["observed_watch_decisions"]
    assert denominator == 223940
    observations = []
    for window in (5, 10, 20):
        counts = audit["current_strict_window_status_counts"][str(window)]
        assert sum(counts.values()) == denominator
        observations.append({"label": f"Strict {window}-minute window",
                             "available_N": counts["AVAILABLE"],
                             "denominator": denominator,
                             "criterion": "contiguous closed regular observations in same half-session"})
    vwap = audit["bar_and_grid_counts"]
    assert vwap["vwap_coverage_ge80pct_decisions"] + vwap["vwap_coverage_lt80pct_decisions"] == denominator
    observations.append({"label": "VWAP coverage >= 80%",
                         "available_N": vwap["vwap_coverage_ge80pct_decisions"],
                         "denominator": denominator,
                         "criterion": "frozen cumulative observed-row coverage condition only"})
    for item in observations:
        item["unavailable_N"] = denominator - item["available_N"]
        item["available_rate"] = item["available_N"] / denominator
    data = {"source_sha256": EXPECTED_SHA, "population": "58 Development sessions / 2155 watches",
            "denominator": denominator, "unit": "observed CLOSED regular watch-decision endpoint",
            "is_Entry1600_or_Sign_performance": False,
            "availability": "historical raw-start+1 completed-bar assumption; actual arrival UNKNOWN",
            "observations": observations}
    target = HERE.parent / "figures"
    target.mkdir(exist_ok=True)
    with (target / "WATCH_GRID_AVAILABILITY_DATA.json").open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "svg.fonttype": "path", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.spines.left": False})
    fig, ax = plt.subplots(figsize=(10.8, 5.5))
    ratios = [r["available_rate"] for r in observations]
    y = list(range(len(observations)))
    ax.barh(y, ratios, height=.58, color="#146b94", label="Condition met")
    ax.barh(y, [1-r for r in ratios], left=ratios, height=.58,
            color="#dce4ea", label="Condition not met")
    for index, record in enumerate(observations):
        fraction = record["available_rate"]
        ax.text(fraction / 2, index,
                f'{fraction:.2%}\n{record["available_N"]:,} / {denominator:,}',
                ha="center", va="center", color="white", fontsize=11, fontweight="bold")
        ax.text(fraction + (1-fraction)/2, index, f'{1-fraction:.2%}',
                ha="center", va="center", color="#394b5a", fontsize=11)
    ax.set_yticks(y, [r["label"] for r in observations])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.set_xlabel("Share of observed watch-decision endpoints")
    ax.tick_params(axis="y", length=0, pad=10)
    ax.grid(axis="x", linestyle=":", alpha=.22)
    ax.set_axisbelow(True)
    ax.set_title("Saved Development RAW: measured input availability", loc="left", pad=22,
                 fontsize=15, fontweight="bold")
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1.015), frameon=False, ncol=2, fontsize=10)
    fig.text(.02, .064, "58 Development sessions/2155 watches; not Entry1600 or Sign performance",
             fontsize=10, color="#283c4d")
    fig.text(.02, .025, "Denominator: 223,940 observed closed regular watch-decision rows. Actual arrival time UNKNOWN.",
             fontsize=9, color="#546674")
    fig.subplots_adjust(left=.27, right=.98, top=.79, bottom=.23)
    fig.savefig(target / "watch-grid-availability.svg", metadata={"Date": None})
    fig.savefig(target / "watch-grid-availability.png", dpi=180)
    plt.close(fig)
    print(json.dumps({"source_hash_verified": True, "denominator": denominator,
                      "available_N": [r["available_N"] for r in observations],
                      "private_rows_read": 0, "fits": 0}))


if __name__ == "__main__":
    main()
