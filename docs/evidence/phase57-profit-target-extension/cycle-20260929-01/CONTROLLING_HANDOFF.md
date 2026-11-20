# 🔒 Profit Target + Exceptional Extension 引き継ぎ

保存JST: 2026-09-29T17:08:10+09:00。開始basis HEAD `6eb22edb57dab19d7d63ea9b71adc99a4a843ebc`。Draft PR #587、研究branchのみ。

14 main policy-arm行は計算・保存されたが、初回batchは後処理 NameError で `INVALID_RUN_POSTPROCESS_EXCEPTION`。保存行からの後処理を追加し、別コードで14 arm / 11,298行を照合して不一致0。失敗記録と暫定High表を消さず、auctionを含むHigh訂正表を追加。mainや本番へは採用しない。

旧funded +3%同一既知mask: IM 75/79、候補−R50 +¥127,600、候補絶対 −¥13,537。R1 30/32、差 −¥73,200、候補絶対 +¥67,379。欠測と広いCI、資金配分固定比較を伴う記述値。High到達はIM44/79、R1 18/32で旧報告と一致。Target時点State/Signalの値joinは未証明。旧案Bは `DEPRIORITIZED_BY_OPERATOR / NOT_EXPERIMENTALLY_REJECTED`。旧 `DESIGN_ONLY_EXPERIMENT_BLOCKED`を保持。

次は `MISSING_EVIDENCE_REQUEST.json` と `NEXT_FINITE_EXPERIMENT_DRAFT.json`。precommit/保存行を再実行しない。main予算0、独立照合予算0。新しい確認・延長・統合には別の有限仕様と承認が必要。結果commit後の保存receiptに本commitを記す。

公開Evidenceのraw bar出来高・売買代金数値は掲載前に除去。`DATA_PUBLICATION_RECEIPT.json`を参照。
