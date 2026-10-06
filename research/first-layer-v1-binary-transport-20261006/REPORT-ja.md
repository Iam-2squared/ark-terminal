最終status: BLOCKED_DATA_OR_LINEAGE / RAW_BINARY_READBACK_BLOCKED。

GitHub上の原本欠落とは判断していません。今回はgzipをtextとしてfetchしていません。

試したbinary-safe取得方法:
1. canonical GitHubへpartial clone（blob:none、no checkout）。private repo認証がrunnerにないため、fatal: could not read Username。exit128。
2. runner Git gatewayへ同じpartial clone。認証を利用できず、同じUsernameエラー。exit128。Git objectsがないためcheckoutには進めていません。
3. GitHub plugin能力の確認。ordinary Git object用clone/checkout/materialize/download機能なし。binary downloadは既存Actions artifactとprivate画像添付のみ。C全3runsのartifact0件。対象gzipには利用不能。

GitHub connectorの認証はrunner Gitへ共有されていません。providerへの再取得、加工、原本の書換、text fetch反復、remote workflow作成は0。

対象4原本354283802 expected bytesに対し、本文回収0/4・actual0 bytes。SHA256/gzip未実行。RAW blockerは解除していません。native cutoff/order/bar/session/lunch/State入力/continuity QAは前提未達のため続行していません。

ユーザー手動uploadによる解除は条件付きで可能です。既存C repoの4つの.csv.gzをそのまま受領し、runnerで全binary本文を読めれば、全4件のbytes/SHA256/gzip完全一致を確認後にRAW blockerを解除できます。その後のnative QAまでPASSした場合のみPHASE0_RECOVERY_PASS_READY_FOR_PRECOMMITでSTOPします。

model/preprocessing fit・threshold・CAL・TEST・provider・Capital・orders・production・main変更・force pushはすべて0。既存checkpoint/Freeze/Entry/teacher/Exposure/State-Core設計を保持し、新しいresearch branchへこの取得経路の確認結果のみを保存します。
