"""Produce honest STOP deliverables without fabricated Capital results."""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import zipfile
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs/evidence/phase57-capital-state9-vnext-20261004"
PRIVATE = REPO.parent / "capital_vnext_private"
BRANCH = "capital-state9-vnext-20261004"
C2 = "c55b2b2134f79cbe33085b6757337048d150c2cb"
SAFETY = {k: False for k in (
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted", "productionReady")}


def save(name, value):
    (OUT/name).parent.mkdir(parents=True, exist_ok=True)
    (OUT/name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)+"\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    now = dt.datetime.now(ZoneInfo("Asia/Tokyo")).isoformat()
    a = json.loads((OUT/"CURRENT_STRATEGY_ADAPTER_AUDIT.json").read_text())
    independent = json.loads((OUT/"INDEPENDENT_AUDIT.json").read_text())
    assert a["status"] == "CAPITAL_ADAPTER_MISMATCH"
    assert independent["status"] == "PASS_SOURCE_ADAPTER_AUDIT_ONLY"
    save("CHECKPOINT_RECEIPTS/C2_RESULT_COMMIT.json", dict(checkpoint="C2_SOURCE_ADAPTER_STOP", actual_result_commit=C2,
                recorded_after_commit=True, saved_at_jst=now))

    blocked = dict(saved_at_jst=now, basis_head=C2, status="NOT_EXECUTED_BLOCKED_BY_C2",
                   blocking_status="CAPITAL_ADAPTER_MISMATCH", new_fits=0, new_portfolio_replays=0,
                   result_values=None, no_zero_imputation=True, safety=SAFETY)
    save("LEGACY_BASELINE_RESULTS.json", blocked | dict(
        complete_legacy_adaptive_reproduction_possible=False,
        legacy_feature_status="LEGACY_FEATURE_UNAVAILABLE", mechanics_only_baseline_created=False,
        fixed_sanity_MAX3_MAX4_MAX5_replayed=False, Final_Equity=None, MaxDD=None, utilization=None))
    save("STATE9_ENTRY_JOIN_AUDIT.json", blocked | dict(
        C4_executed=False, asof_join_coverage=None, path_prefix_coverage=None,
        actual_historical_known_at="UNKNOWN", inherited_assumption="closed-bar bar_end",
        frozen_trace_files_available_N=1600,
        snapshot_preflight_only=dict(current_observed_primary_N=558, display_only_N=882,
                                     neither_N=160, total_N=1600, observed_primary_pct=34.875),
        snapshot_preflight_is_not_causal_join_certification=True,
        display_primary_cannot_replace_unknown_current_primary=True))
    save("STATE9_INCREMENTAL_RESULTS.json", blocked | dict(
        C5_executed=False, current_label_incremental_value=None, path_incremental_value=None,
        support_gate_evaluated=False, value_disposition="UNTESTED_NOT_A_NEGATIVE_VALUE_RESULT",
        future_outcomes_used_as_Runtime_inputs=False, current_CAPITAL_leakage_certification=None))
    save("CAPITAL_RANK_PRECOMMIT.json", blocked | dict(status="NOT_PRECOMMITTED_BLOCKED_BY_C2", C6_executed=False,
        candidate_ranker_count=0, thresholds_precommitted=False, teacher_precommitted=False,
        session_split_precommitted=False, fit_budget_precommitted=False,
        old_085_070_055_thresholds_adopted=False))
    for name in ("CAPITAL_RANK_FEATURE_CONTRACT.json", "CAPITAL_RANK_SPLIT_CONTRACT.json", "CAPITAL_RANK_BUDGET.json"):
        save(name, blocked | dict(contract_created=False, allocated_new_fit_or_threshold_budget=None,
                                 consumed_fit_budget=0, consumed_threshold_search_budget=0))
    save("CAPITAL_POLICY.json", blocked | dict(policy_created=False, policy_hash=None,
        SHORT_allowed=False, margin_allowed=False, leverage_allowed=False,
        current_side="LONG_ONLY", account="CASH_EQUITY_ONLY", MAX_N_definition="CONCURRENT_POSITION_CAP",
        Adaptive_sizing_replaced_by_Equity_divided_by_N=False,
        old_feature_or_parameter_direct_adoption=False, Frozen_Entry_changed=False, Frozen_EXIT_changed=False))
    save("CAPITAL_COMPARISON.json", blocked | dict(arms_replayed_N=0,
        groups={k:{str(n):dict(status="NOT_EXECUTED", Final_Equity=None, MaxDD=None, utilization=None,
                              accepted=None, rejected=None, winner_GE5_capture=None) for n in (3,4,5)}
                for k in ("FIXED_SANITY", "CURRENT_MECHANICS_BASELINE", "STATE9", "STATE9_PLUS_PATH")},
        State9_plus_Path_precommitted=False, winner_selected=None,
        north_star_used_for_sizing_or_thresholds=False))
    save("EXPOSURE_LEDGER.json", dict(saved_at_jst=now, basis_head=C2,
        historical_cohort="Previously outcome-exposed Development:1600 FIRST_ENTRY /2155 watches /58 sessions",
        development_source_and_execution_outcomes_read=True,
        new_protected_opens=0, new_holdout_opens=0, new_fresh_opens=0, new_Validation_opens=0,
        new_OOS_opens=0, new_Prospective_opens=0, provider_requests=0, new_market_data=0,
        new_model_fits=0, new_ranker_fits=0, new_teacher=0, new_threshold_search=0,
        Capital_primary_replay=0, Capital_independent_replay=0, current_State9_full_reconstruction=0,
        Frozen_Entry_replay=0, Frozen_EXIT_replay=0, same_dataset_future_quality_remeasurement=0,
        legacy_original_offline_tests=18, legacy_synthetic_pnl_canary_N=1,
        source_audit_primary_N=1, source_audit_independent_N=1,
        current_Capital_allocation_decisions_N=0, orders=0, main_merges=0, force_pushes=0,
        claude_calls=0, other_external_ai_calls=0, current_raw_row_publication=False, safety=SAFETY))
    save("CAPITAL_CLOSURE.json", dict(saved_at_jst=now, basis_head=C2,
        status="CAPITAL_ADAPTER_MISMATCH", stop_condition="20.B", stop_stage="C2",
        completed=["C0_LATEST_AUDIT", "C1_LEGACY_RECOVERY", "C2_SOURCE_ADAPTER_AUDIT", "INDEPENDENT_SOURCE_AUDIT"],
        not_executed=["C3_BASELINE", "C4_ASOF_JOIN", "C5_INCREMENTAL", "C6_RANK_PRECOMMIT",
                      "C7_CURRENT_CAPITAL_POLICY", "C8_MAX3_MAX4_MAX5_REPLAY", "C9_FULL_PORTFOLIO_AUDIT"],
        Frozen_Entry_HEAD="4a2d6f35946b16820a13449a9288a6685a5c283c",
        Frozen_EXIT_v3_HEAD="c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad",
        EXIT_v3_official_freeze_receipt_HEAD="1ecbcc43f75279fa302f19fd896add2aac15b537",
        Capital_freeze_candidate=False, State9_value_disproved=False,
        Integrated_ready=False, Integrated_started=False, current_Portfolio_values=None,
        candidate_outcome_filtering=0, synthetic_cash_release=0,
        blockers=["39 Frozen EXITs unresolved across29 sessions",
                  "1420 candidate holding windows lack some exact regular1m source marks",
                  "No certified cross-session mark continuity for hypothetically funded unresolved positions",
                  "Legacy quality features unavailable; legacy scorer is not semantically reproducible",
                  "Reference fills and raw source availability timestamps are different; historical actual arrival is unknown"],
        repair_boundary="Read-only recovery of an already frozen admissible source/receipt is allowed. If new prices/data, altered fill/cash timing or a different null-aware comparative protocol are required, this is a new lineage/protocol decision, not an import/path fix. Preserve the old freeze and append the difference before restarting.",
        next_direction="Resolve source/valuation/known-at admission first; resume C2, then C3; do not perform ranking fits while input admission is blocked.",
        orders=0, main_merges=0, force_pushes=0, Claude_used=False, safety=SAFETY))

    chart_dir = OUT/"charts"
    chart_dir.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(10.8,5.5))
    labels = ["Frozen EXIT source", "Candidate regular 1m window", "Entry State9 snapshot"]
    groups = [[1561,39,0],[180,1420,0],[558,882,160]]
    colors = ["#2979A4", "#DA8B35", "#9DABB5"]
    names = [["FILLED","UNRESOLVED",None], ["No missing expected closes","Missing expected closes",None],
             ["Observed current primary","Display-only (not current)","Neither"]]
    for i, parts in enumerate(groups):
        left = 0
        for j, count in enumerate(parts):
            if not count:
                continue
            ax.barh(i,count,left=left,color=colors[j],height=.6)
            if count >= 100:
                ax.text(left+count/2,i,f"{count:,}\n{count/16:.3f}%",ha="center",va="center",color="white",fontsize=10)
            else:
                ax.annotate(str(count),xy=(left+count/2,i),xytext=(left+count/2,i-.48),ha="center",fontsize=10,
                            arrowprops=dict(arrowstyle="-",color=colors[j]))
            left += count
    ax.set_yticks(range(3),labels)
    ax.invert_yaxis()
    ax.set_xlim(0,1600)
    ax.set_xlabel("Frozen candidates (N = 1,600; 58 Development sessions)")
    ax.set_title("Capital vNext: source admission audit — STOP at C2",loc="left",weight="bold",pad=23)
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="x",alpha=.15)
    ax.set_axisbelow(True)
    fig.text(.02,.09,"Rows 1–2: blue = resolved/no missing expected closes; orange = unresolved/missing.\n"
             "Row 3: blue = current observed; orange = display-only; grey = neither.\n"
             "Source snapshot counts only. No causal-join certification or Capital performance was measured.",fontsize=9,color="#425466")
    fig.tight_layout(rect=(0,.18,1,1))
    fig.savefig(chart_dir/"INPUT_ADMISSION_AUDIT.png",dpi=180)
    fig.savefig(chart_dir/"INPUT_ADMISSION_AUDIT.svg")
    plt.close(fig)

    answers = [
        ("旧Capitalの正式lineage", "Fixed:4646d303…／Adaptive v2:f13cc425…(#496)／Realtime:e198040c…(#532)。後続のMSH/Risk v3、LONG-only Capital Rank v2/v3、Replacement、09-27報告closureを区別して保存。Adaptive v2の正式winnerは確認されない。"),
        ("FixedとAdaptiveの違い", "FixedはCurrent MTM Equity/N。Adaptive v2はcausal quality→rank/score weight→candidate cap＋dynamic utilization＋reserve。旧Adaptiveの最大同時保有は9。"),
        ("mechanics再利用率", "列挙16component中12を互換／条件付き候補として回収＝75%。コード行数の再利用率ではない。現行engineへの移植完了0%、旧数値直接採用0%。"),
        ("旧confidence/probability/Selector score", "Frozen current1600 recordsに同義4fieldsは各0件。P1 scoreはU/Q/D percentileの複合で、旧probabilityの代用ではない。LEGACY_FEATURE_UNAVAILABLE。"),
        ("Entry時点State9 joinとcoverage", "C4正式as-of joinは未実行、coverage未確定。Frozen snapshotの事前確認では558/1600＝34.875%にobserved current primary。display-only882、どちらもない160。表示名を補完しない。"),
        ("current label incremental value", "未測定。State9に価値がないという結論ではない。P1 Entry score自体が既にState9 current/historyを含む点も将来の比較で管理する。"),
        ("Path prefixの追加価値", "未測定。Full trace1600本の存在・hashは確認したが、prefix contract/join/diagnosticは未実行。"),
        ("新Capital future leakage0か", "新Capitalは未構築・decision0。current joint canary/証明は未実行なので認証しない。旧sourceのfuture-isolation testsと事前canaryはPASS。"),
        ("旧Adaptive型baselineの成績", "現行cohortでは未実行。旧成績を移植しない。完全旧scorer再現不可、mechanics-only baselineも未precommit。"),
        ("State9-aware Capitalの成績", "未実行。Final Equity／DD／utilization等はnull。"),
        ("MAX3/4/5で変わったこと", "現在の比較は未実行。旧MSH MAX_3はbudget Equity/3＋同時保有10で、今回のcap3と別。"),
        ("Adaptiveを1/Nへ置換したか", "置換0。現在MAX-Nはconcurrent capacityという指示を維持。Fixed Equity/Nは将来sanityに限る。"),
        ("utilization80%/90%達成", "未測定。旧Adaptiveのunweighted event平均をtime-weighted値として流用しない。"),
        ("≥5 winner capture/reject", "未測定。Allocation decision0に対してcapture/reject率0%を捏造しない。"),
        ("return/DD/cost/utilization/stability", "現在のtrade-offは評価不能。旧feeを重ねるとcost double countになるため採用していない。"),
        ("Capital Freeze可能か", "不可。CAPITAL_ADAPTER_MISMATCH。No Capital Freeze Candidate。"),
        ("blocker", "39未約定、候補保有窓の欠測MTM、未証明の跨日valuation、reference fillとsource known-atの境界。旧features不足はLegacy scorerの再現blockerであり、mechanics再利用自体を否定しない。"),
        ("Claude使用", "0回。外部AI使用0。"),
        ("orders/main merge/Safety", "orders0、main merge0、force push0、Safety9＋productionReadyすべてfalse。Frozen strategy変更0。"),
        ("Integratedへ進めるか", "進めない。C2入力admissionを解決し、必要なbaseline／State9 diagnostic／precommit／comparison／auditを終えてからCapital判定。Integratedは未開始。"),
    ]
    report = f"""# 🛑 Ark Terminal — Capital vNext：C2停止Report

作成：{now}  
Repo：`Iam-2squared/ark-terminal`  
研究branch：`{BRANCH}`  
実在basis／C2 result HEAD：`{C2}`

**結論：`CAPITAL_ADAPTER_MISMATCH`。指示書20.BでSTOP。Capital Freeze候補はなく、Integrated versionは未開始。**

最新GitHubとhandoffのcontrolling Entry／EXITは一致した。旧Capitalを回収し、18本の原テストと別経路のsource検算を完了した。1,600全候補を同じFrozen Entry／EXITと厳密なcash／MTMで比較する入力admissionが未成立のため、C3以降のfit／Portfolio replayは0。これはCapitalやState9の性能FAILを示す結果ではない。

## 🔒 Controlling strategyとlineage

| 項目 | authoritative identity／判定 |
|---|---|
| FIRST ENTRY v2 P1_Q70 | `4a2d6f35946b16820a13449a9288a6685a5c283c`／OFFICIAL FREEZE |
| Structural EXIT v3 Local Guard | `c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad`／変更0 |
| v3正式Freeze receipt | `1ecbcc43f75279fa302f19fd896add2aac15b537` |
| 既存Capital開始checkpoint | `d26c733407577cf72fff75a9abfa4c8c2b0f3cbe`／引継ぎ |
| Re-entry／EXIT v4 | Re-entry Evidenceのみ、v4拒否維持。統合への採用0 |
| Side／account | LONG-only／cash-equity-only |

handoffのFixed MAX3/4/5-only範囲は、今回の明示WorkでAdaptive研究へ拡張された。Frozen Entry／EXITとExposureは拡張していない。Entry旧FINAL_HANDOFFのBLOCKED記録は、その後のcorrected-lineage freeze receiptで解決された履歴として保持し、最新statusに混同しない。

P1_Q70は既にState9 current＋past-only historyを含む。将来「current Entry features only」にP1 scoreを使う場合、追加State9入力のないCapital baselineではあるが、戦略全体からState9を除いたcontrolとは呼べない。

## 🧩 旧Capital回収：PASS、旧成績の移植0

| 系統 | 機構 | closure／現在への適用 |
|---|---|---|
| Fixed Lane C | Current MTM Equity/N、MAX10/4/3/2、100株lot、cash分離、exact timestamp order | sanity機構。今回のAdaptive主方式にはしない |
| Adaptive v2／PR#496 | causal quality、S/A/B/C、EQUAL/RANK/SCORE、candidate cap、dynamic deployment/reserve、cap9 | 正式winner未確認。旧4features・score weights・rank thresholds・capsを直接採用しない |
| Realtime R6／PR#532 | 28cell、Frozen Entry event、append-only/idempotent ledger、cash／mark | 機構を回収。旧Shadow／SHORTの権限・計算は現在へ移さない |
| 旧MSH/Risk v3 | 七つのclosed5mのvolatility、MSH Entry、EXIT v5 | 09-13 Development MAX_3 Freezeはbudget divisor3／同時保有10。今回のMAX3と別 |
| 後続LONG Capital v2/v3／Replacement | IM/R1 Entry、R35 control、R50等、旧Development | Capital v2未選定、v3 0/2 PASS、Replacement未選定。negativeを維持 |

Reuse Matrixの16component中12が互換／条件付き候補＝75%。等重みcomponent countであり、実装移植完了率ではない。現行engine移植完了0%、旧パラメータ直接採用0%。

**旧Adaptive報告上の修復点：** synthetic one-tradeでcash endpoint増分3,799JPYに対しreported realizedPnLは3,699JPY。Entry fee100JPYがreported PnLで二重控除される。現金端点自体は一致する。旧sourceは変更していない。再利用時の最小修正は、Entryでfeeを計上済みならEXITのportfolio realizedPnLへ`gross−exitCost`だけを加え、trade単位では`gross−entryCost−exitCost`を保持すること。旧Adaptive utilizationはevent-sample平均であり、要求された時間加重utilizationではない。

## 🔎 現在1600 source／adapter監査

| 検査 | 数値 | 判定 |
|---|---:|---|
| Frozen watch／FIRST ENTRY | 2,155／1,600 | PASS |
| Development sessions | 58 | PASS：Fresh/OOSではない |
| original private component hash | 3,211検査／不一致0 | PASS |
| Entry／EXIT identity join | 1,600／不一致0 | PASS |
| source price arithmetic | 1,600 BUY＋1,561 confirmed SELL／不一致0 | PASS |
| Frozen EXIT FILLED | 1,561／1,600＝97.5625% | source確定 |
| Frozen EXIT UNRESOLVED | 39／1,600＝2.4375% | **BLOCKED**：29sessions |
| regular1m source欠測を含む候補保有窓 | 1,420／1,600＝88.75% | MTM source制約 |
| その窓の欠測expected regular1m closes | 113,303 | 補完0 |
| 旧confidence／probability／Selector opportunity／Selector v2同義fields | 各0／1,600 | LEGACY_FEATURE_UNAVAILABLE |
| State9 snapshot current observed primary | 558／1,600＝34.875% | C4正式join coverageではない |
| State9 display-only／どちらもなし | 882／160 | 正常Stateへの補完0 |

「保有窓」はFrozen個別Entry→EXITのsource completenessであり、仮想Capitalが実際に買った保有株のcoverageではない。Allocationは実行していない。State9 current observed primaryはFrozen snapshotのsource事前確認だけで、as-of join／Path prefixの認証ではない。display_primaryをcurrent primaryへ置換すると欠測を隠すため、行わない。

![入力admissionの監査数値](charts/INPUT_ADMISSION_AUDIT.png)

## 🚧 C2で止める理由と技術修復の境界

確認済み価格・identityのschema mappingは可能で、import/path問題ではない。Legacy Lane-Cは全tradeにfinite EXIT timestamp／priceとentry/exit reference==close markを要求し、39未約定をそのまま表現できない。raw Closeとeffective execution priceも別物なので、合成Closeを挿入して同一にしない。

既存LONG-only null-aware ledgerは未約定をlocked obligationとして保持できる。この機構も回収したが、未約定を確定売却に変えたり、未証明の跨日markを復元したりはできない。39件を全てCapitalが購入するという予測はしていない。ただし全1,600を保持した比較入力の完全性が未成立であり、完結したEquity／DD／Freeze evidenceを事前に確保できない。会計censoringだけの部分再生を、完全比較の代用として黙って開始しない。

**禁止した救済：** UNRESOLVED39件の未来結果による除外、last-observed Close／ゼロによる売却価格補完、未約定cash release、架空の跨日mark、旧scoreの代用品、旧fee追加、Gate緩和。いずれも0。

現行BUYはraw Open×1.0005、SELLはraw Open／exact auction Close×0.9995、commission0。旧round-trip0.05%やR34 sell0.05%を加えると、Frozen cost contractを変える。確定SELL1,561件のsource assumed_available_atはreference fill timestampより1分後で、実際のhistorical arrivalはUNKNOWN。これは継承されたreference-fill／データarrivalの限界であり、このWorkが新たにFrozen EXITのlookaheadを証明したという意味ではない。Current allocatorのknown-at／cash event contractへ無説明でbackdateしたり、Frozen fillを移動したりしない。

既に凍結されたadmissible source／receiptのread-only回収で解決できるならlineageを記録してC2を再開する。新市場データ、fill/cash時刻変更、null-aware部分比較の新protocolが必要なら、今回の停止EvidenceとFreezeを保持して別の明示contractとして扱う。結果を見てthresholdやfeatureを追加する修復はしない。

## 🧪 独立監査と工程status

Primary：展開済みZIP→hash／identity／Decimal。
Independent：元添付nested ZIP bytes→SQLite join／集計→Fraction price計算。Primaryコードをimportしない。不一致0。**PASSはsource adapter監査だけで、C9 full portfolio audit PASSではない。**

| 工程 | status | 実行内容 |
|---|---|---|
| C0 | PASS | latest refs／PR／Actions／controlling status／Exposure |
| C1 | PASS | source・旧policy・closure・再利用候補、18原テスト |
| C2 | **BLOCKED** | source identity/hash/confirmed price PASS、all1600 admission STOP |
| C3〜C8 | NOT EXECUTED | baseline／join／incremental／precommit／rank／MAX3/4/5すべて未実行 |
| C9 | NOT EXECUTED：full portfolio | independent source検算のみ完了 |
| C10 | STOP closure | 本Report、handoff、status付き未実行成果物、private evidence |

current Final Equity／MaxDD／utilization80/90／winner capture／rank allocation／robustnessは**未測定null**。空のEquity curveや仮数値のPortfolioグラフは作成しない。`CAPITAL_DECISIONS.jsonl.gz`と`PORTFOLIO_CURVES.jsonl.gz`はPrivate package内の0-record containerで、未実行を表す。0%成績やゼロPnLを表さない。

GitHub最新Actionsのread-only確認は済み。この研究branchにActions実行0件、追加CI-green claimなし。18原テストはlocal PASS。source独立検算はPASS。新モデル／strategy replayをCIで走らせていない。

## 📋 最後の20質問

| # | 問い | 回答 |
|---:|---|---|
""" + "".join(f"| {i} | {q} | {answer} |\n" for i,(q,answer) in enumerate(answers,1)) + f"""

## 🛡️ Exposure／Safety／次方向

新fit0、新Ranker0、threshold search0、Capital replay0、Entry／EXIT replay0、provider0、新market data0、Protected／Holdout／Fresh／Validation／OOS／Prospective opens0。以前からoutcome-exposedのDevelopment source／execution metadataのみを監査した。

execution／broker／Excel order／RSS order／live／paper／automaticPromotion／productionUpdate／transmitted／productionReadyはすべてfalse。orders0、main merge0、force push0、Claude0。旧sourceと他branchのEvidence上書き0。

**次方向はC2 source／MTM／known-at admissionの解決。C3以降のresearchとIntegratedを自動開始しない。** 現在のCapital成績やState9価値は未判定のまま保持する。Result commit receiptはcommit後に別append-only receiptで保存し、未来SHAを記載しない。
"""
    (OUT/"REPORT-ja.md").write_text(report)
    (OUT/"CONTROLLING_HANDOFF.md").write_text(f"""# Controlling handoff — Capital vNext STOP

JST: {now}
Repo/branch: Iam-2squared/ark-terminal / `{BRANCH}`
Actual basis/C2 result HEAD: `{C2}`. The enclosing closure commit is recorded after commit in CHECKPOINT_RECEIPTS.

Status: **CAPITAL_ADAPTER_MISMATCH / C2 / STOP20.B**. C0/C1 and primary/independent source checks are complete. C3–C8 and C9 full portfolio audit are not executed; no Capital winner/Freeze candidate or Integrated start.

Frozen FIRST_ENTRY v2 P1_Q70 `4a2d6f35946b16820a13449a9288a6685a5c283c`; EXIT v3 `c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad`, formal receipt `1ecbcc43f75279fa302f19fd896add2aac15b537`, unchanged. Re-entry Evidence-only; v4 remains rejected. LONG/cash only.

1600 candidate identity joins,3211 hashes,1600 BUY/1561 SELL source prices match.39 exits remain UNRESOLVED across29 sessions;1420 candidate holding windows have missing exact regular1m marks. Legacy scorer inputs unavailable. Snapshot558 observed current State9 labels is not a formal as-of join certification. No State9 value conclusion.

Old mechanics recovered12/16 conditional candidates (75% unit-count compatibility,0% current migration). Old parameters0% directly adopted. Legacy Adaptive reported realizedPnL double-counts entry fee in a synthetic check; do not reuse its report unchecked. Old MSH MAX_3 budget/cap10 is not current cap3. Preserve subsequent Capital v2/v3/replacement negative Evidence.

Next: resolve current all1600 source/valuation/known-at admission before C3. Read already frozen admissible recovery sources if present; any new data/fill/cash-time/null-comparison protocol must be an explicit new lineage, without altering old Frozen Evidence. Do not delete UNRESOLVED, use last Close, invent cash, hide unknown States, alter thresholds or reuse old performance.

Source audit reproduction: `python research/capital-state9-vnext-20261004/audit_adapter.py`; independent: `python research/capital-state9-vnext-20261004/independent_source_audit.py`. Supply exact original attached handoff and original extracted dependencies. For a new execution, use a new cycle/output path and preserve existing result files; never run over an existing Evidence directory. Code-only conditional-label/unused-initializer cleanups after the first source audit are disclosed in TECHNICAL_AUDIT_CODE_RECEIPT; no outcomes or conclusions changed.

Report and all null/NOT_EXECUTED status artifacts are public-safe aggregates. Row-level source/hash audit is retained in a separate Private STOP Evidence package; do not publish it to the public repository. Empty decisions/curves have0 records because no allocator/replay ran.

All Safety false; fit/replay/search/provider/new protected/execution/orders/main merge/force push/Claude0. Current joint future-isolation and full portfolio accounting tests are not claimed PASS.
""")
    save("CHECKPOINTS/C10_ADAPTER_BLOCKED_CLOSURE.json", dict(saved_at_jst=now, repo="Iam-2squared/ark-terminal",
        branch=BRANCH, basis_head=C2, current_status="CAPITAL_ADAPTER_MISMATCH", what_changed="Report, blocked/NOT_EXECUTED artifacts,source chart and STOP handoff",
        what_did_not_change="Frozen Entry/EXIT/State9/Path/old source/protected boundaries", executed_scope="C0–C2 plus independent source audit, no allocation/fit",
        source_hashes={name:sha(OUT/name) for name in ("CURRENT_STRATEGY_ADAPTER_AUDIT.json","INDEPENDENT_AUDIT.json","EXPOSURE_LEDGER.json","CAPITAL_CLOSURE.json")},
        fit_budget_consumption=0,replay_budget_consumption=0,exposure="outcome-exposed Development only; newly protected0", safety=SAFETY,
        results="39 unresolved, source mismatches0, no Capital selection",unresolved="all1600 source admission / cross-session valuation / execution known-at",
        next_direction="Resolve C2 first; no Integrated start"))

    # Empty containers honestly represent no executed allocator/portfolio, not
    # zero-return synthetic data. Their meaning is explicit in both manifests.
    for name in ("CAPITAL_DECISIONS.jsonl.gz", "PORTFOLIO_CURVES.jsonl.gz"):
        with (PRIVATE/name).open("wb") as f:
            with gzip.GzipFile(filename="",mode="wb",fileobj=f,mtime=0):
                pass
    (PRIVATE/"README.md").write_text(f"""# Capital vNext — Private STOP Evidence

JST: {now}. Status CAPITAL_ADAPTER_MISMATCH /STOP20.B atC2.
Actual public C2 checkpoint `{C2}`; branch `{BRANCH}`. Public Report/closure contains the complete decision and20 answers.

ADAPTER_ROWS:1600 identities, never an allocation ledger.
UNRESOLVED_EXIT_ROWS:39 unchanged missing Frozen exits, with source/price timestamps and reasons.
MARK_COMPLETENESS_ROWS:1600 source completeness checks, not funded-position MTM.
INPUT_HASH_CHECKS:3211 exact source component checks, private filenames retained here only.
CAPITAL_DECISIONS and PORTFOLIO_CURVES:0 records, allocator/replay not executed; no zero-valued financial metrics implied.

Frozen original source dependency hashes are retained in the public SOURCE_MANIFEST /INDEPENDENT_AUDIT. This package adds no market data, State semantics, teacher, rank or policy. No Entry/EXIT source is modified or duplicated as a new authoritative dataset.
""")
    private_components={p.name:dict(bytes=p.stat().st_size,sha256=sha(p),records=0 if p.name in ("CAPITAL_DECISIONS.jsonl.gz","PORTFOLIO_CURVES.jsonl.gz") else None)
                        for p in sorted(PRIVATE.iterdir()) if p.is_file() and p.name != "MANIFEST.json"}
    (PRIVATE/"MANIFEST.json").write_text(json.dumps(dict(saved_at_jst=now,status="CAPITAL_ADAPTER_MISMATCH",basis_head=C2,
                                                       no_portfolio_replay=True,components=private_components),indent=2,sort_keys=True)+"\n")
    delivery=REPO.parent/"Ark_Capital_vNext_C2_STOP_EVIDENCE_20261004_PRIVATE.zip"
    with zipfile.ZipFile(delivery,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PRIVATE.iterdir()):
            if p.is_file():z.write(p,p.name)
    save("PRIVATE_STOP_PACKAGE_RECEIPT.json", dict(saved_at_jst=now,filename=delivery.name,bytes=delivery.stat().st_size,
          sha256=sha(delivery),visibility="PRIVATE",public_row_level_upload=False,component_N=len(private_components)+1))

    sources=[]
    for p in sorted(REPO.rglob("*")):
        if p.is_file() and OUT not in p.parents and "__pycache__" not in p.parts:
            name=str(p.relative_to(REPO))
            if name.startswith("research/capital-state9-vnext-"):
                continue
            ref="d26c733407577cf72fff75a9abfa4c8c2b0f3cbe"
            if name == "predict/research/phase57-capital-allocation-integrated-candidate-freeze.json":ref="84b296102b85ab2909385a8f3ee7ef336c9b6129"
            if name.endswith("CAPITAL_ENDPOINT_RECONCILIATION_HANDOFF.md"):ref="0357d0a507d39515c70687448b515fc543e28f0a"
            sources.append(dict(path=name,ref=ref,bytes=p.stat().st_size,sha256=sha(p),role="read-only source recovery; original file preserved"))
    save("SOURCE_MANIFEST_FINAL.json",dict(saved_at_jst=now,basis_head=C2,sources=sources,
        private_inputs_original_archive_sha256=independent["input_archive_sha256"],
        private_inputs_nested_archive_sha256=independent["nested_archive_sha256"],
        private_component_hash_checks=3211,private_component_mismatches=0))
    files={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=sha(p),visibility="PUBLIC_SAFE")
           for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "MANIFEST.json"}
    save("MANIFEST.json",dict(saved_at_jst=now,basis_head=C2,status="CAPITAL_ADAPTER_MISMATCH",files=files,
         private_package=delivery.name,Capital_decision_records=0,Portfolio_curve_records=0,
         portfolio_graphs_created=False,input_admission_chart_created=True))
    print(json.dumps(dict(status="CAPITAL_ADAPTER_MISMATCH",public_components=len(files)+1,
                         private_package=str(delivery.resolve()),private_package_bytes=delivery.stat().st_size,
                         report=str((OUT/"REPORT-ja.md").resolve())),indent=2))


if __name__ == "__main__":
    main()
