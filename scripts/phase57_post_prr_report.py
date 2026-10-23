"""Render the frozen Phase A tables and descriptive figures without reanalysis."""
from __future__ import annotations

import json
from decimal import Decimal

from scripts import phase57_post_prr_phase_a as a


def yen(value):
    return f"{Decimal(str(value)):,.0f}"


def pp(value):
    return f"{Decimal(str(value)):+.3f}"


def make_figures(result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    path=a.OUT/"figures"
    path.mkdir(exist_ok=False)
    bands=("<5","5-10",">=10")
    x=np.arange(3)
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),sharey=True,layout="constrained")
    for ax,arm in zip(axs,("IM","R1")):
        raw=[float(Decimal(result["bands"][f"ALL_100:{arm}:{b}"]["deltaPnlJpy"]))/1000 for b in bands]
        routed=[float(Decimal(result["bands"][f"ALL_100:{arm}:{b}"]["routedDeltaPnlJpy"]))/1000 for b in bands]
        ax.bar(x-.18,raw,width=.36,label="CCMG - R50",color="#bd5837")
        ax.bar(x+.18,routed,width=.36,label="Frozen route - R50",color="#295c4d")
        ax.set_xticks(x,bands);ax.set_title(arm);ax.axhline(0,color="#555",lw=.8)
        ax.grid(axis="y",alpha=.2)
    axs[0].set_ylabel("Paired normalized delta (thousand JPY)")
    axs[1].legend(loc="lower left",fontsize=8)
    fig.suptitle("Saved EXIT outcomes by future upside band | 100 shares per Entry")
    fig.savefig(path/"01_delta_by_band.png",dpi=180)
    plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),sharey=True,layout="constrained")
    for ax,arm in zip(axs,("IM","R1")):
        for head,col in ((5,"#dd7852"),(10,"#275d52")):
            data=result["rank"][arm][f"head{head}"]["deciles"]
            values=[float(Decimal(data[str(i)]["meanDeltaNetPp"])) if data[str(i)]["pairedN"] else float("nan") for i in range(10)]
            ax.plot(range(10),values,marker="o",ms=3,label=f"Potential {head}%",color=col)
        ax.set_title(arm);ax.set_xticks(range(10));ax.axhline(0,color="#555",lw=.8)
        ax.grid(axis="y",alpha=.2)
    axs[0].set_ylabel("Mean paired CCMG - R50 net return (pp)")
    axs[1].legend(loc="lower left",fontsize=8)
    fig.supxlabel("Frozen fold-local score decile (0 = low)")
    fig.suptitle("Potential rank versus EXIT value | full known-paired population")
    fig.savefig(path/"02_rank_vs_delta.png",dpi=180)
    plt.close(fig)


