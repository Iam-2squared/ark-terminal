# 🔍 C2 Recovery — 影響と意味境界

## ✅ 回収で確定したこと

凍結時の元archive・source token・raw pathを回収し、現在の1,600件のtoday rawはSTOP sourceと完全一致した。別watchのprevious-session contextも対象symbol/sessionだけに照合し、追加minute・値矛盾とも0だった。39件に新しいadmissible SELL sourceは加わっていない。

identity、BUY1,600件、SELL1,561件の費用込み価格は原本と一致。Primaryと、原本ZIP→SQLite/FractionのIndependentでmismatch=0。source有効性は最後にFrozenのlen7・coherent OHLC・nonnegative volume/value条件で再確認し、初回の厳しすぎるpredicateをappend-only補足で訂正した。分類・件数は変わらなかった。

## 📏 旧STOPのmark指標をどう読むか

1,420/1,600のfull regular1m holding-window欠損と113,303 missing rowsは、candidate source completenessの正しい記述である。allocation前に全candidateへ要求すべき正式Gateを証明する数値ではない。旧Lane Cの5分clockと、旧LONG-onlyのfunded-only/null-aware処理を回収したため、この指標だけでCapital admission不能とは結論しない。

ただし現在Frozenへのmark clock・price role・availability・cross-session・計測可能範囲のbindingは確定していない。funded subsetはallocation未実行のためUNKNOWN。5分境界での1分Close存在確認は診断のみで、cadence変更、native5m source生成、補間を実行していない。

## ⏱️ +1分問題の影響

Frozen研究上のreference executionとbar completionの区別は元contractに明記されている。この区別自体を矛盾や新しいlookahead FAILと認定していない。2026年のhistorical retrieval receiptから2025年のactual arrivalやfill confirmationを生成することはできない。

同じ資料をCapital runtimeのcash-known eventへ直接変換する保証はない。reference fillを変えずcash releaseのみ別clockへ移すとしても、同時刻ENTRYの予算、資金再利用、utilization、DDの測定時点に影響する。今回その新bindingを実験しない。

## 🧾 未解決EXITの影響

39件は29session・38symbolに存在する。exact sourceがないことと真のno-trade/haltは同義ではない。unfundedならPortfolio liabilityは発生しないが、その事実はfuture outcomeを見て入口で排除する根拠にならない。fundedなら既存fail-closed/null mechanicsに従う候補はあるものの、完全なPortfolio比較と跨session処理の成立は未確定。

## 🚦 採用しなかった変更

Frozen identity・price・timestamp・EXIT outcome、費用、ranking、threshold、source補完、39件除外はすべて変更0。main merge・force push・provider request・新market data・fit・各replay・Claude・発注は0。新contractは`PROPOSED_NOT_AUTHORIZED`で保存し、C2未PASSとして停止する。
