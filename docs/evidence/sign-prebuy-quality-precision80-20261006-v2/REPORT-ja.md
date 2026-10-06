# 🧭 第一層Sign：実装準備完了、非公開入力待ち

実時計JST: 2026-10-06T13:58:00.601196+09:00
実時計UTC: 2026-10-06T04:58:00.601196+00:00
branch: research/sign-prebuy-quality-precision80-20261006-v2
basis HEAD: 9b75882957fa897c5df016ac5ddcb368602ccedc
owner: codex-root-sign-prebuy-v2

## 🎯 結論と前回からの差

通過群PLUS率80%以上はまだ未検証・未達成。新fit0、閾値選択0、市場性能採点0。今回は固定BUY_INTENTまでの入力境界を強制するextractorと欠測条件/集計監査を実装し、48合成検算がPASSした。これは市場性能の検証ではない。

旧80%はPLUS保持率の条件だった。旧後半13sessionsの通過はPLUS139/MINUS162、PLUS率139/301=46.18%。これを今回80%達成とは扱わない。

## 🔍 確認済みと未確認

旧P0はfirst-intent row id/indexへのjoinを監査済み。G_PRICE62.57%は167268特徴量セルの欠測率であり、Entry欠測率やRAW取得失敗率ではない。凍結strict-window不足、half-session境界、前日不足、分母無効、VWAP coverageなどがnullを生む。実行行への原因配賦は原本未配置で未実施。

旧研究のfill時点Open引用仮定と今回intent境界を区別した。新extractorはFill価格/時刻/遅延、future State/Path suffixへ依存しない。State9/Pathの再計算や意味変更は0。主構造距離とstrict prior local LHLを観測済み入力として記述する。

## 🧪 次の有限案

intent P1全特徴量と構造距離追加、固定Logistic/HGBの最大4候補。Discovery20fit、locked確認3fit、再選択しない診断10fitの最大33fit案。CALで80%PLUSと非退化条件を満たす閾値を固定し、TESTで変更しない。支持件数/schema/producer/成熟をまだ確認できていないためDRAFTであり、実験契約固定・学習は未実行。利益額/資産額/Rによる選択なし。反復利用済みDevelopmentをFreshと呼ばない。

## 📦 blockerと次の方針

非公開入力とモデルはこのworkspaceに未配置。GitHubにはbundleのhash/sizeと公開code/集計だけがある。まず約26MBの Ark_Independent_Entry_EXIT_Sign_V1_20261006_PRIVATE.zip を提供してもらい、記録hashを照合し旧保存入力/モデルを再利用する。intent原grid/matrix/State traceが不足していればcomplete handoffの必要archiveだけを追加する。

その後は未確認の行別欠測原因・intent接続・producer時点/教師成熟を確認し、有限契約を固定してGitHub actual GETを行ってから新fitする。Selector/Entry/EXIT/EOD/費用/約定/State9/Path/Rank維持。第2層/Capital Replay/provider新取得/実運用は0。

## 💾 保存

開始checkpointは9c6ada7734e9420f5b09fd90dfd400bc7e1d5472へ保存し、本文/blob/HEAD actual GET一致。Git pushは401で拒否されたため、既に有効なGitHub APIで新branch/tree/commitを作成し、expected HEAD付きnon-force更新を使用した。失敗したpushを保存完了とは扱っていない。最終保存のcommitとreadbackは自己参照せず別receiptに残す。
