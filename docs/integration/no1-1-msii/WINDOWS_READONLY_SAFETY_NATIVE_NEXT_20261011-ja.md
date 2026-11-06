# No.1.1 — Windows READ ONLY検証 / Safety履歴 / 次のNative工程 (2026-10-11 JST)

対象: Draft PR #591 / integration/no1-1-msii-cash-locked-v1。
研究Freeze: 10c94c92c4bd2a59a22744667fd0210252602df4（不変）。

## 実機確認（ユーザー提供の非機密ログ・画面）

- V3 Excel RSS SnapshotはV2の33.25秒に対してV3が2.86秒。同時間帯V2/V3照合8/8項目一致。
- 実機の注文0件・約定0件だけであり、注文行や部分約定の情報一致はまだ証明されていない。
- RSS4ステータスはCapacity完了、Orders/Executions/Positions配信中。公式Brokerの真の受信時刻ではなく、RSS状態セルの観測。actualFeedTimestampCertified=false。
- 元のCapital/Ownership GateはREAD_ONLY_CAPITAL_PREVIEWを返した。個人保有EXTERNAL 1件、Ark管理0件を区別。
- ワンクリックUI2 localhost起動、30秒自動更新、モデル更新、6/6画面表示を実機で確認。Snapshot FRESH、Refresh Loop ACTIVEを観測。
- SELECTORのnativeライブ候補、PERFORMANCE、G6-G10ライブEvent、注文のBroker照合はUNAVAILABLE。Total Assets未認証は推定表示しない。
- Excel RSS注文許可OFF、全注文mutation FALSE、実注文なし。

## プライベートSafety Ledgerの非機密診断結果

- KILL_SWITCH_LATCHED
- SAFETY_FAULT_COUNT=3
- RESTART_STATE_UNVERIFIED — 初期の安全停止履歴
- READ_ONLY_CAPTURE_FAILED — 過去のRSS取得失敗履歴
- CAPITAL_OR_OWNERSHIP_GATE_BLOCKED — 過去の口座/資金Gate失敗履歴

元のSafety Ledgerは整合性検査にPASSしたが、ラッチした失敗は残っている。最新のREAD ONLY Gate PASSはこれらの問題が現在発生中だという根拠ではなく、同時にSafety解除の根拠でもない。ファイルの削除・編集・自動リセットは禁止。

## Nativeライブ接続の進行条件

1. 凍結したNo.1.1研究原本を変更せず、Selector、State9 Primary、First Entry、EXIT、Capital V5 MAX3 S/A/B Slot Reserve、H2/H3/H5、ML R0 のnative実装/モデル/必要な市場バーと入力系統を照合。
2. Research Freezeの定義やSynthetic Intentをそのまま本番native Decision Eventとして流用しない。元のNo.1.1研究JSONは実稼働のライブ発行器ではない。
3. Yahoo等の確定足、MarketSpeed II市場RSSの観測時刻、Broker真の受信時刻は分離し、未来情報や到着前情報を使わないREAD ONLYイベント経路を認証する。生データ不足はUNAVAILABLEで停止。
4. EntryでPULLBACK/SHARP_DROP除外、100株、現物LONG、MAX3、本人EXTERNAL保有のEXIT対象除外、同銘柄Ark BUY禁止を維持。当日の最初の合法SELL fill後はBUY禁止。SELL intentだけでは禁止を発火しない。
5. UI2には立証できたnativeイベントだけを表示。G6-G10、注文ID、約定、現金/Slot照合とMarketSpeed実機データがないうちは本番準備済みと見なさない。
6. 現在のNo11SafetyLedger.explicitSafetyResetは追加手動承認が必要な暫定実装。最終設計はExcel RSS注文許可1つのみをユーザーの手動許可にする方針と一致させる。ただし履歴を無条件に消さず、検証された自動復旧条件が未完成なら停止維持。
7. 取引時間中の市場RSSの真の到着時刻、障害/再接続、実約定/部分約定/資金のWindows認証が未実施。

## 不変条件

Draft PR、main未マージ、Frozen不変、productionReady=false、executionAllowed=false、Excel発注許可OFF。真のLive feed・native判断・Broker注文往復の未認証をUI2やCI PASSで代用しない。

この文書には個人の銘柄、口座金額、ポジション数量、Private Ledger原本を含めない。
