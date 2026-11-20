# Phase57 — CI保存エラー修正 / 保存済みEvidence再利用

開始時にPR #587 latest HEADを直接確認: `e11f8af571a03c7e73f79a77c3964752fd109a08`。
Draft / 未merge。対象の失敗runとjobはfailure-inventory.jsonに保存。

6 workflowは測定とauditに成功した後、`test ! -e .../measurement`で失敗していた。
既存の成果物を再測定して同じ保存先へ再保存しようとする、完了済み研究のCI再実行契約の不備。
保存先を削除したり、古いmanifestを新しい結果で上書きしたりしない。

修正は完了済み6研究をread-onlyの保存済みEvidence監査へ移す。
現行checkoutと固定snapshotの既存scientific code / protocol / evidenceのGit object identityを確認する。
変更・削除された既存ファイルがあれば再利用を拒否し、自動再測定へfallbackしない。
新規ファイルはhistorical auditで実行しない。

一部のmanifestは生成当時のworkflow hashを含む。このpinは書き換えない。
元のworkflowと研究codeが実在する固定HEADの別checkoutで、既存の監査器を変更せず実行する。
現行treeの同一性はその前後に別検証する。元の研究判定とSafetyを保持する。
既存のfocused testsを実行し、新しい監査receiptだけをActions artifactへ保存する。
証拠の再利用と、現行wrapperを古いhashで偽装することを混同しない。

再測定、再学習、raw cache復元、provider requestは0。
Entry v2のmodel / decision / metric / report、Frozen Selector、Dictionary Gate、研究thresholdは変更しない。
共通Holdout244・その他sealed領域を追加開封しない。

残るEXIT CC Freeze Auditは、以下の研究Gateを検出して正しくfreezeを拒否している。

- `DIP_REPRICE_OPPORTUNITY_timeOrdered_plus5`
- `contractLaterBarOrder`
- `exactRoutedLedger`

Candidate Cは`NEW_LONG_EXIT_CANDIDATE_C_KILL`、freezeAllowed=falseを維持する。
このGateをCI green化のために緩和・削除しない。EXIT policy修正や新規EXIT研究にも進まない。
全体greenとCI保存エラー修正完了は区別して報告する。

LONG-only / cash-equity-only。executionAllowed、brokerWriteAllowed、excelOrderWriteAllowed、
rssOrderFunctionAllowed、liveTradingAllowed、paperTradingAllowed、automaticPromotionAllowed、
productionUpdateAllowed、transmittedは全てfalse。main mergeなし。
