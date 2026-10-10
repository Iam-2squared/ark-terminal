# Economic LONG Selector v2 — DESIGN ONLY / NOT IMPLEMENTED

診断根拠：既存スコアの経済的な単調順位付けの弱さと、選出時の高vol・下落後への集中。観測条件付き分析であり、欠測を含む元Top5全母集団のalphaは未同定。再設計による改善は未検証。この設計はFrozen Selectorの解除・変更を許可しない。

1. **目的**：選出時点のPIT情報で、基準の即時実行価格から固定horizonの実行可能価格までのafter-cost forward valueを順位付けする。現在のsaved OPEN/CLOSEはreference markであり実際の約定価格ではない。データ契約が実行可能性を裏付けるまではexecutable label完成と呼ばない。
2. **target候補（未実装）**：既存30分を比較anchorとして固定net terminal returnを中心にする。 downside/MAEやtail-riskを補助headまたは制約として扱う選択肢を検討し、重み・形式はfit前に一案へprecommitする。未来MFE/MAEは教師ラベル候補のみで、特徴・判定時情報へ渡さない。MFE自体を取れる利益として最適化しない。
3. **horizon / multi-horizon**：5/15/30/60/120分を結果後に選び直す試験はしない。将来multi-horizon objectiveを採るなら、horizonと重みを次の実験前に固定し、現行30分baselineとの比較を残す。今回どの組合せも実装・評価しない。
4. **cost**：今回のcanonical5bpsは比較契約であり実際の全cost保証ではない。将来は手数料・spread・slippage・impactの利用可能な測定契約を別途固定。10/20bps sensitivityを事前定義して保持。結果を良くするcost変更は禁止。
5. **ranking / calibration / abstention**：最終net価値に対するrankingを優先。calibrationは許可されたDevelopment分割内のout-of-fold予測に限る設計とし、no-trade/abstentionも事前宣言・固定budgetの別候補とする。今回threshold、Top-K、cadence、universeを変更しない。
6. **liquidity / tick**：Decision時点で利用可能な情報だけ。実際のtick scheduleがなければ未評価。将来可観測性・実行可能性ゲートを加える案はSelector/universe変更なので、明示承認と新protocolを要する。未来のバー欠測を銘柄採用条件にしない。
7. **missingness**：terminal endpointと経路を分離。原Top5母集団、観測subset、欠測率を保存する。補完ゼロ・勝者filter・後日の生存銘柄listを使わない。MNARを無視した単一の点推定で全母集団の優位性を主張しない。観測改善はラベル改変ではなくsource/data-contract課題として扱う。
8. **null controls**：Frozen Selector、同一PIT universeの固定seed Random Top5、canonical Momentum30を同条件で残す。Repeated Randomを用いる場合はseed list/回数をfit前に固定し、取得可能性に合わせて再抽選しない。時間・sessionを同じにしcluster uncertaintyとtail感度を必須にする。
9. **分割**：既存76 Developmentは既に結果露出済みで、C+D fitted modelも含む。未知性能とは呼ばない。将来のDevelopment train/selection/calibrationを時系列で分離し、horizonの重複labelをpurgeする設計をprecommitする。Validation/DEV TEST/Fresh/OOSは今回未開封のまま。開封順・試行budgetは別途承認までTBD。
10. **Fresh budget**：今回の承認済み新規取得数0、今回使用数0。次工程のsession数・provider request数・料金・splitを事前確定してから別途許可を得る。今回予算を消費しない。
11. **完了条件（将来）**：source/PIT/observabilityを先に監査し、固定基準に対するafter-cost差・absolute net・downside・tail・capacityを事前基準で判定する。改善後もEntry/EXIT/Capital/Portfolio統合と未知評価は別gate。CI greenを性能改善としない。

**未開始**：target実装、training、fitting、hyperparameter search、feature selection、threshold search、新モデルmeasurement、Validation/OOS、Entry/EXIT/Capital。設計書のみでSTOP。
