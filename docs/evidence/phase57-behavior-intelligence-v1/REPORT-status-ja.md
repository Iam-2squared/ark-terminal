# Behavior Intelligence — 初回測定の未成立診断

**PRIMARY_COMPARISON_NOT_ESTIMABLE / S1〜S4すべてINCONCLUSIVE。依頼された研究は未完了、Entry/EXITへの移行はBLOCKED。**

[初回CIレポート](ci-result/REPORT-ja.md)と図・実装・学習済みscore・回帰証拠は保存済み。ただし、CIの成功は主比較の成立を意味しない。以下の診断を最優先で読むこと。

| 評価の段階 | 候補数 |
|---|---:|
| evaluation20日・全候補 | 1,000 |
| 30分MAEが利用可能 | 515 |
| 60分MAEが利用可能 | 349 |
| session-end完全pathが利用可能 | 0 |
| 主比較の共通cohort（30分＋session-end） | 0 |
| 15:25開始slotが欠測 | 1,000 |
| 欠測がそのslotだけ | 471 |
| その他の欠測slotも存在 | 529 |

主比較0件の原因は評価器・保存pathのsession境界の不一致と欠測。今回取り込んだ旧anatomyのregular_slotsは2024-11-05以降、15:25〜15:30にも通常5分足を要求する。一方、既存causal Readerは連続取引barの終端を15:25とし、保存pathは15:25開始slotをmissingとしている。評価20日は全て11月5日以降で、この条件だけで全1,000件が除外された。さらに529件には別slotの欠測もある。

これはWHO/RECENT/NOWの予測力が0という結果ではない。30分で測れる515件までsession-end完全pathとの積集合で除外したため、下落率・Opportunity保持率・有用性を比較できていない。最初の主比較条件を設定した実装側の問題として記録する。

WHOには別の時間上の制約もある。固定候補55日は2024年9〜12月であり、正式Temporal判定が利用可能になる2025-08-21終了後より前。最終234銘柄/293traitを過去へbackfillせず、正式値は全てUNAVAILABLEに維持した。そのためWHOの正式trait値の情報価値は未検証。S4に保持したconfidence/uncertainty等の過去状態を、信頼可能な性格値と同一視しない。

今回使用した候補台帳は許可144日との共通55日・2,750候補のみ（fit30日/embargo5日/evaluation20日）。残89日の固定Selector再推論台帳はまだ作っていない。55日に絞ったことで依頼の144日全体を完了したとは扱わない。

今回は結果を見てwindow・Gate・minimum-N・feature・modelを変更して救済していない。初回測定を失敗Evidenceとして固定し、原因の件数・代表例を[zero-sample-diagnostic.json](zero-sample-diagnostic.json)へ追記した。

残作業は、通常取引と引けauctionの扱い・正規timestamp・欠測理由を原データと契約で監査し、研究上の条件緩和とソフトウェア修正を区別して修正仕様を固定すること。その後に同じ固定score/候補で修正版評価を再生成する。89日の候補再推論とWHOの時間上の識別可能性も別途未解決。現時点で情報源の勝者を選べない。

検証: focused257 PASS、回帰2,949 PASS、substrate/measurementそれぞれ2回生成一致。Common Holdout244とその他sealedの追加開封0。安全9フラグ全false、Frozen SelectorとDictionary Gateは変更なし、main未merge、Entry/EXIT学習未開始。

CI: https://github.com/Iam-2squared/ark-terminal/actions/runs/35492365603

実行checkout HEADは`ea43a10264141b869a46a14756ead68ebc7df2da`。初回ci-receiptの`9ef190d...`はGitHubのPR merge用GITHUB_SHAが入ったため、この追記で訂正する。初回Evidence保存HEADは`f1e3d9e15297f081d09403fb5ad632403ea87e24`。PR587はDraft・未merge。
