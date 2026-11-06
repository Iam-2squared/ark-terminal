# Ark Terminal No.1.2 — 最小限のWindows手動確認までの引き継ぎ (2026-10-11)

## 自動で完了した範囲

GitHub Draft PR #592: No.1.1とは**別の実運用候補研究ブランチ**。Frozen No.1.1 / main / 統合PR #591は変更なし。
- 未来情報を使わない購入前候補ゲート。State9のPULLBACK/SHARP_DROP除外と本人EXTERNAL保有保護。
- 独立した合成現物LONG/MAX3/100株/現金予約・約定台帳。SELL_INTENTで資金・枠を開放せず、SELL_FILLが最初に観測された後の新規BUYを停止。
- 合成State9 SHARP_DROP緊急EXIT候補とStructural Controlの先行優先順位。
- 公式2026/3/30 MarketSpeed II RSS仕様に沿ったRssOrderIDList（発注ID→注文番号）・RssOrderList（累積約定数量）の合成突合。外部個人注文はArkに帰属させない。
- 15:20時刻、ゼロ現金、約定前提の不一致、部分約定、ID重複をfail-closedでテスト。
- Windows / Linux 各32テストPASS（GitHub Actions run 38131153086）。
- 実注文・Excel編集・Safety解除・追加の手動許可はゼロ。

## 機能実装と実取引の区別

この版の pre-BUY score/threshold ratio は**研究用の新しい順位付け**で、Frozen No.1.1 H2/H3/H5 ML/R0ではない。元の凍結研究の損益を引き継ぐ根拠はない。2025分足があっても、正しいFirst Entryスコア/閾値および因果的に観測したState9 Primaryがない限り、No.1.2の実際の取引成績は推定しない。

認証未了：
1. Selector/First Entry/State9/EXITの本物のオンライン特徴量と予測器（観測時刻の証拠付き）。過去のOOFスコアやteacherから実時間スコアを捏造しない。
2. MarketSpeed II RSS市場データの実機受信と、時刻・未確定5分足・ソース障害の検証。
3. 実際のBroker RSS発注ID・注文番号・約定数量・現金/保有/注文中資金の物理照合。RssExecutionListには親注文ID・一意約定IDが存在しないため、特定取引帰属には注文ID経路の検証が必須。
4. No.1.2としての事前登録済み独立OOS/forward経済検証（元No.1.1研究成績をそのまま使用しない）。
5. 誤発注・接続断・キャンセル・部分約定・安全復旧の実機E2E。既存Safety Ledger停止状態を自動削除しない。

これらは**ユーザーによる追加の承認スイッチではなく、実装/一次データ/テストが未完成な部分**。証券会社への実注文送信を伴う検証はユーザーの明示的な実機操作と証券会社の提供する適切な手段が必要。無資金状態で新規資金入金を要求しない。

## 次の最小PC工程（まだ実行しない）

MarketSpeed II起動、Excel RSS注文許可OFFを維持。Ark旧READ ONLY監視はそのまま使用可能。次の新規No.1.2実機研究ゲートでは、別の隔離worktreeの診断ツールから**口座・保有金額を公開せず**、利用可能な市場RSS・First Entry/State9情報・タイムスタンプの実在を確認する。利用できなければ入力ソース不足のまま開発設計へ戻し、架空のLIVE証明やExcel発注許可ONで埋めない。

原本方針：現物LONG/MAX3/100株・個人株保護・当日最初の合法SELL約定後BUY停止は維持。本番がすべて実装・検証された時点での**唯一の手動取引許可はExcel RSS注文利用ON/OFF**。まだその段階ではない。