def report():
    r=a.read("A1_RESULTS.json");c=a.read("A0_CENSUS.json");acct=a.read("ACCOUNTING_RECONCILIATION_RECEIPT.json")
    lines=["# Phase57 Post-PRR Phase A — 会計・比較母集団・EXIT差分監査",
      "", "研究対象：保存済みのR50とCCMG。新fit 0、新policy Replay 0。PR #587はdraft、旧PRRのNO_SELECTIONは維持。",
      "", "## 原本と会計", "",
      f"- Phase A Precommit SHA-256: `{a.sha(a.OUT/'PHASE_A_PRECOMMIT.json')}`。A0 SHA-256: `{a.sha(a.OUT/'A0_CENSUS.json')}`。A1 Spec SHA-256: `{a.sha(a.OUT/'A1_ANALYSIS_SPEC.json')}`。",
      "- R34台帳の支払原価はeffective Entry price × quantity。買付費用はeffective priceに含まれる。売却費用は支払原価の0.05%。PnL = exit price × quantity − paid cost × 1.0005。Net% = 100 × PnL / paid cost。",
      "- 旧CCMG/PRRの一部は売却代金の0.05%を差し引いた。旧receiptを変更せず、原本価格からR34式の列を別保存した。全100株世界では既知pairedの旧差 = 正規化差 × 0.9995。PrimaryではControlのみR34式で、CCMGは委譲値と売却代金basisが混在。",
      f"- 正規化が必要だった既知PnLは全100株 Control {acct['byWorldPolicy']['ALL_100:Control']['changedN']}件／CCMG {acct['byWorldPolicy']['ALL_100:Ccmg']['changedN']}件、Primary Control 0件／CCMG {acct['byWorldPolicy']['PRIMARY_FUNDED:Ccmg']['changedN']}件。Primaryの差分符号変更は{len(acct['signChangedRows'])}件。",
      "- 既存winner_gateはmean JPYを比較する。下表の平均Net％は各Entryの支払原価で割ってから平均した独立列であり、円合計や資本加重リターンで代用していない。",
      "", "## A0 — 件数（特徴とΔの関係を見る前に固定）", "",
      "|母集団|arm|Entry|両outcome既知|R50のみ|両方未知|Δ=0|Δ≠0|CCMG初回intent|R50 model intent|",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for world,label in (("ALL_100","全Entry 100株"),("PRIMARY_FUNDED","Primary 実数量"),("PRIMARY_OUTSIDE_100","Primary外 100株")):
        for arm in ("IM","R1"):
            m=c["table"][f"{arm}:{world}:ALL_ROUTES"]
            lines.append(f"|{label}|{arm}|{m['entryN']}|{m['pairedKnownN']}|{m['controlOnlyN']}|{m['bothUnknownN']}|{m['deltaEqualityN'].get('ZERO',0)}|{m['deltaEqualityN'].get('NONZERO',0)}|{m['ccmgIntentN']}|{m['controlModelIntentN']}|")
    lines += ["", "A0はΔ=0/非0の件数を閲覧したためoutcome blindではない。Primaryは全Entryの部分集合。IM/R1は代替Entry世界で合算Portfolioではない。期間は2025-07-22～2025-08-25の24セッション。", "",
      "## A1 — 保存済みoutcomeの同一Entry差", "",
      "|母集団|arm|paired N|改善 / 同値 / 悪化|CCMG−R50 円合計|平均Net差 pp|固定route−R50 円合計|固定route平均Net差 pp|",
      "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for world,label in (("ALL_100","全Entry 100株"),("PRIMARY_FUNDED","Primary 実数量"),("PRIMARY_OUTSIDE_100","Primary外 100株")):
        for arm in ("IM","R1"):
            v=r["values"][f"{world}:{arm}:ALL_ROUTES"]
            lines.append(f"|{label}|{arm}|{v['pairedN']}|{v['improveN']} / {v['equalN']} / {v['worseN']}|{yen(v['deltaPnlJpy'])}|{pp(v['meanDeltaNetPp'])}|{yen(v['routedDeltaPnlJpy'])}|{pp(v['meanRoutedDeltaNetPp'])}|")
    lines += ["", "固定routeのDEFAULT=R50という同値は仕様。CCMG outcomeが未知な行をCCMG−R50=0とは置いていない。円合計は単独Entryの並列比較であり、資本回転・同時保有制約・約定可能性を含むPortfolio効果ではない。", "",
      "### 上昇帯別（全Entry・100株、同一paired mask）", "",
      "|arm|未来上昇帯|paired N|CCMG−R50 円合計|CCMG平均Net差 pp|固定route−R50 円合計|固定route平均Net差 pp|",
      "|---|---|---:|---:|---:|---:|---:|"]
    for arm in ("IM","R1"):
        for band in ("<5","5-10",">=10",">=5"):
            v=r["bands"][f"ALL_100:{arm}:{band}"]
            lines.append(f"|{arm}|{band}|{v['pairedN']}|{yen(v['deltaPnlJpy'])}|{pp(v['meanDeltaNetPp'])}|{yen(v['routedDeltaPnlJpy'])}|{pp(v['meanRoutedDeltaNetPp'])}|")
    lines += ["", "R1の固定route 5–10%帯は−¥41,500、≥10%帯は−¥19,800。R1の≥5%合計は−¥61,300で、<5%の+¥48,100と相殺して全体−¥13,200。これは旧報告値の会計差を正規化した値。", "",
      "### 平均Net％を独立に見たWinner Gate", "",
      "|母集団|arm|帯|固定route円差|固定route平均Net差 pp|旧receipt|今回の両条件|",
      "|---|---|---|---:|---:|---|---|"]
    for world,label in (("PRIMARY_FUNDED","Primary"),("ALL_100","全Entry")):
        for arm in ("IM","R1"):
            for threshold in (5,10):
                v=r["winnerGateAudit"][f"{world}:{arm}:>={threshold}"]
                lines.append(f"|{label}|{arm}|≥{threshold}%|{yen(v['routedAggregateDeltaJpy'])}|{pp(v['routedMeanDeltaNetPp'])}|{v['oldRoutedReceiptGate']}|{v['routedBothGate']}|")
    lines += ["", "全Entry IMの≥5/≥10は円差が正でも平均Net％差が負。旧receiptの同等とみなせない。PrimaryのPASSは少数のfunded subsetに限る。", "",
      "![上昇帯別差分](figures/01_delta_by_band.png)", "",
      "### 利益・損失の集中と順位", "",
      "|arm|CCMG改善 / 悪化 N|利益総額|損失総額（絶対値）|損失上位5件の損失比|負のセッション|",
      "|---|---:|---:|---:|---:|---:|"]
    for arm in ("IM","R1"):
        v=r["concentration"][f"ALL_100:{arm}"]
        lines.append(f"|{arm}|{v['positiveN']} / {v['negativeN']}|{yen(v['grossGainJpy'])}|{yen(v['grossLossAbsoluteJpy'])}|{Decimal(v['lossTopN']['5']['shareOfGrossLossPct']):.1f}%|{v['negativeSessionN']} / 24|")
    lines += ["", "損失上位5件はIMで約32.6%、R1で約36.0%。最大損失のEntry IDと全セッション差分は`A1_RESULTS.json`に保存。Δ≠0だけで母集団を選んでいない。", "",
      "Potentialのscore/decileとΔの記述的な順位相関（Spearman、全pairedで同値を含む）："]
    for arm in ("IM","R1"):
        lines.append(f"- {arm}: head5 {r['rank'][arm]['head5']['scoreDeltaSpearmanDescriptive']:+.3f}、head10 {r['rank'][arm]['head10']['scoreDeltaSpearmanDescriptive']:+.3f}。単調なEXIT価値の順位関係はこの観察から確認できない。")
    lines += ["", "![Potential順位と差分](figures/02_rank_vs_delta.png)", "",
      "### 対応Entry、SELL判断、約定参照", "",
      f"IM/R1の同じopportunityで両方の保存outcomeが既知な対応組は{r['crossArmOpportunity']['sameOpportunityKnownPairedN']}組。このうち両armでPrimaryは{r['crossArmOpportunity']['bothPrimaryN']}組、Entry分が同じなのは{r['crossArmOpportunity']['sameEntryMinuteN']}組。別Entry時刻の組を同一取引として足していない。", "",
      "|arm|paired中CCMG初回intent|両model intent時刻既知|CCMG intentがR50 fillより先|CCMG fillがR50 fillより後|同一fill価格|完全stage-2 snapshot|",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for arm in ("IM","R1"):
        v=r["intentAndFill"][f"ALL_100:{arm}"]
        lines.append(f"|{arm}|{v['ccmgFirstIntentN']}|{v['bothModelIntentKnownN']}|{v['ccmgIntentBeforeR50FillN']}|{v['ccmgFillAfterR50FillN']}|{v['sameFillPriceN']}|0|")
    lines += ["", "R50の`controlNow`はMODEL_EXITなら判断時刻。FORCED_TERMINALの925を早期SELL_INTENTとして数えない。`controlExitMinute`と`candidateExitMinute`は保存された約定参照時刻で、intent時刻ではない。初回CCMG intentのguard traceはknownAt≤nowを確認できるが、stage-2用の完全なruntime特徴量は保存されていない。", "",
      "## 不足Evidenceと判定", "",
      "- この24セッション外の許可済みDevelopment期間に、同一EntryのR50/CCMG双方のoutcomeがあると確認できない。別期間の教師数を増やしていない。",
      "- frozen feature arrayはreceipt上のSHAだけでこのcheckoutに現物がなく、再hashできない。canonical OOFとrouteのSHAは照合済み。stage-2の入力lineageとfirst intent時点のas-of特徴量を次実験前に監査する必要がある。",
      "- Primaryと全Entry、IM/R1、旧receiptと正規化列の位置付けを維持する。旧POTENTIAL_SKILL_FAILはRank Signal PASSで置換しない。",
      "- 結論：A1は保存済みOutcomeの記述的差分。CCMGの一般適用を支持せず、案Bの実験可否は追加のcausal snapshot・support・独立のGate定義に依存。選定なし、productionReady=false。",
      ""]
    path=a.OUT/"REPORT-ja.md"
    if path.exists():raise ValueError("APPEND_ONLY_REPORT")
    path.write_text("\n".join(lines))
    make_figures(r)


if __name__=="__main__":
    report()
