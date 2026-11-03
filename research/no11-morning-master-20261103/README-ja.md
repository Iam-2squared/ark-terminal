# No.1.1 選定済み銘柄のマスター準備・当日入力接続

## 変更範囲

4,328銘柄の再調査、429銘柄の日足再取得、選定済み47銘柄の前日1分足再取得は行わない。既存のFrozenモデル・Selector・Capital・EXIT・RSS買付可能額方式、ローカル修正、ランチャー設定は変更しない。追加コードは専用privateフォルダーで動かす。

`morning_master.py` は二つの段階を持つ。

### prepare：前日夜に実行できる処理

指定されたChart50/G1 mask/前日archive stageのハッシュ、対象日、選定集合、保存済みcheckpointへの結び付きを確認する。これは取得済みファイルの読取りであり、RSS再収集ではない。

既存の `no11_auto_master_sources.py` をGit blob固定で再利用し、**Chart50に既に選ばれた銘柄だけ**のJPX銘柄検索結果と、最新の近接権利日一覧を取得する。公開根拠の原本bytesをSHA256名でprivate保存し、銘柄属性・業種・近接権利イベントの観測結果を保存する。銘柄リストを変えず、勝手な再ランキング・代替銘柄の補充をしない。1銘柄または権利資料が取得できなくても、取得済み原本と不足理由を残す。

成果物は `ARK_NO11_MORNING_PUBLIC_SOURCE_BASIS_V1` と `ARK_NO11_MORNING_MASTER_HANDOFF_V1`。**正式なdatedMasterでも、EXTERNALLY_REVIEWED証拠でもない。** 近接権利日一覧に記載がないだけで全企業行動の不存在や価格基準を認定しない。現在のJPX検索画面からの基本属性観測も、別途の完全な注意情報・企業行動レビューの代用とはしない。

仕様ファイルはsessionDateと次の絶対パス：

- engineRoot、chartReceipt、passMask、previousStage、previousCaptureDir
- runtimeRoot、h235ModelRoot、weeklySourceRun、settingsFile、outputRoot

実行例：

```powershell
& $python -B -X utf8 $runner prepare --spec $specFile
```

`Prepare-MorningMaster.ps1 -SpecFile ...` は固定Gitソースをprivateに取得、単体テスト後、XLS読取ライブラリxlrd 2.0.2をハッシュ指定・依存追加なし・private `--target` へ配置してprepareを実行する。既存のP1固定Python環境へのインストール・更新はしない。

### finalize：実際の対象日に行う処理

既存形式の真正な `ARK_NO11_SESSION_SECURITY_EVIDENCE_V1` と、その根拠原本フォルダーを受け取る。prepareの未確認資料を自動的にレビュー済みに変更しない。

確認済み根拠がある場合、既存 `Capture-No11SessionReferenceReadOnly.ps1` で選定済み銘柄の当日RSS基準値を取得する。明示的な `--reference-file` がある場合はそれを使用する。固定の9時制限を新設しないが、当日日付の実RSS値が得られなければnative validatorが拒否する。原本collectorの2ブック条件を維持する。発注用の3冊目を勝手に開閉しない。

続いて既存 `no11_prepare_received_inputs.prepare` に、当日参照情報・確認済み根拠・保存済み前日archive・既存モデル保存先を渡し、datedMaster → previousContext → bootstrap-ready-inputsを連続生成する。前日1分足collectorや全銘柄exporter、StartShadowは呼ばない。

```powershell
& $python -B -X utf8 $runner finalize --handoff $handoff `
  --security-evidence $reviewedEvidence --evidence-documents $documents
```

生成結果 `MORNING_PREPARED_BOOTSTRAP` は既存のRSS LIVE設定接続ツールの入力となる。この追加コードは物理的なExcel発注先設定、独立した根拠、当日発注承認を捏造しない。**LIVE設定登録・Trade起動・実発注は行わない。** これらは依然として別の実接続工程。

## 検証範囲

15件のオフライン単体テストは対象集合、日付、原本改変、未確認証拠の拒否、private出力、既存native関数への引数接続を検証する。公開取得とnative master生成はテスト中はfixture/mockであり、実JPXやユーザーの非公開モデル、RSS、実発注が成功した証明ではない。

Windows/Linux GitHub Actionsで単体テストを実行する。実際の公開データ収集はprepareをユーザーPCで実行した結果によって判定する。`MASTER_SOURCE_PREP=PARTIAL_UNREVIEWED` を完了・正式マスターとして扱わない。
