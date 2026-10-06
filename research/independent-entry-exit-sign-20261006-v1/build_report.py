"""Render measured sign results; no fitting, selection, or market recomputation."""
import datetime as dt
import gzip
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sign_io import OUT, PRIVATE, read, rows, sha, save, now


def number(v, digits=4):
    return "NA" if v is None else f"{v:.{digits}f}"


def pct(v):
    return "NA" if v is None else f"{100*v:.2f}%"


def table(headers, values):
    return "\n".join(["| " + " | ".join(map(str, headers)) + " |",
                      "| " + " | ".join(["---"] * len(headers)) + " |"] +
                     ["| " + " | ".join(map(str, row)) + " |" for row in values])


def main():
    discovery = read(OUT / "DISCOVERY_RESULTS.json")
    late = read(OUT / "LATE_DEV_RESULTS.json")
    ablation = read(OUT / "ABLATION_RESULTS.json")
    baseline = read(OUT / "BASELINE_AND_LEGACY_COMPARISON.json")["results"]
    selected = late["candidate"]
    full = discovery["results"][selected]
    result = late["result"]
    raw = result["binary"]
    filt = result["filters"]["0.8"]
    lock = read(OUT / "MODEL_SELECTION_LOCK.json")
    ledger = read(OUT / "FIT_LEDGER.json")
    split = read(OUT / "SPLIT_FIT_CAL_TEST.json")
    audit = read(OUT / "INDEPENDENT_AUDIT.json")
    assert audit["status"] == "PASS" and audit["mismatch_N"] == 0
    assert ledger["new_fits"] == 43 and selected == "AUG_L"
    assert late["status"] == "SIGN_NOT_SEPARATED_IN_THIS_RUN"
    figures = OUT / "figures"
    figures.mkdir(exist_ok=True)
    previews = PRIVATE / "report_figures"
    previews.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "svg.hashsalt": "ARK_INDEPENDENT_SIGN_V1", "svg.fonttype": "none"})

    def finish(fig, name):
        fig.savefig(figures / (name + ".svg"), bbox_inches="tight", metadata={"Date": None})
        fig.savefig(previews / (name + ".png"), dpi=160, bbox_inches="tight")
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
    matrices = []
    for ax, m, title, labels in zip(axes, [raw, filt], ["Binary: p_plus >= 0.5", "Primary filter: CAL q = 80%"],
                                   [["Pred PLUS", "Pred MINUS"], ["PASS", "REJECT"]]):
        a = np.array([[m["TP"], m["FN"]], [m["FP"], m["TN"]]])
        matrices.append(a.tolist())
        ax.imshow(a, cmap="Blues", vmin=0, vmax=170)
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(a[i, j]), ha="center", va="center", fontsize=23,
                        color="white" if a[i, j] > 95 else "#15324d")
        ax.set_xticks([0, 1], labels)
        ax.set_yticks([0, 1], ["Actual PLUS", "Actual MINUS"])
        ax.set_title(title, pad=13)
    fig.suptitle("Locked late Development | 360 known eligible entries | AUG_L", fontsize=14)
    finish(fig, "01_late_confusion")

    fig, ax = plt.subplots(figsize=(8.8, 5.3), constrained_layout=True)
    offsets = {"RAW_L": (-60, -24), "AUG_L": (15, -4), "RAW_H": (10, -25),
               "AUG_H": (-65, 12), "RAW_E": (12, -5), "AUG_E": (-62, -15)}
    for candidate in ["RAW_L", "RAW_H", "RAW_E", "AUG_L", "AUG_H", "AUG_E"]:
        m = discovery["results"][candidate]["filters"]["0.8"]
        ax.scatter(m["plus_retention"] * 100, m["minus_removal"] * 100,
                   color="#167e8c" if candidate == selected else "#7797ba", s=65)
        ax.annotate(candidate + " discovery", (m["plus_retention"] * 100, m["minus_removal"] * 100),
                    xytext=offsets[candidate], textcoords="offset points", fontsize=9,
                    arrowprops={"arrowstyle": "-", "color": "#9ca3af"})
    ax.scatter(filt["plus_retention"] * 100, filt["minus_removal"] * 100,
               marker="*", s=240, color="#bb3e4a", label="AUG_L locked late")
    ax.annotate("AUG_L locked late", (filt["plus_retention"] * 100, filt["minus_removal"] * 100),
                xytext=(-55, 20), textcoords="offset points", color="#9a293b")
    ax.axvline(80, color="#667085", ls="--", lw=1, label="Precommitted arrival criteria")
    ax.axhline(40, color="#667085", ls="--", lw=1)
    ax.fill_between([80, 100], 40, 55, color="#e4f1e7", alpha=0.7)
    ax.set(xlim=(65, 101), ylim=(0, 55), xlabel="PLUS retained (%)", ylabel="MINUS removed (%)",
           title="Primary q = 80% | discovery selection vs locked late check")
    ax.grid(alpha=0.18)
    finish(fig, "02_retention_removal")

    blocks = full["blocks"] + result["blocks"]
    fig, ax = plt.subplots(figsize=(9.2, 4.4), constrained_layout=True)
    x = [b["block"] for b in blocks]
    y = [b["filters"]["0.8"]["balanced_accuracy"] for b in blocks]
    ax.axvspan(0.6, 5.5, color="#eaf1f8")
    ax.axvspan(5.5, 8.4, color="#faedef")
    ax.plot(x[:5], y[:5], marker="o", color="#167e8c", label="Discovery: selected AUG_L")
    ax.plot(x[5:], y[5:], marker="o", color="#bb3e4a", label="One candidate locked late")
    ax.axhline(0.5, color="#475467", ls="--", label="BA = 0.5")
    for b, value in zip(x, y):
        ax.annotate(f"{value:.3f}", (b, value), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=10)
    ax.set(xlim=(0.6, 8.4), ylim=(0.455, 0.60), xticks=x, xlabel="Fixed OOF block",
           ylabel="Balanced accuracy", title="AUG_L primary filter | block-specific CAL thresholds")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.2)
    finish(fig, "03_block_BA")
    save(OUT / "FIGURE_DATA.json", {"status": "MEASURED_ONLY", "late_matrices": matrices,
         "block_BA": [{"block": b, "balanced_accuracy": v} for b, v in zip(x, y)],
         "discovery_filter_points": {c: {k: r["filters"]["0.8"][k] for k in ["plus_retention", "minus_removal"]}
                                     for c, r in discovery["results"].items()},
         "late_filter_point": {k: filt[k] for k in ["plus_retention", "minus_removal"]}})

    # Explain all frozen support conditions even when the gate terminates early.
    g = lock["gate"]
    observed = {"plus_retention_min": filt["plus_retention"], "minus_removal_min": filt["minus_removal"],
                "BA_min": filt["balanced_accuracy"], "MCC_strictly_greater_than": filt["MCC"],
                "coverage_min": filt["prediction_coverage"],
                "blocks_with_BA_above_half_min": sum(b["filters"]["0.8"]["balanced_accuracy"] > .5 for b in result["blocks"]),
                "known_N_min": filt["known_N"], "each_class_N_min": min(filt["TP"] + filt["FN"], filt["TN"] + filt["FP"]),
                "sessions_min": filt["sessions"], "BA_bootstrap_lower_strictly_above": result["CI"]["metrics"]["balanced_accuracy"]["lower"]}
    checks = [{"criterion": k, "fixed": g[k], "observed": value,
               "pass": value > g[k] if "strictly" in k else value >= g[k]}
              for k, value in observed.items()]
    save(OUT / "FROZEN_GATE_DETAIL.json", {"status": late["status"], "candidate": selected,
         "q_primary": .8, "checks": checks, "post_result_gate_changes": 0, "candidate_exchanges": 0})

    # Availability/missingness diagnosis only: the frozen view is unchanged.
    snapshots = rows(PRIVATE / "SNAPSHOTS.jsonl.gz")
    metadata = {r["entry_id"]: r for r in rows(PRIVATE / "METADATA.jsonl.gz")}
    eligible = [r for r in snapshots if metadata[r["entry_id"]]["execution_eligible"]]
    registry = read(OUT / "FEATURE_REGISTRY.json")
    missing = {}
    for group, cols in registry["groups"].items():
        present = {k: sum(r["numeric"][k] is not None for r in eligible) for k in cols}
        missing[group] = {"numeric_N": len(cols), "cells_N": len(eligible)*len(cols),
                          "missing_rate": 1-sum(present.values())/(len(eligible)*len(cols)),
                          "entirely_missing_columns": [k for k, n in present.items() if n == 0]}
    save(OUT / "FEATURE_MISSINGNESS.json", {"status": "POST_LOCK_DIAGNOSTIC_ZERO_FITS", "groups": missing,
         "runtime_eligible_N": len(eligible), "view_modified": False,
         "meaning": "inherited stored numeric nulls; FIT-only zero/missing-indicator treatment fixed before training"})
    save(OUT / "FIRST_PREDICTIONS_DESCRIPTOR.json", {"status": "PRIVATE_PRESERVED", "file": "FIRST_PREDICTIONS.jsonl.gz",
         "sha256": sha(PRIVATE / "FIRST_PREDICTIONS.jsonl.gz"),
         "row_N": len(rows(PRIVATE / "FIRST_PREDICTIONS.jsonl.gz")),
         "contains": "six discovery candidates, one locked late candidate; rows include UNKNOWN and ineligible identities",
         "freshness": "new cycle first outputs, historically exposed Development; no fresh/OOS claim"})
    raw_table = table(["実際の費用後符号", "予測PLUS：p≥0.5", "予測MINUS：p<0.5", "計"],
                      [["PLUS", raw["TP"], raw["FN"], raw["TP"]+raw["FN"]],
                       ["MINUS", raw["FP"], raw["TN"], raw["FP"]+raw["TN"]]])
    filter_table = table(["実際の費用後符号", "PASS_CANDIDATE", "REJECT_CANDIDATE", "計"],
                         [["PLUS", filt["TP"], filt["FN"], filt["TP"]+filt["FN"]],
                          ["MINUS", filt["FP"], filt["TN"], filt["FP"]+filt["TN"]]])
    old_late = baseline["LATE_DEV_LOCKED_CHECK"]["old_stage1"]["filter"]
    old_all = baseline["SELECTED_OOF_ALL"]["old_stage1"]["filter"]
    early_old = table(["参照filter", "区間／既知数", "PLUS通過", "MINUS除去", "通過MINUS率", "BA"],
       [["旧Stage1 primary（保存済み）", "OOF38／1016", f"{old_all['TP']}/462", f"{old_all['TN']}/554", pct(old_all["pass_MINUS_rate"]), number(old_all["balanced_accuracy"])],
        ["旧Stage1 primary（保存済み）", "後半13 sessions／360", f"{old_late['TP']}/167", f"{old_late['TN']}/193", pct(old_late["pass_MINUS_rate"]), number(old_late["balanced_accuracy"])],
        ["今回AUG_L 主q80", "後半13 sessions／360", f"{filt['TP']}/167", f"{filt['TN']}/193", pct(filt["pass_MINUS_rate"]), number(filt["balanced_accuracy"])]] )
    population = table(["区間", "全Entry", "実行適格", "符号既知", "PLUS", "MINUS", "厳密0", "不明：全／適格", "適格予測可能", "ABSTAIN", "sessions"],
        [[label, m["all_Entry_N"], m["execution_eligible_N"], m["known_N"], m["TP"]+m["FN"], m["FP"]+m["TN"],
          m["exact_zero_N"], f"{m['all_unknown_N']}／{m['unknown_N']}", m["predictable_N"], m["ABSTAIN_N"], m["sessions"]]
         for label, m in [("DISCOVERY・全6候補共通", full["filters"]["0.8"]), ("LATE・固定AUG_L", filt)]])
    disc_table = table(["候補", "block平均BA：選択用", "最小block BA", "pool BA", "MCC", "Brier", "PLUS保存", "MINUS除去", "active blocks", "coverage"],
        [[c, number(r["mean_block_filter_BA"], 6), number(r["minimum_block_filter_BA"], 6), number(r["filters"]["0.8"]["balanced_accuracy"]),
          number(r["filters"]["0.8"]["MCC"]), number(r["filters"]["0.8"]["Brier"]), pct(r["filters"]["0.8"]["plus_retention"]),
          pct(r["filters"]["0.8"]["minus_removal"]), r["active_filter_blocks"], pct(r["filters"]["0.8"]["prediction_coverage"])]
         for c, r in sorted(discovery["results"].items(), key=lambda a: a[1]["mean_block_filter_BA"], reverse=True)])
    metrics = table(["後半指標", "生二値p≥0.5", "主filter q80"],
        [[label, number(raw[key]), number(filt[key])] for label, key in [
         ("balanced accuracy", "balanced_accuracy"), ("MCC", "MCC"), ("accuracy", "accuracy"),
         ("PLUS precision", "PLUS_precision"), ("PLUS recall／保存", "PLUS_recall"),
         ("MINUS precision", "MINUS_precision"), ("MINUS recall／除去", "MINUS_recall"),
         ("AUROC（共通スコア）", "AUROC"), ("PLUS AP（共通スコア）", "PLUS_AP"),
         ("MINUS AP（共通スコア）", "MINUS_AP"), ("Brier（共通スコア）", "Brier"), ("log loss（共通スコア）", "log_loss")]])
    ci = table(["主filterの指標", "後半実測", "session bootstrap 95%区間", "有効／NA"],
       [[label, number(filt[key]), f"[{number(v['lower'])}, {number(v['upper'])}]", f"{v['valid_N']}／{v['NA_N']}"]
        for key, label in [("balanced_accuracy", "BA"), ("plus_retention", "PLUS保存率"),
                           ("minus_removal", "MINUS除去率"), ("pass_MINUS_rate", "通過MINUS率")]
        for v in [result["CI"]["metrics"][key]]])
    gate_labels = {"plus_retention_min": "PLUS保存 ≥80%", "minus_removal_min": "MINUS除去 ≥40%", "BA_min": "BA ≥0.60",
                   "MCC_strictly_greater_than": "MCC >0", "coverage_min": "coverage ≥95%",
                   "blocks_with_BA_above_half_min": "BA >0.5のblock ≥2/3", "known_N_min": "既知 ≥100件",
                   "each_class_N_min": "各class ≥30件", "sessions_min": "sessions ≥10",
                   "BA_bootstrap_lower_strictly_above": "BA CI下限 >0.5"}
    gate_table = table(["固定条件", "実測", "確認"],
                       [[gate_labels[r["criterion"]], number(r["observed"]), "達成" if r["pass"] else "未達"] for r in checks])
    block_table = table(["block／区間", "FIT／CAL／TEST既知", "CAL q80 tau", "CAL status", "TEST PLUS保存", "TEST MINUS除去", "TEST BA"],
       [[f"{b['block']}／{'探索' if b['block'] <= 5 else '後半'}", f"{rec['FIT_N']}／{rec['CAL_N']}／{b['filters']['0.8']['known_N']}",
         number(rec["thresholds"]["0.8"]["tau"], 8), rec["thresholds"]["0.8"]["status"],
         pct(b["filters"]["0.8"]["plus_retention"]), pct(b["filters"]["0.8"]["minus_removal"]), number(b["filters"]["0.8"]["balanced_accuracy"])]
        for b in blocks for rec in [next(r for r in ledger["attempts"] if r["block"] == b["block"] and r["candidate"] == selected and r["phase"] != "ABLATION")]])
    aux_q = table(["CAL保存条件", "PLUS通過／167", "MINUS除去／193", "PLUS保存", "MINUS除去", "BA", "通過MINUS率"],
       [[f"q={q}", m["TP"], m["TN"], pct(m["plus_retention"]), pct(m["minus_removal"]), number(m["balanced_accuracy"]), pct(m["pass_MINUS_rate"])]
        for q, m in sorted(result["filters"].items(), reverse=True)])
    abl_table = table(["探索5blocks・Logistic固定", "block平均BA", "full−除外 BA", "新規fit", "等価再利用"],
        [["full AUG_L", number(full["mean_block_filter_BA"], 6), "—", "既存前半5", 0]] +
        [[c, number(r["mean_block_filter_BA"], 6), number(full["mean_block_filter_BA"]-r["mean_block_filter_BA"], 6),
          0 if c == "DROP_G_SCORE" else 5, 5 if c == "DROP_G_SCORE" else 0] for c, r in ablation["results"].items()])
    learning_rows = read(OUT / "LEARNING_DIAGNOSTICS.json")["rows"]
    learning_table = table(["block", "FIT N／BA", "CAL N／BA", "TEST全Entry／BA", "数値欠測：FIT／CAL／TEST"],
       [[b, f"{parts['FIT']['N']}／{number(parts['FIT']['binary']['balanced_accuracy'])}",
         f"{parts['CAL']['N']}／{number(parts['CAL']['binary']['balanced_accuracy'])}",
         f"{parts['TEST']['N']}／{number(parts['TEST']['binary']['balanced_accuracy'])}",
         "／".join(pct(parts["TEST"]["missing_rates"][k]) for k in ["FIT", "CAL", "TEST"])]
        for b in range(1, 9) for parts in [{r["partition"]: r for r in learning_rows if r["block"] == b}]])
    references = baseline["LATE_DEV_LOCKED_CHECK"]
    ref_table = table(["後半・生二値参照", "BA", "MCC", "AUROC", "Brier"],
       [[label, number(m["balanced_accuracy"]), number(m["MCC"]), number(m["AUROC"]), number(m["Brier"])]
        for label, m in [("今回AUG_L", raw)] +
        [(k, v["binary"]) for k, v in references["baselines"].items()] +
        [(k+"（保存予測）", v["binary"]) for k, v in references["legacy_probability_references"].items()]])
    aux = read(OUT / "AUXILIARY_SUBSETS.json")["results"]["LATE_DEV_LOCKED_CHECK"]
    aux_table = table(["後半・補助subset", "全Entry／適格／既知", "PLUS保存", "MINUS除去", "BA", "通過MINUS率", "適格coverage"],
       [[label, f"{m['all_Entry_N']}／{m['execution_eligible_N']}／{m['known_N']}", pct(m["plus_retention"]), pct(m["minus_removal"]),
         number(m["balanced_accuracy"]), pct(m["pass_MINUS_rate"]), pct(m["prediction_coverage"])]
        for label, v in aux.items() for m in [v["filter"]]])
    counts_table = table(["実行内容", "実績"], [["前半6候補×5blocks", 30], ["固定1候補・後半3blocks", 3],
        ["情報群除外・新規fit", 10], ["情報群除外・等価fit再利用", 5], ["新規教師model fit合計／上限", "43／48"],
        ["全trial条件数", 48], ["前処理fit（別counter）", 23], ["技術model fit retry／上限", "0／2"],
        ["旧Sign-only追加fit／producer fit／calibration fit／full-data最終fit", "0／0／0／0"],
        ["Capital接続／Replay／第2層fit／注文", "0／0／0／0"],
        ["原R再生成／新市場特徴／provider取得／保護データ開封", "0／0／0／0"],
        ["main merge／force push／Claude", "0／0／0"]])
    start = read(OUT / "checkpoints/01_STARTED.json")["exact_jst"]
    completed = now()
    report = f"""# 🛡️ Independent Entry→EXIT Sign Classifier V1 — 実行報告

対象は後半ロック確認の符号既知・実行適格360件。教師は固定Entry→固定EXIT/EODの費用後PLUS／MINUSのみ、各Entryを1件として数えた。

**PLUS／MINUS × 生二値予測**

{raw_table}

**PLUS／MINUS × 主filter（CAL PLUS保存条件80%）**

{filter_table}

旧成果との保存値比較：

{early_old}

**後半status：`{late['status']}`。** PLUS139件を残し、28件を拒否。MINUS31件を除き、162件を通過させた。PLUS保存率{pct(filt['plus_retention'])}、MINUS除去率{pct(filt['minus_removal'])}。通過MINUS率はフィルター前{pct(filt['before_MINUS_rate'])}から{pct(filt['pass_MINUS_rate'])}へ**上昇**した。通過集合は実際のPLUS確定集合ではない。

主filter BA={number(filt['balanced_accuracy'],6)}、MCC={number(filt['MCC'],6)}。事前固定したBA≤0.5／MCC≤0の負結果条件に該当する。旧Stage1は90%保存制約・異なるFIT／表現を使ったため、上表は同一訓練条件の優劣判定ではない。旧完了成果32fit、旧不採用判定、V5保持をそのまま保存・再利用した。

## 📊 母集団・実測図

{population}

適格の予測coverageは両区間とも100%。符号不明は予測行として保持し、正負採点から除外。厳密0は0件。元OOF38全体は1,039件、適格1,028件、既知1,016件（PLUS462／MINUS554）、不明23件（適格12件）。58 sessionsのruntime1,600件とwarmup20の既知544件を原本のまま継承した。

![後半の実測混同行列](figures/01_late_confusion.svg)

![PLUS保存とMINUS除去](figures/02_retention_removal.svg)

![固定8blocksのBA](figures/03_block_BA.svg)

## 🔒 固定条件・時間順分割・独立性

Selector、FIRST ENTRY v2 P1_Q70、Structural EXIT v3、EOD／費用／約定、State9 RC2／Path、既存Winner Rankとproducerを保持した。実験コードは独立directoryに追加し、Capital engineをimportしない。推論は`predict_sign(snapshot, model_artifact, threshold_artifact)`。教師、true R、future EXIT、口座資金、数量を引数へ渡せない。出力は同じEntry ID・p_plus・二値符号・研究用PASS/REJECT・hash・cutoff・availability・exposure。将来のRank joinはID契約だけを保存し、adapter接続は0。

原debit/creditのexact比較でPLUS=1／MINUS=0を作る監査adapter以外には、金額・return原値を渡さない。教師viewは6列allowlist、等重み、sample_weight=None、class_weight=None。費用再控除、EXIT再計算、epsilon帯、未知営業日補完は0。結果の大きさを符号不変で変える3,120ケースを独立検算した。

原58 sessions／warmup20／OOF38・8blocksを保持。各blockは過去末尾5sessionsをCAL、それ以前をFIT。FIT教師はCAL開始前、CAL教師はTEST開始前の成熟だけ。前処理はFIT-only（固定0補完＋全数値の欠測indicator、FIT平均／標準偏差、FIT辞書＋UNKNOWN one-hot）。CALでtauを決めた同じモデルをTESTへ使い、CAL後refit・TEST内更新は0。FIT最低100既知／10sessions／各class20、CAL最低50既知／3sessions／各class10を全条件で満たした。

主tauはCALのユニークp_plus＋0＋1超sentinelから、PLUS保存≥80%の中でexact件数BA最大、MINUS除去最大、tau最小の順。CAL BA≤0.5はALL_PASS。生二値p≥0.5と主filterを別評価した。ABSTAINは生二値で正解に数えず、filterでは運用PASSとして残す。

実市場期間は**HISTORICALLY_EXPOSED_DEVELOPMENT**。後半は`LATE_DEV_LOCKED_CHECK`でありFresh／holdout／新しいOOSではない。元のfirst-intent ID、closed prefix、same-time順序とproducer成熟監査を引継ぎ、hash・row identity・FIT producerにCAL/TEST依存0を再照合。historical availabilityは**HISTORICAL_ASSUMED_AVAILABILITY**、actual arrivalはUNKNOWNのまま。

## 🧠 事前固定6候補の比較と1候補ロック

RAWは価格106数値＋State/Path18数値・7カテゴリ＋context9数値＝133数値・7カテゴリ。学習scoreを含まない。AUGは合法な保存済みP1 score／thresholdの2列のみ追加（135数値・7カテゴリ）。両列は全FIT/CAL/TESTで接続100%、追加producer学習0。pP／MOVE_U2／MOVE_U3はwarmup等の接続不足で全区分95%条件未達のため事前除外。MRET、HL0/D1/D2のstack、新しいDaily等は追加しない。

L＝Logistic C0.1／lbfgs／max_iter2000、H＝HistGradientBoosting lr0.05／100iterations／7leaves／depth3／l2=1／early_stopping=False、E＝ExtraTrees300／depth6／leaf10／max_features0.5／bootstrap=False。seed57、全resolved parametersと環境versionを`MODEL_PRECOMMIT.json`に事前固定した。性能を見て設定変更していない。

DISCOVERYは2025-06-27〜2025-08-05の25sessions、共通既知656件。主q80の比較：

{disc_table}

coverage≥95%、active blocks≥3を全6候補が満たした。選択順はblock平均BA→最悪block BA→pool MCC→低Brier→RAW→L/H/E。最高の**AUG_L**を1候補へ固定した。前半block平均BAのRAW_Lとの差は{number(full['mean_block_filter_BA']-discovery['results']['RAW_L']['mean_block_filter_BA'],6)}。pool BAとblock平均BAは別値であり、選択には後者だけを主順位として使った。旧32fitはCALを学習に含む等の非等価条件なので新FITへ流用せず、原本・保存予測・監査・baselineに再利用した。

候補ロックはGitHub commit `3983c8c6ff2ddb028dc497ff8eb462607d00e433`へ保存し、actual GETで本文・blob・HEADを読み戻した後に後半を開始。後半に走らせたのはAUG_Lだけ3blocks。全後半predict／policy保存後に採点し、candidate交換0。前半開始前commitは`2d8062e2d1a29100d5f1e27c7249942c24c970e5`。

## 📉 後半ロック確認と不確実性

後半は2025-08-06〜2025-08-25の13sessions、全369件・適格363件・既知360件。BA CI95%は[{number(result['CI']['metrics']['balanced_accuracy']['lower'],6)}, {number(result['CI']['metrics']['balanced_accuracy']['upper'],6)}]。前半の小さなfilter差を後半で確認できなかった。

{metrics}

生二値のBAは僅かに0.5超だが、PLUSを48／167件しかPLUS予測できない。主filterの負結果をこの別指標で救済しない。確率Brierは同じFIT過去PLUS率B0より悪く、確率品質にも改善を確認できない。p_plusは未校正スコア。

{ci}

session単位2,000回、seed20261006、各sessionの全Entryをまとめて再標本化。モデルrefit・tau再選択0。全指標2,000有効、片class／ゼロ分母NA0。各候補・区間のCIは保存JSONにあり、ここでは後半主結果を示した。CIは期間反復露出・モデル選択・全ての時間依存を補正しない。

{gate_table}

{block_table}

補助q90／q70は事前固定した別保存条件で、後半の都合で主q80を差し替えていない。

{aux_q}

q90とq80の後半実行結果が同じでも、CAL制約と保存されたtauは別に監査した。q70はMINUS除去が増える一方、PLUS保存80%に届かない。この補助結果で候補／合否を変更しない。

## 🧬 情報群の寄与・学習状況・旧参照

後半結果と無関係に、選んだLogisticの設定を保持して探索5blocksのみを比較：

{abl_table}

G_PRICE／G_STATE／G_SCOREの存在は前半で小さなBA差に対応したが、相関のある群を除く比較であり因果効果や未知期間の有効性とは言わない。G_SCORE除外は同じ前半RAW_LとFIT payload・列・教師・設定が一致したため5fitを再利用。ablationで主モデル／後半／閾値を交換していない。

生二値p≥0.5のFIT／CAL／TEST診断：

{learning_table}

FIT BAは0.7031〜0.6079、CAL/TESTは概ね0.5付近。過適合の兆候は考えられるが原因を断定しない。保存数値には欠測が多い（全適格runtimeのG_PRICE {pct(missing['G_PRICE']['missing_rate'])}、G_STATE {pct(missing['G_STATE']['missing_rate'])}）。完全欠落列は0。固定した欠測処理で扱い、結果後の穴埋めや追加特徴は0。TEST件数欄は全Entryで、BAの採点は既知・適格のみ。

{ref_table}

B0は同じFITだけの成熟過去PLUS率を使い、同じCAL手続きで全block ALL_PASS、主filter BA0.5。ALL_PLUS／ALL_MINUS／FIT多数派は生二値の参照。B0のpool AUROCが0.5と僅かに異なるのはblockごとに過去率が異なるため。HL0／D1／D2は保存p_negを1−p_negに向け直しただけで再fit0。旧学習は今回CALの日付を含むため、今回との同一訓練条件比較には使えない。

結果固定後の補助subset（モデル選択・主判定に不使用）：

{aux_table}

既存Rank／旧V5 membershipを集計にだけ利用。少数subsetの結果は全体成功やRank再学習の根拠にしない。

## 🔍 検算・技術修復・保存実績

独立監査は主model／policy／metrics処理をimportせず、保存符号＋予測からexact件数、pairwise AUROC、grouped AP、fsum Brier／log lossを再構成。43モデル・48trial条件、CAL tau tie／support／ALL_PASS、前処理FIT-only、成熟境界、予測保存後採点、1候補、3block、後半bootstrap、合否を照合。**{audit['check_groups']}項目、mismatch={audit['mismatch_N']}、PASS**。独立推論APIの全1,039保存予測一致、禁じた教師・金額・future EXIT・資金・数量の入力拒否、future source→ABSTAIN/PASSを別確認した。合成契約テスト12件PASS。

意味不変の技術修復を明示する。①mutable ledgerの後半block8の1記録欠落を、immutable model・開始claim・sealed予測・閾値・FIT IDから復元。元ledger記録時刻とwarningsは不明として保持し、元実験の時刻を創作しない。②DISCOVERY_RAW_E_BLOCK_04のtraining gzip1件が途中で切れていたため、元の凍結view＋immutable FIT IDから再構成。805行のcanonical payload hashは元signatureと一致し、残存746行も一致。欠損gzipはrepairに保存した。③旧action名のadapterを保存済みPASS系／REJECTへ正しく対応させた。全て修復receiptを保存し、model／primary予測／教師／tau／candidate／合否の変更0、追加fit0。

{counts_table}

開始checkpoint実時計JST：`{start}`。独立監査完了：`{audit['exact_jst']}`。報告書作成：`{completed}`。basis HEAD `4a0b6d5fef69ecee34a05c36789c57478ab37a7a`、tree `7e544213be9d97a966649c4317c6032e609a3ce6`。開始保存時には旧writerの完了commit `07324ba54fc44a7c03ce7702c62bc7484aecf4cc`をparentとしてその成果を保持。競合をleaseで拒否して読み直し、force push0。

開始、入力固定、探索ロック、後半／ablation／独立検算の保存はactual GETで本文・blob・branch HEADを確認した。直近検算checkpoint commitは`09f99aa819cfcfc0e5e5a6101fb0d2222618db8e`。final保存の正確なcommit／tree／実時計／読み戻しは`DELIVERY_RECEIPT.json`と`readbacks/`に追記する。`FROZEN_UPSTREAM_AUDIT.json`では旧研究33件、旧Evidenceの自module以外、root／docsの関連外subtreeのsha一致を確認。final treeについても再照合し、旧成果と凍結コードを保持する。

publicは定義・集計・hash・コード・検算、privateは行別入力・教師・モデル・予測・原ZIP・修復原本を分離。`FIRST_PREDICTIONS.jsonl.gz`はprivateに保存しpublic descriptorでhashと行数を固定。private ZIPに原旧Sign-only ZIPを同じhashのまま含め、最終GitHub commitと再開手順を記録する。

## 🎯 終了方針

指定した独立モジュール、有限比較、1候補ロック、後半確認、寄与分析、独立検算を完了した。今回の表現・family・期間では、PLUS保存80%とMINUS除去40%を同時に実証できず、Sign審査として採用へ進めない。これは全モデル・全情報で予測不可能という結論ではない。既存Entry／EXITの責任へ戻さず、今後の検討は別設計で購入前情報の品質・欠測原因の確認と未閲覧期間の検証を事前固定する範囲に限る。本Workの追加探索は終了。既存Rankを保持し、Capital接続・Replay・第2層学習へ進めない。`productionReady=false`、自動昇格なし。
"""
    (OUT / "REPORT-ja.md").write_text(report)
    print(json.dumps({"status": "REPORT_READY", "characters": len(report), "figures": 3,
                      "new_fits": 0, "report_jst": completed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
