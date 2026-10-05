# V5-Anchored Slot3 — 開始監査と固定STOP

V5を超えたかは測定不能です。指示書内の介入条件と必須canaryが矛盾しているため、仕様precommit・推論・Replay前で停止しました。V5 Championは維持し、D/DRの経済失敗とは判定していません。

記録時刻：2026-10-05T17:50:38.420814+09:00。状態：`V5_ANCHOR_CONTRACT_FAIL / SPECIFICATION_BLOCKED`。終了：`CAPITAL_V5_ANCHOR_P11_CLOSURE_FIXED_STOP`。

## 100万円 → 20 sessions

| 指標 | 保存V5参考値 | D | DR |
|---|---:|---|---|
| 最小 | 1,082,366円 | 未測定 | 未測定 |
| 平均 | 1,190,646円 | 未測定 | 未測定 |
| 中央値 | 1,199,154円 | 未測定 | 未測定 |
| 最大 | 1,297,031円 | 未測定 | 未測定 |
| 200万円到達 | 0/19 | 未評価 | 未評価 |
| V5との差・全19窓Gate | 基準 | 未評価 | 未評価 |

V5値は原指示書に記載された保存結果の参考表示で、今回の新計算ではありません。連結曲線を20 sessionsずつ切り、開始前EOD資産から100万円へ正規化した値です。100万円・保有ゼロへ各窓resetしたReplayではありません。

## 停止理由・最小修正案

SC01（必須解決）：第11節、321–329行は「既存保有数＋先行native BUY成功予定数=2、native admission index3、100株以上、4軸LOW」ならBUYを見送ると定めます。第23節B、648行は「既存0/1ではdirect veto0」を要求します。

例えば既存保有1件・同batchの先行BUY成功予定1件・次が100株以上のnative予定Slot3・4軸LOWの場合、第11節は見送りを要求し、第23節は見送りを禁止します。既存0件＋先行成功予定2件でも同じ矛盾です。V5原本のgateが既存保有＋native pendingを使用し、実funded slotがBUY成功順で決まることもコードで確認しました。DのactionだけでなくDRのtoken発行と回収経路にも影響します。

推奨する最小修正案は、第11節のpolicyを保ち、第23節の該当行を「native BUY成功予定順を含む実際予定Slot1/2ではdirect veto0。既存0/1でも本当の予定Slot3に達した場合は第11節を適用」へ明確化することです。未適用です。もしbatch開始時0/1件には一切介入しない意図なら、第11節にその条件を明示する必要があり、policy範囲の変更になります。

SC02（明確化）：第23節の「exactmedian HIGH」は「第9節のrank fractionがexact1/2ならHIGH」と記す必要があります。raw scoreのtraining中央値にはtiesがあり、例えばT=[0.1,0.2,0.2,0.2,0.3]、s=0.2のrankは2/6でLOWです。第9節のstrict-less-count式や境界を変更する提案ではありません。

## 原本・重複・入力監査

- 指定branchのactual HEADは`14b1910d80335fdf48421383ebf36981ae8f8cfd`。直親は指定V5の`710656491be06235901b45c50a8b5cbd714ba4eb`でした。現branchは設計handoffのみで、実行claim・結果はありません。
- 旧v12の別仕様designも確認しました。開始保有2件限定、0.75回収境界、条件付きcash-reset20を含む旧仕様は継承していません。旧v12も設計のみで、重複Replayはありません。
- 添付指示書は44,058bytes、SHA256=`088f7e90aae89d25feab741ea04211c92f8f175e9603a77a0d800fdf55674ab6`。原文を変更せず保存しました。
- 10 unique ZIP、manifest内705 member hash照合で不一致0。V5 SOURCE_HASHES内144 source照合で不一致0。v11R1/nested V5の内容hashは指示書と一致し、添付v9とnested v9も同一でした。
- V5の必須artifact・台帳・凍結モデル群の所在を確認。GitHubから取得したV5 CLOSURE、slot_policy、allocation、replayはprivate原本とbyte完全一致。2 CSVは既存receiptで記録されたCRLF→LF変換だけで一致しました。
- score/current-native/causal coverage、変更経路のSELL/MTM source、V5 OFF互換性は未評価です。入力の所在・hash確認をruntime認証PASSと扱っていません。
- 画像は現在の添付先から開けました。画像の数値を正確なGateへ流用していません。

## 未実行と固定結論

原本監査と独立仕様レビューを完了しました。実装・canary・OFF復元・D/DR・独立再構築は実行していません。勝率、Loser、Medium/U5/U10、protected100 identities、minute MaxDD、19窓非劣化は全て未評価です。未測定値を0やNO_GOへ置き換えていません。

新fit0、モデル推論0、Control検証Replay0、candidate Replay0、独立再構築Replay0、score/PnL cross-tab0、provider取得0、保護データ開封0、注文0、main merge0、force push0、Champion変更0。全Safety false。

原指示書・原本・旧失敗記録は維持。`activeCapitalChampion=V5`、`selectedCapitalCandidate=null`、`championUpdated=false`。次方針はSC01を明示的に解決しSC02を明確化した別指示書・別cycleです。今回の入力監査は同hashなら再利用できます。仕様変更・自動再開・追加候補研究は行わず固定STOPとします。
