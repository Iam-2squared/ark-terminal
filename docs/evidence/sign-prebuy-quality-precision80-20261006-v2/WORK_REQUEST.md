# 🧭 第一層：購入前品質監査と通過PLUS率80%研究

実時計JST: 2026-10-06T13:52:17.533107+09:00
実時計UTC: 2026-10-06T04:52:17.533107+00:00
文書ID: ARK_SIGN_PREBUY_QUALITY_PRECISION80_V2_20261006
branch: research/sign-prebuy-quality-precision80-20261006-v2
basis HEAD: 9b75882957fa897c5df016ac5ddcb368602ccedc
実行owner: codex-root-sign-prebuy-v2

## 🎯 今回の承認と目標

ユーザーの今回の明示指示により、新Workを開始する。固定Entry→固定EXIT/EODの費用後符号だけを教師にし、予測通過群の既知PLUS率80%以上を最低目標にする。旧WorkのPLUS保持率80%とは異なる。損益額・資産額・R・U教師・sample/class weightをSignの比較、閾値、合否に使用しない。ZEROとUNKNOWNは別枠。80%は実測で検証すべき目標であり、実現済みではない。

## 🔒 維持する境界

Selector/Entry/EXIT/EOD/費用/Fill/State9/Path/profile/窓/gap/既存Rankは変更しない。旧独立Sign v1の終了記録と43fit/5再利用を保持する。今回のSign cutoffはfirst_intentのBUY_INTENT時点。raw Fill Open、Fill時刻、intent→Fill遅延、Fillまでの後続Stateを入力へ流用しない。旧fill-boundary研究はOpen引用のhistorical assumptionを明示しており、今回のcutoffとの差を旧研究の不正とは呼ばない。

## 🔍 最初に完了する作業

既存監査を再利用し、未確認のRAW-prefix由来欠測原因とintent境界の接続だけを調べる。セル欠測率、Entry欠測率、日付/銘柄coverageを分ける。予定足gapを取得失敗と断定せず、取得manifestがなければ原因未確定として残す。品質別の旧予測集計は記述診断であり、完全caseの後付け採用や修復効果の主張に使わない。

## 🧪 新実験の進め方

入力監査後、修復と表現追加を分ける。intent時点の固定P1全特徴量、State9構造水準への距離、確認済み局所pivot、適用外/観測欠損、安全な既存P1予測scoreの再利用を候補にする。最大4候補・33model fitsの有限案を準備するが、入力schema、hash、metadata支持件数、producer成熟/学習依存の確認前には実験契約を凍結した扱いにしない。事前固定とGitHub actual GETの後だけfitする。候補/seed/閾値を後半結果へ合わせて追加しない。

第2層接続・Capital Replay・provider新取得・実運用は今回開始しない。既存58sessionsは反復利用済みDevelopment。別承認のない保護partitionを開封しない。モデル選択用区間と確認用区間を時間順に分け、前処理/学習score producer/教師成熟/閾値も同じ境界で検証する。

## 📦 現在のblockerと次の方針

非公開引継ぎデータは現在のworkspaceに未配置。GitHubのDELIVERYにはbundle hash/sizeがあり、private本体はGitHubへ保存されていない。公開原本と合成データで監査器・intent extractorを実装/検算し、privateの復元・hash照合が済んだ後に行別監査と有限Sign研究へ進む。記録するのは公開code/定義/集計/hash/所在のみ。RAW、行別私的データ、モデル本体をpublic repoへcommitしない。

新fit0、新閾値選択0、市場性能確認0、Replay0、上流変更0。通常の技術修復はまとめて行い、意味・教師・分割・予算の変更は新しい契約として記録する。各checkpointと終了に実時計JST/UTC、現在地、実行量、blocker、次方針を保存し、actual GETで本文/blob/HEADを検証する。
