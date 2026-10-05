# 🧭 次のCapital判断 — 1個の草案、実装未承認

判定: **R_SPECTRUM_INCONCLUSIVE**。Economic relevanceとsupportは確認できたが、悪いR帯と良いR帯を既存causal情報で安全に選び分ける根拠が不足している。今回のAUROCを新Gate承認へ変換しない。

検討する草案は **初回BUY内の100株を超える追加lotへの集中上限** の1個だけ。変更箇所はCapitalの整数数量・配分cap。全Entryに共通の上限候補を別Workで事前に固定し、V5の同じ購入ゲート、同じtarget、MAX3、最低lot、cash・約定制約の下で適用する案。現時点では上限値・式・trade-off受容条件は未決であり、policyとして固定済みとは扱わない。

観測上のdonor課題はRNEG、特にRN1〜RN3と深い負tailへの多lot投入。receiver課題はR1〜R10以上を含む既存購入適格Entryへの配分。R3/R5など単一thresholdを新Gateにはしない。小幅利益も一律悪い候補としない。これらのR帯は将来outcomeによる診断名であり、runtimeの対象選定条件ではない。

元の100株を超える実funded部分とnative water-fill部分の金額・損益をACTUAL_LOT_TRANCHE_FLOW.jsonへ分離した。損失だけでなく大きな利益も追加lotから出ており、上限を置けばmedian wealthが上がるとは示せていない。縮小で解放できるのはcashで、保有slotではない。残したcashは、その時点の同batchまたは後続の新しいFrozen Entryが既存ゲートを通過した場合にだけ使える。過去rejectの復活、早売り、置換、買い増し、Reserve/Rank/Quality Pareto/MRET throttleの再開は行わない。

この草案は、reject済みV5.1のpP順lot優先を再試行する案ではない。高pP/高Qualityは正tailと負tailの両方に順位情報があるため、scoreだけで増額する仮説を支持しない。MRET反転・新weight・新thresholdで救済しない。MRET absolute-loss defenseはINCONCLUSIVEを維持する。

**V5.2を直ちに実装・Replayする根拠は不足。** 別Workでこの追加lot集中機構のcash→受け手・利益減少リスクを固定仕様へ具体化できたときに、初めて評価を検討する。今回は設計仮説1個、実装candidate0、Replay0で閉じる。100万円→200万円の改善・回収利益は未証明。
