# Phase57 PRR EXIT — Controlling Handoff

2026-09-29 JST。Draft PR #587、研究branch `research/phase57-long-only-cash-equity`。本cycleのPrecommit SHA-256は `809c75a42a8c4538fd198091aa23bd77ff28b693aa2ce4279a3aa2baeda0e20a`。設計は `PRR_CCMG_M50_AND_V1` 一候補、Entry時のfold-local TRAIN decision-score medianを2 headともstrictに下回る場合だけCCMG、それ以外はR50と固定した。結果を見た閾値変更はない。

## Controlling decision

`RANK_REPRODUCTION_FAIL` → `NO_SELECTION`。最初のfold-3 pinned OOF test行で、新たな `>=5` headの `predict_proba` と保存済みOOFが事前固定の絶対許容差 `1e-10` を超えて不一致。source/prefit SHA照合と566列feature再生成は通過したが、OOF再現のHard Gateを通らなかった。差分実数とEntry IDはfail-fast CIが保存しておらず不明。AUCやroute prevalenceを推定しない。Route map、decile/quadrant anatomy、Layer A、all-entry、Integrated Capital、0.20pp stress、Month-2xを実施しない。

最初の2 runは依存不足とsource pin転記の切れでfit前停止。転記は元CCMG MANIFESTと同じ実ファイルhashに訂正したことを `SOURCE_PIN_ERRATUM.json` でappend-only公開し、Precommitは一字も変更していない。3回目のCIでfold-3の2 headをfitしてから最初のOOF照合で停止。cycle累計fit試行2/6、Integrated Replay 0/16。30/30 focused synthetic testsはPASS。

Probability headの歴史的 `POTENTIAL_SKILL_FAIL` は両headとも維持。今回のPotential rank routingは `UNMEASURABLE` であり、probability calibrationやrouting economicsの成否を主張しない。

## Evidence and boundaries

- `START_AUDIT.json`: 開始時HEAD、Draft PR、Actions、先行CCMG/R54/WPSD/Guard。
- `CYCLE_PRECOMMIT.json` / `.sha256`: 見る前に固定したroute・Gate・budget。
- `SOURCE_PIN_ERRATUM.json`: 40桁転記の訂正。実ファイルと元MANIFESTは64桁で一致。
- `RANK_REPRODUCTION.json`: fail-fast CI run 36492615798、予め定めた `1e-10` の不一致。
- `ROUTE_FEASIBILITY.json`: OOF不一致により未実施。
- `EXPOSURE_LEDGER.json`: fit 2、Replay 0、provider/restricted/orders/mergeすべて0。
- `INDEPENDENT_AUDIT.json`: source hash、CI停止点、fit数、no-selectionの独立照合。差分実数の独立再計算は不可能と明記。
- `FINAL_CLOSURE.json` と `MANIFEST.json`: controlling status。

Safety 9 flagsは全false。Selector、Entry、Capital、R50、CCMGを変更していない。productionReady=false、paper/live不可、orders=0、main merge=0。新provider、Protected、Fresh、Validation、OOS、Prospectiveは開いていない。

次の境界は別Precommitで数値環境・solverの再現性を調べ、最初の不一致のEntry ID・raw score・両predict値・差分をfit budget内に保存すること。今回の許容差やrouting閾値を結果後に緩めて続行しない。保護されたpartitionや新規providerを使う承認にもならない。
